# Contributing to AnnoABSA

Welcome! This document outlines the standard workflow for contributing. Follow these steps in order for every task.

---

## Workflow

### 1. Pick a task

Browse [`tasks.md`](tasks.md). Tasks are ordered by priority. Claim one by moving it to **In Progress** (or just start — no formal assignment needed).

If you're adding something not on the list, add a new row first so everyone can see what's being worked on.

### 2. Read the orientation docs

Before writing any code, read these in order:

| Doc | What it tells you |
|---|---|
| [`ProjectPrimer.md`](ProjectPrimer.md) | Stack, data format, how to run, working style rules |
| [`../docs/architecture_map.md`](../docs/architecture_map.md) | Module graph, process flow, file-to-task map, known landmines |
| [`session_reports/backend_reference.md`](session_reports/backend_reference.md) | Every function, endpoint, and module (one-page reference) |
| [`../tests/testcases.md`](../tests/testcases.md) | Regression test cases — what must keep working |

**Key rule:** read the **Known landmines** section in `../docs/architecture_map.md` before touching anything. Several past bugs are documented there and cost hours to rediscover.

### 3. Plan (then confirm)

Write a short plan covering:

```
1. [What you'll change] → verify: [how you'll check it worked]
2. [What you'll change] → verify: [how you'll check it worked]
```

Post it and wait for confirmation before coding. For small changes this can be brief.

### 4. Make changes

- **Surgical** — touch only what the task requires. No drive-by refactors.
- **Match style** — look at surrounding code and match its patterns.
- **One task at a time** — no scope creep.

### 5. Run verification

Execute the [Post-Feature Checklist](post_feature_checklist.md) in order:

```
1. Clean        — remove debug prints, unused imports, dead code
2. Compile      — py_compile all changed files
3. Test         — pytest tests/ (expected: 81 passed)
4. Smoke test   — if you changed an endpoint: start backend + frontend,
                  confirm the UI loads without console errors
5. Update docs  — backend_reference.md, docs/architecture_map.md,
                  ProjectPrimer.md, testcases.md (if applicable)
```

### 6. Commit

```
git add -A
git diff --cached --stat   # review what you're about to commit
git commit -m "short description of what and why"
```

Commit messages follow the conventional format: start with a verb in imperative mood, keep the subject under 72 characters, add a blank line then bullet points for details if needed.

---

## Project layout at a glance

```
main.py               — FastAPI app: global state, endpoints, data I/O (to be broken up)
cli.py                — CLI launcher: argparse, config, subprocess management
app/                  — Scaffold for future main.py breakup (empty, docstrings only)
models/schemas.py     — Pydantic request models
services/
  prediction.py       — Prompt building, BM25 retrieval, position helpers
  llm_providers.py    — Provider adapters (Ollama, OpenAI, Anthropic, vLLM) + dispatch
tests/
  test_prediction.py      — 38 tests: prompt, positions, BM25, reasoning
  test_llm_providers.py   — 31 tests: registry, derivation, validation, factory
  test_main_helpers.py    — 12 tests: CSV parsing
  testcases.md            — Full regression walkthrough (manual Tiers 1–6)
frontend/src/         — React + TypeScript + Vite + Tailwind + DaisyUI
|docs/                 — Architecture map, CLI table (for LREC paper)
|evaluation/           — Eval scripts + predictions + user study results
```

---

## Agent/Coding-Tool Notes

If you're working via an AI coding agent (like Hermes, Claude Code, or similar):

- Include the full content of `agentdocs/ProjectPrimer.md` in your first prompt — it has the working style rules the agent needs.
- Reference `docs/architecture_map.md` for module structure and landmines.
- Reference `tests/testcases.md` for the regression baseline.
- The agent should read `agentdocs/post_feature_checklist.md` after implementing and follow it step by step.

---

## Code review expectations

- All 81 pytest tests must pass before merge.
- New features should include new tests (add to the appropriate `tests/test_*.py` file).
- If you change an endpoint or data format: smoke test the UI at `localhost:3000`.
- No new `# Removed _` comments, no duplicate imports, no German/English mixed docstrings.
- Any change that does not comply with the instructions given above will not be added to the project and the contributors will be removed from permenantly if they do not abide these instructions.

---

## Agent Heating Guide — hard-won knowledge from past sessions

*Read this before writing any code. It captures traps, patterns, and architectural rules discovered the hard way.*

### 1. Don't bloat `main.py` and `cli.py`

`main.py` is already **~1206 lines**. `cli.py` is **~947 lines**. They are the two biggest files in the project and they are **not the right place for new code**.

| If you're adding... | Put it here | Example |
|---|---|---|
| A new HTTP endpoint | `app/routes/<name>.py` (new APIRouter file) | `app/routes/nlp.py` |
| Business logic | `services/<name>.py` | `services/nlp_helpers.py` |
| Pydantic request/response models | `models/schemas.py` | `SaveTripletsRequest` |
| A new config key | `load_config()` defaults in `main.py` + `GET /settings` | Phase 4 keys |
| A new provider adapter | `services/llm_providers.py` (add to `PROVIDER_REGISTRY`) | `VLLMProvider` |
| A new provider validation | `services/llm_providers.py` (`validate_provider_config`) | `validate_per_model_config()` |

**Exception:** If the addition is 3–5 lines and tightly coupled to existing code in `main.py`, it's acceptable to add it there. But think twice — every 50 lines you add to `main.py` is 50 lines that will need to be extracted later.

### 2. Two config sources — `CONFIG_DATA` vs `load_config()`

There are **two** config dicts in this project, and they are NOT the same thing:

| Source | What it is | When it's used |
|---|---|---|
| `CONFIG_DATA` | Module-level global dict in `main.py` | Mutated by `PATCH /settings` at runtime. This is the **live, in-memory** state. |
| `load_config()` | Reads from the config JSON file on disk, or returns hardcoded defaults | Called at the start of each request handler. Reflects **what's on disk**. |

**The trap:** Existing endpoints like `get_ai_prediction` mix both — they read some values from `CONFIG_DATA` and others from `load_config()`. When writing a new endpoint, decide which source to use and be consistent.

**Rule of thumb for Phase 4+ code:**
- Read per-model config (`model_a_provider`, `model_a_temperature`, etc.) from **`CONFIG_DATA`** — this is what the settings panel updates
- Read static defaults (`sentiment_elements`, `aspect_categories`) from either — but prefer `CONFIG_DATA` for consistency
- In tests: mutate `main.CONFIG_DATA` directly. Don't mock `load_config()`.

**Why this matters for testing:** When you write a TestClient test, setting `main.CONFIG_DATA["key"] = value` only works if the endpoint reads from `CONFIG_DATA`. If it reads from `load_config()`, your mutation is invisible and the test will fail with a confusing default value.

### 3. The `text` column trap

The endpoint `get_data()` loads the review text with `row.get('text', '')`. If your CSV has a `review_text` column but no `text` column, the text will be **empty string**. This means:
- Position data tests (`find_phrase_positions`) will return `(None, None)` because there's nothing to search
- The existing `get_ai_prediction()` and `get_live_prediction()` both use this pattern

**Fix for test CSVs:** Always include BOTH `text` and `review_text` columns:

```csv
review_id,text,review_text,translation,label
0,"Manzara şahane","Manzara şahane","The view is wonderful",""
```

### 4. Template constants are duplicated (intentionally)

`services/prediction.py` defines `DEFAULT_LABELING_TEMPLATE` and `DEFAULT_CHAT_TEMPLATE`. `cli.py` imports them as aliases:

```python
from services.prediction import DEFAULT_LABELING_TEMPLATE as CLI_DEFAULT_LABELING_TEMPLATE
```

**Never copy-paste the template string into cli.py.** The import-based dedup pattern is intentional and keeps them in sync. If you ever see a raw template string in cli.py, it's a bug from a past session.

### 5. Module-level state in main.py is shared and mutable

`main.py` has module-level globals (`DATA_FILE_PATH`, `CONFIG_DATA`, `CONFIG_PATH`, `DATA_FILE_TYPE`, `AUTO_POSITIONS`) that persist across requests. They are **not** reset between test cases unless you explicitly reset them.

**Consequences for testing with TestClient:**
- Use a **module-scoped fixture** to set env vars and import `main` once
- Use a **function-scoped autouse fixture** to reset `CONFIG_DATA` between tests
- Test ordering matters — the first test can leave side effects for later tests
- If a test fails oddly, suspect state leakage from a previous test

**Example pattern (from `test_live_prediction.py`):**

```python
@pytest.fixture(scope="module")
def app(csv_path):
    os.environ["ABSA_DATA_PATH"] = csv_path
    import main
    main.DATA_FILE_PATH = csv_path
    main.CONFIG_DATA = {"sentiment_elements": [...], ...}
    yield TestClient(main.app)

@pytest.fixture(autouse=True)
def reset_config(app):
    import main
    main.CONFIG_DATA["model_a_provider"] = None
    yield  # teardown — nothing to clean
```

### 6. Mock at the right level

When writing endpoint tests with TestClient, mock at the **highest feasible level**:

| What to test | Mock target | Why |
|---|---|---|
| Endpoint validation (missing params, error codes) | Don't mock anything — the error happens before any provider call | Tests run fast, test pure logic |
| Config propagation (temperature, prompt, model) | `services.llm_providers.get_provider` | Only one mock point, covers the entire dispatch chain |
| Provider-specific behavior (Ollama vs OpenAI) | Instantiate the real provider class and mock its `predict()` | Rarely needed — prefer mocking `get_provider` |

**Never mock at the HTTP/network layer** (e.g., don't mock `ollama.generate` or `openai.ChatCompletion.create`). The provider adapters already encapsulate those. Mock the factory function that returns the adapter.

### 7. Every new settings toggle needs 3 things

If you add a new setting to the Settings panel, it needs to be wired in three places (the "dead toggle" pattern):

1. **Backend:** key in `load_config()` defaults + value in `GET /settings` response
2. **SettingsPanel.tsx:** form field + initial value + save handler
3. **Frontend consumer:** some component actually reads the setting and takes action

If step 3 is missing, you have a "dead toggle" — it saves and loads, but nothing happens. `grep -rn 'your_key' frontend/src/ --include="*.tsx" --include="*.ts" | grep -v SettingsPanel.tsx` should return at least one match outside SettingsPanel.tsx.

### 8. FastAPI TestClient + module imports: the chicken-and-egg problem

`main.py` reads env vars at the module level (line 33: `DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', ...)`). This means you **must** set the env var before `import main`. You cannot import main, then set the env var, then expect it to take effect.

**Correct order:**
```python
os.environ["ABSA_DATA_PATH"] = "/tmp/test.csv"
import main  # reads the env var at this point
```

**Wrong order:**
```python
import main  # reads None → falls back to "annotations.csv"
os.environ["ABSA_DATA_PATH"] = "/tmp/test.csv"  # too late
```

Use a `scope="module"` fixture to handle this once for the entire test file.

### 9. `predict()` now accepts `temperature=0.7`

All 4 provider adapters (`OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`, `VLLMProvider`) accept a `temperature` keyword argument on `predict()`. Default is `0.7`. This was changed from hardcoded `0.0` in Phase 4.

If you add a 5th provider, include `temperature=0.7` in its `predict()` signature and pass it to the API call. The `LLMProviderPort` protocol already declares this parameter.

### 10. Settings dropdowns must match `tailwind.config.js`

The theme dropdown in `SettingsPanel.tsx` lists available DaisyUI themes. This list must match the `daisyui.themes` array in `frontend/tailwind.config.js`. If you add a theme option in one place without the other, the UI will show an option that doesn't work (or hide one that does).

Current available themes (DaisyUI v4.12.24): `light`, `dark`, `coffee`, `forest`, `cupcake`, `aqua`, `lemonade`, and many more. Check with:
```bash
node -e "const t=require('./frontend/node_modules/daisyui/src/theming/themes');console.log(Object.keys(t).join(', '))"
```

### 11. Test count expectations

| Suite | Command | Count (current) |
|---|---|---|
| Backend pytest | `pytest tests/` | **124** (93 existing + 12 per-model + 19 live_prediction) |
| Frontend vitest | `cd frontend && npx vitest run` | **27** (13 hook + 14 component) |
| **Total automated** | — | **151** |

When adding new tests, update `tests/testcases.md` coverage summary.

### 12. FastAPI is single-threaded by default

Without `--workers N`, FastAPI runs on a single thread. A long LLM provider call (e.g., Ollama taking 30s) blocks ALL other requests — even `GET /settings` and favicon requests will hang. If the app "freezes" during a prediction, check if a prior request is still pending in the DevTools Network tab.

Workarounds:
- Add `--workers 4` to the uvicorn command in `cli.py`
- Disable `enable_pre_prediction` and `enable_helper_agent` in Settings
- Kill and restart the backend

### 13. The three config sources are slightly out of sync

| Source | Has `theme`? | Has `model_a_*`? |
|---|---|---|
| `main.py` `load_config()` | ✅ `"dark"` | ✅ (added Phase 4) |
| `cli.py` `ABSAAnnotatorConfig.__init__` | ❌ Missing | ✅ (after Phase 4 Task 4) |
| `frontend/types.ts` `Settings` | ✅ | ✅ |

This is acceptable drift — `cli.py` and `main.py` serve different purposes. Don't "fix" the `theme` key in cli.py unless explicitly asked.

### 14. Data file format cheatsheet

| Column | Required? | Used in | Notes |
|---|---|---|---|
| `review_text` | Yes | UI display, position search | The actual review |
| `text` | Sometimes | `row.get('text', '')` in endpoint code | Same as `review_text` in practice |
| `label` | No | Saved annotations | JSON array of triplet objects, or empty |
| `translation` | No | Optional UI display | English translation |
| `aspect_triplets` | Legacy | Backward compat `get_data()` | STD tuples → Model A |
| `new_triplets` | Legacy | Backward compat `get_data()` | STD tuples → Model B |

### 15. The `'NULL'` sentinel is a string, not Python None

Implicit aspects and opinions use the literal string `'NULL'` (uppercase, quoted). This is checked via `!= 'NULL'` in position logic. **Never convert it to `""` or `None`.** The frontend also checks for `'NULL'` specifically.

### 16. `npx tsc` errors you can ignore

Two pre-existing TypeScript errors exist and are NOT caused by your changes:
```
src/App.tsx:133 — Property 'env' does not exist on type 'ImportMeta'
src/App.tsx:447 — Object literal may only specify known properties, and 'rect' does not exist
```

The first is a missing Vite type reference (`vite/client` in tsconfig). The second is a stale `rect` field in a state setter. Both are harmless and pre-date Phase 4.

### 17. Phase 4 autopilot: the AppActions pattern

A typed `AppActions` interface with 15 methods is wired from `App.tsx` → `HelperAgentChatbox` via a `useRef`. If you add a new interactive feature (e.g., a new button or navigation action), extend the `AppActions` interface in `frontend/src/types.ts` and add the handler to the `useMemo` in `App.tsx`. The helper agent's future response parser will automatically gain access to it.

**Autopilot response format (decided LREC-2026-07-12):** The agent backend should return **hybrid** responses — natural language text with optional structured actions embedded inline. The frontend parser extracts actions from the text and calls `appActionsRef.current` methods. This keeps the chat natural while enabling programmatic control. The exact serialization format (JSON block in markdown, custom delimiter, etc.) is not yet designed — build the parser when the autopilot feature is implemented.

### 18. One final reminder

**Do not fatten `main.py` or `cli.py`.** Every time you add a line to either file, ask yourself: "Could this go in `app/routes/`, `services/`, or a new module?" If the answer is yes, put it there. These two files are technical debt that will eventually be broken up — don't add to the debt. Future agents and the LREC paper authors will thank you.
