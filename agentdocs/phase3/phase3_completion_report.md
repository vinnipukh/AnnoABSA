# Phase 3 — Completion Report: NLP Helper Toolbar

**Date:** 2026-07-11
**Goal:** A collapsible NLP toolbox attached to text-span selection, available in both Manuel and Karşılaştır modes, providing lexicon sentiment lookup, sentence-level sentiment classification, morphological analysis, and embedding similarity.
**Status:** ✅ Complete (3 tasks)

---

## What this is (for the academic reader)

The NLP Helper Toolbox is a research-assistance feature that gives an annotator instant access to four NLP tools on any selected span of review text — without leaving the annotation interface. It supports the **error analysis and decision-making** part of ABSA annotation, where a human annotator may need to verify the polarity of an individual word, check the morphological root of a Turkish inflected form, or compare the contextual similarity of a selected phrase against its surrounding sentence.

The feature was delivered across three tasks:

| Task | Scope | Status |
|---|---|---|
| **Task 1** | Backend NLP module (`services/nlp_helpers.py`), 4 API endpoints (`app/routes/nlp.py`), lazy-loading infrastructure | ✅ Complete |
| **Task 2** | Shared text-selection hook (`useTextSelection.ts`), refactored PhraseAnnotator, clickable text in ManualInputForm | ✅ Complete (absorbed into Task 1) |
| **Task 3** | Collapsible toolbar component (`NlpHelperToolbar.tsx`), unit tests, wiring in App.tsx | ✅ Complete (verified in this session) |

---

## Architecture

The toolbar uses a **three-tier architecture**:

```
┌────────────────────────────────────────────────────┐
│  Frontend: NlpHelperToolbar.tsx                    │
│  Collapsible floating toolbox (red toolbox icon)    │
│  Fixed position: centered above footer             │
├────────────────────────────────────────────────────┤
│  Hook: useTextSelection.ts                         │
│  Reads native browser selection on mouseup          │
│  Computes character offsets via DOM Range walking   │
├────────────────────────────────────────────────────┤
│  Backend: app/routes/nlp.py → services/nlp_helpers  │
│  4 endpoints: lexicon, sentiment, morphology, embs   │
└────────────────────────────────────────────────────┘
```

---

## What was built

### Backend: `services/nlp_helpers.py` (~280 lines)

A new Python module with **four lazy-loaded NLP tools** — each loads into memory only on first use, not at server startup:

| Tool | Library | Model/Resource | Loading |
|---|---|---|---|
| Word-level sentiment | `nlptoolkit-sentinet` (SentiNet) | Turkish polarity lexicon (76,825 synsets) via WordNet flattening | First call ~instant |
| Sentence-level sentiment | HuggingFace `transformers` | `savasy/bert-base-turkish-sentiment-cased` | First call ~30s (1.2 GB) |
| Morphological analysis | `nlptoolkit-morphologicalanalysis` | Turkish FST-based analyzer | First call ~instant |
| Embedding similarity | `sentence-transformers` | `intfloat/multilingual-e5-small` | First call ~5s (118 MB) |

**Lexicon flattening detail:** SentiNet's API is synset-ID-based. The installed Turkish WordNet (~78,327 synsets) is iterated once at first access. Each synset's literals map to the synset's polarity score; when a word appears in multiple synsets with different polarities, scores are averaged. This sacrifices word-sense precision for fast runtime lookup.

**Confirmed working on Python 3.11.15** with `setuptools<75` (required for `pkg_resources` usage by StarlangSoftware packages).

### Backend: `app/routes/nlp.py` (~70 lines)

The **first production route file** under `app/routes/`, establishing the pattern for future endpoint migrations from `main.py`:

| Endpoint | Input | Output | Tool |
|---|---|---|---|
| `GET /nlp/lexicon-polarity` | `text` | Per-word polarity + aggregate | SentiNet |
| `GET /nlp/sentiment` | `text` | Label + confidence | BERT |
| `GET /nlp/morphology` | `word` | Root, POS, inflectional groups | NlpToolkit |
| `GET /nlp/embedding-similarity` | `selection`, `sentence` | Cosine similarity (0.0–1.0) | e5-small |

Wired into `main.py` via `app.include_router(nlp_router)`.

### Frontend: Shared selection hook `useTextSelection.ts`

Originally extracted as a 3-state click machine (Task 2), **significantly revised in this session** (2026-07-11) to use **native browser drag-to-select** instead of custom click-to-select.

**Current implementation:**
- Replaced `handleCharClick` (3-state click machine) with `handleMouseUp(container: HTMLElement)`
- On mouseup, reads `window.getSelection()` and computes character offsets via DOM `Range.toString().length` walking — works correctly even when text is split across multiple `<span>` elements (annotation highlighting)
- Token snapping and phrase cleaning applied as before
- `clearSelection()` also clears the browser's native selection highlight
- Pure functions remain unchanged (`getTokenBounds`, `cleanPhrase`, `getCleanedPositions`)

**Why this change:** Users found the multi-click selection tedious and unnatural. The new approach works exactly like standard desktop text selection (Word, browser): click-drag-release, with the browser's native blue highlight.

### Frontend: `NlpHelperToolbar.tsx` (~260 lines)

A collapsible floating toolbox with two states:

- **Collapsed** — a red toolbox SVG icon (hardcoded `#DC2626` — ignores theme changes)
- **Expanded** — four segment buttons: Sözlük (auto-fetches), Duygu Analizi, Yapı Çözümleme, Benzerlik Karşılaştırması (on-demand)

**Positioning changes made in this session:**
- Originally anchored to `window.getSelection().getBoundingClientRect()` (appeared at top-left near selection)
- Changed to `position: fixed; bottom: 64px; left: 50%; transform: translateX(-50%)` — centered horizontally above the footer, in the empty space below the review columns
- `anchorRect` prop removed as dead code

**Interaction:** Escape key collapses, click-outside collapses, `AbortController` cancels in-flight requests on selection change.

### Frontend: `PhraseAnnotator.tsx` (Manuel mode)

- Refactored to use the shared `useTextSelection` hook
- Annotation form, popup, triplet rendering, and color highlighting unchanged
- `onSelectionChange` callback notifies `App.tsx` for NLP toolbox state
- `select-none` CSS removed — browser handles selection natively
- Custom blue selection overlay removed — browser handles it natively
- Span-level `onMouseDown`/`onMouseOver` event handlers removed

### Frontend: `ManualInputForm.tsx` (Karşılaştır / Compare mode)

- Clickable text spans using the shared `useTextSelection` hook
- Blue highlight overlay and `select-none` CSS removed — native browser selection
- Span-level event handlers removed
- Container div gets `onMouseUp` wired to `handleMouseUp(textContainerRef.current!)`

### `NlpHelperToolbar.test.tsx` (created this session)

**14 component tests** covering:

| Group | Tests | What's tested |
|---|---|---|
| Collapsed state | 3 | Toolbox icon renders, no fetch on mount, no segment labels |
| Expanded state | 7 | Expand on click, auto-fetch lexicon, on-demand sentiment/morphology/similarity, skip similarity when no `sentenceText` |
| Error handling | 2 | Network error and HTTP 500 |
| Keyboard/interaction | 2 | Escape collapses, `onClose` fires |

Uses `ReactDOM.createRoot` + `ReactDOM.flushSync` instead of `@testing-library/react` (incompatible with React 19.2.7 CJS build — `React.act` is undefined).

---

## Files changed across all three tasks

### Created

| File | Lines | Task |
|---|---|---|
| `services/nlp_helpers.py` | ~280 | T1 — Backend NLP tools |
| `app/routes/nlp.py` | ~70 | T1 — API endpoints |
| `frontend/src/hooks/useTextSelection.ts` | ~110 | T2 → revised session — Drag selection hook |
| `frontend/src/hooks/useTextSelection.test.ts` | 78 | T2 — 13 vitest tests for pure functions |
| `frontend/src/components/NlpHelperToolbar.tsx` | ~260 | T3 — Collapsible toolbox component |
| `frontend/src/components/NlpHelperToolbar.test.tsx` | ~250 | T3 — 14 component tests |
| `tests/test_nlp_helpers.py` | 130 | T1 — 12 pytest tests (mocked) |

### Modified

| File | Change |
|---|---|
| `main.py` | +2 lines: `app.include_router(nlp_router)` |
| `app/routes/__init__.py` | Added `nlp` to docstring |
| `pyproject.toml` | Added 7 NLP dependencies + `setuptools<75` |
| `requirements.txt` | Same dep additions |
| `frontend/src/App.tsx` | Added `nlpToolbarSelection` state, `handleNlpSelectionChange` callback, toolbox mount |
| `frontend/src/components/PhraseAnnotator.tsx` | Refactored to use hook; native selection; removed custom overlay |
| `frontend/src/components/ManualInputForm.tsx` | Clickable text; native selection; removed custom overlay |
| `frontend/vite.config.js` | Added vitest test config |
| `docs/architecture_map.md` | Added NLP router, hook, toolbox to module graph |
| `agentdocs/ProjectPrimer.md` | Added new files to stack list |
| `agentdocs/session_reports/backend_reference.md` | Added NLP endpoints, nlp_helpers module |
| `tests/testcases.md` | Added Tier 7 (9 backend) + Tier 7B (8 frontend) test cases |

---

## Dependencies added

```txt
# StarlangSoftware NLP Toolkit (confirmed working on Python 3.11)
nlptoolkit-sentinet
nlptoolkit-wordnet
nlptoolkit-dictionary
nlptoolkit-morphologicalanalysis
# HuggingFace / ML
sentence-transformers
transformers
torch
# Required for pkg_resources compatibility
setuptools<75
# FastAPI file upload (was missing)
python-multipart
```

Frontend (dev-only):
```txt
vitest
```

---

## Key design decisions

### 1. Native browser selection over custom click machine
Originally implemented as a 3-state click cycle (first click = start, second = end, third = reset) using per-character-span `onClick` handlers. User reported this was "tedious, unnatural, and slows down the workflow." Revised to use native browser drag-to-select: `window.getSelection()` is read on mouseup, character offsets are computed via DOM Range walking. Token snapping and cleaning still apply. The browser handles the visual selection highlight.

### 2. Red toolbox icon (theme-independent)
The original bag icon was replaced with a red toolbox SVG. Hardcoded `#DC2626` fill/stroke (no Tailwind theme classes) so it stays red in both light and dark mode.

### 3. Fixed bottom-center positioning
Originally anchored to the selection's `getBoundingClientRect()` which placed the toolbar near the top-left of the screen. Changed to `bottom: 64px; left: 50%; transform: translateX(-50%)` to sit centered above the footer, in the empty space below the review/LLM columns.

### 4. Lazy-loading all models (zero startup cost)
Following the project's existing convention, all four NLP tools load only on first use. Server startup shows no SentiNet, BERT, NlpToolkit, or SentenceTransformer messages.

### 5. First production APIRouter under `app/routes/`

### 6. Lexicon flattening (WordNet synset → word map)

### 7. Auto-vs-on-demand computation policy
- **Lexicon** (local dict, ~1ms) → auto-fetches on expand
- **Sentiment** (BERT, ~1.2 GB) → on segment click
- **Morphology** (NlpToolkit, local, ~5ms) → on segment click
- **Embedding** (e5-small, ~118 MB) → on segment click

---

## Final verification results

| Check | Result |
|---|---|
| `pytest tests/` | **93 passed** (81 existing + 12 NLP helper tests) |
| `npx vitest run` | **27 passed** (13 pure-function + 14 component tests) |
| `npm run build` | **✓** 44 modules, ~271 KB JS |
| No temp files leaked | ✅ All temp files cleaned up |
| `vite.config.js` unchanged | ✅ No net diff |

---

## Tips for future coding agents

### 1. Native selection + Range offset computation
The hook now reads `window.getSelection()` on mouseup. Character offsets are computed by creating a temporary `Range` from the container root to the selection boundary and measuring `range.toString().length`. This works reliably even when text is fragmented across multiple `<span>` elements (annotation highlighting, character runs).

```typescript
function getCharOffset(container: HTMLElement, refNode: Node, refOffset: number): number {
  const r = document.createRange();
  r.selectNodeContents(container);
  r.setEnd(refNode, refOffset);
  return r.toString().length;
}
```

### 2. React 19.2.7 + @testing-library/react incompatibility
`@testing-library/react` v16.3.2 crashes on React 19.2.7 because the CJS build of `react` does not export `React.act`, but `react-dom/test-utils` calls it internally. If adding component tests, use `ReactDOM.createRoot` + `ReactDOM.flushSync` directly instead of testing-library's `render()`.

### 3. WordNet/SentiNet API surfaces
See Task 1 completion report for full reverse-engineered API details. Key: `getPositiveScore()` returns strings, `getSentiSynSet(id)` raises `KeyError`, literal names have parentheses.

### 4. Mock targets for backend NLP tests
Mock the `get_*` functions in `services/nlp_helpers`, not the StarlangSoftware classes directly — lazy-loading prevents deep-path mocking.

### 5. Toolbox auto-collapses on selection change
`NlpHelperToolbar.tsx` has a `useEffect` on `selectedText` that resets all segment results and collapses. This is intentional — results are stale for a new selection.
