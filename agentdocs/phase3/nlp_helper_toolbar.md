# NLP Helper Toolbar — Kickoff

> **⚠️ SUPERSEDED**
> This document was the initial planning brief. It has been superseded by three concrete task documents:
> - [`task1_backend_nlp_helpers.md`](task1_backend_nlp_helpers.md) — backend module + `app/routes/nlp.py` endpoints
> - [`task2_selection_hook.md`](task2_selection_hook.md) — shared `useTextSelection` hook
> - [`task3_toolbar_component.md`](task3_toolbar_component.md) — `NlpHelperToolbar.tsx` component
>
> All tooling and architecture decisions have changed from this brief. Refer to the task docs above.
>
> **Key changes:**
> | Aspect | This doc recommended | Final decision |
> |---|---|---|
> | Morphology | Stanza | [`TurkishMorphologicalAnalysis-Py`](https://github.com/StarlangSoftware/TurkishMorphologicalAnalysis-Py) |
> | Embeddings | LaBSE (1.8GB) | `multilingual-e5-small` (118MB) |
> | Sentiment | Lexicon only | Lexicon + BERT classifier (`savasy/bert-base-turkish-sentiment-cased`) |
> | Endpoint location | Inline in `main.py` | `app/routes/nlp.py` (APIRouter) |
> | Number of segments | 3 | 4 (added sentence-level sentiment) |
> | Bag icon | `bag.png` asset | Inline SVG |
> | Python version | Concerned about 3.13+ | Confirmed working on 3.11 |

New feature, not part of Phase 1. Read fully before planning — several parts involve real
infra tradeoffs (model downloads, latency, a Python version constraint), not just UI work.

## What this is (from the sketch + confirmed answers)

A collapsible toolbar attached to text-span selection, available in **both** Manuel and
Karşılaştır modes. Collapsed state: a small icon (`bag.png`). Clicking it expands a bar
offering three tools that operate on the currently-selected span of review text:

1. **Lexicon-based sentiment lookup** — shows the polarity of the selected word/string.
2. **Contextual embedding comparer** — compares the embedding of the selected span against
   the embedding of the whole sentence.
3. **Morphological analyzer** — Turkish morphological breakdown of the selected word.

Confirmed libraries: **Stanza** (morphological analyzer) and **LaBSE** (embedding comparer).
Lexicon source needed research — see below.

## Assumption I'm making, flag if wrong

The sketch shows the bag icon and the 3-segment bar as one connected unit, and your answer
("opens the lexicon-based sentiment polarity analyzer and other features bar when clicked")
confirms one click reveals everything, not three separate triggers. I'm assuming: clicking
`bag.png` expands the bar; lexicon polarity (cheap, local dict lookup) computes automatically
on expand; the embedding comparer and morphological analyzer (both call external
models/pipelines, slower) compute **on-demand** when their segment is clicked, not
automatically on every selection. This avoids running two heavy model calls on every single
text selection, which would make the UI feel sluggish. **Confirm this before the agent builds
it** — if you actually want all three to auto-compute on selection, say so, but know that means
a LaBSE + Stanza call on every click.

---

## Lexicon source (researched, not in your original answer)

Two well-known Turkish polarity lexicons exist. Recommending one over the other, not both:

- **SentiTurkNet** (Dehkharghani et al.) — the original, most-cited academic resource, but
  it's distributed via academic paper/DOI channels, not a clean pip/GitHub package. Would need
  manual sourcing.
- **HisNet** (`StarlangSoftware/TurkishSentiNet-Py`, pip package `NlpToolkit-SentiNet`) —
  newer, larger (76,825 WordNet synsets from Kenet, labeled positive/negative/neutral with
  strong/weak gradation), actively maintained on GitHub, **directly pip-installable**.

**Recommendation: HisNet.** Directly installable beats "email an author for a dataset" for a
tool other researchers need to set up. Two things to verify before committing:

1. **License is GPL-3.0.** Fine for an internal research tool; worth knowing if this project
   is ever distributed more broadly, since GPL is copyleft.
2. **It's synset-based, not word-based.** The API is `SentiNet().getSentiSynSet(synset_id)` —
   you look up a WordNet synset, not a raw word string. To support "select a word, get its
   polarity" you need a word→synset mapping (their Turkish WordNet/Kenet data), which adds a
   second dependency, or a word-sense-disambiguation step, which is real complexity for a
   selection-triggered UI tool. **Simpler alternative**: at build/startup time, flatten the
   lexicon into a plain `{word: polarity_score}` dict by iterating all synsets, taking each
   synset's literal(s), and assigning that literal the synset's polarity (if a word appears in
   multiple synsets with different polarities, average them or take the majority — pick one,
   document the choice). This sacrifices word-sense precision for a simple, fast runtime
   lookup, which matches what the sketch actually asks for ("shows the polarity of the
   word/selected string" — not "disambiguates which sense"). Recommend this simplification;
   flag to me if you'd rather do real WSD (meaningfully more work, no upside for this feature).

**Compatibility check needed before adopting HisNet**: the pip package
(`pip3.13 install NlpToolkit-SentiNet`) requires **Python 3.13+**. Confirm the project's actual
Python version/environment supports this before committing — if the repo targets an older
Python (common for research tooling), this could be a blocker and you'd need SentiTurkNet
(manually sourced) instead.

```bash
python -V   # confirm >= 3.13 before proceeding with HisNet
```

---

## Backend

### New module, not `main.py`

`main.py` is already ~1600 lines and there's a pending, not-yet-scoped decision about
splitting it up. Don't add to that pile — put this feature's backend logic in a new file, e.g.
`nlp_helpers.py`, imported into `main.py` for the endpoint wiring only. This is a small,
self-contained step toward the eventual reorg, not the reorg itself — don't use this task as an
excuse to split anything else.

### Lazy-load every model, matching existing convention

`main.py` already lazy-imports `ollama`/`openai` inside the functions that use them, not at
module level — this avoids paying import/load cost for providers nobody's using. Do the same
here: don't load Stanza's pipeline, LaBSE, or the flattened lexicon dict at server startup.
Load each on first use, cache in a module-level variable after.

```python
_stanza_pipeline = None
def get_stanza_pipeline():
    global _stanza_pipeline
    if _stanza_pipeline is None:
        import stanza
        # stanza.download('tr') must have been run once already — document this as a
        # one-time setup step, don't auto-download on every server start
        _stanza_pipeline = stanza.Pipeline('tr', processors='tokenize,mwt,pos,lemma,feats')
    return _stanza_pipeline

_labse_model = None
def get_labse_model():
    global _labse_model
    if _labse_model is None:
        from sentence_transformers import SentenceTransformer
        _labse_model = SentenceTransformer('sentence-transformers/LaBSE')
    return _labse_model

_lexicon_dict = None
def get_lexicon():
    global _lexicon_dict
    if _lexicon_dict is None:
        _lexicon_dict = _build_flattened_lexicon()  # one-time flatten, see above
    return _lexicon_dict
```

### Three endpoints

```python
@app.get("/nlp/lexicon-polarity")
def lexicon_polarity(text: str):
    # split text into words, look up each in get_lexicon(), return per-word + aggregate
    ...

@app.get("/nlp/morphology")
def morphology(text: str):
    # run get_stanza_pipeline() on text, return lemma + morphological features per token
    ...

@app.get("/nlp/embedding-similarity")
def embedding_similarity(selection: str, sentence: str):
    # get_labse_model().encode([selection, sentence]), cosine similarity
    ...
```

Exact response shape is your call — keep it minimal (just what the frontend needs to render),
don't add fields "for completeness."

### Known cost — flag to the user in your plan, don't just build it

- Stanza's Turkish model + LaBSE together are a meaningful download (LaBSE alone is ~1.8GB).
  First request after server start will be slow while models load. This is expected, not a
  bug — just make sure loading failure (no internet, model not downloaded) fails with a clear
  error, not a silent hang or crash.

---

## Frontend

### Selection needs to work in both modes — but Karşılaştır mode has no selection today

`PhraseAnnotator.tsx` (Manuel mode) already has click/drag span-selection logic. The
Karşılaştır mode's review-text display is currently **read-only** — no selection handling
exists there at all. You have two options:

- **(A)** Extract just the *selection-detection* logic (not the annotation-creation popup,
  not the highlighting-for-saved-triplets logic) from `PhraseAnnotator.tsx` into a shared
  hook, e.g. `useTextSelection(reviewText, config)`, used by both `PhraseAnnotator` and a new
  lightweight wrapper around Karşılaştır mode's text display.
- **(B)** Duplicate a smaller, read-only selection listener directly in the Karşılaştır text
  display, since it needs much less (no popup, no save, no highlighting-persisted-annotations).

**Recommend (A)** — avoids two copies of selection-detection logic drifting apart, and it's a
small extraction (just the mouse-up/selection-range logic), not a big refactor. But this is a
judgment call between "slightly more upfront work, no duplication" and "faster now, two copies
to maintain" — state which you're doing and why in your plan, don't pick silently.

### Toolbar component

New component, e.g. `NlpHelperToolbar.tsx`: renders the collapsed `bag.png` icon at the
selection point (or wherever the sketch implies — the sketch doesn't show exact positioning
relative to the selected text, use your judgment, anchor it near the selection). On click,
expands to the 3-segment bar. Per the auto-vs-on-demand assumption above: lexicon result
fetches immediately on expand; embedding comparer and morphological analyzer each fetch only
when their segment is clicked.

Mount this in both `PhraseAnnotator.tsx` and the Karşılaştır mode's text display, wired to
whichever selection mechanism you chose above.

---

## Definition of done

- Selecting a span of text in **either** mode shows the `bag.png` icon.
- Clicking it expands the 3-segment bar; lexicon polarity appears without further clicks.
- Clicking the embedding-comparer segment shows a similarity score between the selection and
  the full sentence.
- Clicking the morphological-analyzer segment shows Stanza's breakdown of the selected word.
- None of the three models/lexicon load until first actually used (verify via server logs —
  nothing Stanza/LaBSE/lexicon-related should happen at server startup).
- Selecting text in Karşılaştır mode does not interfere with the existing checkbox-based
  triplet selection in that mode — these are two different interactions on the same screen,
  confirm they don't conflict (e.g. selecting text inside a triplet's displayed term shouldn't
  toggle its checkbox).

## What I need from you

1. Confirm the Python version compatibility check above before committing to HisNet.
2. A plan in `[Step] → verify: [check]` format, covering backend module setup, each endpoint,
   the selection-sharing decision (A or B), and the toolbar component.
3. State explicitly which auto-vs-on-demand computation policy you're building (per the
   assumption section) — confirm or push back before implementing.
4. Wait for go-ahead, then full file contents/diffs.