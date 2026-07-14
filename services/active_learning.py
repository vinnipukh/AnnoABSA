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
        has_original_label = "original_label" in data.columns
        # In 4-way NEWUI CSVs, original_label = GT model output, not user annotation.
        # Skip the fallback when model-label columns exist (dataframe is 4-way).
        is_newui = has_original_label and any(
            col in data.columns for col in ("gemma4_31b_label", "majority_vote", "gpt_oss_120b_label", "qwen3.6_35b_label")
        )

        for _, row in data.iterrows():
            text = row.get("text", "")
            texts.append(text)

            # Only use the 'label' column for user annotations in 4-way mode.
            # In standard mode, fall back to original_label as a compatible source.
            raw_label = row.get("label")
            if raw_label is None or pd.isna(raw_label) or str(raw_label).strip() in ("", "[]"):
                if not is_newui:
                    raw_label = row.get("original_label") or ""
                else:
                    raw_label = ""
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
                    if isinstance(lbl, (list, tuple)):
                        # Tuple format: (aspect_term, aspect_category, polarity)
                        cat = str(lbl[1]) if len(lbl) > 1 else ""
                        pol = str(lbl[2]) if len(lbl) > 2 else ""
                    else:
                        # Dict format: {"aspect_category": ..., "sentiment_polarity": ...}
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
