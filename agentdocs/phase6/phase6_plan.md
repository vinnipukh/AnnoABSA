# Phase 6 — Polish, Tests, Autopilot & ML Features

**Status:** 🟢 Completed
**Goal:** Remaining polish items, frontend test coverage, autopilot mode, RAG extension, and active learning ML suggestions

---

## Task 1: Emoji → SVG in pre-Phase 3 components

**Objective:** Replace emoji icons with SVGs in `HelperAgentChatbox.tsx` and `NlpHelperToolbar.tsx` per the ui-ux-review skill's rule against emoji as structural icons.

**Affected files:**
- `frontend/src/components/HelperAgentChatbox.tsx` — 3 instances of `🤖`
- `frontend/src/components/NlpHelperToolbar.tsx` — `📖🤖🔧📊` segment buttons, `😊😞😐` sentiment labels

**Verification:** `npx vitest run` (27 passed) + `npx tsc --noEmit`

---

## Task 2: Fix TSConfig — eliminate pre-existing `env` error

**Objective:** Add `"vite/client"` to the `types` array in `tsconfig.json` to fix the `Property 'env' does not exist on type 'ImportMeta'` error (landmine #16).

**Affected files:**
- `frontend/tsconfig.json`

**Verification:** `npx tsc --noEmit` should show 1 error (down from 2).

---

## Task 3: Frontend component tests for uncovered components

**Objective:** Add vitest tests for `SettingsPanel.tsx`, `ModelTripletColumn.tsx`, and `HelperAgentChatbox.tsx` — the three components with zero test coverage.

**New files:**
- `frontend/src/components/SettingsPanel.test.tsx`
- `frontend/src/components/ModelTripletColumn.test.tsx`
- `frontend/src/components/HelperAgentChatbox.test.tsx`

**Verification:** `npx vitest run` shows increased test count.

---

## Task 4: CLI flags for Phase 4 Live Compare config

**Objective:** Add `--model-a-provider`, `--model-a-model`, `--model-a-temperature`, `--model-a-prompt`, `--model-b-*`, `--helper-agent-*` CLI flags to `cli.py` so Live Compare mode can be configured from the command line without opening the Settings panel.

**Affected files:**
- `cli.py`

**Verification:** `pytest tests/` (128 passed)

---

## Task 5: Autopilot mode — response parser

**Objective:** Build the structured-response parser in `HelperAgentChatbox` that extracts action directives from the agent's reply and calls `appActionsRef.current` methods. The design decision was made in Phase 4 (hybrid text + inline actions) but no serializer format or parser exists.

**Affected files:**
- `frontend/src/components/HelperAgentChatbox.tsx`
- `app/routes/reviews.py` (agent_chat may need to return structured data)

**Verification:** Manual — agent reply triggers navigation, mode switch, etc.

---

## Task 6: RAG verification and extension to Model A/B and Helper Agent

**Objective:** Verify that the existing BM25-based RAG (`get_most_similar_examples()` in `services/prediction.py`) still works after the Phase 5 main.py breakup, and extend it to also serve examples for Model A/B (live prediction) and the Helper Agent chat.

### Current state

The BM25 RAG implementation uses `rank_bm25` to retrieve the most similar labeled examples from the dataset, which are then included as few-shot examples in the LLM prompt.

**Where RAG runs today:**

| Endpoint | Gets few-shot examples via BM25? | How |
|---|---|---|
| `GET /ai_prediction` | ✅ Yes | `provider.predict()` → `build_prediction_prompt()` → `get_most_similar_examples()` |
| `GET /live_prediction` | ✅ Yes | Same path — `provider.predict()` → `build_prediction_prompt()` |
| `POST /agent/chat` | ❌ No | Uses `DEFAULT_CHAT_TEMPLATE.format()` directly — no BM25 retrieval |

### How RAG works (confirmed working):

1. `build_prediction_prompt(text, examples, n_few_shot, ...)` calls `get_most_similar_examples(text, examples, n_few_shot)`
2. `get_most_similar_examples()` tokenizes all example texts and the query text with `re.findall(r'\b\w+\b', text.lower())`
3. A `BM25Okapi` model is built from the tokenized examples
4. The top-n most similar examples by BM25 score are returned
5. They're included in the prompt as few-shot demonstrations

### Extension for Model A/B and Helper Agent

**Model A/B (live_prediction):** ✅ Already uses RAG. The `get_live_prediction()` endpoint collects `examples` from the dataset and passes them to `provider.predict()` → `build_prediction_prompt()`. No changes needed.

**Helper Agent (agent_chat):** ❌ Does not use RAG. The chat template is formatted directly with `review_text`, `model_a_triplets`, etc. To add RAG:
1. Retrieve similar examples from the dataset using `get_most_similar_examples()`
2. Include them in the chat template by adding a `{few_shot_examples}` placeholder
3. Update `agent_chat()` in `app/routes/reviews.py` to call BM25 retrieval and format the template with the examples

### Verification

```bash
# Unit test for BM25 retrieval
pytest tests/test_prediction.py -k "get_most_similar" -v

# Full suite (no regressions)
pytest tests/ -q

# Manual: verify agent chat includes few-shot examples
# Set up a dataset with labels, open Helper Agent, ask a question,
# verify the response shows awareness of labeled examples
```

---

## Task 7: Active Learning Based ML Triplet Suggestions

**Objective:** Build an active learning system that suggests triplets by training lightweight ML models on the current annotations and identifying uncertain/informative examples for the annotator to label next.

### Background

Active learning is a human-in-the-loop ML paradigm where the model selects which examples the human should annotate next, prioritizing the ones it's most uncertain about. This minimizes annotation effort while maximizing model performance.

In the context of ABSA, this means:
1. Train a lightweight classifier on the current `label` annotations
2. For each unlabeled review, compute the model's prediction uncertainty
3. Suggest the most uncertain examples for the annotator to review
4. As more labels are added, retrain and re-rank → the suggestions improve over time

### Approach

**Phase 1: Simple uncertainty-based (TF-IDF + Logistic Regression)**

Use scikit-learn (lightweight, no GPU needed):
- Extract TF-IDF features from review texts
- Train a multi-label Logistic Regression for aspect categories + sentiment polarities
- Compute prediction entropy for each unlabeled review
- Return the top-N most uncertain reviews as "suggestions"

**Phase 2: Embedding-based (SentenceTransformer)**

Use the existing `intfloat/multilingual-e5-small` model (already installed for the NLP Helper Toolbar):
- Encode all review texts as embeddings
- Train a lightweight classifier on top of embeddings
- Active learning via uncertainty sampling or diversity sampling (coreset)
- More accurate than TF-IDF but slightly slower

### Implementation

**New file: `services/active_learning.py`**

```python
"""Active learning — triplet suggestions based on uncertainty sampling.

Trains a lightweight classifier on current annotations and identifies
the most informative examples for the annotator to label next.
"""
import numpy as np
from typing import Any

def train_uncertainty_model(labeled_reviews: list[dict]) -> Any:
    """Train a classifier on currently labeled reviews.
    
    Args:
        labeled_reviews: list of {'text': str, 'label': [...]} with label as
            list of triplet dicts (aspect_term, aspect_category, sentiment_polarity)
    
    Returns:
        A trained model/pipeline object.
    """
    # Phase 1: TF-IDF + LogisticRegression
    # Phase 2: SentenceTransformer + classifier
    pass

def rank_by_uncertainty(model: Any, unlabeled_reviews: list[str], n: int = 5) -> list[int]:
    """Rank unlabeled reviews by prediction uncertainty.
    
    Args:
        model: Trained model from train_uncertainty_model()
        unlabeled_reviews: list of review texts not yet annotated
        n: Number of suggestions to return
    
    Returns:
        Indices of the n most uncertain reviews, sorted by uncertainty descending.
    """
    pass

def suggest_triplets(text: str, model: Any) -> list[dict]:
    """Predict triplets for a single review using the trained model.
    
    Args:
        text: Review text to predict for
        model: Trained model
    
    Returns:
        List of triplet dicts with confidence scores.
    """
    pass
```

**New endpoint: `app/routes/learning.py`**

```python
"""Active learning endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["learning"])

@router.get("/learning/suggestions")
def get_learning_suggestions(n: int = 5):
    """Return the n most uncertain reviews for annotation."""
    # 1. Load data and separate labeled vs unlabeled
    # 2. Train model on labeled reviews
    # 3. Rank unlabeled by uncertainty
    # 4. Return top-n
    pass

@router.get("/learning/predict/{data_idx}")
def predict_from_ml_model(data_idx: int):
    """Predict triplets using the ML model (not LLM)."""
    # Much faster than LLM prediction — useful for quick suggestions
    pass
```

**Frontend: `frontend/src/components/ActiveLearningSuggestions.tsx`**

A new panel (similar to AISuggestions) that shows:
- "Önerilen Sıradaki İnceleme" with uncertainty scores
- ML-based triplet predictions for the current review
- "Güven Skoru" (confidence score) for each predicted triplet

### Dependencies to add

```
scikit-learn>=1.3
```

(If using embedding-based approach, `sentence-transformers` is already installed.)

### Verification

```bash
# Unit tests
pytest tests/test_active_learning.py -v

# Full suite (no regressions)
pytest tests/ -q

# Manual: open app, annotate a few reviews, open Suggestions panel,
# verify uncertain reviews appear at the top
```

---

## Summary table

| # | Task | Difficulty | New files | Dependencies |
|---|---|---|---|---|
| 1 | Emoji → SVG | Easy | 0 | None |
| 2 | Fix TSConfig | Easy | 0 | None |
| 3 | Component tests | Medium | 3 test files | None |
| 4 | CLI flags | Easy | 0 | None |
| 5 | Autopilot parser | Hard | 0 | None |
| 6 | RAG extension | Easy | 0 | None |
| 7 | Active learning | Hard | `services/active_learning.py`, `app/routes/learning.py`, frontend component | `scikit-learn` |
| 8 | Fix route imports (`import main` → `app.config`/`app.data`) | Easy | `app/routes/ai.py`, `app/routes/reviews.py` | None |
| 9 | Break up `cli.py` (~962 lines) | Medium | New modules from `cli.py` | None |
| 10 | Clean up `pyproject.toml` — check for stale `[project.scripts]` | Easy | `pyproject.toml` | None |

---

## Risks and open questions

1. **Scikit-learn version compatibility.** Must work on Python 3.11. scikit-learn 1.3+ supports 3.11. If torch is already installed (from sentence-transformers), scikit-learn's numpy dependency is already satisfied.

2. **Active learning cold start.** With zero labeled examples, there's nothing to train on. Solution: use LLM predictions (existing `get_ai_prediction`) as pseudo-labels for the first active learning iteration, or fall back to random sampling until N annotations are collected.

3. **Multi-label formulation.** Each review can have multiple triplets (multiple aspect categories with different polarities). This is a multi-label classification problem. Simple approach: one binary classifier per (aspect_category, polarity) pair. More sophisticated: classifier chain or label powerset.

4. **RAG vs agent_chat template.** The `DEFAULT_CHAT_TEMPLATE` currently includes `{review_text}`, `{model_a_name}`, `{model_a_triplets}`, etc. Adding `{few_shot_examples}` requires updating the template string and all imports of it (in `app/config.py` via `services/prediction`).

5. **Helper Agent RAG context window.** Few-shot examples from BM25 can be long. The chat context might exceed the model's limit. Solution: limit to 2-3 examples and truncate if needed.

---

## Additional backend-only tasks

### Task 8: Fix route file imports

**Objective:** Route files `app/routes/ai.py` and `app/routes/reviews.py` currently use `import main` then `main.CONFIG_DATA`, `main.load_data()`, etc. This works because `main.py` re-exports from `app/` modules, but it creates a fragile dependency. Fix by importing directly from `app.config` and `app.data`.

**Changes in `app/routes/ai.py`:**
```python
# Before:
import main
from services import llm_providers
# uses: main.load_data(), main.CONFIG_DATA, main.DATA_FILE_TYPE

# After:
from app.config import CONFIG_DATA, DATA_FILE_TYPE, load_config
from app.data import load_data
from services import llm_providers
# uses: load_data(), CONFIG_DATA, DATA_FILE_TYPE, load_config()
```

**Changes in `app/routes/reviews.py`:**
Same pattern — replace `import main` + `main.X` with `from app.config import X` + `from app.data import X`.

**Verification:**
```bash
pytest tests/ -q
# Expected: 128 passed, no regressions
```

---

### Task 9: Break up `cli.py` (~962 lines)

**Objective:** `cli.py` is now the largest file in the project. It mixes 4 distinct concerns:
1. `ABSAAnnotatorConfig` class — config management (lines 56-288)
2. `start_backend()` / `start_frontend()` / `start_full_app()` — subprocess management (lines 290-390)
3. Helper functions — `update_vite_port_config`, `is_port_in_use` (lines 393-425)
4. `std_triplets_to_label()` — STD format conversion (lines 428-454)
5. `main()` — argparse + dispatch (lines 457-947)

**Proposed extraction:**
- `cli/config.py` — `ABSAAnnotatorConfig` class
- `cli/runner.py` — `start_backend()`, `start_frontend()`, `start_full_app()`, helper functions
- `cli/convert.py` — `std_triplets_to_label()`
- `cli/__init__.py` — re-exports, imports from submodules
- `cli.py` — thin wrapper: `from cli import main; main()`

**Verification:**
```bash
python -m py_compile cli.py cli/config.py cli/runner.py cli/convert.py
python cli.py --data-path examples/semeval_reviews.csv --backend-only
# Expected: backend starts without errors
pytest tests/ -q
```
