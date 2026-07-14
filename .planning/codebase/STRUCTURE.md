# AnnoABSA Codebase Structure

## Directory Tree

```
AnnoABSA/
├── main.py                     # FastAPI app launcher (entry point)
├── cli.py                      # CLI entry point → delegates to cli/
├── pyproject.toml              # Python project metadata & dependencies
├── README.md                   # Project documentation
├── setup.sh                    # Unix setup script
├── setup.bat                   # Windows setup script
├── package.json                # Root package.json (empty, frontend has its own)
├── package-lock.json
├── uv.lock                     # Dependency lock file
│
├── app/                        # BACKEND — FastAPI application (6 files)
│   ├── __init__.py             # Package docstring, submodule listing
│   ├── config.py               # Global state (DATA_FILE_PATH, CONFIG_DATA, etc.)
│   ├── data.py                 # Data I/O (load_data, save_data, parse_triplet_column)
│   ├── positions.py            # Auto-fill position data (auto_add_missing_positions)
│   └── routes/                 # Route handlers (8 files)
│       ├── __init__.py
│       ├── nlp.py              # /nlp/* — NLP toolbar endpoints
│       ├── reviews.py          # /data/{idx}, /review/{idx}/save, /agent/chat
│       ├── settings.py         # /settings GET + PATCH
│       ├── ai.py               # /ai_prediction/{idx}, /live_prediction/{idx}
│       ├── upload.py           # /upload-data, /auto-add-positions
│       ├── timing.py           # /timing/{idx}, /avg-annotation-time
│       └── learning.py         # /learning/suggestions, /learning/predict/{idx}
│
├── services/                   # BACKEND — Business logic (5 files)
│   ├── __init__.py
│   ├── llm_providers.py        # Provider adapters (5 backends) + registry + factory
│   ├── prediction.py           # Prompt building, BM25 retrieval, dynamic Pydantic models
│   ├── nlp_helpers.py          # Lazy-loaded NLP tools (SentiNet, BERT, NlpToolkit, e5)
│   └── active_learning.py      # TF-IDF + LogisticRegression active learning
│
├── models/                     # BACKEND — Pydantic schemas (2 files)
│   ├── __init__.py
│   └── schemas.py              # SaveTripletsRequest, AgentChatRequest
│
├── cli/                        # CLI — Command-line tool (4 files)
│   ├── __init__.py             # Argparse + dispatch (592 lines, main())
│   ├── config.py               # ABSAAnnotatorConfig class
│   ├── runner.py               # Process management (start_backend, start_frontend)
│   └── convert.py              # STD format ↔ internal format conversion
│
├── frontend/                   # FRONTEND — React SPA
│   ├── index.html              # HTML entry point
│   ├── package.json            # Dependencies (React 19, Vite, DaisyUI, Tailwind)
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── public/                 # Static assets (3 files)
│   │   ├── index.html
│   │   ├── manifest.json
│   │   └── robots.txt
│   ├── build/                  # Production build output (4 files)
│   │   ├── index.html
│   │   ├── manifest.json
│   │   ├── robots.txt
│   │   └── assets/
│   │       └── index-a6690626.css
│   └── src/                    # Source code (19 files)
│       ├── index.tsx           # React entry point
│       ├── index.css           # Global styles (Tailwind directives)
│       ├── App.tsx             # Root component (770 lines, all state)
│       ├── App.css             # App-level styles
│       ├── types.ts            # All TypeScript interfaces
│       ├── phraseColoring.tsx  # Character-level highlight engine (312 lines)
│       ├── hooks/              # Custom React hooks (2 files)
│       │   ├── useTextSelection.ts    # DOM-based text selection
│       │   └── useTextSelection.test.ts
│       └── components/         # React components (15 .tsx files)
│           ├── ModelTripletColumn.tsx        # Side-by-side model comparison
│           ├── ModelTripletColumn.test.tsx
│           ├── ManualInputForm.tsx           # Manual triplet entry form
│           ├── PhraseAnnotator.tsx           # Click-to-select annotation on text
│           ├── AISuggestions.tsx             # AI prediction suggestions panel
│           ├── HelperAgentChatbox.tsx        # Chat panel with LLM agent
│           ├── HelperAgentChatbox.test.tsx
│           ├── SettingsPanel.tsx             # Configuration panel
│           ├── SettingsPanel.test.tsx
│           ├── EditReviewTextModal.tsx       # Review text editing modal
│           ├── NlpHelperToolbar.tsx          # NLP tools toolbar
│           ├── NlpHelperToolbar.test.tsx
│           ├── WelcomeOverlay.tsx            # First-load onboarding overlay
│           ├── ActiveLearningSuggestions.tsx # Active learning suggestions panel
│           └── CustomCheckbox.tsx            # Styled checkbox component
│
├── tests/                      # Python tests (7 files)
│   ├── __init__.py
│   ├── test_smoke.py
│   ├── test_prediction.py
│   ├── test_main_helpers.py
│   ├── test_nlp_helpers.py
│   ├── test_llm_providers.py
│   ├── test_live_prediction.py
│   └── testcases.md
│
├── evaluation/                 # Evaluation & user studies (5+ files)
│   ├── eval.py                 # Model evaluation runner
│   ├── eval_exc.py             # Evaluation exceptions/errors
│   ├── pool_a.json             # Evaluation pool A
│   ├── pool_b.json             # Evaluation pool B
│   └── user_study_results/     # User study data (16 JSON files)
│
├── examples/                   # Example data (3 files)
│   ├── example_config.json
│   ├── restaurant_reviews.json
│   └── semeval_absa.json
│
├── docs/                       # Documentation (1 file)
│   └── architecture_map.md
│
├── agentdocs/                  # Agent development docs (35+ files)
│   ├── ProjectPrimer.md
│   ├── tasks.md
│   ├── phase1/ ... phase7/
│   └── session_reports/
│
├── uploads/                    # Uploaded data files (runtime)
├── temp/                       # Temporary config files (runtime)
└── .planning/                  # Planning directory
    └── codebase/
```

---

## File Counts by Directory

| Directory | Source Files | Lines (approx) | Purpose |
|-----------|-------------|----------------|---------|
| `./` (root) | 2 | 58 + 23 (pyproject.toml) | Backend entry points + project config |
| `app/` | 6 | ~580 | FastAPI application package |
| `app/routes/` | 8 | ~870 | API route handlers (7 routers) |
| `services/` | 5 | ~1550 | Business logic services |
| `models/` | 2 | ~16 | Pydantic request schemas |
| `cli/` | 4 | ~1000 | CLI argument parsing + process management |
| `frontend/src/` | 19 | ~3200 | React SPA source code |
| `frontend/src/components/` | 15 | ~1800 | React components (15 .tsx) |
| `frontend/src/hooks/` | 2 | ~160 | React hooks |
| `tests/` | 8 | ~300 | Python test suite |
| `evaluation/` | 4 | ~200 | Evaluation scripts |
| `examples/` | 3 | — | Example data files |
| `agentdocs/` | 35+ | ~5000 | Agent development docs |

**Total lines of source code (excluding examples, docs, agentdocs): ~6200**

---

## Key File Responsibilities

### Backend

| File | Lines | Responsibility |
|------|-------|----------------|
| `main.py` | 52 | FastAPI app creation, CORS, route registration, startup event |
| `app/config.py` | 113 | Global state: file path, file type, config data, config load/save functions |
| `app/data.py` | 194 | Data I/O (CSV/JSON), triplet parsing (tuple/list/dict), comparison CSV loading, metadata queries |
| `app/positions.py` | 147 | Auto-fill missing `at_start`/`at_end`/`ot_start`/`ot_end` positions for existing annotations |
| `app/routes/reviews.py` | 220 | Main data endpoint (`GET /data/{idx}`), save endpoint (`POST /review/{idx}/save`), agent chat (`POST /agent/chat`) |
| `app/routes/settings.py` | 97 | Configuration read/write (`GET /settings`, `PATCH /settings`) |
| `app/routes/ai.py` | 181 | AI prediction (`GET /ai_prediction/{idx}`) and live compare prediction (`GET /live_prediction/{idx}`) |
| `app/routes/nlp.py` | 51 | NLP tool endpoints (lexicon, sentiment, morphology, embedding) |
| `app/routes/upload.py` | 54 | File upload and position auto-fill trigger |
| `app/routes/timing.py` | 83 | Annotation timing storage and aggregation |
| `app/routes/learning.py` | 169 | Active learning: uncertainty sampling suggestions and ML-based predictions |
| `services/llm_providers.py` | 687 | Hexagonal provider pattern: LLMProviderPort protocol, 5 adapters (Ollama, OpenAI, Anthropic, vLLM, CustomOpenAI), registry, factory, derivation, validation |
| `services/prediction.py` | 378 | Prompt template building (Turkish), BM25 retrieval, dynamic Pydantic model generation, phrase position finding |
| `services/nlp_helpers.py` | 230 | Lazy-loaded NLP tools: SentiNet lexicon, BERT Turkish sentiment, NlpToolkit morphology, e5-small embeddings |
| `services/active_learning.py` | 190 | TF-IDF → OneVsRestClassifier pipeline, entropy-based uncertainty scoring |

### CLI

| File | Lines | Responsibility |
|------|-------|----------------|
| `cli/__init__.py` | ~592 | Argparse definitions (40+ flags), config assembly, STD format conversion, dispatch to runner |
| `cli/config.py` | 258 | `ABSAAnnotatorConfig` — fluent config builder with setter methods, JSON save/load |
| `cli/runner.py` | 180 | `start_backend()` (uvicorn subprocess), `start_frontend()` (npm run dev), `start_full_app()` (both in threads) |
| `cli/convert.py` | 33 | `std_triplets_to_label()` — STD-format triplet string to internal dict format |

### Frontend

| File | Lines | Responsibility |
|------|-------|----------------|
| `App.tsx` | 770 | Root component: all state, all API calls, keyboard shortcuts, modal management |
| `types.ts` | 126 | All TypeScript interfaces: TripletItem, ReviewComparisonData, ChatMessage, Settings, AppActions |
| `phraseColoring.tsx` | 312 | Color engine: 25 Tailwind color classes, character-level highlight rendering, color mixing for overlaps |
| `hooks/useTextSelection.ts` | 140 | DOM Range walking for character-level text selection, token snapping, phrase cleaning |

### Tests

| File | Responsibility |
|------|----------------|
| `tests/test_smoke.py` | Backend connectivity and basic operations |
| `tests/test_prediction.py` | Prediction service functions (prompt building, BM25, positions) |
| `tests/test_main_helpers.py` | Helper functions from data.py and config.py |
| `tests/test_nlp_helpers.py` | NLP helper tool unit tests |
| `tests/test_llm_providers.py` | LLM provider adapter tests |
| `tests/test_live_prediction.py` | Live compare mode prediction tests |

---

## Module Dependency Relationships

### Backend Dependencies

```
main.py
  ├── app.config.*            (global state)
  ├── app.data.*              (load_data, save_data, parse_triplet_column)
  ├── app.positions.*         (auto_add_missing_positions)
  ├── app.routes.nlp          (mount /nlp/*)
  ├── app.routes.settings     (mount /settings)
  ├── app.routes.reviews      (mount /data, /review, /agent/chat)
  ├── app.routes.ai            (mount /ai_prediction, /live_prediction)
  ├── app.routes.timing        (mount /timing)
  ├── app.routes.upload        (mount /upload)
  └── app.routes.learning      (mount /learning)

app/routes/reviews.py
  ├── app.config               (CONFIG_DATA, DATA_FILE_PATH, DATA_FILE_TYPE)
  ├── app.data                 (load_data, save_data, parse_triplet_column, _load_comparison_csv)
  ├── models.schemas           (SaveTripletsRequest, AgentChatRequest)
  ├── services.llm_providers   (get_provider, _derive_provider, validate_provider_config)
  ├── services.prediction      (DEFAULT_CHAT_TEMPLATE, generate_mock_reasoning, get_most_similar_examples)
  └── services.llm_providers   (indirect)

app/routes/ai.py
  ├── app.config               (CONFIG_DATA, DATA_FILE_TYPE, load_config)
  ├── app.data                 (load_data)
  ├── services.llm_providers   (_derive_provider, get_provider, validate_provider_config, validate_per_model_config)
  └── services.prediction      (DEFAULT_LABELING_TEMPLATE, find_phrase_positions)

app/routes/learning.py
  ├── app.config               (CONFIG_DATA, DATA_FILE_TYPE)
  ├── app.data                 (load_data)
  └── services.active_learning (get_uncertainty_scores, labeled_texts_from_data, train_labeled_data)

app/routes/settings.py
  ├── app.config               (CONFIG_DATA, CONFIG_PATH)
  └── app.data                 (get_total_count, get_current_index, max_number_of_idxs)

app/routes/nlp.py
  └── services.nlp_helpers     (lexicon_polarity, sentiment_classify, morphology, embedding_similarity)

services/llm_providers.py
  ├── services.prediction      (build_prediction_prompt, build_absa_models)
  ├── ollama                   (external)
  ├── openai                   (external)
  ├── anthropic                (external)
  └── pydantic/BaseModel       (external)

services/prediction.py
  ├── rank_bm25.BM25Okapi      (external)
  ├── pydantic/BaseModel, create_model (external)
  └── enum.Enum                (stdlib)

services/nlp_helpers.py
  ├── SentiNet.SentiNet        (external)
  ├── transformers.pipeline    (external — BERT)
  ├── NlpToolkit               (external)
  ├── sentence_transformers    (external — e5-small)
  └── WordNet.WordNet          (external)

services/active_learning.py
  ├── sklearn (TfidfVectorizer, LogisticRegression, OneVsRestClassifier) (external)
  ├── scipy.stats.entropy      (external)
  └── numpy                    (external)
```

### Frontend Dependencies

```
App.tsx
  ├── types                    (TripletItem, ReviewComparisonData, ChatMessage, Settings, AppActions)
  ├── components/*             (all 11 components imported)
  └── react (useState, useEffect, useRef, useCallback) (library)

components/ModelTripletColumn.tsx
  ├── types                    (TripletItem)
  └── components/CustomCheckbox

components/PhraseAnnotator.tsx
  ├── hooks/useTextSelection   (text selection hook)
  ├── types                    (TripletItem, AspectItem)
  └── phraseColoring           (createTextHighlights, renderHighlightedText, etc.)

components/HelperAgentChatbox.tsx
  └── types                    (ChatMessage, AppActions, ReviewComparisonData)

hooks/useTextSelection.ts
  └── react (useState, useCallback, useMemo)

phraseColoring.tsx
  └── types                    (AspectItem, ColorClasses)
```

### CLI Dependencies

```
cli.py (entry)
  └── cli/__init__.py:main()

cli/__init__.py
  ├── cli/config               (ABSAAnnotatorConfig)
  ├── cli/runner               (start_backend, start_frontend, start_full_app)
  ├── cli/convert              (std_triplets_to_label)
  └── services.llm_providers   (_derive_provider, validate_provider_config)

cli/runner.py
  ├── cli/config               (ABSAAnnotatorConfig)
  ├── subprocess               (stdlib — uvicorn)
  ├── threading                (stdlib)
  └── socket/signal/atexit     (stdlib)

cli/config.py
  └── services.prediction      (DEFAULT_LABELING_TEMPLATE, DEFAULT_CHAT_TEMPLATE)

cli/convert.py
  └── ast.literal_eval         (stdlib)
```

---

## Dependency Graph (Simplified)

```
                          ┌──────────┐
                          │  cli.py  │
                          └────┬─────┘
                               │
                    ┌──────────┴──────────┐
                    │  cli/__init__.py    │
                    └──────────┬──────────┘
                               │
         ┌────────────────────┼────────────────────┐
         │                    │                     │
   cli/config.py       cli/runner.py         cli/convert.py
         │                    │
         │                    ▼
         │            main.py (uvicorn)
         │                 │
         ▼                 ▼
  services.prediction ──► routes/* ◄── app/data.py
         │                 │            app/config.py
         ▼                 │            app/positions.py
  services/llm_providers   │
         │                 ▼
         ▼           services/nlp_helpers.py
  Ollama / OpenAI /         │
  Anthropic / vLLM /   BERT / SentiNet /
  CustomOpenAI         NlpToolkit / e5

  frontend/src/App.tsx ◄── REST/HTTP ──► routes/*
       │
       ├── components/ModelTripletColumn
       ├── components/ManualInputForm
       ├── components/PhraseAnnotator ◄── hooks/useTextSelection
       ├── components/HelperAgentChatbox
       ├── components/AISuggestions
       ├── components/SettingsPanel
       ├── components/NlpHelperToolbar
       └── components/ActiveLearningSuggestions
```

---

## Key Architecture Patterns

1. **Hexagonal (Ports & Adapters)** — `services/llm_providers.py` defines an `LLMProviderPort` protocol with `predict()` and `chat()` methods. Five adapter classes implement it. The `get_provider()` factory returns the right adapter based on config.

2. **Lazy Loading** — `services/nlp_helpers.py` loads heavy NLP models (BERT, SentiNet, NlpToolkit, e5-small) only on first call, cached in module-level globals.

3. **Global Mutable Config** — `app/config.py` uses module-level globals (`CONFIG_DATA`, `DATA_FILE_PATH`, etc.) that are mutated by CLI setup, settings API, and file uploads. Simple but not thread-safe.

4. **Dynamic Pydantic Models** — `services/prediction.py:build_absa_models()` generates Pydantic models at runtime with enums constrained to valid phrases from the review text, enabling structured JSON output from LLMs.

5. **BMI-based Similarity** — `services/prediction.py:get_most_similar_examples()` uses BM25 Okapi for few-shot example retrieval, falling back to simple truncation if rank_bm25 is unavailable.

6. **File-based Persistence** — No database. All annotations stored in CSV or JSON files. Config stored as JSON. Simple, portable, git-friendly.

7. **Single Component State** — All frontend state lives in `App.tsx` using `useState` hooks, passed to children as props. No global state management library.
