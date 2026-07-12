# AnnoABSA — Architecture Map

Purpose: let a coding agent orient without reading the whole codebase. This is the current
(as-is) architecture after Phase 5 (main.py breakup). Line numbers are no longer included since
code has been split into multiple files — verify against actual files before editing.

---

## 1. Process graph (who talks to whom)

```
┌─────────────┐   spawns via subprocess.Popen   ┌──────────────────┐
│   cli.py     │────────────────────────────────▶│  uvicorn (main:app) │
│ (launcher)   │   sets os.environ ABSA_DATA_PATH │   = main.py FastAPI  │
│              │   sets os.environ ABSA_CONFIG_PATH  app, backend       │
└──────┬───────┘                                 └────────┬─────────┘
       │                                                    │ HTTP (localhost:8000)
       │ spawns via subprocess.run(["npm","run","dev"])     │
       ▼                                                    ▼
┌──────────────┐                                  ┌──────────────────┐
│ npm/vite dev  │◀────────────HTTP requests───────│  App.tsx (React)  │
│ server (3000) │        (fetch calls, no client   │  + child components│
└──────────────┘         library, raw fetch)       └──────────────────┘
```

**Key fact**: `cli.py` and `main.py` never talk after startup except through two one-shot
environment variables read once at import time (`ABSA_DATA_PATH`, `ABSA_CONFIG_PATH`). There
is no live IPC, no shared process, no re-invocation of `cli.py` logic from inside `main.py`.

---

## 2. Backend module graph (after Phase 5 breakup)

The backend was broken up from one monolithic `main.py` (~1206 lines) into a thin launcher +
9 focused modules:

```
main.py  (thin launcher — ~50 lines)
│  Re-exports from app/ modules for backward compat (cli.py, tests)
│  Mounts 6 route routers: nlp, settings, reviews, ai, timing, upload
│  Startup: startup_event()
│
├── app/config.py
│     Global state: DATA_FILE_PATH, DATA_FILE_TYPE, CONFIG_PATH, CONFIG_DATA, AUTO_POSITIONS
│     Functions: set_data_file(), set_config_file(), load_config(), set_config()
│
├── app/data.py
│     Data I/O: load_data(), save_data(), parse_triplet_column(), _load_comparison_csv()
│     Navigation: get_total_count(), get_current_index(), max_number_of_idxs()
│
├── app/positions.py
│     Position logic: auto_add_missing_positions()
│
├── app/routes/settings.py     (APIRouter)
│     GET  /settings
│     PATCH /settings
│
├── app/routes/reviews.py      (APIRouter)
│     GET  /data/{data_idx}
│     POST /review/{data_idx}/save
│     POST /agent/chat
│
├── app/routes/ai.py           (APIRouter)
│     GET  /ai_prediction/{data_idx}
│     GET  /live_prediction/{data_idx}
│
├── app/routes/timing.py       (APIRouter)
│     POST /timing/{data_idx}
│     GET  /avg-annotation-time
│
├── app/routes/upload.py       (APIRouter)
│     POST /upload-data
│     POST /auto-add-positions
│
├── app/routes/nlp.py          (APIRouter, Phase 3)
│     GET  /nlp/lexicon-polarity
│     GET  /nlp/sentiment
│     GET  /nlp/morphology
│     GET  /nlp/embedding-similarity
│
├── models/schemas.py
│     Pydantic models: SaveTripletsRequest, AgentChatRequest
│
├── services/nlp_helpers.py
│     4 lazy-loaded NLP tools (SentiNet, BERT, NlpToolkit, e5-small)
│
├── services/prediction.py
│     Templates, prompt builders, BM25 retrieval, position helpers
│
└── services/llm_providers.py
      Provider adapters: OllamaProvider, OpenAIProvider, AnthropicProvider, VLLMProvider
      Dispatch: PROVIDER_REGISTRY, get_provider(), _derive_provider()
      Validation: validate_provider_config(), validate_per_model_config()
```

### Data flow for a single review, end to end

```
CSV/JSON file (DATA_FILE_PATH)
   │  load_data()
   ▼
GET /data/{idx}  ──▶  {text, label, translation, aspect_category_list,
                        model_a_triplets, model_b_triplets}
   │
   ▼ (frontend renders three columns in Compare mode, or PhraseAnnotator in Manual mode)
User annotates → POST /review/{idx}/save  (the ONLY live save endpoint)
   │  save_data()
   ▼
CSV/JSON file (DATA_FILE_PATH)   ← same file, now updated
```

### AI prediction flow

```
GET /ai_prediction/{idx}     (in app/routes/ai.py)
   │
   ├─ _derive_provider(CONFIG_DATA)  → determines which provider
   ├─ validate provider has required keys
   ├─ get_provider(name, config)     → factory returns adapter instance
   ├─ provider.predict(…)            → calls build_prediction_prompt + build_absa_models
   │                                    then dispatches to the LLM backend
   └─ add position data if save_phrase_positions is enabled
```

### Helper Agent flow

```
POST /agent/chat             (in app/routes/reviews.py)
   │
   ├─ build system prompt from chat template (DEFAULT_CHAT_TEMPLATE)
   ├─ append last 4 turns of chat history
   ├─ _derive_provider → get_provider → provider.chat()
   └─ fallback: Turkish rule-based responses on error
```

### Live Prediction flow (Phase 4)

```
GET /live_prediction/{idx}?role=model_a|model_b    (in app/routes/ai.py)
   │
   ├─ validate_per_model_config(role, CONFIG_DATA)
   │    • provider and model must be non-None (no fallback)
   │    • provider's global keys (openai_key, etc.) validated
   ├─ get_provider(CONFIG_DATA[{role}_provider], CONFIG_DATA)
   ├─ provider.predict(temperature=CONFIG_DATA[{role}_temperature],
   │                    prompt_template=CONFIG_DATA[{role}_prompt])
   └─ add position data if save_phrase_positions is enabled
```

---

## 3. Frontend module graph (`frontend/src/`)

```
App.tsx  (single top-level component, owns ALL state — no state management library)
│  state: currentIndex, reviewData, manualTriplets, chatMessages, isDark, mode, ...
│  fetches: GET /data/{idx}, GET /settings, POST /review/{idx}/save
│  keyboard shortcut: Ctrl+Shift+{key} configurable via Settings → ai_shortcut_key
│
├─ components/ModelTripletColumn.tsx
│     props: title, badgeText, triplets — GENERIC, renders any model's predictions
│     with checkboxes for selection/deselection, optional onRunPrediction for live mode
│
├─ components/ManualInputForm.tsx
│     props: text/onSubmit callbacks, manual triplet entry. Clickable
│     character-level spans via useTextSelection hook (shared with PhraseAnnotator).
│     Exposes onSelectionChange for NLP toolbar. Used in Compare mode center column.
│
├─ components/PhraseAnnotator.tsx
│     Click-to-select span annotator for Manual mode. Character-level rendering,
│     inline color highlighting, popup form for category/polarity, position math.
│     Selection logic extracted into shared useTextSelection hook.
│
├─ components/NlpHelperToolbar.tsx
│     Collapsible floating toolbox: red toolbox icon (collapsed) → 4-segment card (expanded).
│     Fixed at bottom-center above the footer. Segments: Sözlük, Duygu Analizi / Yapı / Benzerlik.
│
├─ components/NlpHelperToolbar.test.tsx
│     14 vitest tests: collapse/expand, auto-fetch lexicon, on-demand segments,
│     error handling, Escape key, abort-on-unmount.
│
├─ components/HelperAgentChatbox.tsx
│     props: chat messages, send handler, appActions ref — floating panel,
│     talks to POST /agent/chat. Autopilot action registry via useRef.
│
├─ components/CustomCheckbox.tsx        — generic, no app-specific logic
├─ components/AISuggestions.tsx         — AI suggestion list with accept/reject
├─ components/SettingsPanel.tsx         — Settings modal, 8 sections (incl. Phase 4/5)
├─ hooks/useTextSelection.ts            — shared native-drag selection hook
│     Pure functions: getTokenBounds, cleanPhrase, getCleanedPositions
│     Hook: reads window.getSelection() on mouseup, computes char offsets
│     via DOM Range walking. Returns [state, actions]
├─ hooks/useDarkMode.ts                 — dark/light theme toggle
├─ phraseColoring.tsx                    — polarity→color mapping (25-color palette)
└─ types.ts                              — TripletItem, ReviewComparisonData, ChatMessage,
      AppActions (15 methods), Settings (with Phase 4/5 fields)
```

**Key fact**: Selection uses native browser drag-to-select (mousedown → drag → mouseup).
The hook reads `window.getSelection()` on mouseup and computes character offsets
via DOM Range walking. Token snapping via `getTokenBounds()` expands to word
boundaries.

---

## 4. LLM-provider adapters

The port/adapter pattern is fully implemented. All four providers sit behind a common interface
defined in `services/llm_providers.py`.

### Interface (implicit, duck-typed)

```python
def predict(self, text, considered_sentiment_elements, examples,
            aspect_categories, polarities, allow_implicit_aspect_terms,
            allow_implicit_opinion_terms, n_few_shot, llm_model,
            prompt_template=None, temperature=0.7) -> (dict, list)
```

```python
def chat(self, messages, model, temperature=0.7, max_tokens=300) -> str
```

### Provider implementations

| Provider | predict() method | chat() method | Key difference |
|---|---|---|---|
| `OllamaProvider` | `ollama.generate` with Pydantic `model_json_schema()` format | `ollama.chat()` | Structured output via schema |
| `OpenAIProvider` | `client.beta.chat.completions.parse` with `response_format` | `client.chat.completions.create` | Native structured output |
| `AnthropicProvider` | `client.messages.create`, parse JSON from text | Same, with format conversion | No structured output support |
| `VLLMProvider` | OpenAI client with custom `base_url`, standard completion + JSON parse | Same | No `beta.parse` support |

### Dispatch

Both `get_ai_prediction` and `agent_chat` endpoints (in `app/routes/ai.py` and `app/routes/reviews.py`)
dispatch the same way:
1. `_derive_provider(CONFIG_DATA)` — auto-detects from config keys
2. `get_provider(name, config)` — looks up `PROVIDER_REGISTRY` and instantiates
3. `validate_provider_config(name, config)` — checks required keys are set

---

## 5. File-to-task map

| File(s) | What lives there | Task |
|---|---|---|
| `main.py` | Thin launcher: imports + mounts routers, startup event | Phase 5 (was 1206 lines → 50 lines) |
| `app/config.py` | Global state + config functions | Phase 5 |
| `app/data.py` | Data I/O + navigation helpers | Phase 5 |
| `app/positions.py` | Position auto-fill logic | Phase 5 |
| `app/routes/settings.py` | GET/PATCH /settings | Phase 5 |
| `app/routes/reviews.py` | Data, save, agent chat endpoints | Phase 5 |
| `app/routes/ai.py` | AI prediction + live prediction endpoints | Phase 5 |
| `app/routes/timing.py` | Timing + avg annotation time endpoints | Phase 5 |
| `app/routes/upload.py` | Upload data + auto-add-positions endpoints | Phase 5 |
| `app/routes/nlp.py` | 4 NLP Helper Toolbar endpoints | Phase 3 |
| `models/schemas.py` | SaveTripletsRequest, AgentChatRequest | Step 2 of root reorg |
| `services/prediction.py` | Templates, prompt builders, BM25, position helpers | Phase 1-2 |
| `services/llm_providers.py` | 4 providers, registry, dispatch, validation | Phase 1-4 |
| `services/nlp_helpers.py` | 4 lazy-loaded NLP tools | Phase 3 |
| `cli.py` | Argparse, config, subprocess management, STD conversion | Phase 1-5 |
| `frontend/src/App.tsx` | Layout, mode toggle, chat, NLP toolbar state, AppActions, keyboard shortcuts | Phases 2-5 |
| `frontend/src/types.ts` | TripletItem, Settings, AppActions interfaces | Phases 2-5 |
| `frontend/src/components/SettingsPanel.tsx` | Settings modal, 8 sections | Phases 2-5 |
| `frontend/src/components/ModelTripletColumn.tsx` | Generic comparison column with Run button | Phase 2-4 |
| `frontend/src/components/HelperAgentChatbox.tsx` | Chat panel (emoji → SVG pending) | Phase 2 |
| `frontend/src/components/NlpHelperToolbar.tsx` | Toolbox (emoji → SVG pending) | Phase 3 |
| `frontend/src/components/AISuggestions.tsx` | AI suggestion list | Phase 2 |
| `frontend/src/hooks/useTextSelection.ts` | Drag selection hook | Phase 3 |
| `tests/test_live_prediction.py` | 19 endpoint tests for live prediction | Phase 4 |
| `tests/test_smoke.py` | 4 compile-only smoke tests | Phase 5 |
| `evaluation/eval.py` | Standalone eval script | Phase 1 |

---

## 6. Known landmines (don't rediscover these — read once, remember)

- **`POST /annotations/{idx}` was deleted** — it was dead code with no frontend callers.
  The only live save endpoint is `POST /review/{idx}/save`.
- **`predict_openai` was deleted** — no callers. Use `OpenAIProvider` directly.
- **`Item` and `AnnotationData` Pydantic models were deleted** — no callers.
- **`set_data_file()` is NOT dead code** — called by the `upload_data` endpoint.
- **`'NULL'` is a literal string sentinel for implicit aspects/opinions**, checked via
  `!= 'NULL'` in `auto_add_missing_positions`. Never convert it to `""`.
- **NlpToolkit packages need `setuptools<75`** — the StarlangSoftware packages
  (`nlptoolkit-sentinet`, etc.) use `pkg_resources` at import time, removed in
  setuptools 75+. Install with `pip install 'setuptools<75'` before installing them.
- **BM25 tokenization has no Turkish stemming** — plain `\b\w+\b` regex + lowercase.
  Don't assume more few-shot examples will help without fixing this first.
- **`aspect_category`/`sentiment_polarity` values stay in English** — confirmed user decision,
  not an oversight. Don't translate them anywhere.
- **Template constants are imported as aliases** in `cli.py` from `services/prediction`.
  Never copy-paste the template string — the import-based dedup keeps them in sync.
- **`get_live_prediction` reads per-model config from `CONFIG_DATA`, not `load_config()`**
  The live prediction endpoint uses `CONFIG_DATA.get(f"{role}_provider")` directly.
- **`predict()` now accepts `temperature=0.7`** — all 4 providers accept this parameter.
- **`validate_per_model_config()`** — checks per-model config completeness in `services/llm_providers.py`.
- **After Phase 5 breakup, `main.py` re-exports from `app/` modules.** `import main; main.CONFIG_DATA`
  still works because `from app.config import *` is in `main.py`. Tests that mutate
  `main.CONFIG_DATA["key"] = val` still work — they're mutating the same dict object.
- **Route file imports are inconsistent.** `app/routes/settings.py` correctly imports from `app.config` and `app.data`. However, `app/routes/ai.py`, `app/routes/reviews.py`, `app/routes/timing.py`, and `app/routes/upload.py` use `import main` then access `main.CONFIG_DATA`, `main.load_data()`, etc. This works (main.py re-exports everything) but violates the clean layering — it's a Phase 6 fix item. If adding a new route file, always import from `app.config` and `app.data` directly, not from `main`.
- **`requirements.txt` was deleted** in Phase 5. Use `pyproject.toml` as the single source
  of truth for dependencies. Run `pip install -e .` to install.
- **The `annoabsa` entry-point shim was deleted** in Phase 5. Use `python cli.py` to run.
- **`temp_absa_config.json` now lives in `temp/` directory**, not the project root.
  The `temp/` directory is gitignored and created at runtime.
