# 🔌 AnnoABSA — External Integrations

> **Generated:** Codebase analysis — integrations focus.
> **Last updated:** 2026-07-13

---

## 1. LLM Provider Integrations

AnnoABSA supports **five LLM backends** through a hexagonal architecture (`LLMProviderPort` protocol). All providers implement a common `predict()` and `chat()` interface, dispatched via the `PROVIDER_REGISTRY` in `services/llm_providers.py`.

### 1.1 Provider Registry

```python
PROVIDER_REGISTRY = {
    "ollama":        OllamaProvider,
    "openai":        OpenAIProvider,
    "anthropic":     AnthropicProvider,
    "vllm":          VLLMProvider,
    "custom_openai": CustomOpenAIProvider,
}
```

Provider selection is handled by `_derive_provider(config)`: explicit `llm_provider` key takes priority; otherwise auto-derived from configured credentials (falls back to `ollama`).

---

### 1.2 Ollama (Local)

| Detail | Value |
|---|---|
| **Type** | Local inference |
| **SDK** | `ollama` Python library |
| **Default host:port** | `localhost:11434` (ollama library default) |
| **Default model** | `gemma3:4b` |
| **Structured output** | Yes — uses `ollama.generate()` with `format=Aspects.model_json_schema()` |
| **Chat endpoint** | `ollama.chat()` |
| **Config key** | None required (runs locally) |
| **Used by** | `GET /ai_prediction/{idx}`, `POST /agent/chat` |

**Source:** `services/llm_providers.py` — `OllamaProvider` class (lines 70–136)

---

### 1.3 OpenAI

| Detail | Value |
|---|---|
| **Type** | Cloud API |
| **SDK** | `openai` Python library |
| **Base URL** | `https://api.openai.com/v1` (default) |
| **Auth** | API key (`openai_key` in config) |
| **Structured output** | Yes — uses `client.beta.chat.completions.parse()` with `response_format=Aspects` |
| **Chat endpoint** | `client.chat.completions.create()` |
| **Config keys** | `openai_key` |
| **Required** | API key must be set, or ValueError raised |

**Source:** `services/llm_providers.py` — `OpenAIProvider` class (lines 140–231)

---

### 1.4 Anthropic (Claude)

| Detail | Value |
|---|---|
| **Type** | Cloud API |
| **SDK** | `anthropic` Python library |
| **Base URL** | `https://api.anthropic.com/v1` (default) |
| **Auth** | API key (`anthropic_key` in config) |
| **Structured output** | No structured JSON API — manual JSON extraction from response text |
| **Default model** | `claude-sonnet-4-20250514` |
| **Message format** | OpenAI-style → Anthropic format conversion (system role extracted) |
| **Chat endpoint** | `client.messages.create()` |
| **Config keys** | `anthropic_key` |
| **Required** | API key must be set, or ValueError raised |

**Source:** `services/llm_providers.py` — `AnthropicProvider` class (lines 234–333)

---

### 1.5 vLLM

| Detail | Value |
|---|---|
| **Type** | Self-hosted, OpenAI-compatible |
| **SDK** | `openai` Python library with custom `base_url` |
| **Auth** | API key = `"EMPTY"` (vLLM default) |
| **Structured output** | No — uses standard `client.chat.completions.create()` + manual JSON parse |
| **Config keys** | `vllm_url` (e.g., `http://localhost:8001/v1`) |
| **Required** | URL must be set, or ValueError raised |

**Source:** `services/llm_providers.py` — `VLLMProvider` class (lines 336–427)

---

### 1.6 Custom OpenAI-Compatible

| Detail | Value |
|---|---|
| **Type** | Any OpenAI-compatible endpoint |
| **SDK** | `openai` Python library with custom `base_url` + `api_key` |
| **Supported endpoints** | DeepSeek, Together AI, Groq, Fireworks, etc. |
| **Structured output** | **Tries** `client.beta.chat.completions.parse()` first; falls back to standard completion + manual JSON parse if not supported |
| **Config keys** | `custom_openai_url`, `custom_openai_key`, `custom_openai_model` |
| **Required** | Both URL and API key must be set, or ValueError raised |

**Source:** `services/llm_providers.py` — `CustomOpenAIProvider` class (lines 430–545)

---

### 1.7 Provider Validation

```python
validate_provider_config(provider_name, config) -> list[str]
```

Returns validation errors per provider:
- **openai** — checks `openai_key`
- **anthropic** — checks `anthropic_key`
- **vllm** — checks `vllm_url`
- **custom_openai** — checks `custom_openai_url` + `custom_openai_key`
- **ollama** — no validation needed (local)

Per-model validation (`validate_per_model_config`) adds provider + model checks for `model_a`, `model_b`, and `helper_agent` roles.

---

## 2. HuggingFace Model Downloads

Two HuggingFace models are downloaded at runtime (lazy-loaded on first use):

### 2.1 `savasy/bert-base-turkish-sentiment-cased`

| Detail | Value |
|---|---|
| **Purpose** | Sentence-level sentiment classification |
| **Library** | `transformers.pipeline("sentiment-analysis", ...)` |
| **Load location** | `services/nlp_helpers.py` → `get_sentiment_classifier()` |
| **Lazy loading** | Yes — loaded on first call |
| **Input** | Text (truncated to 512 tokens) |
| **Output** | `{"label": "positive"|"negative", "score": float}` |

### 2.2 `intfloat/multilingual-e5-small`

| Detail | Value |
|---|---|
| **Purpose** | Embedding similarity between selected text and sentence |
| **Library** | `sentence_transformers.SentenceTransformer` |
| **Load location** | `services/nlp_helpers.py` → `get_embedding_model()` |
| **Lazy loading** | Yes — loaded on first call |
| **Prompt prefix** | `"query: "` for selection, `"passage: "` for sentence |
| **Metric** | Cosine similarity |
| **Output** | `{"similarity": float (0-1), "selection_length": int}` |

---

## 3. NlpToolkit / StarlangSoftware Libraries

Four Java-origin NLP libraries ported to Python (via the `nlptoolkit-*` PyPI packages), used in the NLP Helper Toolbar:

| Library | Python Package | Lazily Loaded In | Purpose |
|---|---|---|---|
| **SentiNet** | `nlptoolkit-sentinet` | `get_sentinet()` | Word-level sentiment scores |
| **WordNet** | `nlptoolkit-wordnet` | `_build_flattened_lexicon()` | Turkish word relationships / synsets |
| **Dictionary** | `nlptoolkit-dictionary` | (via WordNet) | Turkish lexicon |
| **FsmMorphologicalAnalyzer** | `nlptoolkit-morphologicalanalysis` | `get_morphological_analyzer()` | Morphological parsing (roots, inflectional groups, POS) |

### 3.1 SentiNet + WordNet Lexicon Pipeline

The `_build_flattened_lexicon()` function in `services/nlp_helpers.py`:
1. Iterates all synsets in **WordNet**
2. Looks up each synset ID in **SentiNet** for polarity scores
3. Averages scores across synsets for duplicate words
4. Returns `{word: (polarity, score)}` dictionary

### 3.2 Endpoints consuming NLP helpers

| Endpoint | Function Used |
|---|---|
| `GET /nlp/lexicon-polarity?text=...` | `lexicon_polarity()` |
| `GET /nlp/sentiment-classify?text=...` | `sentiment_classify()` |
| `GET /nlp/morphology?word=...` | `morphology()` |
| `GET /nlp/embedding-similarity?selection=...&sentence=...` | `embedding_similarity()` |

**Source:** `services/nlp_helpers.py` (all 230 lines)
**Router:** `app/routes/nlp.py`

---

## 4. CORS Configuration

Configured in `main.py` via FastAPI's `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # ⚠️ All origins allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Implications:** The backend accepts requests from any origin. This is appropriate for local development but should be restricted in production deployments.

---

## 5. File Upload Handling

### 5.1 Upload endpoint

`POST /upload-data` — accepts multipart/form-data file uploads:

| Detail | Value |
|---|---|
| **Route** | `POST /upload-data` |
| **Handler** | `app/routes/upload.py` → `upload_data()` |
| **Accepted types** | `.csv`, `.json` |
| **Storage** | `./uploads/uploaded_{timestamp}.{ext}` |
| **Max size** | No explicit limit (default FastAPI/uvicorn) |
| **Processing** | Validates file, saves to disk, updates global `DATA_FILE_PATH`, returns row count |

### 5.2 Upload directory

```python
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
# Resolves to: <project_root>/uploads/
```

### 5.3 Frontend file input

- Hidden `<input type="file" accept=".csv,.json">` in `App.tsx`
- Triggers `POST /upload-data` with `FormData`
- On success, resets `currentIndex` to 0 and reloads UI

---

## 6. Port Usage

| Service | Default Port | Configurable Via |
|---|---|---|
| **Backend (FastAPI/uvicorn)** | `8000` | `--backend-port` CLI flag |
| **Frontend (Vite dev server)** | `3000` | `--frontend-port` CLI flag |
| **Ollama** (external dependency) | `11434` | Ollama server default |
| **vLLM** (external dependency) | `8001` | vLLM server (user-configured) |

The frontend connects to the backend at `http://localhost:8000` by default, overridable via `VITE_BACKEND_URL` environment variable.

---

## 7. Data Persistence

### 7.1 File I/O

All data is persisted as flat files — no database:

| Format | Reader | Writer | Encoding |
|---|---|---|---|
| **CSV** | `pandas.read_csv()` | `DataFrame.to_csv()` | UTF-8 |
| **JSON** | `json.load()` | `json.dump(..., ensure_ascii=False)` | UTF-8 |

### 7.2 Data file lifecycle

1. **Startup:** File path from `ABSA_DATA_PATH` env var or CLI argument
2. **Runtime:** `load_data()` / `save_data()` in `app/data.py`
3. **Upload:** `POST /upload-data` replaces the current data file
4. **Save:** `POST /review/{idx}/save` updates the label for a single row

### 7.3 Config persistence

Configuration is stored as a JSON file (`.json`):
- Loaded from `ABSA_CONFIG_PATH` env var
- Modified via `PATCH /settings` endpoint
- Written to temp file by CLI runner during startup

### 7.4 Comparison CSV integration

| Feature | Details |
|---|---|
| **Model A CSV** | `--compare-model-a-csv` / config `compare_model_a_csv` |
| **Model B CSV** | `--compare-model-b-csv` / config `compare_model_b_csv` |
| **Format detection** | Auto-detects STD format (review + triplet columns) vs per-row format (review_id + triplet columns) |
| **Parser** | `_load_comparison_csv()` + `parse_triplet_column()` in `app/data.py` |

---

## 8. API Endpoints Summary

### 8.1 Backend routers

| Router Module | Prefix / Tags | Endpoints |
|---|---|---|
| `app/routes/reviews.py` | `reviews` | `GET /data/{idx}`, `POST /review/{idx}/save`, `POST /agent/chat` |
| `app/routes/ai.py` | `ai` | `GET /ai_prediction/{idx}`, `GET /live_prediction/{idx}` |
| `app/routes/nlp.py` | `nlp` | `GET /nlp/lexicon-polarity`, `/nlp/sentiment-classify`, `/nlp/morphology`, `/nlp/embedding-similarity` |
| `app/routes/settings.py` | `settings` | `GET /settings`, `PATCH /settings` |
| `app/routes/upload.py` | `upload` | `POST /upload-data`, `POST /auto-add-positions` |
| `app/routes/timing.py` | `timing` | Annotation timing endpoints |
| `app/routes/learning.py` | `learning` | `GET /learning/suggestions`, `GET /learning/predict/{idx}` |

### 8.2 External dependencies requiring network

- **OpenAI API** — `https://api.openai.com/v1` (HTTPS outbound)
- **Anthropic API** — `https://api.anthropic.com/v1` (HTTPS outbound)
- **Custom OpenAI API** — User-specified URL (configurable)
- **Ollama** — `localhost:11434` (local, no network)
- **vLLM** — User-specified URL (typically `localhost:8001/v1`)
- **HuggingFace Hub** — Model download at first use (`huggingface.co`)
