# AnnoABSA — Project Primer (give this at the start of every session)

You are helping modify **AnnoABSA**, a web-based annotation tool for Aspect-Based Sentiment
Analysis (ABSA), forked/customized for Turkish ABSA research (accepted to LREC 2026).

You have filesystem access to the repo at `C:\Users\arhan\PycharmProjects\AnnoABSA`.
Read `docs/architecture_map.md` for the module graph, `agentdocs/session_reports/backend_reference.md` for the full function
reference, and `tests/testcases.md` for the regression baseline.

---

## Stack

- **Backend**: Python (3.11), FastAPI, pandas, rank-bm25, ollama, openai, anthropic.
  - `main.py` (~50 lines) — thin launcher: imports from `app/` modules, mounts 6 route routers, startup event.
  - `app/config.py` — global state (`DATA_FILE_PATH`, `CONFIG_DATA`, etc.) + config functions.
  - `app/data.py` — data I/O (`load_data`, `save_data`, `parse_triplet_column`) + navigation helpers.
  - `app/positions.py` — position auto-fill logic (`auto_add_missing_positions`).
  - `app/routes/settings.py` — GET/PATCH /settings.
  - `app/routes/reviews.py` — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat.
  - `app/routes/ai.py` — GET /ai_prediction/{idx}, GET /live_prediction/{idx}.
  - `app/routes/timing.py` — POST /timing/{idx}, GET /avg-annotation-time.
  - `app/routes/upload.py` — POST /upload-data, POST /auto-add-positions.
  - `app/routes/nlp.py` — APIRouter with 4 NLP endpoints (Phase 3).
  - `models/schemas.py` — Pydantic models (SaveTripletsRequest, AgentChatRequest).
  - `services/prediction.py` — prompt building, BM25 retrieval, position helpers, template constants.
  - `services/llm_providers.py` — 4 provider adapters + registry + dispatch + validation.
  - `services/nlp_helpers.py` — NLP Helper Toolbar: 4 lazy-loaded tools.
  - `cli.py` — argparse-based launcher, starts backend + frontend as subprocesses.
- **Frontend**: React + TypeScript, Vite, Tailwind (`frontend/src/`).
- **Data storage**: CSV or JSON, loaded/saved via `load_data()`/`save_data()` in `app/data.py`.
  File type is auto-detected from extension.
- **Tests**: pytest in `tests/` (128 tests), manual walkthrough in `tests/testcases.md`.

---

## Working style — follow this strictly

- **One task at a time.** I will give you a single, scoped task per session. Do not attempt to
  address other known issues or "while I'm here" improvements.
- **Minimum code that solves the problem.** No speculative flexibility, no abstractions for
  single-use code, no extra config options I didn't ask for.
- **Surgical changes.** Touch only what the task requires. Don't reformat, refactor, or
  "clean up" adjacent code. Match existing style even if you'd write it differently.
- **State assumptions explicitly.** If something in the task is ambiguous or you're missing
  information, stop and ask — don't guess and proceed.
- **Give me a plan before writing code**, in this form, then wait for me to confirm:
  ```
  1. [Step] → verify: [how I'll check this worked]
  2. [Step] → verify: [how I'll check this worked]
  ```

---

## Data format

### Standard (STD) triplet row

```csv
review_text,aspect_triplets,new_triplets,reasoning,label
```

Supported column combinations:

| Columns | Source | Notes |
|---|---|---|
| `review_text` only + `label` | Any file | After annotation, saved triplets go into `label` as JSON array. |
| `review_text`, `aspect_triplets`, `new_triplets`, `reasoning` | Old inline-column format | `aspect_triplets` maps to Model A, `new_triplets` to Model B. Both parsed via `parse_triplet_column()` in `app/data.py`. |
| `review_text` only + `--compare-model-a-csv` + `--compare-model-b-csv` | Current pattern | External CSVs override inline columns. See "How to run" below. |

### Label JSON schema (saved to CSV/JSON after annotation)

```json
[
  {
    "id": "manual_0",
    "aspect_term": "pasta",
    "aspect_category": "FOOD#QUALITY",
    "sentiment_polarity": "positive",
    "opinion_term": "güzel",
    "at_start": 0,
    "at_end": 4,
    "ot_start": null,
    "ot_end": null
  }
]
```

- `at_start`/`at_end` are 0-indexed inclusive character positions for the aspect term.
- `ot_start`/`ot_end` are positions for the opinion term (null if `click_on_token=off`).
- `"NULL"` is a literal string sentinel for implicit aspects/opinions — never convert to `""`.
- Saved via `POST /review/{idx}/save` (the only live save endpoint — `/annotations/{idx}` was deleted).

### Phase 4: Live Compare Mode config keys

Added to the JSON config file and settings panel:

| Key | Type | Default | Purpose |
|---|---|---|---|
| `compare_mode` | `"csv" \| "live"` | `"csv"` | Compare mode selector |
| `model_a_provider` | `str\|None` | `None` | Provider for Model A live predictions |
| `model_a_model` | `str\|None` | `None` | Model name for Model A |
| `model_a_prompt` | `str\|None` | `DEFAULT_LABELING_TEMPLATE` | Prompt template for Model A |
| `model_a_temperature` | `float` | `0.7` | Temperature for Model A |
| `model_b_provider` | `str\|None` | `None` | Provider for Model B |
| `model_b_model` | `str\|None` | `None` | Model name for Model B |
| `model_b_prompt` | `str\|None` | `DEFAULT_LABELING_TEMPLATE` | Prompt template for Model B |
| `model_b_temperature` | `float` | `0.7` | Temperature for Model B |
| `helper_agent_provider` | `str\|None` | `None` | Provider for Helper Agent |
| `helper_agent_model` | `str\|None` | `None` | Model name for Helper Agent |
| `helper_agent_prompt` | `str\|None` | `DEFAULT_CHAT_TEMPLATE` | Chat prompt for Helper Agent |
| `helper_agent_temperature` | `float` | `0.7` | Temperature for Helper Agent |

Note: no fallback — if `model_a_provider` is `None`, the endpoint returns HTTP 400.

---

## How to run

### Minimal (annotation only, no comparison models)

```bash
python cli.py --data-path examples/semeval_reviews.csv
```

This starts the backend (`uvicorn`) on port 8000 and the frontend (`npm run dev`) on port 3000.
Opens the browser automatically.

### With comparison models (Compare mode)

```bash
python cli.py \
  --data-path examples/semeval_reviews.csv \
  --compare-model-a-csv results/model_a_output.csv \
  --compare-model-a-name "GPT-4o" \
  --compare-model-b-csv results/model_b_output.csv \
  --compare-model-b-name "Claude 4"
```

The comparison CSVs use STD format: columns `review` (review text) and `triplet` (std triplet list).

### With LLM AI predictions

```bash
python cli.py \
  --data-path examples/semeval_reviews.csv \
  --llm-provider ollama \
  --llm-model gemma3:4b \
  --enable-pre-prediction
```

Available providers:
- `ollama` (default) — requires running Ollama server on `localhost:11434`
- `openai` — requires `--openai-key`
- `anthropic` — requires `--anthropic-key`
- `vllm` — requires `--vllm-url` (e.g. `http://localhost:8001/v1`)

### With auto-position filling

```bash
python cli.py --data-path data.csv --auto-positions
```

Scans all rows at startup and fills `at_start`/`at_end`/`ot_start`/`ot_end` for any
phrases missing them.

### Running backend alone (without CLI)

```bash
set ABSA_DATA_PATH=examples/semeval_reviews.csv
set ABSA_CONFIG_PATH=config.json
uvicorn main:app --port=8000
```

### Live Compare Mode (Phase 4)

```bash
# 1. Start the app (CSV mode is default)
python cli.py --data-path examples/semeval_reviews.csv

# 2. Open Settings → switch "Karşılaştırma Modu" to ⚡ Canlı
# 3. Configure Model A and Model B with their own provider, model, prompt, temperature
# 4. Close Settings
# 5. Click "Model A Çalıştır" / "Model B Çalıştır" in each column
```

Requires the chosen LLM providers to be running (Ollama server, API keys configured, etc.).

### Running tests

```bash
pytest tests/          # 128 automated tests
```

Manual walkthrough: `tests/testcases.md` requires a running backend + frontend + browser.
