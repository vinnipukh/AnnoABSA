# Phase 4, Task 1 — Completion Report: Live Compare Mode

**Date:** 2026-07-12
**Goal:** Add a Live Compare mode alongside the existing CSV-based Compare mode, where Model A and Model B each have independently configurable provider, model, prompt, and temperature. The Helper Agent also gets its own config. A mode selector (CSV vs Live) controls which data populates the comparison columns.
**Status:** ✅ Core implementation complete (9 files, +630 lines)

---

## What this is (for the academic reader)

The original AnnoABSA Compare mode loads pre-computed triplets from CSV files. While useful for comparing two static model outputs, it does not allow interactive experimentation — changing prompts, adjusting temperature, or comparing different models live. Phase 4 adds a **Live Compare mode** that turns each comparison column into an on-demand LLM prediction engine, each with its own provider, model, prompt, and temperature settings.

This enables a research workflow where an annotator can:
- Iterate on prompt engineering and immediately see how the output changes
- Compare two different LLMs side by side (e.g., deepseek-v4-flash vs deepseek-v4-pro)
- Adjust sampling temperature per model to observe its effect on triplet quality
- Configure the Helper Agent independently with its own provider, model, prompt, and temperature

The two modes (CSV and Live) are mutually exclusive — a radio toggle in the Settings panel selects which mode the Compare view uses. In CSV mode, the app works exactly as before (no regression). In Live mode, each column shows a "Run" button that triggers a live prediction using that model's config.

### Autopilot compatibility

In addition to the Live Compare feature, this task lays the **architectural foundation** for a future autopilot mode, where the Helper Agent can programmatically drive the app (navigate reviews, switch modes, select/deselect triplets, trigger predictions, etc.). A typed `AppActions` interface with 15 methods is wired through `App.tsx` → `HelperAgentChatbox` via a `useRef`, ready for a structured-response parser to be added later.

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
│  3. get_provider(model_a_provider, CONFIG_DATA)                  │
│  4. provider.predict(temperature=model_a_temperature,            │
│                      prompt_template=model_a_prompt)             │
│  5. Return predictions                                           │
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

## Files changed (9 files, +630 / −53 lines)

### Modified files

| File | Δ | What changed |
|---|---|---|
| `services/llm_providers.py` | +53 / −5 | Added `temperature` param to all 4 `predict()` methods + protocol + `predict_llm()`. Replaced hardcoded `temperature=0.0` with parameter in Ollama, OpenAI, Anthropic, and VLLM providers. Added `validate_per_model_config(role, config)`. |
| `main.py` | +167 / −8 | Added 13 config keys to `load_config()` defaults (`compare_mode`, 4× `model_a_*`, 4× `model_b_*`, 4× `helper_agent_*`). Exposed all in `GET /settings`. Added 85-line `GET /live_prediction/{data_idx}?role=model_a\|model_b` endpoint. Modified `agent_chat()` to read per-agent provider/model/prompt/temperature. |
| `frontend/src/types.ts` | +42 / −0 | Extended `Settings` with 13 new fields. Added `AppActions` interface (15 methods) for autopilot compatibility. |
| `frontend/src/App.tsx` | +151 / −16 | Added `liveModelATriplets`/`liveModelBTriplets` state, `isModelAPredicting`/`isModelBPredicting` loaders, `fetchLivePrediction()` function. Updated `loadReviewRow` to clear live state. Conditional rendering based on `compare_mode`. Created `appActions` via `useMemo<AppActions>` — passed to `HelperAgentChatbox`. |
| `frontend/src/components/SettingsPanel.tsx` | +120 / −0 | Added `ModelConfigSection` sub-component (collapsible DaisyUI collapse with provider dropdown, model input, temperature slider 0.0–2.0, prompt textarea). Added compare mode selector (CSV / Live). Added 3 collapsible sections for Model A, Model B, Helper Agent. Wired save/load for all new fields. |
| `frontend/src/components/ModelTripletColumn.tsx` | +47 / −10 | Added optional `onRunPrediction` and `isPredicting` props. Shows a "Model X Çalıştır" button in empty state when in live mode (with loading spinner). Preserves CSV-mode empty state when no `onRunPrediction`. |
| `frontend/src/components/HelperAgentChatbox.tsx` | +13 / −1 | Added optional `appActions` prop. Stores actions in `useRef` for future structured-response parser access without re-render overhead. |
| `tests/test_llm_providers.py` | +85 / −0 | Added `TestValidatePerModelConfig` (9 tests: valid configs, missing provider/model/both, missing API keys). Added `TestProviderTemperatureParam` (parameterized across 4 providers checking `temperature` default = 0.7). |

### Supporting changes

| File | Δ | What changed |
|---|---|---|
| `agentdocs/tasks.md` | +5 / −2 | Marked two old tasks as superseded by Phase 4. Added Phase 4 Live Compare Mode task. |
| `agentdocs/phase4/phase4_plan.md` | (new) | 885-line plan written before implementation began. |

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

Logic:
1. Validates `role` is `model_a` or `model_b` (400 otherwise)
2. Reads per-model config keys from `CONFIG_DATA`
3. Calls `validate_per_model_config(role, config)` — if provider or model is blank, returns 400 with a clear message (no fallback)
4. Loads review text + few-shot examples (same logic as existing AI prediction)
5. Calls `validate_provider_config()` to check global API keys
6. Dispatches to `get_provider(provider_name, CONFIG_DATA).predict(..., temperature=..., prompt_template=...)`
7. Adds position data if `save_phrase_positions` is enabled
8. Returns predictions

---

## Design decisions

### 1. New endpoint vs modifying existing `get_ai_prediction`

The existing `GET /ai_prediction/{data_idx}` is used by AI Suggestions and reads from global config. A separate endpoint (`GET /live_prediction`) keeps the concerns isolated — zero risk of breaking AI Suggestions, and the new endpoint can enforce per-model validation rules independently.

### 2. No fallback for per-model config (confirmed by user)

Model A/B must have provider + model explicitly configured. If blank, the endpoint returns HTTP 400 with a descriptive error. This follows KISS — no implicit merging, no cascading defaults, no surprising behavior. Each model's configuration stands on its own.

Helper Agent uses a soft fallback: if `helper_agent_provider` is not set, it falls back to the derived global provider (backward compatible with existing users).

### 3. Collapsible sections in Settings Panel

The panel already had 5 sections. Adding 3 more with 4 fields each would make the panel scroll excessively. DaisyUI's `collapse` component keeps the panel manageable — each model's config is hidden by default and expands on click.

### 4. Temperature param added to `predict()` (not read from config inside)

`temperature` is an explicit parameter on the `predict()` method rather than read from config internally. This follows the dependency injection principle from the [python-design-patterns](../python-design-patterns/SKILL.md) skill — the parameter is visible at the call site, testable via signature inspection, and makes the provider adapters stateless with respect to temperature.

### 5. Autopilot via `useRef` (not context or global state)

`AppActions` is stored in a `useRef` inside `HelperAgentChatbox` rather than a React Context or window global. This avoids re-render overhead (ref mutations don't trigger re-renders) and keeps the action registry colocated with the component that will consume it (the future response parser).

---

## Autopilot compatibility

A typed `AppActions` interface was added to support a future mode where the Helper Agent can programmatically drive the app. 15 actions are exposed:

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

## Verification

| Check | Result |
|---|---|
| `py_compile services/llm_providers.py` | ✅ OK |
| `py_compile main.py` | ✅ OK |
| `pytest tests/` | **105 passed** (93 existing + 12 new) in 0.43s |
| `npx tsc --noEmit` | ✅ No new errors (2 pre-existing only) |
| `npx vite build` | ✅ 44 modules, 278 KB JS + 75 KB CSS, built in 2.18s |
| Autopilot ad-hoc verification | ✅ 6/6 checks passed (15 methods, 3 files, imports, props, ref storage) |

---

## What remains (Phase 4 Tasks 2+)

The following items from the plan are **not yet completed** and should be picked up as future tasks:

| Task | What | Difficulty |
|---|---|---|
| **Task 2** | Integration test file `tests/test_live_prediction.py` (10+ tests with FastAPI TestClient) | Medium |
| **Task 3** | Doc updates: `agentdocs/session_reports/backend_reference.md`, `docs/architecture_map.md`, `agentdocs/ProjectPrimer.md`, `tests/testcases.md` | Easy |
| **Task 4** | Sync default template constants in `cli.py` with `services/prediction.py` | Easy |

---

## Tips for future coding agents

### 1. Temperature parameter is on predict(), not read from config

All 4 providers accept `temperature` as a keyword argument to `predict()`. The `temperature` parameter was added to the `LLMProviderPort` protocol and to `predict_llm()` (the backward-compat wrapper). If adding a 5th provider, include `temperature=0.7` in its `predict()` signature.

### 2. validate_per_model_config checks both per-model AND global keys

The per-model config only stores `provider`, `model`, `prompt`, and `temperature`. API keys (`openai_key`, `anthropic_key`, `vllm_url`) remain global. The validation checks:
- Per-model provider is set → clear error
- Per-model model is set → clear error
- Provider's required global keys exist → delegates to existing `validate_provider_config()`

### 3. New endpoint follows get_ai_prediction's exact data-loading pattern

`GET /live_prediction/{data_idx}` duplicates the JSON/CSV branching logic from `get_ai_prediction()`. If the data-loading logic changes (e.g., adding support for new file formats), both endpoints must be updated. A future refactoring task could extract the shared data-loading logic into a helper.

### 4. Live Compare mode uses separate state from CSV mode

In `App.tsx`, `liveModelATriplets` / `liveModelBTriplets` are entirely separate from `currentData.model_a_triplets` / `currentData.model_b_triplets`. The `compare_mode` setting determines which set is passed to `ModelTripletColumn`. This means:
- CSV mode → `currentData.model_a_triplets` (loaded from CSV via `get_data()`)
- Live mode → `liveModelATriplets` (loaded via `fetchLivePrediction`)

### 5. AppActions ref pattern avoids re-render overhead

`appActions` is stored in a `useRef` inside `HelperAgentChatbox` (not in state). This means the future response-parser can call actions without triggering re-renders of the chatbox. The ref is kept in sync via `useEffect` whenever the prop changes.
