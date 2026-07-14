# 🏗️ AnnoABSA — Technology Stack

> **Generated:** Codebase analysis — tech-focused.
> **Last updated:** 2026-07-13

---

## 1. Overview

AnnoABSA is a full-stack web application for **Aspect-Based Sentiment Analysis (ABSA)** annotation. It combines a Python/FastAPI backend with a React/TypeScript frontend, supported by NLP toolkits, ML models, and multiple LLM provider integrations.

| Layer | Technology | Version (declared) |
|---|---|---|
| **Backend** | Python | ≥3.11 |
| **Backend framework** | FastAPI | latest (pip) |
| **Backend server** | uvicorn | latest (pip) |
| **Frontend** | React | ^19.1.1 |
| **Frontend language** | TypeScript | ^5.9.2 |
| **Build tool** | Vite | ^4.5.14 |
| **Styling** | Tailwind CSS | ^3.4.17 |
| **Component library** | DaisyUI | ^4.12.24 |
| **CSS processing** | PostCSS | ^8.5.6 |
| **Autoprefixer** | autoprefixer | ^10.4.21 |
| **Icon library** | Phosphor Icons | ^2.1.10 |

---

## 2. Backend — Python / FastAPI

### 2.1 Core framework

- **Python 3.11+** — Minimum required version
- **FastAPI** — ASGI web framework for REST endpoints
- **uvicorn** — ASGI server (`uvicorn main:app --reload`)

### 2.2 Data handling

| Package | Purpose |
|---|---|
| **pandas** | CSV data I/O, DataFrame operations |
| **python-multipart** | File upload parsing (multipart/form-data) |

### 2.3 ML / AI

| Package | Purpose | Typical version range |
|---|---|---|
| **scikit-learn** | TF-IDF vectorizer, LogisticRegression (active learning) | ≥1.x |
| **transformers** | HuggingFace pipeline for sentiment classification | latest |
| **torch** | Backend for HuggingFace models and sentence-transformers | latest |
| **sentence-transformers** | Embedding similarity (multilingual-e5-small) | latest |
| **rank-bm25** | BM25 retrieval for few-shot example selection | latest |

### 2.4 NLP (Turkish)

| Package | Purpose | Source |
|---|---|---|
| **nlptoolkit-sentinet** | SentiNet lexicon for word-level sentiment | pip (nlptoolkit-\*) |
| **nlptoolkit-wordnet** | Turkish WordNet for synset traversal | pip (nlptoolkit-\*) |
| **nlptoolkit-dictionary** | Turkish dictionary (word forms) | pip (nlptoolkit-\*) |
| **nlptoolkit-morphologicalanalysis** | FsmMorphologicalAnalyzer (morphological parsing) | pip (nlptoolkit-\*) |

### 2.5 LLM providers

| Package | Purpose |
|---|---|
| **openai** | OpenAI API SDK and generic OpenAI-compatible APIs (vLLM, custom) |
| **ollama** | Local Ollama inference (Python SDK) |
| **anthropic** | Anthropic Claude API SDK |

### 2.6 Version pinning note

> `setuptools<75` is pinned in `pyproject.toml` to avoid compatibility issues with HuggingFace `transformers` or other deep learning packages that still depend on older setuptools behavior (e.g., `pkg_resources`).

---

## 3. Frontend — React / TypeScript

### 3.1 Core

| Technology | Version | Notes |
|---|---|---|
| **React** | ^19.1.1 | Latest React 19 with concurrent features |
| **React DOM** | ^19.1.1 | |
| **TypeScript** | ^5.9.2 | Strict mode disabled; noImplicitAny=false |

### 3.2 Build & dev server

| Tool | Version | Notes |
|---|---|---|
| **Vite** | ^4.5.14 | Dev server on port 3000, build output to `build/` |
| **@vitejs/plugin-react** | ^4.0.0 | React Fast Refresh |
| **@types/node** | ^24.3.1 | Node type definitions |

### 3.3 Styling

| Tool | Version | Notes |
|---|---|---|
| **Tailwind CSS** | ^3.4.17 | Utility-first CSS framework |
| **DaisyUI** | ^4.12.24 | Component library (7 themes configured: light, dark, coffee, forest, cupcake, aqua, lemonade) |
| **PostCSS** | ^8.5.6 | CSS transformation pipeline |
| **autoprefixer** | ^10.4.21 | Vendor prefix insertion |

### 3.4 Icons

| Package | Version |
|---|---|
| **@phosphor-icons/react** | ^2.1.10 |

### 3.5 Type definitions (React)

| Package | Version |
|---|---|
| **@types/react** | ^19.1.12 |
| **@types/react-dom** | ^19.1.9 |

### 3.6 App architecture

- **Single-page application (SPA)** — no router; state-driven view switching (`compare` vs `manual` modes)
- **Vite proxy** — frontend calls backend at `http://localhost:8000` (configurable via `VITE_BACKEND_URL`)
- **Entry point** — `frontend/src/index.tsx` → `App.tsx`
- **Component tree:**
  - `App.tsx` — root component; manages all state, handles API calls
  - `ModelTripletColumn.tsx` — displays Model A/B triplet columns
  - `ManualInputForm.tsx` — manual triplet entry form
  - `PhraseAnnotator.tsx` — inline text annotation UI
  - `AISuggestions.tsx` — AI prediction suggestions panel
  - `SettingsPanel.tsx` — settings modal (PATCH /settings)
  - `HelperAgentChatbox.tsx` — LLM-powered chat assistant
  - `NlpHelperToolbar.tsx` — NLP analysis toolbar
  - `ActiveLearningSuggestions.tsx` — active learning panel
  - `WelcomeOverlay.tsx` — first-run overlay
  - `EditReviewTextModal.tsx` — edit review text modal
  - `CustomCheckbox.tsx` — reusable checkbox
  - `PhraseAnnotator` / `phraseColoring.tsx` — annotation coloring logic
  - `hooks/useTextSelection.ts` — text selection hook

---

## 4. Development Tooling

### 4.1 Python toolchain

| Tool | Status |
|---|---|
| **uv** | Installed (package installer) |
| **pip** | Not available at shell level |
| **python** | 3.11.15 available |

### 4.2 Node.js toolchain

| Tool | Expected |
|---|---|
| **npm** | Required for frontend dev/build (verified in runner.py) |
| **npx** | Available |

### 4.3 CLI

- **`annoabsa`** — Python CLI (`cli.py` → `cli/__init__.py` → `cli.runner`)
- Supports `--backend-port`, `--frontend-port`, `--llm-provider`, `--openai-key`, `--anthropic-key`, `--vllm-url`, `--model-a-*`, `--model-b-*`, `--helper-agent-*`
- STD format conversion (`--format std` / `--export-std`)

---

## 5. Testing

### 5.1 Backend (Python)

| Tool | Details |
|---|---|
| **pytest** | 6 test files, 128 tests |
| Test files | `tests/test_smoke.py`, `tests/test_prediction.py`, `tests/test_live_prediction.py`, `tests/test_llm_providers.py`, `tests/test_nlp_helpers.py`, `tests/test_main_helpers.py` |

### 5.2 Frontend (TypeScript)

| Tool | Version | Details |
|---|---|---|
| **vitest** | ^4.1.10 | 5 test files, 51 tests |
| **jsdom** | ^29.1.1 | DOM environment for vitest |
| **@testing-library/react** | ^16.3.2 | React component testing |
| **@testing-library/jest-dom** | ^6.9.1 | Custom DOM matchers |
| Test files | `HelperAgentChatbox.test.tsx`, `SettingsPanel.test.tsx`, `ModelTripletColumn.test.tsx`, `useTextSelection.test.ts`, `NlpHelperToolbar.test.tsx` |

---

## 6. Infrastructure & Deployment

### 6.1 Ports

| Service | Default Port |
|---|---|
| **Backend (FastAPI/uvicorn)** | `8000` |
| **Frontend (Vite dev server)** | `3000` |

### 6.2 Data persistence

| Format | Details |
|---|---|
| **CSV** | UTF-8 encoded, pandas DataFrame |
| **JSON** | UTF-8 encoded, list of dicts |
| **Config** | JSON file loaded at startup (`ABSA_CONFIG_PATH`) |

### 6.3 Compatibility notes

- **Tsconfig:** `target: "es5"`, `strict: false`, `noImplicitAny: false`, `jsx: "react-jsx"`
- **Vite config:** JS loader overrides for `.js` → `jsx`, `.ts` → `ts`, `.tsx` → `tsx`
- **PostCSS:** Tailwind CSS + autoprefixer plugins only
