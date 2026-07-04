# main.py — Function Reference

**File:** `C:\Users\arhan\PycharmProjects\AnnoABSA\main.py`
**Lines:** ~1750
**Purpose:** FastAPI backend for AnnoABSA. Serves annotation data, manages CSV/JSON persistence, dispatches LLM predictions via pluggable provider adapters, and handles the Helper Agent chat endpoint.

---

## Module-Level State

These global variables hold the backend's runtime configuration. Set once at import time from environment variables, then mutated by uploads and config changes.

| Variable | Set by | Purpose |
|---|---|---|
| `DATA_FILE_PATH` | `ABSA_DATA_PATH` env var or `upload_data` | Path to the active CSV or JSON dataset |
| `DATA_FILE_TYPE` | Derived from file extension | `"json"` or `"csv"` |
| `CONFIG_PATH` | `ABSA_CONFIG_PATH` env var | Path to the JSON config file |
| `CONFIG_DATA` | Config file loaded at import | Dict of all annotation settings |
| `AUTO_POSITIONS` | `auto_positions` key in CONFIG_DATA | Whether to auto-fill positions on startup |
| `UPLOAD_DIR` | Hardcoded to `uploads/` | Where uploaded files are saved |

---

## Template Constants

| Constant | Purpose |
|---|---|
| `DEFAULT_LABELING_TEMPLATE` | Turkish-language prompt for ABSA triplet prediction. Placeholders: `{implicit_aspect_note}`, `{implicit_opinion_note}`, `{aspect_categories}`, `{polarities}`, `{element_names}`, `{element_keys}`. |
| `DEFAULT_CHAT_TEMPLATE` | Turkish-language prompt for the Helper Agent. Placeholders: `{review_text}`, `{model_a_name}`, `{model_a_triplets}`, `{model_b_name}`, `{model_b_triplets}`. |

---

## Pydantic Request Models

| Model | Fields | Used by endpoint |
|---|---|---|
| `Item` | `name: str`, `value: int` | `POST /data/{idx}` (legacy) |
| `AnnotationData` | `name: str`, `value: list` | `POST /annotations/{idx}` (legacy) |
| `SaveTripletsRequest` | `triplets: list` | `POST /review/{idx}/save` |
| `AgentChatRequest` | `review_text`, `model_a_triplets`, `model_b_triplets`, `user_message`, `chat_history` | `POST /agent/chat` |

---

## Module-Level Functions

### `set_data_file(file_path: str)`
- **Purpose:** Update the active data file path and detect JSON vs CSV.
- **Called by:** `cli.py` at startup, `upload_data` endpoint.
- **Side effects:** Mutates globals `DATA_FILE_PATH` and `DATA_FILE_TYPE`.

### `set_config_file(config_path: str)`
- **Purpose:** Set the path to the JSON config file.
- **Called by:** `cli.py` at startup.
- **Side effects:** Mutates global `CONFIG_PATH`.

### `load_config() -> dict`
- **Purpose:** Read config JSON from disk (or return defaults).
- **Called by:** `get_ai_prediction`, `agent_chat`, and other request handlers that need fresh config values.
- **Returns:** Full config dict with defaults for all keys.

### `set_config(config_dict: dict)`
- **Purpose:** Replace the entire `CONFIG_DATA` dict (e.g. from CLI config).
- **Called by:** `cli.py` when loading a saved config file.

### `load_data() -> list | pd.DataFrame`
- **Purpose:** Read the current dataset from disk.
- **Called by:** Every data endpoint (`get_data`, `post_annotations`, `save_review_triplets`, etc.).
- **Returns:** List of dicts for JSON, `pd.DataFrame` for CSV.

### `save_data(data)`
- **Purpose:** Write data back to disk. Handles JSON (json.dump) and CSV (df.to_csv).
- **Called by:** `post_annotations`, `post_timing`, `save_review_triplets`, `auto_add_missing_positions`.

### `parse_triplet_column(raw_val, prefix="t") -> list`
- **Purpose:** Parse a Python list-literal string into triplet dicts.
- **Handles:** STD tuple format `[('term','CAT','pol')]`, STD list format `[['term','CAT','pol']]`, and dict format.
- **Handles empty/null:** `None`, `"nan"`, `"None"`, `"[]"`, `""` all return `[]`.
- **Called by:** `get_data()` and `_load_comparison_csv()`.

### `generate_mock_reasoning(text, model_a_name, model_b_name, model_a_list, model_b_list) -> str`
- **Purpose:** Produce a Turkish-language analysis comparing two model outputs.
- **Logic:** Finds common aspects, model-A-only and model-B-only aspects, generates a recommendation.
- **Called by:** `get_data()` when the CSV has no `reasoning` column.

### `_load_comparison_csv(csv_path, data_idx, review_text, prefix) -> list`
- **Purpose:** Load triplets from an external comparison CSV.
- **Supports:** STD format (`review`, `triplet` columns, matched by text) and per-row format (`review_id`, `aspect_term`, `aspect_category`, `sentiment_polarity`, matched by index).
- **Called by:** `get_data()`.

### `get_total_count() -> int`
- **Purpose:** Return the total number of rows/items in the dataset.
- **Called by:** `get_settings()`, frontend for pagination.

### `get_current_index() -> int`
- **Purpose:** Find the index of the first unannotated item.
- **Logic:** JSON → first entry without `"label"` key. CSV → first row with empty/NaN label. Returns `len(data)` if all annotated.
- **Called by:** `get_settings()`, frontend for initial load position.

### `max_number_of_idxs() -> int`
- **Purpose:** Alias for `get_total_count()`. Returns the max valid index + 1.
- **Called by:** `get_settings()`.

### `find_phrase_positions(text, phrase) -> tuple`
- **Purpose:** Locate a phrase in text (exact match first, then case-insensitive).
- **Returns:** `(start, end)` 0-indexed inclusive, or `(None, None)` if not found.
- **Called by:** `get_ai_prediction()`, `auto_add_missing_positions()`.
- **Note:** If phrase is `"NULL"` or empty, returns `(None, None)` without searching.

### `auto_add_missing_positions()`
- **Purpose:** Scan all rows and fill `at_start`/`at_end`/`ot_start`/`ot_end` for any phrase missing them.
- **Gate:** Only runs if `AUTO_POSITIONS` global is `True` (controlled by `--auto-positions` CLI flag).
- **Called by:** `startup_event()` and the `/auto-add-positions` endpoint.

### `predict_llm(...)` (backward-compatible wrapper)
- **Purpose:** Predict triplets via Ollama. Wraps `OllamaProvider.predict()`.
- **Status:** Legacy — kept for `eval.py` which imports it by name.
- **Called by:** `eval.py` only. All new code uses the adapter pattern directly.

### `predict_openai(...)` (backward-compatible wrapper)
- **Purpose:** Predict triplets via OpenAI. Wraps `OpenAIProvider.predict()`.
- **Status:** Legacy — same as `predict_llm`, kept for backward compat.
- **Called by:** `eval.py` only.

### `get_most_similar_examples(input_text, examples, n) -> list`
- **Purpose:** BM25-based retrieval of the n most similar labeled examples.
- **Tokenization:** `\b\w+\b` regex + lowercase. No Turkish stemming.
- **Called by:** `build_prediction_prompt()`.

### `find_valid_phrases_list(text, max_tokens_in_phrase=None) -> list`
- **Purpose:** Enumerate all valid sub-phrases from text for structured output.
- **Logic:** Splits at punctuation/whitespace, enumerates contiguous sub-phrases, filters by word count and edge characters.
- **Called by:** `build_absa_models()`.

### `build_prediction_prompt(...) -> tuple`
- **Purpose:** Build the LLM prompt for ABSA prediction and retrieve few-shot examples.
- **Template mode:** Uses `DEFAULT_LABELING_TEMPLATE` with `.format()` substitution (Turkish).
- **Backward compat mode:** When `prompt_template=None`, uses the original English hardcoded prompt.
- **Returns:** `(prompt_string, few_shot_examples_list)`.
- **Called by:** All provider adapters' `predict()` methods.

### `build_absa_models(...) -> tuple`
- **Purpose:** Build dynamic Pydantic model and Enums for structured LLM output.
- **Returns:** `(Aspects_model_class, field_types_dict, enums_dict)`.
- **Called by:** All provider adapters' `predict()` methods.

### `_derive_provider(config: dict) -> str`
- **Purpose:** Derive the LLM provider name from config settings.
- **Logic:**
  1. Explicit `llm_provider` key → return it
  2. Exactly 1 of `openai_key`/`anthropic_key`/`vllm_url` set → derive to that
  3. Multiple set + no explicit → `ValueError`
  4. None set → `"ollama"`
- **Called by:** `get_ai_prediction()`, `agent_chat()`.
- **Note:** `cli.py` has an inline copy that must stay in sync. See docstring for reason.

### `get_provider(provider_name: str, config: dict) -> ProviderClass`
- **Purpose:** Factory — instantiate the right provider adapter.
- **Raises:** `ValueError` for unknown provider names.
- **Called by:** `get_ai_prediction()`, `agent_chat()`.

---

## Provider Adapter Classes

### `OllamaProvider`
- **Requires:** Running Ollama server (default `localhost:11434`).
- **`predict()`:** Uses `ollama.generate` with Pydantic `model_json_schema()` for structured output.
- **`chat()`:** Uses `ollama.chat()` for general conversation.

### `OpenAIProvider`
- **Requires:** `openai_key` in config.
- **`predict()`:** Uses `client.beta.chat.completions.parse` with Pydantic `response_format`.
- **`chat()`:** Uses `client.chat.completions.create` for general conversation.

### `AnthropicProvider`
- **Requires:** `anthropic_key` in config.
- **`predict()`:** Sends prompt via `client.messages.create`, parses JSON from response text (Anthropic doesn't support structured output).
- **`chat()`:** Converts OpenAI-format messages to Anthropic format, calls `client.messages.create`.

### `VLLMProvider`
- **Requires:** `vllm_url` in config (e.g. `http://localhost:8001/v1`).
- **`predict()`:** Uses `openai` client with custom base_url, standard completion + manual JSON parse (vLLM doesn't support `beta.parse`).
- **`chat()`:** Uses `openai` client with custom base_url for general conversation.

---

## Provider Registry

```
PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "vllm": VLLMProvider,
}
```

Used by `get_provider()` to map provider name → class.

---

## FastAPI Endpoints

### `GET /settings`
- **Handler:** `get_settings()`
- **Purpose:** Return config + row count to the frontend. Acts as de facto health check (no separate `/health` endpoint).
- **Returns:** Sentiment elements, categories, polarities, all boolean flags, `current_index`, `max_number_of_idxs`, `session_id`.

### `GET /data/{data_idx}`
- **Handler:** `get_data(data_idx)`
- **Purpose:** Return a single row's review text, label, comparison model triplets, and initial reasoning.
- **Returns:** Full row dict (see return type in docstring).

### `GET /data/count` (implied by total_count in settings)
- **Purpose:** No dedicated endpoint — total count is returned via `/settings`.

### `GET /data/current-index`
- **Handler:** `get_current_index()` (inlined in settings)
- **Purpose:** Returned as part of `/settings`.

### `GET /data/max-index`
- **Handler:** `max_number_of_idxs()` (inlined in settings)
- **Purpose:** Returned as part of `/settings`.

### `POST /data/{data_idx}`
- **Handler:** `post_data(data_idx, item)`
- **Purpose:** **DEPRECATED.** Hardcodes `"annotations.csv"`, only accepts an integer.
- **Replace with:** `POST /review/{data_idx}/save`.

### `POST /annotations/{data_idx}`
- **Handler:** `post_annotations(data_idx, annotation_data)`
- **Purpose:** **DEPRECATED.** No frontend callers — the app uses `POST /review/{data_idx}/save` exclusively. Kept for backward compatibility.

### `POST /timing/{data_idx}`
- **Handler:** `post_timing(data_idx, timing)`
- **Purpose:** Append a timing entry (duration + change flag) to a row's timings list.

### `POST /auto-add-positions`
- **Handler:** `manual_auto_add_positions()`
- **Purpose:** Manually trigger `auto_add_missing_positions()`.

### `GET /ai_prediction/{data_idx}`
- **Handler:** `get_ai_prediction(data_idx)`
- **Purpose:** Generate LLM predictions for a row. Dispatches to configured provider, collects few-shot examples, adds position data.
- **Note:** May be slow (LLM call). Frontend calls this to get AI suggestions for the current row.

### `GET /avg-annotation-time`
- **Handler:** `get_avg_annotation_time()`
- **Purpose:** Calculate average annotation duration across all rows with timing data.

### `POST /upload-data`
- **Handler:** `upload_data(file)`
- **Purpose:** Accept a CSV/JSON file upload from the frontend, save to `uploads/`, activate as current dataset. Only `.csv` and `.json` accepted.

### `POST /review/{data_idx}/save`
- **Handler:** `save_review_triplets(data_idx, req)`
- **Purpose:** **PRIMARY save endpoint.** Saves annotation triplets to the label field. Called by `handleNextReview` in the frontend (both Compare and Manual modes).

### `POST /agent/chat`
- **Handler:** `agent_chat(req)`
- **Purpose:** Handle messages from the Helper Agent chat panel. Builds system prompt with review context + model comparison, appends last 4 turns of history, dispatches to configured provider. Falls back to Turkish rule-based responses on error.

---

## Startup Event

### `startup_event()`
- **Registered with:** `@app.on_event("startup")`
- **Purpose:** Log the data file path, config path, and optionally run `auto_add_missing_positions()` if `AUTO_POSITIONS` is enabled.

---

## CORS Middleware

Configured to allow all origins (`*`), all methods, all headers. No authentication.

---

## Error Handling Pattern

All endpoints wrap their handler body in `try/except FileNotFoundError` (→ `404`) and `try/except Exception` (→ `500`) with the exception detail serialized in the response. Exceptions from `_derive_provider()` (ambiguity errors) are caught and re-raised as `HTTPException(400)`.
