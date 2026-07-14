# AnnoABSA

**AnnoABSA** is a web-based annotation tool for Aspect-Based Sentiment Analysis (ABSA). It combines a modern React + TypeScript frontend with a FastAPI backend and supports manual annotation, LLM-assisted suggestions, autopilot mode, active learning, and an NLP helper toolbox.

Accepted at **LREC 2026** in Palma, Mallorca, Spain.

---

## What this fork adds

This repository is a customized fork of the original AnnoABSA project, adapted for Turkish ABSA research and extended across six major development phases.

### Phase 1 — Foundation

- **STD format dataset support** — `review,triplet` CSV parsing with implicit aspect handling (`NULL`)
- **Generalized two-model comparison** — configurable comparison CSVs and display names via CLI and JSON config
- **New LLM providers** — Anthropic, vLLM added alongside Ollama and OpenAI
- **Turkish-language prompts** — configurable labeling and chat templates
- **Restored manual annotation** — span-based annotator with mode toggle (Compare 2 LLMs / Manual)

### Phase 2 — Settings & Suggestions

- **Settings panel** — 5 sections (annotation elements, appearance, AI prediction, saving, system prompts)
- **AI suggestion list** — accept/reject individual predicted triplets
- **Edit review text modal**, timing and session tracking

### Phase 3 — NLP Helper Toolbox

- **4 lazy-loaded Turkish NLP tools**:
  - **SentiNet lexicon** — per-word polarity lookup
  - **BERT sentiment classifier** (`savasy/bert-base-turkish-sentiment-cased`)
  - **Morphological analyzer** (NlpToolkit) — root word, POS, inflectional groups
  - **Embedding similarity** (`intfloat/multilingual-e5-small`)
- **4 API endpoints** under `/nlp/`
- **Native drag-to-select** — select text like any editor
- **14 vitest tests** + **12 pytest tests** for the toolbox

### Phase 4 — Live Compare Mode

- **Per-model provider/model/temperature/prompt** for Model A and Model B
- **Live vs CSV mode selector** — real-time LLM comparison without pre-computed CSVs
- **CLI flags** for all Live Compare config: `--model-a-provider`, `--model-a-model`, `--model-a-temperature`, `--model-a-prompt`, `--model-b-*`, `--helper-agent-*`

### Phase 5 — Architecture Cleanup

- **main.py breakup** (1206 → 50 lines) — extracted `app/config.py`, `app/data.py`, `app/positions.py`, and 6 route files (`settings`, `reviews`, `ai`, `timing`, `upload`)
- **cli.py breakup** (1053 → 6 lines) — extracted `cli/config.py`, `cli/runner.py`, `cli/convert.py`
- **Route import cleanup** — all route files import from `app.config` and `app.data` instead of `main`
- **Smoke tests** — 4 compile-only checks

### Phase 6 — Polish, Autopilot & ML Features

- **Emoji → SVG** — all structural emoji replaced with inline SVGs
- **Component tests** — +24 vitest tests (SettingsPanel, ModelTripletColumn, HelperAgentChatbox)
- **Autopilot parser** — `[[action:methodName(args)]]` directive extraction + execution in HelperAgentChatbox
- **Autopilot backend prompt** — LLM instructed to generate action directives (13 available actions)
- **RAG extension** — BM25 few-shot retrieval added to Helper Agent chat
- **Active learning** — TF-IDF + LogisticRegression uncertainty sampling (`services/active_learning.py`, `app/routes/learning.py`)
- **Custom OpenAI provider** — any OpenAI-compatible API via URL + API key
- **Welcome overlay** — landing page for first-time users (shows every page load for live demos)
- **Active Learning panel** — click the 💡 button in the header to see uncertain reviews ranked by entropy
- **TSConfig fix** — eliminated pre-existing `env` TypeScript error
- **scikit-learn** added, stale `[project.scripts]` cleaned

### Phase 7.1 — Compare Mode UI Rework (4-Way Grid)

- **4-Way Compare Mode** — 2x2 grid (Ground Truth + Gemma + Qwen + GPT) with compact triplet chips
- **Consensus diamond** — Color-coded by majority_vote (green=3, yellow=2, red=1) at grid center
- **Resolution panel** — 3-tier curation: Auto-Accept, Quick Diff, Manual Review
- **NEWUI CSV parser** — `_load_4way_row()` for `semeval_tr_llm_annotated.csv` format
- **5 new components**: CompactTripletChip, ReviewHeader, FourWayGrid, ResolutionPanel
- **13 new vitest tests** for resolution panel

---

## Core capabilities

- Manual ABSA annotation with drag-to-select span selection
- LLM-assisted prediction (Ollama, OpenAI, Anthropic, vLLM, Custom OpenAI)
- Live Compare Mode — per-model LLM configuration in real time
- Autopilot — Helper Agent can navigate, save, toggle, and run predictions via `[[action:...]]` directives
- Active learning — TF-IDF + LogisticRegression uncertainty sampling ranks which reviews to annotate next
- NLP Helper Toolbox — lexicon, BERT sentiment, morphology, embedding similarity
- Welcome overlay with quick-start instructions and keyboard shortcuts
- Support for CSV and JSON datasets
- Configurable sentiment elements, categories, and polarities
- Position-aware annotations with character offsets
- Timing and session tracking
- Dark mode and modern responsive UI (DaisyUI)

---

## Tech stack

- **Backend:** Python 3.11, FastAPI, pandas, rank-bm25, scikit-learn
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, DaisyUI
- **NLP toolkit:** SentiNet, BERT (Turkish), NlpToolkit, multilingual-e5-small
- **AI / Retrieval:** Ollama, OpenAI, Anthropic, vLLM, Custom OpenAI, BM25-based retrieval
- **Testing:** pytest (128 backend tests), vitest (64 frontend tests)

---

## Repository structure

```
AnnoABSA/
├── main.py                  # FastAPI launcher (~50 lines)
├── cli.py                   # Thin wrapper around cli/ package (6 lines)
├── cli/                     # Extracted cli modules
│   ├── config.py            # ABSAAnnotatorConfig
│   ├── runner.py            # start_backend, start_frontend, start_full_app
│   └── convert.py           # std_triplets_to_label
├── app/
│   ├── config.py            # Global state: CONFIG_DATA, load_config()
│   ├── data.py              # Data I/O: load/save CSV/JSON
│   ├── positions.py         # Position auto-fill
│   └── routes/
│       ├── nlp.py           # 4 NLP endpoints (Phase 3)
│       ├── settings.py      # GET/PATCH /settings
│       ├── reviews.py       # GET /data/{idx}, POST /save, POST /agent/chat
│       ├── ai.py            # GET /ai_prediction, /live_prediction
│       ├── timing.py        # POST /timing, GET /avg-annotation-time
│       ├── upload.py        # POST /upload-data, /auto-add-positions
│       └── learning.py      # GET /learning/suggestions, /learning/predict (Phase 6)
├── services/
│   ├── prediction.py        # Prompt building, BM25 retrieval, templates
│   ├── llm_providers.py     # 5 provider adapters + dispatch + custom_openai
│   ├── nlp_helpers.py       # 4 lazy-loaded NLP tools
│   └── active_learning.py   # TF-IDF + LogisticRegression uncertainty sampling
├── models/schemas.py        # Pydantic models
├── frontend/src/
│   ├── App.tsx              # Root component, all state
│   ├── components/          # 20 React components (incl. CompactTripletChip, FourWayGrid, ResolutionPanel, ReviewHeader)
│   ├── hooks/               # useTextSelection, useDarkMode
│   └── types.ts             # TripletItem, Settings, AppActions, ChatMessage
├── tests/                   # 128 pytest tests + testcases.md walkthrough
├── agentdocs/               # Plans, completion reports, project primer
├── docs/                    # Architecture map, CLI reference
├── setup.sh                 # macOS / Linux one-click setup
├── setup.bat                # Windows one-click setup
└── examples/                # Sample datasets and config files
```

---

## Getting started

### Prerequisites

- **Python 3.11+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)

### Quick setup

**Windows:**
```batch
setup.bat
```

**macOS / Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Create a Python virtual environment
2. Pin `setuptools<75` (required by the StarlangSoftware NLP toolkit)
3. Install Python dependencies (FastAPI, scikit-learn, transformers, etc.)
4. Install frontend dependencies (React, Vite, Tailwind)
5. Display usage instructions

> **Note:** The BERT sentiment model (~1.2 GB) and e5-small embedding model (~118 MB) download automatically on first use to `~/.cache/huggingface/`. First requests to the corresponding `/nlp/` endpoints may be slow (10–30s).

### Run the app

```bash
# Activate environment
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Start with demo data
python cli.py examples/semeval_reviews.csv
```

The backend starts on port 8000 and frontend on port 3000. The browser opens automatically with a **Welcome Overlay** showing quick-start options.

---

## Usage examples

### Basic annotation
```bash
python cli.py --data-path examples/semeval_reviews.csv
```

### With LLM predictions
```bash
python cli.py --data-path examples/semeval_reviews.csv \
  --llm-provider ollama --llm-model gemma3:4b \
  --enable-pre-prediction
```

### Live Compare Mode (per-model config)
```bash
python cli.py --data-path examples/reviews.csv \
  --model-a-provider openai --model-a-model gpt-4o --model-a-temperature 0.3 \
  --model-b-provider anthropic --model-b-model claude-sonnet-4-20250514
```

### Custom OpenAI-compatible provider
```bash
python cli.py --data-path examples/reviews.csv \
  --llm-provider custom_openai --llm-model my-model \
  --custom-openai-url http://localhost:8001/v1 --custom-openai-key my-key
```

### With comparison CSV files
```bash
python cli.py --data-path examples/semeval_reviews.csv \
  --compare-model-a-csv results/model_a.csv --compare-model-a-name "GPT-4o" \
  --compare-model-b-csv results/model_b.csv --compare-model-b-name "Claude 4"
```

### Helper Agent autopilot
The Helper Agent can navigate, save, toggle, and run predictions. Just chat with it:
```
Kullanıcı: "Sonraki incelemeye geç ve kaydet"
Agent: "Tamam, kaydedip geçiyorum [[action:saveAndNext()]]"
```
The `[[action:...]]` directive is stripped from display and executed automatically.

### Active Learning suggestions
Click the 💡(lightbulb) button in the header bar, then click **Tara**. After annotating 2+ reviews, the model ranks unlabeled reviews by uncertainty and suggests which to annotate next.

---

## Running tests

```bash
# Backend tests (128 pytest)
pytest tests/ -q

# Frontend tests (64 vitest)
cd frontend && npx vitest run
```

Manual walkthrough: `tests/testcases.md` requires a running backend + frontend + browser.

---

## Supported data formats

AnnoABSA supports:

- **Standard CSV / JSON annotation data** with internal `label` objects
- **STD format CSVs** using `review,triplet` columns
- Optional translations, timing data, and phrase-position metadata

---

## Available providers

| Provider | CLI flag | Requires |
|---|---|---|
| Ollama (default) | `--llm-provider ollama` | Running Ollama on `localhost:11434` |
| OpenAI | `--llm-provider openai` | `--openai-key` |
| Anthropic | `--llm-provider anthropic` | `--anthropic-key` |
| vLLM | `--llm-provider vllm` | `--vllm-url` (e.g. `http://localhost:8001/v1`) |
| Custom OpenAI | `--llm-provider custom_openai` | `--custom-openai-url`, `--custom-openai-key` |

---

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/data/{idx}` | GET | Review text, labels, model comparisons |
| `/review/{idx}/save` | POST | Save annotation triplets |
| `/agent/chat` | POST | Helper Agent chat (with RAG few-shot) |
| `/ai_prediction/{idx}` | GET | LLM-based ABSA prediction |
| `/live_prediction/{idx}` | GET | Per-model live prediction |
| `/settings` | GET/PATCH | Read/update all settings |
| `/timing/{idx}` | POST | Log annotation timing |
| `/avg-annotation-time` | GET | Average time per annotation |
| `/upload-data` | POST | Upload new CSV/JSON dataset |
| `/auto-add-positions` | POST | Fill missing character positions |
| `/nlp/lexicon-polarity` | GET | SentiNet word polarity |
| `/nlp/sentiment` | GET | BERT sentence sentiment |
| `/nlp/morphology` | GET | Turkish morphological analysis |
| `/nlp/embedding-similarity` | GET | Cosine similarity (e5-small) |
| `/learning/suggestions` | GET | Active learning — uncertain reviews |
| `/learning/predict/{idx}` | GET | ML-based triplet predictions |

---

## Annotation workflow

1. **Open the app** — Welcome Overlay appears with quick-start options
2. **Upload data** or start with demo reviews
3. **Choose mode**: Compare (side-by-side LLM outputs) or Manual (span-based annotation)
4. **Select text** — drag-to-select: click, hold, drag, release
5. **Use NLP tools** — the red toolbox icon appears at the bottom: lexicon auto-fetches, others on click
6. **Chat with Helper Agent** — ask questions, get autopilot navigation
7. **Run AI predictions** — click the AI button in the header
8. **Get suggestions** — click the 💡 button for active learning recommendations
9. **Save and advance** — footer button saves current annotations and moves to the next review

---

## Why this fork exists

This fork preserves the original goal of AnnoABSA — efficient ABSA annotation — while making the system more flexible for real research workflows:

- Custom dataset formats (STD, CSV, JSON)
- Multiple model providers with Live Compare Mode
- Configurable prompts in Turkish
- Autopilot mode for semi-automated annotation pipelines
- Active learning to prioritize uncertain reviews
- NLP Helper Toolbox for instant Turkish lexical, morphological, and semantic tools
- Native drag-to-select text interaction

---

## Citation

```bibtex
@inproceedings{hellwig2026annoabsa,
  title={AnnoABSA: A Web-Based Annotation Tool for Aspect-Based Sentiment Analysis with Retrieval-Augmented Suggestions},
  author={Hellwig, Nils Constantin and Fehle, Jakob and Kruschwitz, Udo and Wolff, Christian},
  booktitle={Proceedings of LREC 2026},
  year={2026}
}
```

---

## License

MIT License.
