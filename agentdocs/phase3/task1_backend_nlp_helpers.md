# Task 1: Backend — NLP Helpers Module

> **⚠️ CRITICAL RULE: Do NOT add new endpoints or functions to `main.py`.**
> `main.py` is frozen for bug fixes only. All new feature code goes into `app/routes/` (for endpoints) or `services/` (for business logic). This task creates the first production route file under `app/routes/` — the pattern to follow for all future endpoint additions.

## What this is

A new Python module `services/nlp_helpers.py` providing four NLP tools for the NLP Helper Toolbar:

1. **Word-level sentiment** (SentiNet / HisNet lexicon via WordNet flattening)
2. **Sentence-level sentiment** (HuggingFace classifier)
3. **Morphological analysis** (NlpToolkit)
4. **Embedding similarity** (multilingual-e5-small)

All loaded **lazily** (first-use only). All wired as endpoints in `main.py`. No imports happen at server startup.

---

## Tool decisions (confirmed)

| Tool | Library | Notes |
|---|---|---|
| Word-level lexicon | `nlptoolkit-sentinet` (HisNet) via `SentiNet.SentiNet` + `nlptoolkit-wordnet` | Option B: flatten via WordNet synset iteration → `{word: polarity}` dict |
| Sentence-level classifier | `savasy/bert-base-turkish-sentiment-cased` | Transformers pipeline |
| Morphological analysis | `nlptoolkit-morphologicalanalysis` via `FsmMorphologicalAnalyzer` | Per-word analysis (no disambiguation) — local NlpToolkit, not ITU API |
| Embedding similarity | `intfloat/multilingual-e5-small` via `sentence-transformers` | Cosine similarity between selection and full sentence |

---

## Implementation steps

### Step 1 — Create `services/nlp_helpers.py`

New file. No imports at module level — every tool is lazy-loaded.

**File structure:**
```
services/nlp_helpers.py
├── Module-level globals (_sentinet, _sentiment_classifier, etc.)
├── init check flag: _nlp_initialized = False
├── get_sentinet()               # → SentiNet instance
├── get_sentiment_classifier()   # → transformers pipeline
├── get_morphological_analyzer() # → FsmMorphologicalAnalyzer
├── get_embedding_model()        # → SentenceTransformer
├── get_lexicon()                # → {word: (polarity, score)} dict
├── _build_flattened_lexicon()   # one-time WordNet→SentiNet flatten
├── lexicon_polarity(text)       # endpoint handler
├── sentiment_classify(text)     # endpoint handler
├── morphology(word)             # endpoint handler
├── embedding_similarity(selection, sentence)  # endpoint handler
```

#### Lazy-loading pattern (all 4 tools)

```python
import numpy as np

_sentinet = None
_sentiment_classifier = None
_morphological_analyzer = None
_embedding_model = None
_lexicon_dict = None

def get_sentinet():
    global _sentinet
    if _sentinet is None:
        from SentiNet import SentiNet
        _sentinet = SentiNet()
    return _sentinet

def get_sentiment_classifier():
    global _sentiment_classifier
    if _sentiment_classifier is None:
        from transformers import pipeline
        _sentiment_classifier = pipeline(
            "sentiment-analysis",
            model="savasy/bert-base-turkish-sentiment-cased",
            tokenizer="savasy/bert-base-turkish-sentiment-cased"
        )
    return _sentiment_classifier

def get_morphological_analyzer():
    global _morphological_analyzer
    if _morphological_analyzer is None:
        from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
        _morphological_analyzer = FsmMorphologicalAnalyzer()
    return _morphological_analyzer

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('intfloat/multilingual-e5-small')
    return _embedding_model
```

**→ verify: `python -c "from services.nlp_helpers import get_sentinet; sn = get_sentinet(); print(type(sn).__name__)"` prints `SentiNet`**

#### Lexicon flattening (Option B — WordNet-based)

The SentiNet API is synset-ID-based (`getSentiSynSet("TUR10-0000001")`). Install `nlptoolkit-wordnet` and flatten at **build time** (called once on first access, cached):

```python
def get_lexicon():
    global _lexicon_dict
    if _lexicon_dict is None:
        _lexicon_dict = _build_flattened_lexicon()
    return _lexicon_dict

def _build_flattened_lexicon() -> dict:
    """Build {word: (polarity, score)} dict by iterating WordNet synsets.

    For each synset in WordNet, look up its polarity in SentiNet.
    If a word appears in multiple synsets with different polarities,
    average the scores and pick the dominant polarity label.
    """
    from WordNet import WordNet
    sentinet = get_sentinet()
    wn = WordNet()
    lexicon = {}
    for synset in wn.getSynSetList():
        synset_id = synset.getId()
        ss = sentinet.getSentiSynSet(synset_id)
        if ss is None:
            continue
        pos_score = ss.getPositiveScore()
        neg_score = ss.getNegativeScore()
        if pos_score > neg_score:
            polarity = "positive"
            score = pos_score
        elif neg_score > pos_score:
            polarity = "negative"
            score = neg_score
        else:
            polarity = "neutral"
            score = 0.0
        for literal in synset.getSynonym():
            word = literal.getName().lower()
            if word in lexicon:
                existing_pol, existing_score = lexicon[word]
                avg_score = (existing_score + score) / 2
                lexicon[word] = (
                    "positive" if avg_score > 0
                    else "negative" if avg_score < 0
                    else "neutral",
                    avg_score
                )
            else:
                lexicon[word] = (polarity, score)
    return lexicon
```

> **Note:** The exact API (`WordNet.getSynSetList()`, `SynSet.getId()`, `SynSet.getSynonym()`, `Literal.getName()`) depends on the `nlptoolkit-wordnet` version installed. Adjust during implementation — verify with one synset first.

**→ verify: `python -c "from services.nlp_helpers import get_lexicon; l = get_lexicon(); print(f'Lexicon entries: {len(l)}'); print(l.get('güzel'), l.get('kötü'))"` shows entries for known Turkish words**

#### Endpoint handlers

```python
def lexicon_polarity(text: str) -> dict:
    """Per-word sentiment lookup from SentiNet.

    Returns:
        {"words": [{"word": str, "polarity": str, "score": float}],
         "aggregate": str}
    """
    lexicon = get_lexicon()
    tokens = [w.strip(".,!?;:\"'()[]").lower() for w in text.split()]
    results = []
    for token in tokens:
        if not token:
            continue
        entry = lexicon.get(token)
        if entry:
            results.append({
                "word": token,
                "polarity": entry[0],
                "score": round(entry[1], 4)
            })
        else:
            results.append({
                "word": token,
                "polarity": "unknown",
                "score": 0.0
            })
    # Aggregate: majority polarity among known words
    known = [r for r in results if r["polarity"] != "unknown"]
    if known:
        from collections import Counter
        agg = Counter(r["polarity"] for r in known).most_common(1)[0][0]
    else:
        agg = "neutral"
    return {"words": results, "aggregate": agg}


def sentiment_classify(text: str) -> dict:
    """Sentence-level sentiment classification (HuggingFace).

    Returns:
        {"label": "positive"|"negative"|"neutral", "score": float}
    """
    classifier = get_sentiment_classifier()
    result = classifier(text, truncation=True, max_length=512)[0]
    return {
        "label": result["label"].lower(),
        "score": round(result["score"], 4)
    }


def morphology(word: str) -> dict:
    """Morphological analysis of a single word (NlpToolkit).

    Returns:
        {"word": str, "parses": [{"root": str, "ig": [str], "pos": str}]}
    """
    analyzer = get_morphological_analyzer()
    result = analyzer.morphologicalAnalysis(word)
    parses = []
    for i in range(result.size()):
        parse = result.getFsmParse(i)
        root = parse.getWord()
        # Extract inflectional groups
        ig_count = parse.size()
        igs = []
        for j in range(ig_count):
            ig = parse.getInflectionalGroup(j)
            igs.append(str(ig))
        # Determine POS from first inflectional group
        first_ig = parse.getInflectionalGroup(0) if ig_count > 0 else None
        pos = str(first_ig).split("+")[0] if first_ig else "?"
        parses.append({
            "root": str(root).split()[0] if " " in str(root) else str(root),
            "ig": igs,
            "pos": pos
        })
    return {"word": word, "parses": parses}


def embedding_similarity(selection: str, sentence: str) -> dict:
    """Cosine similarity between selected span and full sentence.

    Returns:
        {"similarity": float (0.0-1.0), "selection_length": int}
    """
    model = get_embedding_model()
    emb_sel = model.encode("query: " + selection)
    emb_sent = model.encode("passage: " + sentence)
    sim = float(np.dot(emb_sel, emb_sent) /
                (np.linalg.norm(emb_sel) * np.linalg.norm(emb_sent)))
    return {
        "similarity": round(sim, 4),
        "selection_length": len(selection)
    }
```

**→ verify: `python -c "from services.nlp_helpers import lexicon_polarity; print(lexicon_polarity('güzel'))"` returns a dict with words and aggregate**

### Step 2 — Create `app/routes/nlp.py` (APIRouter, not inline in main.py)

The `app/routes/` directory already exists with an APIRouter pattern. Create the **first real route file** there:

```python
"""NLP Helper Toolbar endpoints.

Migrated from inline @app.get() in main.py to a proper APIRouter.

Endpoints:
    GET /nlp/lexicon-polarity      — per-word sentiment lookup
    GET /nlp/sentiment             — sentence-level sentiment classification
    GET /nlp/morphology            — morphological analysis (NlpToolkit)
    GET /nlp/embedding-similarity  — cosine similarity via e5-small
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.get("/lexicon-polarity")
def get_lexicon_polarity(text: str):
    try:
        from services.nlp_helpers import lexicon_polarity as _lp
        return _lp(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lexicon error: {str(e)}")


@router.get("/sentiment")
def get_sentiment(text: str):
    try:
        from services.nlp_helpers import sentiment_classify as _sc
        return _sc(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment error: {str(e)}")


@router.get("/morphology")
def get_morphology(word: str):
    try:
        from services.nlp_helpers import morphology as _mo
        return _mo(word)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Morphology error: {str(e)}")


@router.get("/embedding-similarity")
def get_embedding_similarity(selection: str, sentence: str):
    try:
        from services.nlp_helpers import embedding_similarity as _es
        return _es(selection, sentence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
```

**Why this matters:** All existing endpoint files under `app/routes/` are currently empty scaffolding (docstrings only). This is the **first production route file** — it establishes the pattern for migrating the rest of `main.py`'s endpoints later.

**→ verify: `python -m py_compile app/routes/nlp.py`** exits with code 0

### Step 3 — Include the router in `main.py`

> ⚠️ This is the **only** change to `main.py` allowed for this feature. Do not add any other endpoints, imports, or logic to `main.py` — it is frozen for bug fixes only.

Add three lines near the top of `main.py` (after the existing imports, before `app = FastAPI()`):

```python
from app.routes.nlp import router as nlp_router
# ... then after app = FastAPI() and CORS middleware:
app.include_router(nlp_router)
```

This is the standard FastAPI pattern for splitting routes across files. The prefix `/nlp` is baked into the router definition, so the endpoints will be available at `/nlp/lexicon-polarity`, `/nlp/sentiment`, `/nlp/morphology`, `/nlp/embedding-similarity`.

**→ verify: Start backend, `curl http://localhost:8000/nlp/morphology?word=güzel` → HTTP 200 with JSON parses**

### Step 4 — Update `app/routes/__init__.py`

Add the new module to the docstring:

```python
"""Route handlers for the FastAPI application.

Submodules:
    nlp         — NLP Helper Toolbar (lexicon, sentiment, morphology, embedding)
    settings    — GET /settings, PATCH /settings          (future)
    reviews     — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat (future)
    ai          — GET /ai_prediction/{idx}                (future)
    upload      — POST /upload-data                       (future)
"""
```

**→ verify: `python -m py_compile app/routes/__init__.py`** exits with code 0

### Step 5 — Update `pyproject.toml` and `requirements.txt`

Add to both files:
```
nlptoolkit-sentinet
nlptoolkit-morphologicalanalysis
nlptoolkit-wordnet
nlptoolkit-dictionary
sentence-transformers
transformers
torch
setuptools<75       # pinned: newer setuptools removed pkg_resources that NlpToolkit needs
```

**→ verify: `uv pip install` in project root succeeds, no conflicts**

### Step 6 — Create `tests/test_nlp_helpers.py`

New test file with pure-logic tests (no model loading — mock the lazy-loading functions or test the endpoint handlers with known test data).

> **Important:** These tests should mock the model/analyzer calls so they run without downloading any model files. They test the handler logic, not the model behavior.

```python
"""Tests for services/nlp_helpers.py — handler logic without model loading.

Each test mocks the lazy-loaded model/analyzer so tests run
instantly without any model files downloaded.
"""
import pytest
from unittest.mock import patch, MagicMock

# ── lexicon_polarity ──────────────────────────────────────────────────

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_single_word(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {"güzel": ("positive", 1.0)}
    result = lexicon_polarity("güzel")
    assert result["aggregate"] == "positive"
    assert result["words"][0]["word"] == "güzel"
    assert result["words"][0]["polarity"] == "positive"

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_multi_word(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {
        "güzel": ("positive", 1.0),
        "kötü": ("negative", 1.0),
    }
    result = lexicon_polarity("güzel kötü")
    assert len(result["words"]) == 2
    assert result["aggregate"] in ("positive", "negative")  # tie → first wins

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_unknown(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {}
    result = lexicon_polarity("xyzzy")
    assert result["words"][0]["polarity"] == "unknown"
    assert result["aggregate"] == "neutral"

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_punctuation(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {"güzel": ("positive", 1.0)}
    result = lexicon_polarity("güzel!")
    assert result["words"][0]["word"] == "güzel"
    assert result["words"][0]["polarity"] == "positive"

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_empty(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    result = lexicon_polarity("")
    assert result["words"] == []
    assert result["aggregate"] == "neutral"


# ── sentiment_classify ────────────────────────────────────────────────

@patch("services.nlp_helpers.get_sentiment_classifier")
def test_sentiment_classify_positive(mock_get_classifier):
    from services.nlp_helpers import sentiment_classify
    mock_clf = MagicMock()
    mock_clf.return_value = [{"label": "POSITIVE", "score": 0.98}]
    mock_get_classifier.return_value = mock_clf
    result = sentiment_classify("Harika bir yemek")
    assert result["label"] == "positive"
    assert result["score"] == 0.98

@patch("services.nlp_helpers.get_sentiment_classifier")
def test_sentiment_classify_negative(mock_get_classifier):
    from services.nlp_helpers import sentiment_classify
    mock_clf = MagicMock()
    mock_clf.return_value = [{"label": "NEGATIVE", "score": 0.95}]
    mock_get_classifier.return_value = mock_clf
    result = sentiment_classify("Berbat servis")
    assert result["label"] == "negative"


# ── morphology ────────────────────────────────────────────────────────

def _make_mock_parse(root="güzel", igs=None, pos="ADJ"):
    """Helper: create a mock FsmParse."""
    mock = MagicMock()
    mock.getWord.return_value = root
    igs = igs or ["ADJ"]
    mock.size.return_value = len(igs)
    mock.getInflectionalGroup.side_effect = lambda i: MagicMock(
        __str__=lambda self: igs[i]
    )
    return mock

@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_single_parse(mock_get_analyzer):
    from services.nlp_helpers import morphology
    mock_analyzer = MagicMock()
    mock_parse = _make_mock_parse(root="güzel", igs=["ADJ"], pos="ADJ")
    mock_parse_list = MagicMock()
    mock_parse_list.size.return_value = 1
    mock_parse_list.getFsmParse.return_value = mock_parse
    mock_analyzer.morphologicalAnalysis.return_value = mock_parse_list
    mock_get_analyzer.return_value = mock_analyzer

    result = morphology("güzel")
    assert result["word"] == "güzel"
    assert len(result["parses"]) == 1
    assert result["parses"][0]["root"] == "güzel"

@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_empty_word(mock_get_analyzer):
    from services.nlp_helpers import morphology
    mock_analyzer = MagicMock()
    mock_parse_list = MagicMock()
    mock_parse_list.size.return_value = 0
    mock_analyzer.morphologicalAnalysis.return_value = mock_parse_list
    mock_get_analyzer.return_value = mock_analyzer

    result = morphology("")
    assert result["word"] == ""
    assert result["parses"] == []


# ── embedding_similarity ──────────────────────────────────────────────

@patch("services.nlp_helpers.get_embedding_model")
def test_embedding_similarity_identical(mock_get_model):
    from services.nlp_helpers import embedding_similarity
    mock_model = MagicMock()
    # Identical vectors → cos_sim = 1.0
    mock_model.encode.side_effect = [
        np.array([1.0, 0.0]),
        np.array([1.0, 0.0]),
    ]
    mock_get_model.return_value = mock_model
    result = embedding_similarity("lezzetli", "lezzetli yemek")
    assert result["similarity"] == 1.0
    assert result["selection_length"] == 8

@patch("services.nlp_helpers.get_embedding_model")
def test_embedding_similarity_orthogonal(mock_get_model):
    from services.nlp_helpers import embedding_similarity
    mock_model = MagicMock()
    mock_model.encode.side_effect = [
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
    ]
    mock_get_model.return_value = mock_model
    result = embedding_similarity("a", "b")
    assert result["similarity"] == 0.0


# ── Error handling ────────────────────────────────────────────────────

@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_analyzer_error(mock_get_analyzer):
    """Analyzer raises → morphology() should propagate."""
    from services.nlp_helpers import morphology
    mock_get_analyzer.side_effect = RuntimeError("Model not found")
    with pytest.raises(RuntimeError):
        morphology("test")
```

**→ verify: `pytest tests/test_nlp_helpers.py -v` passes all tests**

---

## Step-by-step verification (run in order)

| Step | Action | Expected result |
|---|---|---|
| 1 | `uv pip install nlptoolkit-sentinet nlptoolkit-morphologicalanalysis nlptoolkit-wordnet nlptoolkit-dictionary sentence-transformers transformers torch 'setuptools<75'` | All install without errors |
| 2 | `python -c "from SentiNet import SentiNet; sn = SentiNet(); print(f'SentiNet: {len(sn.getPositives())} positives')"` | Shows count > 0 (no import error) |
| 3 | `python -c "from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer; ma = FsmMorphologicalAnalyzer(); r = ma.morphologicalAnalysis('güzel'); print(f'Parses: {r.size()}')"` | Prints "Parses: 1" or more |
| 4 | Create `services/nlp_helpers.py` with all lazy-loading functions | File parses without error |
| 5 | `python -m py_compile services/nlp_helpers.py` | Exit code 0, no syntax errors |
| 6 | Create `app/routes/nlp.py` with APIRouter | File parses without error |
| 7 | `python -m py_compile app/routes/nlp.py` | Exit code 0 |
| 8 | Add `from app.routes.nlp import router as nlp_router` + `app.include_router(nlp_router)` in `main.py` | No import errors |
| 9 | `python -m py_compile main.py` | Exit code 0 |
| 10 | Update `app/routes/__init__.py` docstring; `python -m py_compile app/routes/__init__.py` | Exit code 0 |
| 11 | Start backend: `uvicorn main:app --port=8000` | Server starts; logs show **no** SentiNet/BERT/NlpToolkit/e5-small messages |
| 12 | `curl "http://localhost:8000/nlp/morphology?word=güzel"` | HTTP 200, JSON with `parses` array containing at least 1 parse |
| 13 | `curl "http://localhost:8000/nlp/lexicon-polarity?text=güzel"` | HTTP 200, JSON like `{"words":[{"word":"güzel","polarity":"positive","score":1.0}],"aggregate":"positive"}` |
| 14 | `curl "http://localhost:8000/nlp/sentiment?text=Yemekler+çok+lezzetliydi"` | HTTP 200, JSON with `label: "positive"` and `score > 0.5` |
| 15 | `curl "http://localhost:8000/nlp/embedding-similarity?selection=lezzetliydi&sentence=Yemekler+çok+lezzetliydi"` | HTTP 200, JSON with `similarity` between 0.0 and 1.0 |
| 16 | Check server logs from steps 12–15 | First request to each endpoint shows a model-loading message; subsequent requests are fast (cached) |
| 17 | `pytest tests/test_nlp_helpers.py -v` | All tests pass (mock-based, no model downloads) |
| 18 | Restart backend; `curl http://localhost:8000/settings` — confirm existing endpoints still work | HTTP 200 with settings data |

---

## Test cases to add to `tests/testcases.md`

Add a new tier to the testcases document:

### Tier 7 — NLP Helper Toolbar Backend

| ID | Test | Expected | Verdict |
|---|---|---|---|
| NLB1 | `GET /nlp/lexicon-polarity?text=güzel` returns known word | Polarity for "güzel" is "positive" | — |
| NLB2 | `GET /nlp/lexicon-polarity?text=xyzzy` returns unknown word | polarity="unknown", aggregate="neutral" | — |
| NLB3 | `GET /nlp/sentiment?text=Harika` with positive text | label="positive", score > 0.7 | — |
| NLB4 | `GET /nlp/sentiment?text=Berbat` with negative text | label="negative", score > 0.7 | — |
| NLB5 | `GET /nlp/morphology?word=güzel` | Returns at least 1 parse with root + POS | — |
| NLB6 | `GET /nlp/embedding-similarity` with identical selection+sentence | similarity=1.0 | — |
| NLB7 | Lazy loading: no model import at startup | Server logs contain none of: "SentiNet", "pipeline", "FsmMorphological", "SentenceTransformer" | — |
| NLB8 | All 4 endpoints return HTTP 500 on internal error | Each wraps exceptions properly | — |
| NLB9 | Router registration in `main.py` | `from app.routes.nlp import router as nlp_router` + `app.include_router(nlp_router)` | — |

---

## Docs to update after implementation

| Doc | What to change |
|---|---|
| `agentdocs/session_reports/backend_reference.md` | Change "all 13 HTTP endpoints" on line 11 to reflect 4 new endpoints in `app/routes/nlp.py`; add new file entry for `app/routes/nlp.py` in the file table |
| `docs/architecture_map.md` | Update the endpoint list under `main.py` to note that NLP endpoints live in `app/routes/nlp.py`; update the module graph if it shows endpoint locations |
| `agentdocs/phase3/nlp_helper_toolbar.md` (kickoff doc) | Mark as completed once all 4 endpoints are live |
| `tests/testcases.md` | Add Tier 7 table (above) to the document |
