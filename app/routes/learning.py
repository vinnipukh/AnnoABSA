"""
Active learning endpoints — GET /learning/suggestions, GET /learning/predict/{data_idx}.

Uses TF-IDF + LogisticRegression (OneVsRestClassifier) with entropy-based
uncertainty sampling following the Label Studio active learning approach.
"""
import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.config import CONFIG_DATA, DATA_FILE_TYPE
from app.data import load_data
from services.active_learning import (
    get_uncertainty_scores,
    labeled_texts_from_data,
    train_labeled_data,
)

router = APIRouter(tags=["learning"])


def _get_file_type() -> str:
    """Resolve the effective file type from config or global default."""
    return CONFIG_DATA.get("DATA_FILE_TYPE", DATA_FILE_TYPE)


@router.get("/learning/suggestions")
def get_learning_suggestions(n: int = Query(5, ge=1, le=50)):
    """Return the *n* most uncertain (unlabeled) reviews for active learning.

    The model is trained on all currently labeled reviews. Unlabeled reviews
    are scored by entropy across all binary label classifiers. The highest-
    entropy (most uncertain) reviews are returned first, making them the best
    candidates for the next round of manual annotation.

    Parameters
    ----------
    n : int
        Number of suggestions to return (1-50, default 5).

    Returns
    -------
    list[dict]
        Each entry: ``{'data_idx': int, 'text': str, 'uncertainty': float}``
        sorted by uncertainty descending.
    """
    try:
        data = load_data()
        file_type = _get_file_type()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

    texts, label_sets = labeled_texts_from_data(data, file_type)

    # Identify which indices are unlabeled (have no annotations)
    unlabeled_indices = [i for i, ls in enumerate(label_sets) if not ls]

    if not unlabeled_indices:
        return {"suggestions": [], "message": "All reviews are already labeled."}

    model_data = train_labeled_data(texts, label_sets)
    if model_data is None:
        # Not enough labeled data — return first n unlabeled items with
        # uniform uncertainty (no model available)
        suggestions = []
        for idx in unlabeled_indices[:n]:
            suggestions.append({
                "data_idx": int(idx),
                "text": texts[idx],
                "uncertainty": 1.0,
            })
        return {"suggestions": suggestions, "message": "Not enough labeled data to train model."}

    # Score only unlabeled texts
    unlabeled_texts = [texts[i] for i in unlabeled_indices]
    scores = get_uncertainty_scores(model_data, unlabeled_texts)

    # Sort by uncertainty descending
    ranked = sorted(
        zip(unlabeled_indices, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    suggestions = []
    for idx, score in ranked[:n]:
        suggestions.append({
            "data_idx": int(idx),
            "text": texts[idx],
            "uncertainty": float(round(score, 6)),
        })

    return {"suggestions": suggestions}


@router.get("/learning/predict/{data_idx}")
def get_learning_predict(data_idx: int):
    """Return ML-based triplet predictions for a single review.

    Trains a TF-IDF + LogisticRegression (OneVsRestClassifier) on all
    currently labeled reviews, then predicts (category, polarity) pairs
    for the specified review index.

    Parameters
    ----------
    data_idx : int
        0-based index of the review to predict.

    Returns
    -------
    list[dict]
        Predicted triplets with keys ``aspect_category``, ``sentiment_polarity``,
        ``confidence`` (probability from the binary classifier), ``label``
        (the ``"CATEGORY__POLARITY"`` string).
    """
    try:
        data = load_data()
        file_type = _get_file_type()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

    if data_idx < 0 or (file_type == "json" and data_idx >= len(data)) or (file_type != "json" and data_idx >= len(data)):
        raise HTTPException(status_code=404, detail=f"Index {data_idx} out of range.")

    texts, label_sets = labeled_texts_from_data(data, file_type)

    # Only keep reviews that have at least one label for training
    labeled_texts = [texts[i] for i in range(len(texts)) if label_sets[i]]
    labeled_labels = [label_sets[i] for i in range(len(texts)) if label_sets[i]]

    if len(labeled_texts) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough labeled reviews ({len(labeled_texts)}); need at least 2 to train.",
        )

    model_data = train_labeled_data(labeled_texts, labeled_labels)
    if model_data is None:
        raise HTTPException(status_code=400, detail="Failed to train model — check labeled data.")

    model = model_data["model"]
    label_columns = model_data["label_columns"]

    target_text = texts[data_idx]

    # predict_proba returns shape (1, n_labels) — each column is P(positive)
    proba = model.predict_proba([target_text])
    label_probs = {}
    for col_idx, col_name in enumerate(label_columns):
        p_pos = float(proba[0, col_idx])
        label_probs[col_name] = p_pos

    # Return ones with predictions (only labels above 0.5 threshold to reduce noise)
    predictions = []
    for label_name, confidence in sorted(label_probs.items(), key=lambda x: x[1], reverse=True):
        # Parse "CATEGORY__POLARITY" back to components
        parts = label_name.rsplit("__", 1)
        if len(parts) == 2:
            category, polarity = parts
        else:
            category, polarity = label_name, ""

        predictions.append({
            "aspect_category": category,
            "sentiment_polarity": polarity,
            "confidence": float(round(confidence, 6)),
            "label": label_name,
        })

    return predictions
