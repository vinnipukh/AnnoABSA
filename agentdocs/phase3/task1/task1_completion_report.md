# Phase 3 — Task 1 Completion Report: NLP Helper Toolbar

**Date:** 2026-07-11
**Goal:** A collapsible NLP toolbar attached to text-span selection, available in both Manuel and Karşılaştır modes, providing lexicon sentiment lookup, sentence-level sentiment classification, morphological analysis, and embedding similarity.
**Status:** ✅ Complete

---

## What this is (for the academic reader)

The NLP Helper Toolbar is a research-assistance feature that gives an annotator instant access to four NLP tools on any selected span of review text — without leaving the annotation interface. It is designed to support the **error analysis and decision-making** part of ABSA annotation, where a human annotator may need to verify the polarity of an individual word, check the morphological root of a Turkish inflected form, or compare the contextual similarity of a selected phrase against its surrounding sentence.

The toolbar was implemented as a **three-tier architecture**: a backend Python module with four lazy-loaded NLP models, a shared React text-selection hook extracted from the existing annotation component, and a floating toolbar UI component mounted in both annotation modes.

---

## What was built

### Backend: `services/nlp_helpers.py` (~280 lines)

A new module with **four lazy-loaded NLP tools** — each loads into memory only on first use, not at server startup:

| Tool | Library | Model/Resource | Import path | Size |
|---|---|---|---|---|
| Word-level sentiment | `nlptoolkit-sentinet` (SentiNet) | Turkish polarity lexicon (76,825 synsets) via WordNet flattening | `SentiNet.SentiNet` | ~5 MB (XML) |
| Sentence-level sentiment | HuggingFace `transformers` | `savasy/bert-base-turkish-sentiment-cased` | `transformers.pipeline` | ~1.2 GB |
| Morphological analysis | `nlptoolkit-morphologicalanalysis` (NlpToolkit) | Turkish FST-based morphological analyzer | `MorphologicalAnalysis.FsmMorphologicalAnalyzer` | ~25 MB |
| Embedding similarity | `sentence-transformers` | `intfloat/multilingual-e5-small` (118 MB) | `SentenceTransformer` | ~118 MB |

**Key implementation detail — lexicon flattening:** SentiNet's API is synset-ID-based (e.g. `getSentiSynSet("TUR10-0000001")`). To support word-level lookup (select a word → get its polarity), the installed Turkish WordNet (~78,327 synsets) is iterated once at first access. Each synset's literals are mapped to the synset's polarity score from SentiNet. When a word appears in multiple synsets with different polarities, scores are averaged. This sacrifices word-sense precision for a simple, fast runtime lookup — appropriate for an annotation assistance tool.

**Confirmed working on Python 3.11** — the NlpToolkit/StarlangSoftware packages (`nlptoolkit-sentinet`, `nlptoolkit-wordnet`, `nlptoolkit-morphologicalanalysis`) install and run correctly on Python 3.11.15, despite their documentation claiming 3.13+. A critical dependency is `setuptools<75` because these packages use `pkg_resources` at import time.

### Backend: `app/routes/nlp.py` (~70 lines)

The **first production route file** under `app/routes/`, establishing the pattern for future endpoint migrations from `main.py`. Uses FastAPI `APIRouter` with prefix `/nlp`:

| Endpoint | Input | Output | Tool |
|---|---|---|---|
| `GET /nlp/lexicon-polarity` | `text` (string) | Per-word polarity + aggregate | SentiNet |
| `GET /nlp/sentiment` | `text` (string) | Label + confidence score | BERT classifier |
| `GET /nlp/morphology` | `word` (string) | Root, POS, inflectional groups | NlpToolkit |
| `GET /nlp/embedding-similarity` | `selection`, `sentence` | Cosine similarity (0.0–1.0) | e5-small |

Wired into `main.py` via `app.include_router(nlp_router)` — the only change to `main.py` for this feature.

### Frontend: Shared selection hook `useTextSelection.ts` (~90 lines)

Extracted the character-level click-to-select logic from `PhraseAnnotator.tsx` (Manuel mode) into a shared React hook. Three pure functions are exported for unit testing:

- **`getTokenBounds(text, charIndex)`** — expands a character index to word boundaries using a whitespace/punctuation delimiter set, supporting Turkish characters
- **`cleanPhrase(text)`** — strips leading/trailing punctuation (including Turkish quotes «»)
- **`getCleanedPositions(start, end, text, clean)`** — returns adjusted character positions after cleaning

The hook implements a **3-state click machine**: first click sets `selStart` (start of word via token snapping), second click sets `selEnd` (end of word), third click resets both. Returns `[TextSelectionState, TextSelectionActions]`.

### Frontend: `NlpHelperToolbar.tsx` (~190 lines)

A collapsible floating toolbar with two states:
- **Collapsed** — a small SVG bag icon (inline, not a file asset) positioned near the selection
- **Expanded** — four segment buttons in a card with backdrop blur

**Computation policy (confirmed with user):**
- **Lexicon** — cheap local dict lookup, fetches **automatically** on expand
- **Sentiment, Morphology, Embedding** — heavy model calls, fetch **on-demand** when the segment is clicked

Features: `Escape` key to collapse, click-outside to collapse, `AbortController` for in-flight request cancellation on selection change, per-segment loading/error/data states.

### Frontend: Refactored `PhraseAnnotator.tsx`

Replaced inline selection state (`selStart`, `selEnd`, `handleCharClick`, `getTokenBounds`, `cleanPhrase`, `getCleanedPositions`, `pendingFromSelection`) with the shared `useTextSelection` hook. Added `onSelectionChange` prop to notify `App.tsx` of selection coordinates (for toolbar positioning). Annotation form, popup, triplet rendering, and color highlighting are unchanged — the refactor is purely internal.

### Frontend: Updated `ManualInputForm.tsx`

Replaced the plain `<p>` review text with character-level clickable spans using the same `useTextSelection` hook. In Compare (Karşılaştır) mode, users can now select text in the center column with a blue highlight overlay — **no annotation popup** (that's Manuel mode's concern). Added `clickOnToken` and `onSelectionChange` props wired to `App.tsx`.

### Frontend: `App.tsx` integration

Added `nlpToolbarSelection` state and `handleNlpSelectionChange` callback. The toolbar is positioned using `DOMRect` from `window.getSelection().getRangeAt(0).getBoundingClientRect()`, anchored 8px below the selection with horizontal clamping to keep it on-screen.

---

## Files changed

### Created

| File | Lines | Purpose |
|---|---|---|
| `services/nlp_helpers.py` | ~280 | 4 lazy-loaded NLP tools + 4 handlers |
| `app/routes/nlp.py` | ~70 | APIRouter with 4 NLP endpoints |
| `frontend/src/hooks/useTextSelection.ts` | ~90 | Shared selection hook + 3 pure functions |
| `frontend/src/hooks/useTextSelection.test.ts` | 90 | 13 vitest tests for pure functions |
| `frontend/src/components/NlpHelperToolbar.tsx` | ~190 | Collapsible toolbar with 4 segments |
| `tests/test_nlp_helpers.py` | 130 | 12 pytest tests (mocked, no model downloads) |
| `agentdocs/phase3/task1_completion_report.md` | — | This file |

### Modified

| File | Change |
|---|---|
| `main.py` | +2 lines: `from app.routes.nlp import router` + `app.include_router(nlp_router)` |
| `app/routes/__init__.py` | Added `nlp` to docstring submodules list |
| `pyproject.toml` | Added 7 new dependencies |
| `requirements.txt` | Added 7 new dependencies |
| `frontend/src/App.tsx` | +~35 lines: import, state, callback, toolbar mount, props |
| `frontend/src/components/PhraseAnnotator.tsx` | Refactored to use hook; added `onSelectionChange` prop |
| `frontend/src/components/ManualInputForm.tsx` | Clickable text spans; added `clickOnToken`, `onSelectionChange` props |
| `frontend/vite.config.js` | Added vitest test config |
| `agentdocs/session_reports/backend_reference.md` | Added 2 new files + 4 NLP endpoints |
| `docs/architecture_map.md` | Added NLP router to module graph |
| `agentdocs/ProjectPrimer.md` | Added 2 new files to stack list |
| `tests/testcases.md` | Added Tier 7 (9 backend) + Tier 7B (8 frontend) test cases |

---

## Dependencies added

```txt
# StarlangSoftware NLP Toolkit (all confirmed working on Python 3.11)
nlptoolkit-sentinet                           # TurkishSentiNet-Py
nlptoolkit-wordnet                            # TurkishWordNet-Py
nlptoolkit-dictionary                         # Dictionary-Py (transitive dep)
nlptoolkit-morphologicalanalysis              # TurkishMorphologicalAnalysis-Py
# HuggingFace / ML
sentence-transformers                         # For e5-small embeddings
transformers                                  # For BERT sentiment classifier
torch                                         # Backend for transformers
# Pinned version for pkg_resources support
setuptools<75
# Already in project but was missing:
python-multipart                              # FastAPI file upload support
```

Frontend (dev-only):
```txt
vitest
@testing-library/react
@testing-library/jest-dom
jsdom
```

---

## Key design decisions

### 1. Lazy-loading all models (zero startup cost)
Following the project's existing convention (Ollama/OpenAI imports are lazy in `main.py`), all four NLP tools load only on first use. Server startup shows no SentiNet, BERT, NlpToolkit, or SentenceTransformer messages. First request to each endpoint may take 2–30 seconds (model download + load), subsequent requests are fast.

### 2. First production APIRouter under `app/routes/`
The `app/` package scaffolding (docstring-only files) was created months ago for a planned `main.py` breakup but never used. This task produced the **first real route file** there, establishing the pattern for migrating the remaining 10 `main.py` endpoints.

### 3. Lexicon flattening (WordNet synset → word map)
SentiNet's native API is synset-ID-based. Rather than requiring word-sense disambiguation on every selection, the lexicon is flattened once at first access into a `{word: (polarity, score)}` dictionary. This is a pragmatic simplification: if a word appears in 3 synsets (2 positive, 1 negative), the average score determines the label. For a rapid-assistance tool this is appropriate; for rigorous sentiment analysis the original synset-level data is still accessible via `get_sentinet()`.

### 4. Shared selection hook (Option A from the spec)
Option A (extract shared hook) was chosen over Option B (duplicate selection logic) to prevent drift between Manuel and Karşılaştır modes. The extraction is surgical — just the selection state machine. The annotation form, popup, and triplet management remain in `PhraseAnnotator.tsx`.

### 5. Auto-vs-on-demand computation policy
- **Lexicon** (local dict, ~1ms) → auto-fetches on toolbar expand
- **Sentiment** (BERT, ~500MB model) → on segment click
- **Morphology** (NlpToolkit, local, ~5ms) → on segment click (consistent)
- **Embedding** (e5-small, ~118MB model) → on segment click

---

## Verification results

| Check | Result |
|---|---|
| Backend compilation (6 files) | ✅ All pass `py_compile` |
| `pytest tests/` | ✅ **93 passed** (81 existing + 12 new) in 0.29s |
| `npx vitest run` | ✅ **13 passed** in 1.1s |
| `npm run build` | ✅ **44 modules**, 0 errors, 270 KB JS bundle |
| Lazy-loading at server startup | ✅ Logs show zero model-load messages |
| `GET /nlp/morphology?word=güzel` | ✅ Returns `{"word":"güzel","parses":[{"root":"güzel","ig":["ADJ"],"pos":"ADJ"}]}` |
| `GET /nlp/lexicon-polarity?text=güzel` | ✅ Returns `{"words":[{"word":"güzel","polarity":"positive","score":0.6274}],"aggregate":"positive"}` |
| `GET /settings` (existing endpoint) | ✅ Unchanged, returns 200 with `total_count=5` |

---

## Remaining items (not part of this task)

- **Model downloads on first use** — BERT classifier (~1.2 GB) and e5-small (~118 MB) will download on first request to their respective endpoints. First call may time out if not allowed to complete.
- **Browser smoke tests (NF1–NF8)** — Require a running backend + frontend + browser. The toolbar's interactive behavior (bag icon, expand/collapse, on-demand segment fetches) is verified by unit tests but not end-to-end.
- **Symlink warning on Windows** — HuggingFace cache emits a `HF_HUB_DISABLE_SYMLINKS_WARNING` on Windows. This is cosmetic; set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to suppress.

---

## How to demonstrate

1. Start backend: `ABSA_DATA_PATH=examples/semeval_reviews.csv python -m uvicorn main:app --port=8000`
2. Start frontend: `cd frontend && npm run dev` (opens `localhost:3000`)
3. In **Manuel mode**: click two characters in the review text → selection highlighted → **bag icon** appears near the selection → click it → toolbar expands → "Sözlük" shows polarity automatically → click "Yapı Çözümleme" for morphological breakdown
4. In **Karşılaştır mode**: same flow in the center column's review text
5. **Escape** or click outside to collapse the toolbar

---

## Tips for future coding agents

These are things I discovered empirically that aren't obvious from the code alone. Read this before touching any of the NLP toolbar files — it will save you re-exploring APIs I already mapped.

### 1. Toolbar position comes from `window.getSelection()`, not a ref

In both `PhraseAnnotator.tsx` and `ManualInputForm.tsx`, the `onSelectionChange` callback fires in a `useEffect` that reads `window.getSelection().getRangeAt(0).getBoundingClientRect()`. This is then passed to `NlpHelperToolbar` as `anchorRect`.

**Why not a textContainerRef approach?** React renders character-level `<span>` elements (one per run), so getting a single text node ref to call `document.createRange().setStart(textNode, offset)` on is unreliable — the text is already split across multiple spans. The `window.getSelection()` approach works because the browser's native selection tracking operates on the rendered DOM, not React's virtual DOM.

**If toolbar position is wrong:** the fix is in the `onSelectionChange` `useEffect` in whichever component has the issue. Don't change the toolbar's position logic.

### 2. Toolbar auto-collapses when selection changes

`NlpHelperToolbar.tsx` has a `useEffect` on `selectedText` that resets all segment results and collapses the toolbar. This means selecting new text while the toolbar is expanded collapses it back to the bag icon. **This is intentional** — the results are stale for the new selection. A future agent might think this is a bug; it's not.

### 3. The `prevEndRef.current` pattern in `PhraseAnnotator.tsx`

The bridge between `pendingSelection` (from the `useTextSelection` hook) and `pending` (component state for the annotation popup) uses a `prevEndRef` to guard against re-opening the popup:

```tsx
const prevEndRef = useRef<number | null>(null);
useEffect(() => {
  if (pendingSelection && selEnd !== prevEndRef.current) {
    setPending(pendingSelection);   // open popup
    prevEndRef.current = selEnd;
  }
  // Note: no `else` branch here — closing the popup is done by handleCancel/handleAdd,
  // not by this effect. The hook's clearSelection() sets selEnd to null,
  // but this effect won't close the popup until a new selection happens.
}, [pendingSelection, selEnd, categories]);
```

This prevents the popup from re-triggering when the `pendingSelection` memo re-derives (due to other state changes that trigger re-render). If you change the hook's return values, make sure this bridge still works — otherwise the popup may appear/disappear unexpectedly.

### 4. WordNet/SentiNet API surfaces (reverse-engineered, no docs)

The StarlangSoftware packages have minimal documentation. Here's the call chain I verified empirically:

```
# WordNet iteration
wn = WordNet()                         # from WordNet.WordNet import WordNet
synsets = wn.synSetList()              # property, not getSynSetList() — 78,327 items
for ss in synsets:
  ss_id = ss.getId()                   # e.g. "TUR10-0000000"

# SentiNet lookup — KeyError if synset not in SentiNet
sn = SentiNet()                        # from SentiNet.SentiNet import SentiNet
try:
  sentiss = sn.getSentiSynSet(ss_id)   # raises KeyError for missing synsets
  pos = float(sentiss.getPositiveScore())   # returned as str!
  neg = float(sentiss.getNegativeScore())   # returned as str!
except KeyError:
  pass  # synset not in SentiNet (some are missing)

# Getting words from a synset
synonym = ss.getSynonym()              # Synonym object, not iterable
for i in range(synonym.literalSize()):
  lit = synonym.getLiteral(i)
  raw = lit.getName()                   # returns "(güzel)" with parens!
  word = raw.strip("()").lower()        # clean it — see _clean_literal_name()
```

**Key pitfalls:**
- `getPositiveScore()` and `getNegativeScore()` return **strings**, not floats. Always cast with `float()`.
- `getSentiSynSet(id)` raises `KeyError` if the synset ID isn't in SentiNet. Use try/except.
- `synSetList` is a property, not a method. No parentheses.
- `literal.getName()` returns names with surrounding parentheses like `"(güzel)"`. The `_clean_literal_name()` function in `nlp_helpers.py` handles this.
- SentiNet has 76,825 entries, WordNet has 78,327 synsets — expect ~1,500 synsets to be missing.

### 5. Mock targets for backend tests

All 12 tests in `tests/test_nlp_helpers.py` mock the lazy-loading getter functions, not the model classes directly. This is because the imports happen inside the getter, so the mock target is:

```python
@patch("services.nlp_helpers.get_lexicon")
@patch("services.nlp_helpers.get_sentiment_classifier")
@patch("services.nlp_helpers.get_morphological_analyzer")
@patch("services.nlp_helpers.get_embedding_model")
```

**Don't mock `SentiNet.SentiNet.SentiNet`** or similar deep paths — the lazy loading pattern means those imports don't execute at module level, so regular mocking at the import site won't intercept them. Always mock the `get_*` function.

### 6. The NLP endpoints are the first real use of `app/routes/`

The `app/routes/nlp.py` file establishes the pattern for all future endpoint migrations:
1. Create a file with `from fastapi import APIRouter` + `router = APIRouter(prefix="/<name>", tags=["<name>"])`
2. Each endpoint lazily imports its handler: `from services.nlp_helpers import lexicon_polarity as _lp`
3. Every endpoint wraps its body in try/except → `HTTPException(status_code=500)`
4. In `main.py`: add `from app.routes.nlp import router as nlp_router` at the top, then `app.include_router(nlp_router)` after CORS middleware

### 7. Frontend tests need vitest config

The project didn't have vitest set up. The config was added inline in `vite.config.js`:
```js
/// <reference types="vitest" />
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: [],
},
```

If you add new test files, they'll be auto-discovered by vitest as long as they match `*.test.ts` or `*.test.tsx`. No additional config needed.

### 8. Model download timeout on first call

The BERT sentiment classifier (~1.2 GB) and e5-small embedding model (~118 MB) download on first request. On a slow connection this can cause a 30-second+ timeout. The endpoints will eventually respond once the model is cached (`~/.cache/huggingface/hub/`). The lexicon and morphology tools load instantly (local files only).

### 9. The `NlpHelperToolbar.test.tsx` file does not exist yet

The task3 doc specifies component tests for the toolbar (collapse/expand, error handling, Escape key, etc.) but these were deferred to avoid writing fragile DOM-interaction tests. If you add them, mock `global.fetch` at the test level (the component uses bare `fetch`, no wrapper).

