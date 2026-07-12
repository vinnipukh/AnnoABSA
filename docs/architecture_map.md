# AnnoABSA — Architecture Map

Purpose: let a coding agent orient without reading the whole codebase. This is the current
(as-is) architecture after root reorganization. Line numbers are no longer included since
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

## 2. Backend module graph (post-reorganization)

The backend was split from one monolithic `main.py` (~1750 lines) into six modules:

```
main.py  (residual — ~1053 lines)
│  Global state: DATA_FILE_PATH, DATA_FILE_TYPE, CONFIG_PATH, CONFIG_DATA, AUTO_POSITIONS
│  Data I/O: load_data(), save_data(), set_data_file(), set_config_file()
│  Config: load_config(), set_config()
│  Helper methods: get_total_count(), get_current_index(), max_number_of_idxs()
│  Position logic: auto_add_missing_positions()
|  Endpoints (11 in main.py, 4 in nlp router = 15 total):
│    GET  /settings
│    PATCH /settings
│    GET  /data/{data_idx}
│    POST /timing/{data_idx}
│    POST /auto-add-positions
│    GET  /avg-annotation-time
│    POST /upload-data
│    POST /review/{data_idx}/save
│    GET  /ai_prediction/{data_idx}
│    GET  /live_prediction/{data_idx}  — per-model live prediction (Phase 4)
│    POST /agent/chat
│  Startup: startup_event()
│
├── services/nlp_helpers.py
│    4 lazy-loaded NLP tools (first-use only, zero startup cost):
│      get_sentinet()               — SentiNet lexicon from StarlangSoftware
│      get_sentiment_classifier()   — BERT Turkish sentiment pipeline
│      get_morphological_analyzer() — NlpToolkit FsmMorphologicalAnalyzer
│      get_embedding_model()        — multilingual-e5-small SentenceTransformer
│      get_lexicon()                — flattened {word: (polarity, score)} dict via WordNet
│    Handlers:
│      lexicon_polarity(text)       — per-word + aggregate polarity
│      sentiment_classify(text)     — BERT label + confidence
│      morphology(word)             — root, POS, inflectional groups
│      embedding_similarity(sel, sent) — cosine similarity (0.0–1.0)
│
├── app/routes/nlp.py     (APIRouter, first production route file)
│    4 NLP Helper Toolbar endpoints (lazy imports from services/nlp_helpers):
│      GET /nlp/lexicon-polarity      — SentiNet per-word sentiment
│      GET /nlp/sentiment             — BERT sentence-level sentiment
│      GET /nlp/morphology            — NlpToolkit morphological analysis
│      GET /nlp/embedding-similarity  — e5-small cosine similarity
│
├── models/schemas.py
│     Pydantic models shared across endpoints:
│       SaveTripletsRequest  — used by POST /review/{idx}/save
│       AgentChatRequest     — used by POST /agent/chat
│
├── services/prediction.py
│     Prompt building and ABSA model generation (used by all providers):
│       DEFAULT_LABELING_TEMPLATE  — Turkish labeling prompt
│       DEFAULT_CHAT_TEMPLATE      — Turkish helper-agent prompt
│       build_prediction_prompt()  — formats template + few-shot examples
│       build_absa_models()        — creates dynamic Pydantic model + enums
│       get_most_similar_examples() — BM25 retrieval (no Turkish stemming)
│       find_valid_phrases_list()   — enumerate valid sub-phrases from text
│       find_phrase_positions()     — locate phrase in text (exact then case-insensitive)
│       generate_mock_reasoning()   — Turkish analysis paragraph (fallback)
│
└── services/llm_providers.py
      Provider adapters (each implements predict() + chat()):
        OllamaProvider    — local via ollama Python lib
        OpenAIProvider    — via openai Python lib, structured output
        AnthropicProvider — via anthropic Python lib, JSON extraction from text
        VLLMProvider      — via openai lib + custom base_url, manual JSON parse
      Dispatch:
        PROVIDER_REGISTRY — dict mapping name → class
        get_provider()    — factory: name + config → instance
        _derive_provider() — auto-detect provider from config keys
      Backward compat:
        predict_llm()     — wraps OllamaProvider, imported by evaluation/eval.py
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
POST /ai_prediction/{idx}
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
POST /agent/chat
   │
   ├─ build system prompt from chat template (DEFAULT_CHAT_TEMPLATE)
   ├─ append last 4 turns of chat history
   ├─ _derive_provider → get_provider → provider.chat()
   └─ fallback: Turkish rule-based responses on error
```

### Live Prediction flow (Phase 4)

```
GET /live_prediction/{idx}?role=model_a|model_b
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
│
├─ components/ModelTripletColumn.tsx
│     props: title, badgeText, triplets — GENERIC, renders any model's predictions
│     with checkboxes for selection/deselection
│
├─ components/ManualInputForm.tsx
│     props: text/onSubmit callbacks, manual triplet entry. Now has clickable
│     character-level spans via useTextSelection hook (shared with PhraseAnnotator).
│     Also exposes onSelectionChange for NLP toolbar. Used in Compare mode center column.
│
├─ components/PhraseAnnotator.tsx
│     Click-to-select span annotator for Manual mode. Character-level rendering,
│     inline color highlighting, popup form for category/polarity, position math.
│     Selection logic extracted into shared useTextSelection hook.
│
├─ components/NlpHelperToolbar.tsx
│     Collapsible floating toolbox: red toolbox icon (collapsed) → 4-segment card (expanded).
│     Positioned fixed at bottom-center above the footer (not anchored to selection).
│     Segments: Sözlük (lexicon, auto-fetches), Duygu Analizi / Yapı / Benzerlik
│     (on-demand). Escape/click-outside to collapse. Mounted in App.tsx for both modes.
│
├─ components/NlpHelperToolbar.test.tsx
│     14 vitest tests: collapse/expand, auto-fetch lexicon, on-demand segments,
│     error handling, Escape key, abort-on-unmount.
│
├─ components/HelperAgentChatbox.tsx
│     props: chat messages, send handler — floating panel, talks to POST /agent/chat
│
├─ components/CustomCheckbox.tsx        — generic, no app-specific logic
├─ components/AISuggestions.tsx         — AI suggestion list with accept/reject
├─ components/SettingsPanel.tsx         — Settings modal, 5 sections
├─ hooks/useTextSelection.ts            — shared native-drag selection hook
│     Pure functions: getTokenBounds, cleanPhrase, getCleanedPositions
│     Hook: reads window.getSelection() on mouseup, computes char offsets
│     via DOM Range walking. Returns [state, actions]
├─ hooks/useDarkMode.ts                 — dark/light theme toggle
├─ phraseColoring.tsx                    — polarity→color mapping (25-color palette)
└─ types.ts                              — TripletItem, ReviewComparisonData, ChatMessage
      ReviewComparisonData.model_a_triplets / model_b_triplets
```

**Key fact**: Selection uses native browser drag-to-select (mousedown → drag → mouseup).
The hook reads `window.getSelection()` on mouseup and computes character offsets
via DOM Range walking. Token snapping via `getTokenBounds()` expands to word
boundaries. Runs are grouped by continuous background color — no
per-character borders.

---

## 4. LLM-provider adapters (completed — not planned)

The port/adapter pattern described in the original Phase 1 brief is fully implemented.
All four providers sit behind a common interface:

### Interface (implicit, duck-typed)

Each provider class implements:
```python
def predict(self, text, considered_sentiment_elements, examples,
            aspect_categories, polarities, allow_implicit_aspect_terms,
            allow_implicit_opinion_terms, n_few_shot, llm_model,
            prompt_template=None, temperature=0.7) -> (dict, list)
```

And:
```python
def chat(self, messages, model, temperature=0.7, max_tokens=300) -> str
```

### Current implementations (in `services/llm_providers.py`)

| Provider | predict() method | chat() method | Key difference |
|---|---|---|---|
| `OllamaProvider` | `ollama.generate` with Pydantic `model_json_schema()` format | `ollama.chat()` | Structured output via schema |
| `OpenAIProvider` | `client.beta.chat.completions.parse` with `response_format` | `client.chat.completions.create` | Native structured output |
| `AnthropicProvider` | `client.messages.create`, parse JSON from text | Same, with format conversion | No structured output support; manual JSON extraction |
| `VLLMProvider` | OpenAI client with custom `base_url`, standard completion + JSON parse | Same | No `beta.parse` support; thin wrapper around OpenAI API |

### Dispatch (`_derive_provider` + `get_provider` factory)

Both `get_ai_prediction` and `agent_chat` endpoints dispatch the same way:

1. `_derive_provider(CONFIG_DATA)` — auto-detects from config keys:
   - Explicit `llm_provider` → use it
   - Exactly one of `openai_key`/`anthropic_key`/`vllm_url` set → derive to that
   - Multiple set + no explicit → `ValueError`
   - None set → `"ollama"`
2. `get_provider(name, config)` — looks up `PROVIDER_REGISTRY` and instantiates
3. `validate_provider_config(name, config)` — checks required keys are set;
   called by both endpoints and `cli.py` at startup (replaces the triplicated
   inline validation that previously existed in all three call sites).

---

## 5. File-to-task map

| File(s) | What lives there | Task |
|---|---|---|---|
| `main.py` | Global state, data I/O, config functions, 11 HTTP endpoints, startup event, validate_per_model_config import | Residual / Phase 2 Task 2, Phase 4 Task 1 |
| `models/schemas.py` | SaveTripletsRequest, AgentChatRequest | Step 2 of root reorg |
| `services/prediction.py` | Templates, prompt builders, BM25 retrieval, position helpers | Step 4 of root reorg |
| `services/llm_providers.py` | 4 provider adapter classes, registry, factory, _derive_provider, predict_llm, validate_provider_config, validate_per_model_config | Task 3 + Step 3 of root reorg + Phase 4 Task 1 |
| `services/nlp_helpers.py` | 4 lazy-loaded NLP tools + 4 handler functions | Phase 3 Task 1 (new) |
| `app/routes/nlp.py` | APIRouter with 4 NLP endpoints (first production route file) | Phase 3 Task 1 (new) |
| `cli.py` | Argparse, config management, start_backend/start_frontend, STD format conversion, Phase 4 default config keys | Tasks 1, 3, 4 + Phase 4 Task 4 |
| `frontend/src/App.tsx` | Top-level layout, mode toggle, chat toggle, NLP toolbar state, state management | Tasks 2, 5 + P3T1 |
| `frontend/src/types.ts` | TripletItem, ReviewComparisonData with model_a/b naming | Task 2 |
| `frontend/src/components/PhraseAnnotator.tsx` | Click-to-select span annotator (uses useTextSelection hook) | Task 5 + Phase 3 Task 1 |
| `frontend/src/components/ManualInputForm.tsx` | Clickable text + manual triplet form (uses useTextSelection hook) | Phase 3 Task 1 (reworked) |
| `frontend/src/components/ModelTripletColumn.tsx` | Generic comparison column | Task 2 (consumer only) |
| `frontend/src/components/NlpHelperToolbar.tsx` | Collapsible floating toolbox: red toolbox icon, 4 segments, auto/on-demand fetches | Phase 3 Task 3 |
| `frontend/src/components/NlpHelperToolbar.test.tsx` | 14 vitest tests for toolbar component | Phase 3 Task 3 |
| `frontend/src/components/AISuggestions.tsx` | AI suggestion list with accept/reject | Phase 2 Task 1 |
| `frontend/src/components/SettingsPanel.tsx` | Settings modal with 5 sections | Phase 2 Task 2 |
| `frontend/src/components/HelperAgentChatbox.tsx` | Floating chat panel | Unchanged |
| `frontend/src/hooks/useTextSelection.ts` | Shared native-drag selection hook | Phase 3 Task 2 |
| `frontend/src/hooks/useTextSelection.test.ts` | 13 vitest tests for pure functions | Phase 3 Task 2 |
| `evaluation/eval.py` | Standalone evaluation script | Imports predict_llm from services/llm_providers |
| `evaluation/eval_exc.py` | Multi-process eval launcher | Unchanged |

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
- **Template constants are duplicated** between `services/prediction.py` and `cli.py`
  (CLI can't import from prediction.py without triggering FastAPI import-time side effects).
  Keep both copies in sync.
- **`get_live_prediction` reads per-model config from `CONFIG_DATA`, not `load_config()`**
  The live prediction endpoint uses `CONFIG_DATA.get(f"{role}_provider")` directly rather than
  `load_config().get(...)`. This ensures settings panel `PATCH /settings` updates take effect
  immediately. The existing `get_ai_prediction` endpoint uses `load_config()` for some reads
  and `CONFIG_DATA` for others — both work when a config file is active, but in tests you
  must mutate `CONFIG_DATA`, not mock `load_config()`.
- **`predict()` now accepts `temperature=0.7`** — all 4 provider adapters and the `predict_llm()`
  wrapper accept this parameter. The default is 0.7 (was hardcoded 0.0).
- **`validate_per_model_config()`** — Phase 4 validation function in `services/llm_providers.py`.
  Checks per-model config completeness. Called by `get_live_prediction()`.
