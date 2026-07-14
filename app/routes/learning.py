"""
ML prediction endpoint — GET /learning/predict/{data_idx}.

Trains TF-IDF + LogisticRegression (OneVsRestClassifier) on user-annotated
reviews and returns triplet predictions for a single review.
"""
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from app.config import CONFIG_DATA, DATA_FILE_TYPE
from app.data import load_data
from services.active_learning import (
    labeled_texts_from_data,
    train_labeled_data,
)

router = APIRouter(tags=["learning"])


def _get_file_type() -> str:
    """Resolve the effective file type from config or global default."""
    return CONFIG_DATA.get("DATA_FILE_TYPE", DATA_FILE_TYPE)


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
            detail=f"Yetersiz etiketlenmis inceleme ({len(labeled_texts)}); en az 2 gerekli.",
        )

    model_data = train_labeled_data(labeled_texts, labeled_labels)
    if model_data is None:
        raise HTTPException(status_code=400, detail="Model egitilemedi — etiketli verileri kontrol edin.")

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
