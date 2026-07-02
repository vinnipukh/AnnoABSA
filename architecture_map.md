# AnnoABSA — Architecture Map

Purpose: let a coding agent orient without reading the whole codebase. This is the current
(as-is) architecture plus the one planned change (LLM-provider ports/adapters, see bottom).
Treat line numbers as approximate — verify against the actual file before editing, they will
drift as tasks land.

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

## 2. Backend module graph (`main.py`, ~1178 lines, monolithic — no internal module boundaries yet)

```
main.py
│
├─ Module-level state (set once at import, mutated by set_* functions)
│  ├─ DATA_FILE_PATH, DATA_FILE_TYPE  ← from env ABSA_DATA_PATH        (~L18-19)
│  ├─ CONFIG_PATH, CONFIG_DATA        ← from env ABSA_CONFIG_PATH      (~L20-35, load_config)
│  └─ AUTO_POSITIONS                  ← from CONFIG_DATA               (~L33)
│
├─ Data I/O layer (no class, just functions operating on module globals)
│  ├─ load_data() / save_data(data)                                    (~L82-100)
│  │    reads/writes DATA_FILE_PATH as CSV (pandas) or JSON, branching on DATA_FILE_TYPE
│  ├─ find_phrase_positions(text, phrase)                               (~L464)
│  └─ auto_add_missing_positions()                                      (~L485-560)
│       calls load_data/save_data, fills at_start/at_end/ot_start/ot_end by text.find()
│
├─ Pydantic request/response models                                    (~L116-140)
│  ├─ Item, AnnotationData, SaveTripletsRequest, AgentChatRequest
│
├─ HTTP endpoints (FastAPI decorators — this IS the app's public contract)
│  ├─ GET  /settings                          get_settings()            (~L141)
│  │       → returns CONFIG_DATA as JSON (categories, polarities, flags for frontend)
│  ├─ GET  /data/{data_idx}                   get_data()                (~L240)
│  │       → calls load_data(), parse_triplet_column() for comparison columns,
│  │         returns {text, label, translation, aspect_category_list,
│  │                   deepseek_triplets, qwen_triplets, ...}
│  │       ⚠ deepseek/qwen names are hardcoded — Task 2 generalizes this
│  ├─ GET  /data/count                        get_total_count()         (~L334)
│  ├─ GET  /data/current-index                get_current_index()       (~L345)
│  ├─ GET  /data/max-index                    max_number_of_idxs()      (~L367)
│  ├─ POST /data/{data_idx}                   post_data()               (~L380)
│  ├─ POST /annotations/{data_idx}            post_annotations()        (~L399)
│  │       → writes to the `label` field via save_data(). THE canonical save path
│  │         for manual annotations. STD-format loaded data flows through here
│  │         unmodified once converted at load time (see Task 1).
│  ├─ POST /timing/{data_idx}                 post_timing()             (~L429)
│  ├─ POST /auto-add-positions                manual_auto_add_positions() (~L629)
│  ├─ GET  /ai_prediction/{data_idx}          get_ai_prediction()       (~L934)
│  │       → dispatches to predict_llm() or predict_openai() based on
│  │         CONFIG_DATA['openai_key'] presence (implicit priority — Task 3 replaces
│  │         this with an explicit --llm-provider flag + 4-way dispatch)
│  ├─ GET  /avg-annotation-time                get_avg_annotation_time() (~L1042)
│  ├─ POST /review/{data_idx}/save            save_review_triplets()    (~L1118)
│  │       → SECOND save path, used by App.tsx's current three-column UI
│  │         (distinct from POST /annotations/{data_idx} — verify which one
│  │         each frontend flow actually calls before assuming; don't assume
│  │         they're interchangeable)
│  └─ POST /agent/chat                        agent_chat()              (~L1140)
│          → Helper Agent chat panel backend. OpenAI-only today (Task 3/4 extend
│            this to all 4 providers). Contains its own hardcoded prompt string
│            and hardcoded "DeepSeek"/"Qwen" references (Task 4 fixes both).
│
├─ LLM prediction functions (the part becoming ports/adapters — see §4)
│  ├─ predict_llm(...)     — Ollama, lazy `from ollama import generate`         (~L640)
│  ├─ predict_openai(...)  — OpenAI, lazy `from openai import OpenAI`           (~L734)
│  ├─ get_most_similar_examples(input_text, examples, n)  — BM25 retrieval      (~L851)
│  │       tokenizes via `\b\w+\b` regex + lowercase, NO Turkish stemming
│  └─ find_valid_phrases_list(text, max_tokens_in_phrase)                       (~L908)
│
└─ Comparison/reasoning helpers
   ├─ parse_triplet_column(raw_val, prefix)   — ast.literal_eval STD-syntax parser (~L176)
   │       currently only feeds comparison columns; Task 1 reuses its approach for
   │       the main label field via a sibling converter, not this function directly
   └─ generate_mock_reasoning(text, ds_list, qw_list)  — hardcoded model names (~L209)
```

### Data flow for a single review, end to end (current/as-is)

```
CSV/JSON file (DATA_FILE_PATH)
   │  load_data()
   ▼
GET /data/{idx}  ──▶  {text, label, translation, aspect_category_list,
                        deepseek_triplets, qwen_triplets}
   │
   ▼ (frontend renders three columns)
User annotates in ManualInputForm  ──▶  POST /annotations/{idx}  (or /review/{idx}/save —
                                          confirm which one App.tsx actually calls)
   │  save_data()
   ▼
CSV/JSON file (DATA_FILE_PATH)   ← same file, now updated
```

## 3. Frontend module graph (`frontend/src/`)

```
App.tsx  (single top-level component, owns ALL state — no state management library)
│  state: currentIndex, reviewData, manualTriplets, chatMessages, isDark, ...
│  fetches: GET /data/{idx}, GET /settings, POST /review/{idx}/save (or /annotations/{idx})
│
├─ components/ModelTripletColumn.tsx
│     props: title, badgeText, triplets — GENERIC, already reusable (title/badge are props,
│     not hardcoded) — the hardcoding lives in what App.tsx PASSES to it, and in main.py's
│     response field names (deepseek_triplets/qwen_triplets), not in this component itself.
│
├─ components/ManualInputForm.tsx
│     props: text/onSubmit-style form callbacks — plain dropdown+text entry, NO click-to-select
│     span interaction (Task 5 adds that as a new sibling component, doesn't modify this one
│     unless explicitly told to keep it as an alternate simpler mode).
│
├─ components/HelperAgentChatbox.tsx
│     props: chat messages, send handler — talks to POST /agent/chat.
│
├─ components/CustomCheckbox.tsx        — generic, no app-specific logic
├─ components/DarkModeToggle.tsx        — generic, pairs with hooks/useDarkMode.ts
├─ hooks/useDarkMode.ts
├─ phraseColoring.tsx                    — polarity→color mapping (reuse for Task 5's
│                                           span-highlighting, don't invent new colors)
└─ types.ts                              — TripletItem, ReviewComparisonData, ChatMessage
      ReviewComparisonData.deepseek_triplets/qwen_triplets ← Task 2 renames these
```

## 4. Planned: LLM-provider ports/adapters (the agreed hexagonal slice — nothing else)

**Scope boundary, stated explicitly**: this is the ONLY part of the app being hexagonal-ized
right now. Do not extract ports/adapters for data storage, HTTP endpoints, or anything else —
that's explicitly out of scope per the user's decision. The rest of `main.py` stays as-is
(monolithic FastAPI functions operating on module globals) until/unless a separate decision is
made later.

### Why this slice specifically

Task 3 already requires four interchangeable LLM backends (Ollama, OpenAI, Anthropic, vLLM)
behind one dispatch point (`get_ai_prediction`). That's structurally already a port with
multiple adapters — the only gap is that today it's an if/elif on config keys calling four
free functions with duplicated signatures, not a defined interface.

### Target shape (minimum viable, no more)

```
Port (interface, one method):
    predict(text, considered_sentiment_elements, examples, aspect_categories,
            polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms,
            n_few_shot, llm_model) -> Aspects

Adapters (one class/module per provider, each implements the port):
    OllamaAdapter     — wraps today's predict_llm body
    OpenAIAdapter      — wraps today's predict_openai body
    AnthropicAdapter   — new, Task 3
    VLLMAdapter        — new, Task 3 (thin wrapper around OpenAIAdapter with base_url)

Dispatch (replaces today's if config['openai_key'] implicit-priority logic):
    get_provider(config) -> one of the above, selected via explicit --llm-provider flag
```

**What this buys you**: `get_ai_prediction` and `agent_chat` (Task 4 extends chat to all
providers too) both call `provider.predict(...)` without knowing which backend it is. Adding a
5th provider later means writing one new adapter class, zero changes to call sites.

**What this explicitly does NOT include** (don't scope-creep into these):
- No dependency-injection framework — plain Python, a dict or simple factory function mapping
  provider name → adapter instance is sufficient for 4 options.
- No change to how `get_ai_prediction`/`agent_chat` are invoked from FastAPI — they stay exactly
  where they are, just call the port instead of branching directly on provider logic inline.
- No abstraction of the BM25 retrieval (`get_most_similar_examples`) — that's shared
  infrastructure the port's adapters call into, not something to hide behind another interface
  unless a second retrieval method is actually needed (it isn't, right now).
- Prompt construction (Task 4) can live either inside each adapter or as a shared helper the
  port calls before dispatching — pick whichever is less code; don't add a "prompt builder"
  interface for its own sake with only one implementation.

### Where this lands relative to Phase 1 tasks

Implement this shape **as part of Task 3**, not as a separate refactor pass — Task 3 was
already going to touch `predict_llm`/`predict_openai`/`get_ai_prediction` and add two new
provider functions; building them as adapters from the start avoids writing four free
functions now and converting them to classes later. If Task 3 is already in progress or done
as free functions, wrapping them in thin adapter classes afterward is a small follow-up, not a
rewrite.

## 5. File-to-task map (which Phase 1 task touches which file/region)

| File | Region | Task(s) |
|---|---|---|
| `main.py` | `load_data`/`save_data`, module-level DATA_FILE_* | Task 1 (indirectly — conversion happens in `cli.py`, not here, per Option A) |
| `main.py` | `get_data` (~L240), `generate_mock_reasoning` (~L209) | Task 2 |
| `main.py` | `predict_llm`, `predict_openai`, `get_ai_prediction` | Task 3 (+ hexagonal slice, §4) |
| `main.py` | `agent_chat` (~L1140) | Task 3 (provider dispatch), Task 4 (prompt) |
| `main.py` | prompt strings inside `predict_llm`/`predict_openai` | Task 4 |
| `main.py` | position logic (`auto_add_missing_positions`, `find_phrase_positions`) | Task 5 (read-only reference, not modified) |
| `cli.py` | argparse block (~L393-463) | Task 1 (`--format std`), Task 3 (`--llm-provider`, `--anthropic-key`, `--vllm-base-url`) |
| `cli.py` | `start_backend` (~L228) | Task 1 (STD conversion happens here, Option A) |
| `cli.py` | `ABSAAnnotatorConfig` | Task 4 (new prompt-template config fields) |
| `frontend/src/App.tsx` | top-level layout, mode state | Task 5 (mode toggle, chat-panel toggle) |
| `frontend/src/types.ts` | `ReviewComparisonData` | Task 2 (rename fields) |
| `frontend/src/components/ModelTripletColumn.tsx` | — | Task 2 (consumer, not modified itself) |
| `frontend/src/components/ManualInputForm.tsx` | — | Task 5 (new sibling component, this one likely untouched) |
| new: `frontend/src/components/PhraseAnnotator.tsx` | — | Task 5 (new file) |

## 6. Known landmines (don't rediscover these — read once, remember)

- **Two save endpoints exist** (`POST /annotations/{idx}` and `POST /review/{idx}/save`) —
  confirm which one the current frontend flow actually uses before assuming either is dead
  code or the "main" one.
- **`set_data_file()` in `main.py` is dead code** — nothing calls it. The actual mechanism is
  the module-level `os.environ.get('ABSA_DATA_PATH', ...)` line at import time.
- **`'NULL'` is a literal string sentinel for implicit aspects/opinions**, checked via
  `!= 'NULL'` in `auto_add_missing_positions`. Never convert it to `""` — that breaks the
  existing convention (see Task 1 kickoff doc for the full reasoning).
- **BM25 tokenization has no Turkish stemming** — plain `\b\w+\b` regex + lowercase. This will
  matter more as Task 3/4 lean harder on retrieval quality; not itself a Phase 1 task, but
  don't assume "more few-shot examples" (a Phase 3 item) will help without this being fixed
  first.
- **`aspect_category`/`sentiment_polarity` values stay in English** — confirmed user decision,
  not an oversight. Don't translate them anywhere.