# AnnoABSA

**AnnoABSA** is a web-based annotation tool for Aspect-Based Sentiment Analysis (ABSA), customized for Turkish ABSA research. Core mode is **4-Way Comparison** — a 2×2 grid comparing Ground Truth, Gemma, Qwen, and GPT annotations with consensus resolution and ML-based label suggestions.

Accepted at **LREC 2026** in Palma, Mallorca, Spain.

---

## What this fork adds

This repository is a customized fork of the original AnnoABSA project, extended across seven major development phases.

### Phase 1 — Foundation
- STD format dataset support (`review,triplet` CSV), implicit aspect handling (`NULL`)
- Generalized two-model comparison with configurable CSV/names
- New LLM providers: Anthropic, vLLM, Custom OpenAI alongside Ollama and OpenAI
- Turkish-language prompts, restored manual annotation, mode toggle

### Phase 2 — Settings & Suggestions
- 5-section settings panel, AI suggestion list (accept/reject), edit review text modal

### Phase 3 — NLP Helper Toolbox
- 4 lazy-loaded Turkish NLP tools: SentiNet lexicon, BERT sentiment, morphological analysis, embedding similarity
- Native drag-to-select text interaction

### Phase 4 — Live Compare Mode
- Per-model provider/model/temperature/prompt for Model A and Model B
- Live vs CSV mode selector — real-time LLM comparison

### Phase 5 — Architecture Cleanup
- main.py 1206→50 lines, CLI 1053→6 lines — extracted to `app/`, `cli/`, `services/`

### Phase 6 — Polish, Autopilot & ML
- Emoji→SVG, component tests, autopilot `[[action:...]]` directives, RAG (BM25), Active Learning (TF-IDF+LR), Custom OpenAI provider, Welcome overlay

### Phase 7.1 — 4-Way Compare Mode
- 2×2 grid (GT + Gemma + Qwen + GPT) with compact triplet chips and consensus diamond
- 3-tier resolution panel: Auto-Accept, Quick Diff, Manual Review
- NEWUI CSV parser for `semeval_tr_llm_annotated.csv`

### Phase 7.2–7.3 — Testing, TypeScript, Autonomous Pipeline
- 104 new tests (81 backend + 23 frontend), 3 TS errors resolved, Vite 4→5
- App.tsx split into 7 custom hooks (770→250 lines)
- `annotateAll()` pipeline, Ctrl+Shift+L, chat predictions endpoint

### Phase 7.4 — 4-Way Polish
- Demo mode (6-sample data), tier filter (Tier 2/3), auto-save on navigation
- CSV export (`GET /data/export-4way`), save button in resolution panel, emoji remediation

### Phase 7.5 — ML Per-Review Prediction (current)
- **"Tahmin Et" button** — TF-IDF + LogisticRegression trained on user-annotated reviews
- Predicts triplets for the current review, auto-selects matches in the 4-way grid
- Default mode is now **4-Way Comparison**
- Removed non-functional Active Learning suggestions (💡 lightbulb)
- Removed Tier 1 from filter dropdown

---

## Core capabilities

- **4-Way Comparison** — 2×2 grid comparing 4 model annotations with consensus resolution
- **ML label prediction** — TF-IDF + LogisticRegression suggests labels from previous user annotations
- Manual ABSA annotation with drag-to-select span selection
- LLM-assisted prediction (Ollama, OpenAI, Anthropic, vLLM, Custom OpenAI)
- NLP Helper Toolbox — lexicon, BERT sentiment, morphology, embedding similarity
- CSV/JSON dataset support with configurable sentiment elements and categories
- Position-aware annotations, timing/session tracking, dark mode (DaisyUI)

---

## Tech stack

- **Backend:** Python 3.11, FastAPI, pandas, rank-bm25, scikit-learn
- **Frontend:** React 19, TypeScript, Vite 5, Tailwind CSS, DaisyUI 4
- **NLP:** SentiNet, BERT (Turkish), NlpToolkit, multilingual-e5-small
- **AI:** Ollama, OpenAI, Anthropic, vLLM, Custom OpenAI, BM25 retrieval
- **Testing:** pytest (224 backend tests), vitest (94 frontend tests)

---

## Repository structure

```
AnnoABSA/
├── main.py                  # FastAPI launcher (~50 lines)
├── cli.py / cli/            # CLI: config, runner, convert
├── app/
│   ├── config.py            # Global state: CONFIG_DATA, defaults
│   ├── data.py              # Data I/O + 4-way CSV parser
│   ├── positions.py         # Position auto-fill
│   └── routes/              # 9 route modules
│       ├── nlp.py           # 4 NLP endpoints
│       ├── settings.py      # GET/PATCH /settings
│       ├── reviews.py       # GET /data, POST /save, /agent/chat
│       ├── ai.py            # AI prediction endpoints
│       ├── timing.py        # Timing/session tracking
│       ├── upload.py        # File upload
│       ├── learning.py      # GET /learning/predict/{idx}
│       ├── chat_predictions.py
│       └── export.py        # GET /data/export-4way
├── services/
│   ├── prediction.py        # Prompt building, BM25, templates
│   ├── llm_providers.py     # 5 provider adapters
│   ├── nlp_helpers.py       # 4 lazy-loaded NLP tools
│   └── active_learning.py   # TF-IDF + LogisticRegression
├── models/schemas.py        # Pydantic models
├── frontend/src/
│   ├── App.tsx              # Root component (250 lines)
│   ├── components/          # 20 React components
│   ├── hooks/               # 7 custom hooks
│   ├── data/                # Demo data
│   └── types.ts             # Type definitions + AppActions
├── tests/                   # 224 pytest tests (11 files)
├── setup.sh / setup.bat     # One-click setup
└── examples/                # Sample datasets
```

---

## Getting started

### Prerequisites

- **Python 3.11+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)

### Quick setup

**Windows:** `setup.bat`
**macOS / Linux:** `chmod +x setup.sh && ./setup.sh`

The setup script creates a venv, installs Python + frontend deps, and displays usage instructions. NLP models (BERT ~1.2 GB, e5-small ~118 MB) download on first use.

### Run the app

```bash
source .venv/bin/activate       # macOS/Linux
.venv\Scripts\activate          # Windows

python cli.py examples/semeval_tr_llm_annotated.csv
```

The app opens in **4-Way Comparison mode** by default on ports 8000 (backend) + 3000 (frontend).

---

## Usage examples

### Basic 4-Way annotation
```bash
python cli.py --data-path examples/semeval_tr_llm_annotated.csv
```

### With LLM predictions
```bash
python cli.py --data-path examples/semeval_reviews.csv --llm-provider ollama
```

### Live Compare Mode
```bash
python cli.py --data-path examples/reviews.csv \
  --model-a-provider openai --model-a-model gpt-4o \
  --model-b-provider anthropic --model-b-model claude-sonnet-4-20250514
```

### ML label suggestions
After annotating 2+ reviews, click the **"Tahmin Et"** button (⚡ lightning icon) in the header. The model trains on your annotations and auto-selects matching triplets in the 4-way grid.

---

## Running tests

```bash
# Backend (224 pytest)
pytest tests/ -q

# Frontend (94 vitest)
cd frontend && npx vitest run
```

---

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/data/{idx}` | GET | Review text, labels, 4-way model triplets |
| `/review/{idx}/save` | POST | Save annotation triplets |
| `/agent/chat` | POST | Helper Agent chat (with RAG few-shot) |
| `/ai_prediction/{idx}` | GET | LLM-based ABSA prediction |
| `/live_prediction/{idx}` | GET | Per-model live prediction |
| `/settings` | GET/PATCH | Read/update all settings |
| `/timing/{idx}` | POST | Log annotation timing |
| `/upload-data` | POST | Upload new CSV/JSON dataset |
| `/nlp/lexicon-polarity` | GET | SentiNet word polarity |
| `/nlp/sentiment` | GET | BERT sentence sentiment |
| `/nlp/morphology` | GET | Turkish morphological analysis |
| `/nlp/embedding-similarity` | GET | Cosine similarity (e5-small) |
| `/learning/predict/{idx}` | GET | ML-based triplet predictions for current review |
| `/data/export-4way` | GET | Export CSV with annotations + resolution tiers |

---

## Annotation workflow

1. **Open the app** — Welcome Overlay appears with quick-start options
2. **Upload data** or start with demo reviews (6 samples covering all 3 tiers)
3. **4-Way Comparison mode** opens by default — 2×2 grid comparing GT, Gemma, Qwen, GPT
4. **Select triplets** — click chips in any column to mark them as accepted
5. **Use "Tahmin Et"** — after annotating 2+ reviews, get ML-based label suggestions
6. **Filter by tier** — use Tier 2/3 filter to focus on uncertain reviews
7. **Resolve** — the resolution panel guides you: Auto-Accept (Tier 1), Quick Diff (Tier 2), Manual (Tier 3)
8. **Save and advance** — footer button saves current annotations and moves to next review

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

---

## Badges

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](#)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](#)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](#)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)
[![Backend Tests](https://img.shields.io/badge/tests-224_pytest-4B8BBE?logo=pytest&logoColor=white)](#running-tests)
[![Frontend Tests](https://img.shields.io/badge/tests-94_vitest-6E9F18?logo=vitest&logoColor=white)](#running-tests)
[![LREC 2026](https://img.shields.io/badge/LREC-2026-800080)](#citation)

---

## Project Status

**Active development — Phase 7.5 (current).** This fork is actively maintained with ongoing improvements. The 4-Way Comparison mode is stable and feature-complete; iterative refinements to the ML prediction pipeline, UI polish, and test coverage continue.

Pull requests are welcome for bug fixes, Turkish NLP integrations, and additional provider support.

---

## Troubleshooting / FAQ

### `setup.bat` fails — missing `@vitejs/plugin-react`

**Problem:** After running `setup.bat`, launching the frontend fails with `ERR_MODULE_NOT_FOUND: Cannot find package '@vitejs/plugin-react'`.

**Root cause:** The system may have `NODE_ENV=production` set, which causes `npm install` to skip `devDependencies` (including `@vitejs/plugin-react`, `vite`, `daisyui`, `tailwindcss`). `setup.bat` now explicitly sets `NODE_ENV=development` and verifies all critical packages post-install.

**Fix:** Re-run `setup.bat` or manually install missing packages:
```bash
cd frontend
set NODE_ENV=development
npm install
```

If the issue persists, verify the packages exist on disk:
```bash
dir frontend\node_modules\@vitejs\plugin-react
dir frontend\node_modules\vite
dir frontend\node_modules\daisyui
```

### NLP models download on first use

BERT (~1.2 GB) and e5-small (~118 MB) are **lazy-loaded**. The app starts without them. The first time you use Duygu Analizi (sentiment) or Benzerlik Karşılaştırması (similarity), HuggingFace downloads the models — this may take a few minutes with visible server-side progress output.

### `setuptools<75` requirement

Turkish NLP packages (`nlptoolkit-sentinet`, `nlptoolkit-morphologicalanalysis`) use `pkg_resources`, which was removed in setuptools 75+. A version constraint is enforced in `pyproject.toml`. If you get `ModuleNotFoundError: pkg_resources`, run:
```bash
pip install 'setuptools<75'
```

### "0 inceleme etiketlendi" despite labeled reviews

The "Tahmin Et" button trains only on rows where **you** have saved annotations (the `label` column). Model predictions in 4-way columns (`gemma4_31b_label`, etc.) are **not** used as training data. Annotate at least 2 reviews manually before using ML prediction.

---

## Acknowledgements

- **Original AnnoABSA** — Nils Constantin Hellwig, Jakob Fehle, Udo Kruschwitz, and Christian Wolff for the annotation tool presented at LREC 2026
- **Turkish NLP tools** — [StarlangSoftware](https://github.com/starlangsoftware) for SentiNet, NlpToolkit (morphological analysis), and WordNet
- **Multilingual embeddings** — [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) for cross-lingual sentence similarity
- **BERT Turkish** — [dbmdz/bert-base-turkish-uncased](https://huggingface.co/dbmdz/bert-base-turkish-uncased) for sentiment analysis
- **LREC 2026** — reviewers and organizers for constructive feedback on the original submission
