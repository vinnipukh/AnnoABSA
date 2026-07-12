# Phase 4 — Completion Report: Live Compare Mode

**Date:** 2026-07-12
**Goal:** Add a Live Compare mode alongside the existing CSV-based Compare mode, where Model A and Model B each have independently configurable provider, model, prompt, and temperature. The Helper Agent also gets its own config. A mode selector (CSV vs Live) controls which data populates the comparison columns.
**Status:** ✅ Complete (4 tasks, 13 files)

---

## What this is (for the academic reader)

The original AnnoABSA Compare mode loads pre-computed triplets from CSV files. While useful for comparing two static model outputs, it does not allow interactive experimentation — changing prompts, adjusting temperature, or comparing different models live. Phase 4 adds a **Live Compare mode** that turns each comparison column into an on-demand LLM prediction engine, each with its own provider, model, prompt, and temperature settings.

This enables a research workflow where an annotator can:
- Iterate on prompt engineering and immediately see how the output changes
- Compare two different LLMs side by side (e.g., deepseek-v4-flash vs deepseek-v4-pro)
- Adjust sampling temperature per model to observe its effect on triplet quality
- Configure the Helper Agent independently with its own provider, model, prompt, and temperature

The two modes (CSV and Live) are mutually exclusive — a radio toggle in the Settings panel selects which mode the Compare view uses. In CSV mode, the app works exactly as before (no regression). In Live mode, each column shows a "Run" button that triggers a live prediction using that model's config.

Per-model config follows **no-fallback semantics**: if a model's provider or model name is blank, the endpoint returns HTTP 400 with a descriptive error. No implicit merging with global defaults occurs. This design principle was confirmed by the user: *"There should be no 'global model' for the user. If it's blank, it should not work. As simple as that."*

A typed `AppActions` interface (15 methods) is wired from `App.tsx` → `HelperAgentChatbox` via `useRef`, laying the architectural foundation for a future autopilot mode.

---

## Task breakdown

| Task | Scope | Files | Status |
|---|---|---|---|
| **Task 1** | Core implementation: temperature param, config keys, live_prediction endpoint, agent_chat updates, validate_per_model_config, Settings interface, SettingsPanel UI, App.tsx live state, ModelTripletColumn Run button, types.ts + AppActions | 9 files, +630 lines | ✅ Complete |
| **Task 2** | Integration tests: `tests/test_live_prediction.py` with FastAPI TestClient, mocked provider, 19 tests covering validation, happy path, config propagation, position data | 1 file, +363 lines | ✅ Complete |
| **Task 3** | Doc updates: `backend_reference.md`, `architecture_map.md`, `ProjectPrimer.md`, `testcases.md` — line counts, endpoint counts, Live Prediction flow diagram, Tier 9 test cases, Phase 4 config keys | 4 doc files | ✅ Complete |
| **Task 4** | cli.py sync: add 13 Phase 4 config keys to `ABSAAnnotatorConfig.__init__` default dict, verify template constant dedup pattern | 1 file, +14 lines | ✅ Complete |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Settings Panel                            │
│  ┌─ Compare Mode ────────┐  ┌─ Model A Config (collapsible) ──┐ │
│  │  ○ CSV  ● Live        │  │  Provider │ Model │ Temp │ Prompt│ │
│  └───────────────────────┘  └──────────────────────────────────┘ │
│                              ┌─ Model B Config (collapsible) ──┐ │
│                              │  Provider │ Model │ Temp │ Prompt│ │
│                              └──────────────────────────────────┘ │
│                              ┌─ Helper Agent (collapsible) ─────┐ │
│                              │  Provider │ Model │ Temp │ Prompt│ │
│                              └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
          │ PATCH /settings  │  GET /settings
          ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│  CONFIG_DATA (in-memory)  ←→  config JSON file (disk)            │
│                                                                  │
│  Keys added: compare_mode, model_a_*, model_b_*, helper_agent_*  │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼  GET /live_prediction/{idx}?role=model_a|model_b
┌──────────────────────────────────────────────────────────────────┐
│  get_live_prediction()                                           │
│  1. Read per-model config from CONFIG_DATA (no fallback)         │
│  2. validate_per_model_config(role, config)                      │
│     → provider + model must be non-None                          │
│     → provider's global keys (openai_key, etc.) validated        │
│  3. get_provider(role_provider, CONFIG_DATA)                     │
│  4. provider.predict(temperature=role_temperature,               │
│                      prompt_template=role_prompt)                │
│  5. Add position data if save_phrase_positions is enabled        │
│  6. Return predictions                                           │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼  Frontend
┌──────────────────────────────────────────────────────────────────┐
│  App.tsx — Live Compare Mode                                     │
│                                                                  │
│  ┌─ Model A ──────┐    ┌─ Center ──┐    ┌─ Model B ──────┐      │
│  │ [▶ Run]         │    │ Review    │    │ [▶ Run]         │      │
│  │ (after click)   │    │ text      │    │ (after click)   │      │
│  │ triplets appear │    │ Manual    │    │ triplets appear │      │
│  └─────────────────┘    │ triplets  │    └─────────────────┘      │
│                         └───────────┘                             │
│                                                                  │
│  ┌─ Autopilot actions (AppActions ref) ──────────────────────┐   │
│  │  navigateTo, nextReview, switchMode, selectTriplet, save  │   │
│  │  → passed to HelperAgentChatbox via useRef                │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Files changed (13 files, +1,007 / −63 lines)

### Task 1 — Core implementation

| File | Δ | What changed |
|---|---|---|
| `services/llm_providers.py` | +53 / −5 | Added `temperature` param to all 4 `predict()` methods + protocol + `predict_llm()`. Replaced hardcoded `temperature=0.0` with parameter in Ollama, OpenAI, Anthropic, and VLLM providers. Added `validate_per_model_config(role, config)`. |
| `main.py` | +167 / −8 | Added 13 config keys to `load_config()` defaults. Exposed all in `GET /settings`. Added 85-line `GET /live_prediction/{data_idx}` endpoint. Modified `agent_chat()` to read per-agent config. |
| `frontend/src/types.ts` | +42 / −0 | Extended `Settings` with 13 new fields. Added `AppActions` interface (15 methods) for autopilot. |
| `frontend/src/App.tsx` | +151 / −16 | Added live state, fetch function, conditional rendering by `compare_mode`, AppActions `useMemo`. |
| `frontend/src/components/SettingsPanel.tsx` | +120 / −0 | Added `ModelConfigSection` (provider/model/temp/prompt collapse), compare mode selector (CSV/Live), 3 collapsible sections. |
| `frontend/src/components/ModelTripletColumn.tsx` | +47 / −10 | Added `onRunPrediction` + `isPredicting` props, Run button in empty state with SVG play icon + spinner. |
| `frontend/src/components/HelperAgentChatbox.tsx` | +13 / −1 | Added optional `appActions` prop, stored in `useRef`. |

### Task 2 — Integration tests

| File | Δ | What changed |
|---|---|---|
| `tests/test_live_prediction.py` | +363 / −0 | 19 tests with TestClient: validation (11), happy path (3), config propagation (4), position data (1). |

### Task 3 — Documentation

| File | Δ | What changed |
|---|---|---|
| `agentdocs/session_reports/backend_reference.md` | ~+20 | Line counts (main.py ~1206, llm_providers.py ~557), validate_per_model_config entry, live_prediction endpoint, provider table with temperature. |
| `docs/architecture_map.md` | ~+30 | Endpoint count 10→11, Live Prediction flow diagram, temperature in provider interface, file-to-task map updates, 3 new landmines. |
| `agentdocs/ProjectPrimer.md` | ~+40 | Stack descriptions, test count 93→124, Live Compare Mode how-to-run, Phase 4 config keys table. |
| `tests/testcases.md` | ~+25 | Tier 9 (10 manual cases LC1–LC10), coverage summary updated to 124+27=151, test file list updated. |

### Task 4 — cli.py sync

| File | Δ | What changed |
|---|---|---|
| `cli.py` | +14 / −0 | Added 13 Phase 4 config keys to `ABSAAnnotatorConfig.__init__` default dict. |

---

## New config keys

All stored in `CONFIG_DATA`, persisted to JSON config file, exposed via `GET /settings`, mutable via `PATCH /settings`.

| Key | Type | Default | Purpose |
|---|---|---|---|
| `compare_mode` | `"csv" \| "live"` | `"csv"` | Controls which mode the Compare view uses |
| `model_a_provider` | `str \| None` | `None` | Provider for Model A live predictions |
| `model_a_model` | `str \| None` | `None` | Model name for Model A |
| `model_a_prompt` | `str \| None` | `DEFAULT_LABELING_TEMPLATE` | Labeling prompt for Model A |
| `model_a_temperature` | `float` | `0.7` | Temperature for Model A |
| `model_b_provider` | `str \| None` | `None` | Provider for Model B |
| `model_b_model` | `str \| None` | `None` | Model name for Model B |
| `model_b_prompt` | `str \| None` | `DEFAULT_LABELING_TEMPLATE` | Labeling prompt for Model B |
| `model_b_temperature` | `float` | `0.7` | Temperature for Model B |
| `helper_agent_provider` | `str \| None` | `None` | Provider for Helper Agent |
| `helper_agent_model` | `str \| None` | `None` | Model name for Helper Agent |
| `helper_agent_prompt` | `str \| None` | `DEFAULT_CHAT_TEMPLATE` | Chat prompt for Helper Agent |
| `helper_agent_temperature` | `float` | `0.7` | Temperature for Helper Agent |

---

## API surface additions

### `GET /live_prediction/{data_idx}?role=model_a|model_b`

Returns a list of predicted aspect dicts (same shape as `GET /ai_prediction/{data_idx}`).

**Logic:**
1. Validates `role` is `model_a` or `model_b` (400 otherwise)
2. Reads per-model config keys from `CONFIG_DATA` (not `load_config()`)
3. Calls `validate_per_model_config(role, config)` — if provider or model is blank, returns 400 with a clear message
4. Loads review text + few-shot examples (same logic as existing AI prediction)
5. Calls `validate_provider_config()` to check global API keys
6. Dispatches to `get_provider(provider_name, CONFIG_DATA).predict(..., temperature=..., prompt_template=...)`
7. Adds position data if `save_phrase_positions` is enabled
8. Returns predictions

**Error responses:**
- 400: `"model_a: No provider configured."` / `"model_a: No model configured."` / `"OpenAI API key is required"` / `"Unknown role 'model_c'"`
- 404: Row index out of range

---

## Design decisions

### 1. New endpoint vs modifying existing `get_ai_prediction`

The existing `GET /ai_prediction/{data_idx}` is used by AI Suggestions and reads from global config. A separate endpoint keeps the concerns isolated — zero risk of breaking AI Suggestions, and the new endpoint can enforce per-model validation rules independently. Also makes extension easier: adding `role=model_c` or `model_d` is a trivial change.

### 2. No fallback for per-model config (confirmed by user)

Model A/B must have provider + model explicitly configured. If blank, the endpoint returns HTTP 400 with a descriptive error. This follows **KISS** — no implicit merging, no cascading defaults, no surprising behavior.

Helper Agent uses a soft fallback: if `helper_agent_provider` is not set, it falls back to the derived global provider (backward compatible with existing users).

### 3. Temperature param added to `predict()` (not read from config inside)

`temperature` is an explicit parameter on the `predict()` method rather than read from config internally. This follows the **dependency injection** principle from the [python-design-patterns](../python-design-patterns/SKILL.md) skill — the parameter is visible at the call site, testable via signature inspection, and makes the provider adapters stateless with respect to temperature.

### 4. Collapsible sections in Settings Panel

The panel already had 5 sections. Adding 3 more with 4 fields each would make the panel scroll excessively. DaisyUI's `collapse` component keeps the panel manageable — each model's config is hidden by default and expands on click.

### 5. Live mode uses separate state from CSV mode

In `App.tsx`, `liveModelATriplets` / `liveModelBTriplets` are entirely separate from `currentData.model_a_triplets` / `currentData.model_b_triplets`. The `compare_mode` setting determines which set is passed to `ModelTripletColumn`. This means no merge logic, no overlay complexity, and clear state management.

### 6. Per-model config reads from `CONFIG_DATA`, not `load_config()`

The live prediction endpoint reads from the in-memory `CONFIG_DATA` dict (which is mutated by `PATCH /settings`), not from the disk-based config file. This ensures settings panel updates take effect immediately without a restart. This is documented as a known landmine in `architecture_map.md`.

### 7. Validation checks both per-model AND global keys

Per-model config stores only `provider`, `model`, `prompt`, and `temperature`. API keys (`openai_key`, `anthropic_key`, `vllm_url`) remain global as deployment-level secrets. The validation checks per-model fields first (provider + model must be non-None), then delegates to `validate_provider_config()` for global key checks — no duplication of validation logic.

### 8. Mock at `get_provider`, not at the HTTP layer (test strategy)

Integration tests mock `services.llm_providers.get_provider` (the factory function), not individual provider classes or HTTP connections. This exercises the full endpoint dispatch chain (validation, config reading, error handling, response formatting) while avoiding real LLM API calls.

---

## Verification

| Check | Result |
|---|---|
| `py_compile services/llm_providers.py` | ✅ |
| `py_compile main.py` | ✅ |
| `py_compile cli.py` | ✅ |
| `pytest tests/` | **124 passed** (93 existing + 12 per-model + 19 live_prediction) |
| `npx vitest run` | **27 passed** (13 hook + 14 component) |
| `npx tsc --noEmit` | ✅ 2 pre-existing errors only (landmine #16) |
| Phase 4 config keys in cli.py | ✅ 13 keys present with correct defaults |
| Template dedup (cli.py imports) | ✅ `DEFAULT_LABELING_TEMPLATE as CLI_DEFAULT_LABELING_TEMPLATE`, no raw string copies |

---

## Autopilot compatibility

A typed `AppActions` interface was added to support a future mode where the Helper Agent can programmatically drive the app. 15 actions are exposed via `useRef`:

```
navigateTo        → setCurrentIndex(index)
nextReview        → (p + 1) % totalCount
prevReview        → (p - 1 + totalCount) % totalCount
switchMode        → setMode('compare' | 'manual')
toggleChat        → setShowFloatingChat
selectTriplet     → toggleModelA / toggleModelB
selectAllTriplets → selectAllModelA / selectAllModelB
clearAllTriplets  → clearAllModelA / clearAllModelB
addManualTriplet  → setManualTriplets([...prev, triplet])
removeManualTriplet → filter out by id
saveAndNext       → handleNextReview (calls POST /review/{idx}/save)
triggerAIPrediction → fetchAIPrediction
triggerLivePrediction → fetchLivePrediction(role)
clearAll          → reset all selections + manual triplets
openSettings      → setShowSettings(true)
```

**Future work to enable autopilot:** Add a response parser in `HelperAgentChatbox` that checks the agent's reply for structured actions (e.g., `{"action": "nextReview"}`) and calls `appActionsRef.current.nextReview()`. The backend's `agent_chat` endpoint would return a composite response with both text and action directives.

---

## Tips for future coding agents

### 1. Two config sources — `CONFIG_DATA` vs `load_config()`

`CONFIG_DATA` is the live in-memory dict mutated by `PATCH /settings`. `load_config()` re-reads from the config JSON file on disk. The live prediction endpoint reads from `CONFIG_DATA`; the old AI prediction endpoint mixes both. When writing endpoint tests with TestClient, mutate `main.CONFIG_DATA` directly — don't mock `load_config()`.

### 2. Test isolation with module-level state

`main.py` has module-level globals that persist across tests when sharing a module-scoped `TestClient`. Use an autouse fixture to reset per-model config between tests:

```python
@pytest.fixture(autouse=True)
def reset_config(app):
    import main
    main.CONFIG_DATA["model_a_provider"] = None
    main.CONFIG_DATA["model_a_model"] = None
    main.CONFIG_DATA["model_a_prompt"] = None
    main.CONFIG_DATA["model_a_temperature"] = 0.7
    ...
    yield
```

### 3. Test CSV must have both `text` and `review_text` columns

The endpoint reads `row.get('text', '')`. If the test CSV only has `review_text`, the review text will be empty and position data tests will fail. Always include both columns in test data.

### 4. Template constants are duplicated between main.py, cli.py, and services/prediction.py

`cli.py` imports `DEFAULT_LABELING_TEMPLATE` and `DEFAULT_CHAT_TEMPLATE` from `services/prediction` via aliases (`CLI_DEFAULT_LABELING_TEMPLATE`). `main.py` imports them directly. **Never copy-paste the template string** — the import-based dedup pattern keeps them in sync. If you see a raw template string in cli.py or main.py, it's a bug.

### 5. Settings dropdowns for provider must match PROVIDER_REGISTRY

The `PROVIDER_OPTIONS` array in `SettingsPanel.tsx` must match the keys in `PROVIDER_REGISTRY` (`services/llm_providers.py`). If you add a 5th provider, add it to both places — the SettingsPanel dropdown and the registry — plus its required config keys in `validate_provider_config()`.

### 6. The `'NULL'` sentinel is a string, not Python None

Implicit aspects and opinions use the literal string `'NULL'` (uppercase, quoted). Checked via `!= 'NULL'` in position logic. Never convert it to `""` or `None`.

### 7. SVG icons replace emoji in SettingsPanel

Per the [ui-ux-review](../ui-ux-review/SKILL.md) skill, emoji were replaced with SVG vectors in the Phase 4 Settings additions (CSV/Live toggle buttons, model status indicators, unsaved-changes footer). If adding more UI to the Settings panel, use Heroicons-style SVGs with proper viewBox attributes — no emoji.
