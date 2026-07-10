# AnnoABSA

**AnnoABSA** is a web-based annotation tool for Aspect-Based Sentiment Analysis (ABSA). It combines a modern React + TypeScript frontend with a FastAPI backend and supports both manual annotation and optional LLM-assisted suggestions.

Accepted at **LREC 2026** in Palma, Mallorca, Spain.

---

## What this fork adds

This repository is a customized fork of the original AnnoABSA project, adapted for Turkish ABSA research and extended across several major phases of development.

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
- Manual annotation now supports span selection, inline highlighting, and position-aware triplet creation.

---

## Core capabilities

- Manual ABSA annotation in the browser
- Optional LLM-assisted prediction and review
- Support for CSV and JSON datasets
- Configurable sentiment elements, categories, and polarities
- Position-aware annotations with character offsets
- Timing and session tracking options
- Dark mode and modern responsive UI

---

## Tech stack

- **Backend:** Python, FastAPI
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **AI / Retrieval:** Ollama, OpenAI, Anthropic, vLLM, BM25-based retrieval

---

## Repository structure

- `main.py` — FastAPI backend, data handling, annotation saving, AI prediction
- `cli.py` — command-line entrypoint and configuration handling
- `frontend/` — React + TypeScript UI
- `agentdocs/` — implementation briefs, kickoff notes, and completion reports
- `examples/` — sample datasets and configuration files
- `evaluation/` — evaluation utilities and experiments

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
2. Install Python dependencies (FastAPI, pandas, etc.)
3. Install frontend dependencies (React, Vite, Tailwind)

### Run the app

**Windows:**
```batch
.venv\Scripts\activate
python cli.py examples/restaurant_reviews.csv
```

**macOS / Linux:**
```bash
source .venv/bin/activate
python cli.py examples/restaurant_reviews.csv
```

You can also load a configuration file:

```bash
python cli.py examples/restaurant_reviews.json --load-config examples/example_config.json
```

---

## Manual install (if setup scripts don't work)

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Then run with:

```bash
python cli.py examples/restaurant_reviews.csv
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
2. **Manual** — select spans directly in the review text and create annotations manually

The manual mode supports token-based or character-based selection depending on configuration.

---

## AI assistance

AnnoABSA can generate suggestions using configurable LLM providers:

- Ollama
- OpenAI
- Anthropic
- vLLM

The prediction pipeline uses retrieval-augmented few-shot prompting to improve output quality over time.

---

## Why this fork exists

This fork preserves the original goal of AnnoABSA — efficient ABSA annotation — while making the system more flexible for real research workflows:

- custom dataset formats
- multiple model providers
- configurable prompts
- a restored manual annotation experience
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
