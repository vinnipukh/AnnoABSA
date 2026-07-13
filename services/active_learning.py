"""
Active learning system using Label Studio approach.

Pipeline: TfidfVectorizer → LogisticRegression (OneVsRestClassifier)
Uncertainty sampling: entropy-based (higher entropy = more uncertain)
Multi-label ABSA: each (CATEGORY, polarity) pair encoded as a binary label.

Reference: https://github.com/HumanSignal/label-studio-sdk/blob/master/examples/active_learning/active_learning.py
"""
import json
import warnings
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import entropy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline


def get_model():
    """Build a TF-IDF + LogisticRegression pipeline for multi-label ABSA.

    Uses:
        - TfidfVectorizer: max 1000 features, unigrams + bigrams
        - OneVsRestClassifier: one binary LogisticRegression per (category, polarity) label
    """
    return make_pipeline(
        TfidfVectorizer(max_features=1000, ngram_range=(1, 2)),
        OneVsRestClassifier(LogisticRegression(C=10, max_iter=1000)),
    )


def labeled_texts_from_data(data, file_type: str):
    """Extract (texts, label_sets) from loaded annotation data.

    Parameters
    ----------
    data : list[dict] or pd.DataFrame
        Loaded annotation data (from load_data()).
    file_type : str
        ``"json"`` or ``"csv"``.

    Returns
    -------
    texts : list[str]
        Review texts.
    label_sets : list[list[str]]
        For each review, a list of ``"CATEGORY__POLARITY"`` strings extracted
        from its label annotations. Reviews with no labels yield an empty list.
    """
    texts = []
    label_sets = []

    if file_type == "json":
        for item in data:
            text = item.get("text", "")
            texts.append(text)

            raw_labels = item.get("label", [])
            if isinstance(raw_labels, list):
                labels = []
                for lbl in raw_labels:
                    cat = lbl.get("aspect_category", lbl.get("category", ""))
                    pol = lbl.get("sentiment_polarity", lbl.get("polarity", ""))
                    if cat and pol:
                        labels.append(f"{cat}__{pol}")
                label_sets.append(labels)
            else:
                label_sets.append([])
    else:
        # CSV / DataFrame
        for _, row in data.iterrows():
            text = row.get("text", "")
            texts.append(text)

            raw_label = row.get("label", "")
            if pd.isna(raw_label) or str(raw_label).strip() in ("", "[]"):
                label_sets.append([])
                continue

            try:
                parsed = json.loads(str(raw_label))
            except (json.JSONDecodeError, ValueError):
                try:
                    import ast

                    parsed = ast.literal_eval(str(raw_label))
                except Exception:
                    parsed = []

            if isinstance(parsed, list):
                labels = []
                for lbl in parsed:
                    cat = lbl.get("aspect_category", lbl.get("category", ""))
                    pol = lbl.get("sentiment_polarity", lbl.get("polarity", ""))
                    if cat and pol:
                        labels.append(f"{cat}__{pol}")
                label_sets.append(labels)
            else:
                label_sets.append([])

    return texts, label_sets


def train_labeled_data(texts, labels) -> Optional[dict]:
    """Train a multi-label classifier on labeled reviews.

    Parameters
    ----------
    texts : list[str]
        Review texts.
    labels : list[list[str]]
        For each review, the set of ``"CATEGORY__POLARITY"`` labels.

    Returns
    -------
    dict or None
        ``{'model': fitted_pipeline, 'label_columns': list[str]}``
        or ``None`` if fewer than 2 labeled texts are available.
    """
    # Collect all unique label strings across the dataset
    all_labels = sorted({lbl for row in labels for lbl in row})
    if not all_labels:
        return None

    # Build multi-label binary matrix
    y = np.zeros((len(texts), len(all_labels)), dtype=int)
    for i, row_labels in enumerate(labels):
        for lbl in row_labels:
            if lbl in all_labels:
                y[i, all_labels.index(lbl)] = 1

    labeled_mask = y.sum(axis=1) > 0
    n_labeled = labeled_mask.sum()

    if n_labeled < 2:
        return None

    x_labeled = [texts[i] for i in range(len(texts)) if labeled_mask[i]]
    y_labeled = y[labeled_mask]

    model = get_model()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_labeled, y_labeled)

    return {"model": model, "label_columns": all_labels}


def get_uncertainty_scores(model_data: dict, texts: list) -> np.ndarray:
    """Compute entropy-based uncertainty scores for unlabeled texts.

    Higher scores = more uncertain (better candidates for annotation).

    For each text, entropy is computed across the binary predictions for every
    label: ``H = -sum(p * log(p) + (1-p) * log(1-p))``.

    Parameters
    ----------
    model_data : dict
        Output from :func:`train_labeled_data` — must contain ``'model'``
        and ``'label_columns'``.
    texts : list[str]
        Texts to score.

    Returns
    -------
    np.ndarray
        Entropy score per text (higher = more uncertain).
    """
    model = model_data["model"]
    n_labels = len(model_data["label_columns"])

    proba = model.predict_proba(texts)
    # proba shape: (n_texts, n_labels) — each column is P(positive) for that
    # binary OneVsRest classifier.
    entropy_scores = np.zeros(len(texts))
    for label_idx in range(n_labels):
        p_pos = proba[:, label_idx]
        # Avoid log(0) by clipping
        p_pos = np.clip(p_pos, 1e-15, 1 - 1e-15)
        p_neg = 1.0 - p_pos
        label_entropy = -p_pos * np.log(p_pos) - p_neg * np.log(p_neg)
        entropy_scores += label_entropy

    return entropy_scores
