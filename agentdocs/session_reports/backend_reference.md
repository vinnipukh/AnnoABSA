# Backend — Function Reference

**Root:** `C:\Users\arhan\PycharmProjects\AnnoABSA\`
**Purpose:** FastAPI backend for AnnoABSA. Serves annotation data, manages CSV/JSON persistence,
dispatches LLM predictions via pluggable provider adapters, and handles the Helper Agent chat endpoint.

**Architecture:** After Phase 5 breakup, `main.py` is a thin launcher (~50 lines). All logic lives in `app/` modules and `app/routes/` files.

| File | Lines | Purpose |
|---|---|---|
| `main.py` | ~50 | Thin launcher: imports from `app/`, mounts route routers, startup event |
| `app/config.py` | ~111 | Global state (`DATA_FILE_PATH`, `CONFIG_DATA`, etc.) + config functions (`load_config`, `set_config`) |
| `app/data.py` | ~195 | Data I/O (`load_data`, `save_data`, `parse_triplet_column`) + navigation helpers (`get_total_count`, `get_current_index`) |
| `app/positions.py` | ~147 | Position auto-fill logic (`auto_add_missing_positions`) |
| `app/routes/settings.py` | ~96 | GET/PATCH /settings endpoints |
| `app/routes/reviews.py` | ~190 | GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat |
| `app/routes/ai.py` | ~180 | GET /ai_prediction/{idx}, GET /live_prediction/{idx} |
| `app/routes/timing.py` | ~82 | POST /timing/{idx}, GET /avg-annotation-time |
| `app/routes/upload.py` | ~53 | POST /upload-data, POST /auto-add-positions |
| `app/routes/nlp.py` | ~51 | APIRouter for 4 NLP endpoints (lexicon-polarity, sentiment, morphology, embedding-similarity) |
| `models/schemas.py` | ~12 | Pydantic request models |
| `services/prediction.py` | ~357 | Prompt building, BM25 retrieval, position logic, template constants |
| `services/llm_providers.py` | ~557 | LLM provider adapters, registry, factory, dispatch, per-model config validation |
| `services/nlp_helpers.py` | ~280 | NLP Helper Toolbar: 4 lazy-loaded tools (SentiNet, BERT, NlpToolkit, e5-small) |
| `cli.py` | ~962 | Argparse-based launcher, starts backend + frontend as subprocesses |

---

## app/config.py — Module-Level State

These global variables hold the backend's runtime configuration. Set once at import time from
environment variables, then mutated by uploads and config changes.

| Variable | Set by | Purpose |
|---|---|---|
| `DATA_FILE_PATH` | `ABSA_DATA_PATH` env var or `upload_data` | Path to the active CSV or JSON dataset |
| `DATA_FILE_TYPE` | Derived from file extension | `"json"` or `"csv"` |
| `CONFIG_PATH` | `ABSA_CONFIG_PATH` env var | Path to the JSON config file |
| `CONFIG_DATA` | Config file loaded at import | Dict of all annotation settings |
| `AUTO_POSITIONS` | `auto_positions` key in `CONFIG_DATA` | Whether to auto-fill positions on startup |

### Config Functions

#### `set_data_file(file_path: str)`
- **Purpose:** Update the active data file path and detect JSON vs CSV.
- **Called by:** `cli.py` at startup, `upload_data` endpoint.
- **Side effects:** Mutates globals `DATA_FILE_PATH` and `DATA_FILE_TYPE`.

#### `set_config_file(config_path: str)`
- **Purpose:** Set the path to the JSON config file.
- **Called by:** `cli.py` at startup.
- **Side effects:** Mutates global `CONFIG_PATH`.

#### `load_config() -> dict`
- **Purpose:** Read config JSON from disk (or return defaults).
- **Called by:** `get_ai_prediction`, `agent_chat`, and other request handlers that need fresh config values.
- **Returns:** Full config dict with defaults for all keys.

#### `set_config(config_dict: dict)`
- **Purpose:** Replace the entire `CONFIG_DATA` dict (e.g. from CLI config).
- **Called by:** `cli.py` when loading a saved config file.

---

## app/data.py — Data I/O

#### `load_data() -> list | pd.DataFrame`
- **Purpose:** Read the current dataset from disk.
- **Called by:** Every data endpoint (`get_data`, `save_review_triplets`, `get_ai_prediction`, etc.).
- **Returns:** List of dicts for JSON, `pd.DataFrame` for CSV.

#### `save_data(data)`
- **Purpose:** Write data back to disk. Handles JSON (`json.dump`) and CSV (`df.to_csv`).
- **Called by:** `post_timing`, `save_review_triplets`, `auto_add_missing_positions`.

#### `parse_triplet_column(raw_val, prefix="t") -> list`
- **Purpose:** Parse a Python list-literal string into triplet dicts.
- **Handles:** STD tuple format, STD list format, dict format.
- **Handles empty/null:** `None`, `"nan"`, `"None"`, `"[]"`, `""` all return `[]`.
- **Called by:** `get_data()` and `_load_comparison_csv()`.
- **Backward-compat note:** Old-format CSV files with `aspect_triplets` / `new_triplets` columns are still supported.

#### `_load_comparison_csv(csv_path, data_idx, review_text, prefix) -> list`
- **Purpose:** Load triplets from an external comparison CSV.
- **Supports:** STD format (`review`, `triplet` columns) and per-row format.
- **Called by:** `get_data()`.

#### `get_total_count() -> int`
- **Purpose:** Return total number of rows/items in the dataset.
- **Called by:** `get_settings()`, frontend for pagination.

#### `get_current_index() -> int`
- **Purpose:** Find the first unannotated item.
- **Called by:** `get_settings()`.

#### `max_number_of_idxs() -> int`
- **Purpose:** Alias for `get_total_count()`.
- **Called by:** `get_settings()`.

---

## app/positions.py — Position Logic

#### `auto_add_missing_positions()`
- **Purpose:** Scan all rows and fill `at_start`/`at_end`/`ot_start`/`ot_end` for any phrase missing them.
- **Gate:** Only runs if `AUTO_POSITIONS` is `True`.
- **Called by:** `startup_event()` and the `/auto-add-positions` endpoint.

---

## models/schemas.py — Pydantic Request Models

| Model | Fields | Used by endpoint |
|---|---|---|
| `SaveTripletsRequest` | `triplets: list` | `POST /review/{idx}/save` |
| `AgentChatRequest` | `review_text`, `model_a_triplets`, `model_b_triplets`, `user_message`, `chat_history` | `POST /agent/chat` |

---

## services/prediction.py — Prediction Utilities

### Template Constants

| Constant | Purpose |
|---|---|
| `DEFAULT_LABELING_TEMPLATE` | Turkish-language prompt for ABSA triplet prediction. Placeholders: `{implicit_aspect_note}`, `{implicit_opinion_note}`, `{aspect_categories}`, `{polarities}`, `{element_names}`, `{element_keys}`. |
| `DEFAULT_CHAT_TEMPLATE` | Turkish-language prompt for the Helper Agent. Placeholders: `{review_text}`, `{model_a_name}`, `{model_a_triplets}`, `{model_b_name}`, `{model_b_triplets}`. |

### Functions

#### `build_prediction_prompt(text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, prompt_template=None) -> tuple`
- **Purpose:** Build the LLM prompt for ABSA prediction and retrieve few-shot examples.
- **Returns:** `(prompt_string, few_shot_examples_list)`.
- **Called by:** All provider adapters' `predict()` methods.

#### `build_absa_models(text, considered_sentiment_elements, polarities, aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms) -> tuple`
- **Purpose:** Build dynamic Pydantic model and Enums for structured LLM output.
- **Called by:** All provider adapters' `predict()` methods.

#### `get_most_similar_examples(input_text, examples, n) -> list`
- **Purpose:** BM25-based retrieval of the n most similar labeled examples.
- **Called by:** `build_prediction_prompt()`.

#### `find_valid_phrases_list(text, max_tokens_in_phrase=None) -> list`
- **Purpose:** Enumerate all valid sub-phrases from text for structured output.
- **Called by:** `build_absa_models()`.

#### `find_phrase_positions(text, phrase) -> tuple`
- **Purpose:** Locate a phrase in text (exact match first, then case-insensitive).
- **Returns:** `(start, end)` 0-indexed inclusive, or `(None, None)` if not found.
- **Called by:** `get_ai_prediction()` in `app/routes/ai.py`, `auto_add_missing_positions()` in `app/positions.py`.
- **Note:** If phrase is `"NULL"` or empty, returns `(None, None)` without searching.

#### `generate_mock_reasoning(text, model_a_name, model_b_name, model_a_list, model_b_list) -> str`
- **Purpose:** Produce a Turkish-language analysis comparing two model outputs.
- **Called by:** `get_data()` in `app/routes/reviews.py`.

---

## services/llm_providers.py — LLM Provider Adapters

### Provider Registry

```
PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "vllm": VLLMProvider,
}
```

### Dispatch Functions

#### `_derive_provider(config: dict) -> str`
- **Purpose:** Derive the LLM provider name from config settings.
- **Called by:** `get_ai_prediction()` in `app/routes/ai.py`, `agent_chat()` in `app/routes/reviews.py`.

#### `validate_provider_config(provider_name: str, config: dict) -> list[str]`
- **Purpose:** Check that the chosen provider has its required config keys.
- **Called by:** Endpoints in `app/routes/ai.py` and `app/routes/reviews.py`.

#### `validate_per_model_config(role: str, config: dict) -> list[str]`
- **Purpose:** Validate per-model config completeness (Phase 4 Live Compare Mode).
- **Called by:** `get_live_prediction()` in `app/routes/ai.py`.

#### `get_provider(provider_name: str, config: dict) -> ProviderClass`
- **Purpose:** Factory — instantiate the right provider adapter.

### Provider Adapter Classes

| Provider | Requires | `predict()` | `chat()` |
|---|---|---|---|
| **`OllamaProvider`** | Running Ollama server (default `localhost:11434`) | `predict(temperature=0.7)` — `ollama.generate` with Pydantic `model_json_schema()` for structured output | `ollama.chat()` |
| **`OpenAIProvider`** | `openai_key` in config | `predict(temperature=0.7)` — `client.beta.chat.completions.parse` with Pydantic `response_format` | `client.chat.completions.create` |
| **`AnthropicProvider`** | `anthropic_key` in config | `predict(temperature=0.7)` — `client.messages.create`, parses JSON from response text | Same, with OpenAI→Anthropic format conversion |
| **`VLLMProvider`** | `vllm_url` in config | `predict(temperature=0.7)` — Standard completion + manual JSON parse | OpenAI client with custom `base_url` |

### Backward-Compatible Wrapper

#### `predict_llm(text, ...) -> tuple`
- **Purpose:** Predict triplets via Ollama. Wraps `OllamaProvider.predict()`.
- **Status:** Legacy — kept for `eval.py` which imports it by name.

---

## Endpoints by Route File

### `app/routes/settings.py` — Settings (2 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/settings` | `get_settings()` | Return config + row count (acts as health check) |
| PATCH | `/settings` | `update_settings()` | Merge config updates into CONFIG_DATA + persist to JSON file |

### `app/routes/reviews.py` — Reviews & Agent (3 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/data/{data_idx}` | `get_data()` | Return a row's review text, label, comparison triplets, reasoning |
| POST | `/review/{data_idx}/save` | `save_review_triplets()` | **PRIMARY save** — called by `handleNextReview` in both modes |
| POST | `/agent/chat` | `agent_chat()` | Handle Helper Agent chat messages |

### `app/routes/ai.py` — AI Predictions (2 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/ai_prediction/{data_idx}` | `get_ai_prediction()` | Generate AI predictions via configured LLM provider |
| GET | `/live_prediction/{data_idx}` | `get_live_prediction()` | Generate AI predictions using per-model config for Live Compare Mode. Requires `?role=model_a\|model_b` |

### `app/routes/timing.py` — Timing (2 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| POST | `/timing/{data_idx}` | `post_timing()` | Append a timing entry (duration + change flag) |
| GET | `/avg-annotation-time` | `get_avg_annotation_time()` | Calculate average annotation duration |

### `app/routes/upload.py` — Upload & Positions (2 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| POST | `/upload-data` | `upload_data()` | Accept CSV/JSON upload, activate as current dataset |
| POST | `/auto-add-positions` | `manual_auto_add_positions()` | Manually trigger `auto_add_missing_positions()` |

### `app/routes/nlp.py` — NLP Helper Toolbar (4 endpoints)

| Method | Path | Handler | Purpose |
|---|---|---|---|
| GET | `/nlp/lexicon-polarity` | `get_lexicon_polarity()` | Per-word sentiment lookup via SentiNet lexicon |
| GET | `/nlp/sentiment` | `get_sentiment()` | Sentence-level sentiment classification via BERT |
| GET | `/nlp/morphology` | `get_morphology()` | Morphological analysis via NlpToolkit |
| GET | `/nlp/embedding-similarity` | `get_embedding_similarity()` | Cosine similarity between selection and full sentence via e5-small |

All four NLP endpoints use lazy imports — models load on first request, not at server startup.

---

## Startup Event

### `startup_event()` (in `main.py`)
- **Registered with:** `@app.on_event("startup")`
- **Purpose:** Log data file and config paths; optionally run `auto_add_missing_positions()` if `AUTO_POSITIONS` is enabled.

---

## CORS Middleware

Configured to allow all origins (`*`), all methods, all headers. No authentication.

---

## Error Handling Pattern

All endpoints wrap their handler body in `try/except FileNotFoundError` (→ `404`) and
`try/except Exception` (→ `500`). Exceptions from `_derive_provider()` (ambiguity errors)
are caught and re-raised as `HTTPException(400)`.
