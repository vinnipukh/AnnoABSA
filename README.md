# AnnoABSA

**AnnoABSA** is a web-based annotation tool for Aspect-Based Sentiment Analysis (ABSA). It combines a modern React + TypeScript frontend with a FastAPI backend and supports manual annotation, LLM-assisted suggestions, and an NLP helper toolbox.

Accepted at **LREC 2026** in Palma, Mallorca, Spain.

---

## What this fork adds

This repository is a customized fork of the original AnnoABSA project, adapted for Turkish ABSA research and extended across three major development phases.

### Phase 1 highlights

#### 1. STD format dataset support
- Added support for the research group's `review,triplet` CSV format.
- Triplets are parsed from Python list-literal strings, including implicit aspects represented with `NULL`.
- Existing annotation data can be loaded and exported while preserving compatibility with the internal label schema.

#### 2. Generalized two-model comparison
- The original hardcoded DeepSeek/Qwen comparison view was generalized.
- Comparison CSVs and display names can now be configured through CLI flags and JSON config.
- The UI renders comparison columns dynamically using generic model labels.

#### 3. New LLM providers
- Added support for **Anthropic** and **vLLM**.
- Provider selection is configurable instead of being inferred from a single key.
- The prediction pipeline now supports multiple backends through a cleaner dispatch flow.

#### 4. Prompt improvements
- Labeling prompts were consolidated and made configurable.
- Turkish-language prompt defaults were introduced for better ABSA annotation quality.
- The helper-agent chat prompt was also made configurable and aligned with the generalized comparison flow.

#### 5. Restored manual annotation screen
- Reintroduced a span-based manual annotator inspired by the original AnnoABSA experience.
- Added a mode toggle between **Compare 2 LLMs** and **Manual**.
- Added an independent toggle for the helper-agent chat panel.
- Manual annotation now supports span selection via native browser drag-to-select, inline color highlighting, popup form for category/polarity, and position-aware triplet creation.

### Phase 2 highlights

- **Settings panel** with 5 sections (annotation elements, appearance, AI prediction, saving, system prompts).
- **AI suggestion list** with accept/reject for individual predicted triplets.
- Edit review text modal.
- Timing and session tracking.

### Phase 3 highlights — NLP Helper Toolbox

- **Backend NLP module** (`services/nlp_helpers.py`) with four lazy-loaded Turkish NLP tools:
  - **SentiNet lexicon** — per-word polarity lookup via WordNet-flattened dictionary
  - **BERT sentiment classifier** (`savasy/bert-base-turkish-sentiment-cased`) — sentence-level positive/negative/neutral with confidence score
  - **Morphological analyzer** (NlpToolkit) — root word, POS tag, inflectional groups
  - **Multilingual embedding similarity** (`intfloat/multilingual-e5-small`) — cosine similarity between selected span and full sentence
- **4 API endpoints** under `/nlp/` via `app/routes/nlp.py` (first production APIRouter).
- **Red toolbox icon** floating at the bottom-center of the screen — click to expand a 4-segment card with auto-fetching lexicon (instant) and on-demand sentiment, morphology, and embedding comparison.
- **Native drag-to-select** — select text like in any text editor: click, hold, drag, release. No more multi-click cycles.
- **14 vitest component tests** for the toolbox, **12 pytest tests** for the backend NLP handlers.

---

## Core capabilities

- Manual ABSA annotation in the browser (drag-to-select spans)
- Optional LLM-assisted prediction and review (Ollama, OpenAI, Anthropic, vLLM)
- NLP Helper Toolbox with lexicon, sentiment, morphology, and embedding tools
- Support for CSV and JSON datasets
- Configurable sentiment elements, categories, and polarities
- Position-aware annotations with character offsets
- Timing and session tracking options
- Dark mode and modern responsive UI

---

## Tech stack

- **Backend:** Python 3.11, FastAPI, pandas, rank-bm25
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, DaisyUI
- **NLP toolkit:** SentiNet, BERT (Turkish), NlpToolkit, multilingual-e5-small
- **AI / Retrieval:** Ollama, OpenAI, Anthropic, vLLM, BM25-based retrieval
- **Testing:** pytest (93 backend tests), vitest (27 frontend tests)

---

## Repository structure

```
AnnoABSA/
├── main.py                  # FastAPI backend: global state, 10 HTTP endpoints, data I/O
├── cli.py                   # CLI launcher (argparse) — starts backend + frontend
├── services/
│   ├── prediction.py        # Prompt building, BM25 retrieval, position helpers
│   ├── llm_providers.py     # 4 provider adapters (Ollama, OpenAI, Anthropic, vLLM)
│   └── nlp_helpers.py       # NLP Helper Toolbox: 4 lazy-loaded tools + handlers
├── app/
│   └── routes/
│       └── nlp.py           # APIRouter with 4 NLP endpoints
├── models/
│   └── schemas.py           # Pydantic request models
├── frontend/
│   └── src/
│       ├── App.tsx          # Root component, all state
│       ├── components/      # 12 React components (incl. NlpHelperToolbar)
│       └── hooks/           # useTextSelection (drag-to-select), useDarkMode
├── tests/                   # 93 pytest tests + testcases.md walkthrough
├── agentdocs/               # Implementation briefs, session reports, project primer
├── docs/                    # Architecture map, CLI reference
└── examples/                # Sample datasets and configuration files
```

---

## Getting started

### Prerequisites

- **Python 3.11+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)

### Quick setup (all platforms)

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
3. Install Python dependencies (FastAPI, transformers, sentence-transformers, etc.)
4. Install frontend dependencies (React, Vite, Tailwind)
5. Display usage instructions

> **Note:** The BERT sentiment model (~1.2 GB) and e5-small embedding model (~118 MB) download automatically on first use to `~/.cache/huggingface/`. First requests to the corresponding `/nlp/` endpoints may be slow (10–30s). Subsequent requests are fast.

### Run the app

**Windows:**
```batch
.venv\Scripts\activate
python cli.py examples/semeval_reviews.csv
```

**macOS / Linux:**
```bash
source .venv/bin/activate
python cli.py examples/semeval_reviews.csv
```

You can also load a configuration file:

```bash
python cli.py examples/semeval_reviews.json --load-config examples/example_config.json
```

---

## Manual install (if setup scripts don't work)

```bash
pip install 'setuptools<75'
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Then run with:

```bash
python cli.py examples/semeval_reviews.csv
```

---

## Supported data formats

AnnoABSA supports:

- **Standard CSV / JSON annotation data** with internal `label` objects
- **STD format CSVs** using `review,triplet`
- Optional translations, timing data, and phrase-position metadata

---

## Annotation workflow

The app supports two main workflows:

1. **Compare 2 LLMs** — inspect model-generated triplets side by side and refine annotations
2. **Manual** — drag-select spans directly in the review text and create annotations

**Drag-to-select**: click and hold on a word, drag across the desired text, then release. The browser's native blue highlight shows your selection. Token snapping auto-expands to word boundaries. A red toolbox icon appears at the bottom of the screen — click it to access the NLP Helper Toolbox.

### Using the NLP Helper Toolbox

1. Select any span of text in either mode
2. A **red toolbox icon** appears at the bottom-center of the screen
3. Click it to expand the 4-segment card:
   - **📖 Sözlük** (lexicon) — polarity loads automatically
   - **🤖 Duygu Analizi** (sentiment) — click to run BERT classifier
   - **🔧 Yapı Çözümleme** (morphology) — click for root + POS + inflectional groups
   - **📊 Benzerlik** (embedding similarity) — click to compare selection vs. full sentence
4. Press **Escape** or click outside to collapse

---

## AI assistance

AnnoABSA can generate suggestions using configurable LLM providers:

- Ollama
- OpenAI
- Anthropic
- vLLM

The prediction pipeline uses retrieval-augmented few-shot prompting to improve output quality over time.

---

## Running with comparison models or AI predictions

```bash
# With comparison models (Compare mode)
python cli.py \
  --data-path examples/semeval_reviews.csv \
  --compare-model-a-csv results/model_a_output.csv \
  --compare-model-a-name "GPT-4o" \
  --compare-model-b-csv results/model_b_output.csv \
  --compare-model-b-name "Claude 4"

# With LLM AI predictions
python cli.py \
  --data-path examples/semeval_reviews.csv \
  --llm-provider ollama \
  --llm-model gemma3:4b \
  --enable-pre-prediction

# With auto-position filling
python cli.py --data-path data.csv --auto-positions
```

Available providers: `ollama` (default), `openai`, `anthropic`, `vllm`.

---

## Running tests

```bash
pytest tests/                              # 93 backend tests
cd frontend && npx vitest run              # 27 frontend tests
```

Manual walkthrough: `tests/testcases.md` requires a running backend + frontend + browser.

---

## Why this fork exists

This fork preserves the original goal of AnnoABSA — efficient ABSA annotation — while making the system more flexible for real research workflows:

- custom dataset formats
- multiple model providers
- configurable prompts
- a restored manual annotation experience with native drag-to-select
- an NLP Helper Toolbox for instant access to Turkish lexical, morphological, and semantic tools
- UI modes that fit both comparison-driven and human-only annotation sessions

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

## Contact

For questions, feedback, or collaboration, contact the AnnoABSA authors via the repository or the corresponding author listed in the paper.

---

## License

MIT License.
