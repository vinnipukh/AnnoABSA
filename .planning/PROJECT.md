# AnnoABSA

## What This Is

AnnoABSA is a web-based annotation tool for Aspect-Based Sentiment Analysis (ABSA), forked and customized for Turkish ABSA research. It combines a FastAPI backend with a React/TypeScript frontend and supports manual span-based annotation, LLM-assisted prediction (Ollama, OpenAI, Anthropic, vLLM, Custom OpenAI), Live Compare Mode (per-model provider/model/temperature/prompt), autopilot navigation via `[[action:...]]` directives, active learning (TF-IDF + LogisticRegression uncertainty sampling), and an NLP Helper Toolbox (SentiNet lexicon, BERT sentiment classifier, NlpToolkit morphological analyzer, e5-small embedding similarity). Accepted at **LREC 2026** in Palma, Mallorca, Spain.

## Core Value

A researcher can efficiently annotate Turkish reviews for ABSA triplets (aspect term, aspect category, sentiment polarity) using manual selection, AI suggestions, or autonomous pipeline actions — and export results in a sharable format.

## Requirements

### Validated

- ✓ **STD format dataset support** — Two-column CSV (`review,triplet`) loading via `--format std` flag, with `std_triplets_to_label()` converter and `--export-std` round-trip export — Phase 1
- ✓ **Generalized two-model comparison** — Configurable comparison CSVs and display names via `--compare-model-a-csv`, `--compare-model-a-name`, `--compare-model-b-csv`, `--compare-model-b-name`. Renamed from `deepseek_triplets`/`qwen_triplets` to `model_a_triplets`/`model_b_triplets` — Phase 1
- ✓ **New LLM providers** — Anthropic and vLLM added alongside Ollama and OpenAI, behind a hexagonal provider adapter pattern (`LLMProviderPort` protocol, `PROVIDER_REGISTRY`, `get_provider()` factory) — Phase 1
- ✓ **Turkish-language prompts** — Configurable `DEFAULT_LABELING_TEMPLATE` and `DEFAULT_CHAT_TEMPLATE` with `.format()` placeholders, category/polarity values stay in English — Phase 1
- ✓ **Restored manual annotation** — `PhraseAnnotator` component with click-to-select span annotation, inline color highlighting, popup form for category/polarity — Phase 1
- ✓ **Mode toggle** — "Karşılaştır" (Compare) / "Manuel" (Manual) mode selector in header, per-review state, no triplet loss on toggle — Phase 1
- ✓ **AI Suggestions** — `AISuggestions` component with accept/reject, auto-trigger gating, AbortController on row nav — Phase 2
- ✓ **Settings Panel** — Modal with 5+ sections (annotation elements, appearance, AI prediction, saving, system prompts), PATCH /settings endpoint — Phase 2
- ✓ **NLP Helper Toolbox** — 4 lazy-loaded Turkish NLP tools (SentiNet lexicon, BERT sentiment classifier, NlpToolkit morphological analyzer, e5-small embedding similarity), 4 API endpoints under `/nlp/`, native drag-to-select via `useTextSelection` hook — Phase 3
- ✓ **Live Compare Mode** — Per-model provider/model/temperature/prompt for Model A and Model B, Live vs CSV mode selector, 13 new config keys, `GET /live_prediction/{data_idx}?role=model_a|model_b` endpoint — Phase 4
- ✓ **Autopilot AppActions** — 15-method `AppActions` interface wired through `App.tsx` → `HelperAgentChatbox` via `useRef`, `[[action:methodName(args)]]` parser in frontend — Phase 4/6
- ✓ **Architecture cleanup (main.py breakup)** — 1206→50 lines, extracted `app/config.py`, `app/data.py`, `app/positions.py`, 6 route files under `app/routes/` — Phase 5
- ✓ **CLI breakup** — 1053→6 lines thin wrapper, extracted `cli/config.py`, `cli/runner.py`, `cli/convert.py` — Phase 6
- ✓ **Emoji → SVG** — All structural emoji replaced with inline SVGs in HelperAgentChatbox and NlpHelperToolbar — Phase 6
- ✓ **TSConfig fix** — `"vite/client"` added to types array, eliminated pre-existing `env` error — Phase 6
- ✓ **Component tests** — 24+ vitest tests for SettingsPanel, ModelTripletColumn, HelperAgentChatbox — Phase 6
- ✓ **RAG extension** — BM25 few-shot retrieval added to Helper Agent chat via `{few_shot_examples}` placeholder in `DEFAULT_CHAT_TEMPLATE` — Phase 6
- ✓ **Active learning** — `services/active_learning.py` (TF-IDF + LogisticRegression), `app/routes/learning.py` (`GET /learning/suggestions`, `GET /learning/predict/{idx}`), Lightbulb button in header — Phase 6
- ✓ **Custom OpenAI provider** — Any OpenAI-compatible API via URL + API key, added to `PROVIDER_REGISTRY` — Phase 6
- ✓ **Smoke tests** — 4+ compile-only checks in `tests/test_smoke.py` — Phase 5
- ✓ **Live Compare tests** — 19 integration tests in `tests/test_live_prediction.py` with FastAPI TestClient — Phase 4
- ✓ **4-Way Compare Mode (NEWUI)** — 2x2 grid (GT + Gemma + Qwen + GPT), compact triplet chips, consensus diamond, 3-tier resolution panel — Phase 7.1
- ✓ **NEWUI CSV parser** — `_load_4way_row()` for `semeval_tr_llm_annotated.csv` with `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff` — Phase 7.1
- ✓ **Resolution panel tests** — 13 vitest tests for 3-tier curation logic — Phase 7.1
- ✓ **Active learning tests** — 18 pytest tests for `services/active_learning.py` (train, predict, uncertainty scoring) — Phase 7.2
- ✓ **Learning route tests** — 16 pytest tests for `app/routes/learning.py` via TestClient — Phase 7.2
- ✓ **CLI tests** — 31 pytest tests for `cli/config.py`, `cli/convert.py`, `cli/runner.py` — Phase 7.2
- ✓ **Endpoint tests (misc routes)** — 16 pytest tests for settings/timing/upload — Phase 7.2
- ✓ **3 TS errors fixed** — `rect`, `global`, `includes` resolved (0 remaining) — Phase 7.2
- ✓ **Vite 4→5 upgrade** — `^5.4.19`, deprecated esbuild config removed — Phase 7.2
- ✓ **App.tsx split** — 770→250 lines, 5 custom hooks extracted, 4 hook test files (87 total frontend tests) — Phase 7.2
- ✓ **Timing route bug fix** — HTTPException(404) no longer swallowed as 500 by generic except — Phase 7.2
- ✓ **3 `[[action:...]]` directives** — `selectTriplet`, `addTriplet`, `annotateAll` added to DEFAULT_CHAT_TEMPLATE (15 total) — Phase 7.3
- ✓ **Ctrl+Shift+L shortcut** — toggles Active Learning panel, ref-forwarded callback pattern — Phase 7.3
- ✓ **Auto-suggest banner** — `AutoSuggestBanner.tsx`, DaisyUI alert-info, Heroicons SVG, accessibility — Phase 7.3
- ✓ **addTriplet 3-arg wrapper** — `addTriplet(term, category, polarity)` in AppActions, fully tested — Phase 7.3
- ✓ **Chat predictions endpoint** — `GET /chat/predictions/{idx}` returning Turkish text + predictions, 18 tests — Phase 7.3
- ✓ **annotateAll() pipeline** — predict → filter → addTriplet → saveAndNext → loop, abort safety, progress toasts — Phase 7.3
- ✓ **CSV column names on grid headers** — monospace labels on 2x2 card headers — Phase 7.4
- ✓ **Demo mode toggle** — 4th mode button, 6-sample demo data covering all 3 tiers — Phase 7.4
- ✓ **Tier filter dropdown** — All/Tier 1/2/3 filtering review queue on navigation — Phase 7.4
- ✓ **Auto-save on navigation** — prev and next both save with toast confirmation — Phase 7.4
- ✓ **Save button in resolution panel** — Heroicons save SVG, `aria-label="Kaydet"` — Phase 7.4
- ✓ **CSV export endpoint** — `GET /data/export-4way` with all columns + annotation fields, 9 tests — Phase 7.4

### Active

*(None — Phase 7 fully complete!)*

### Out of Scope

- Database-backed persistence (file-based CSV/JSON only) — defer to future if scale demands it
- User accounts / multi-user support — single-user research tool
- English UI translation — Turkish-language research tool
- Real-time collaborative annotation — single-annotator workflow

## Context

- **Stack:** Python 3.11, FastAPI, uvicorn / React 19, TypeScript 5.9, Vite 5, Tailwind CSS 3, DaisyUI 4
- **ML/NLP:** scikit-learn, transformers, torch, sentence-transformers, rank-bm25, nlptoolkit-* (SentiNet, WordNet, Dictionary, MorphologicalAnalysis)
- **LLM Providers:** Ollama (localhost:11434), OpenAI, Anthropic, vLLM, Custom OpenAI (any OpenAI-compatible API)
- **Testing:** 237 pytest (backend) + 88 vitest (frontend) = 325 automated tests
- **Data:** CSV or JSON files, auto-detected from extension, loaded/saved via `load_data()`/`save_data()` in `app/data.py`
- **Dev history:** 7 completed phases (Phases 1-6) + 4 Phase 7 sub-phases fully complete. Backend: 237 tests. Frontend: 88 tests. 0 TS errors.
- **Route modules:** 9 (`nlp`, `settings`, `reviews`, `ai`, `timing`, `upload`, `learning`, `chat_predictions`, `export`)
- **Frontend components:** 21 React components + 7 custom hooks + demo data module
- **Known issues:**
  - `data.py` import staleness: `from app.config import X` creates by-value copies; prefer `import app.config as cfg`
  - CORS allows all origins (`*`) — no authentication
  - No persistent database — flat file I/O, not thread-safe
  - `setuptools<75` pin required for NlpToolkit `pkg_resources` compatibility
  - React 19 CJS + `@testing-library/react` incompatibility; use `createRoot` + `flushSync` for tests
  - BM25 tokenization has no Turkish stemming — plain `\b\w+\b` regex
  - FastAPI is single-threaded by default — long LLM calls block all other requests
  - `'NULL'` is a literal string sentinel for implicit aspects — never convert to `""`

## Constraints

- **Python**: >=3.11
- **setuptools**: <75 (StarlangSoftware compatibility)
- **Ports**: 8000 (backend), 3000 (frontend)
- **Models**: BERT ~1.2GB, e5-small ~118MB download on first use
- **Architecture**: Two-process (FastAPI + Vite dev server), REST-only communication
- **State**: Global module-level dict (`CONFIG_DATA`) — no DI, not thread-safe

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| File-based persistence (CSV/JSON) | Simplicity for research datasets; no DB operations overhead | ✓ Good |
| Hexagonal LLM provider adapters | Clean separation of provider-specific code; easy to add 5th provider | ✓ Good |
| No fallback for per-model config | Per-model provider/model must be explicitly configured — KISS | ✓ Good |
| Native drag-to-select over click machine | Users found multi-click tedious; native selection matches desktop editors | ✓ Good |
| `data-theme` DaisyUI theming over CSS dark mode | DaisyUI handles theme colors natively via semantic classes | ✓ Good |
| Lazy-loaded NLP models | Zero startup time; models load on first use (10-30s delay acceptable) | ✓ Good |
| Separate CSV vs Live state in App.tsx | Clear state management; no merge logic between modes | ✓ Good |
| `[[action:...]]` inline directives for autopilot | Hybrid text+actions keeps chat natural while enabling programmatic control | ✓ Good — 15 actions registered, full pipeline functional |
| Separate endpoint for Live predictions | Zero risk of breaking AI Suggestions; independent validation rules | ✓ Good |
| `createRoot` + `flushSync` for React 19 tests | Bypasses `@testing-library/react` CJS `act` bug | ✓ Good |
| Frontend `FALLBACK_DATA` / `DEMO_DATA` for demo mode | No backend dependency for demo; reusable pattern | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-14 — Phase 7 fully complete (all 4 sub-phases, 237+88 tests)*
