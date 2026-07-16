"""Tests for services/active_learning.py — multi-label ABSA active learning.

Tests cover:
- labeled_texts_from_data: JSON and CSV extraction paths
- train_labeled_data: multi-label binary matrix + pipeline training
"""

import numpy as np
import pandas as pd
import pytest
from services.active_learning import (
    labeled_texts_from_data,
    train_labeled_data,
    predict_texts,
)


# ---------------------------------------------------------------------------
# labeled_texts_from_data
# ---------------------------------------------------------------------------


class TestLabeledTextsFromData:
    """Tests for labeled_texts_from_data — extracting texts + label_sets."""

    def test_json_format_returns_texts_and_labels(self):
        data = [
            {
                "text": "yemek güzel",
                "label": [
                    {
                        "aspect_category": "Food#quality",
                        "sentiment_polarity": "positive",
                    }
                ],
            },
            {
                "text": "servis hızlı",
                "label": [
                    {
                        "aspect_category": "Service#general",
                        "sentiment_polarity": "positive",
                    }
                ],
            },
        ]
        texts, label_sets = labeled_texts_from_data(data, "json")
        assert texts == ["yemek güzel", "servis hızlı"]
        assert label_sets == [
            ["Food#quality__positive"],
            ["Service#general__positive"],
        ]

    def test_csv_format_returns_texts_and_labels(self):
        df = pd.DataFrame({
            "text": ["yemek güzel", "servis hızlı"],
            "label": [
                '[{"aspect_category": "Food#quality", "sentiment_polarity": "positive"}]',
                '[{"aspect_category": "Service#general", "sentiment_polarity": "positive"}]',
            ],
        })
        texts, label_sets = labeled_texts_from_data(df, "csv")
        assert texts == ["yemek güzel", "servis hızlı"]
        assert label_sets == [
            ["Food#quality__positive"],
            ["Service#general__positive"],
        ]

    def test_empty_labels_returns_empty_sets(self):
        data = [
            {"text": "yemek güzel", "label": []},
            {"text": "servis hızlı", "label": []},
        ]
        texts, label_sets = labeled_texts_from_data(data, "json")
        assert texts == ["yemek güzel", "servis hızlı"]
        assert label_sets == [[], []]

    def test_missing_category_or_polarity_skips_label(self):
        data = [
            {
                "text": "test",
                "label": [
                    {"aspect_category": "Food#quality", "sentiment_polarity": ""},
                    {"aspect_category": "", "sentiment_polarity": "positive"},
                    {"category": "Service#general", "polarity": "positive"},
                ],
            }
        ]
        texts, label_sets = labeled_texts_from_data(data, "json")
        assert texts == ["test"]
        # Only the third label has both non-empty category and polarity
        assert label_sets == [["Service#general__positive"]]

    def test_malformed_json_falls_back_to_ast_literal_eval(self):
        """Single-quoted string is invalid JSON but valid Python (ast fallback)."""
        df = pd.DataFrame({
            "text": ["yemek güzel"],
            "label": [
                "[{'aspect_category': 'Food#quality', 'sentiment_polarity': 'positive'}]",
            ],
        })
        texts, label_sets = labeled_texts_from_data(df, "csv")
        assert texts == ["yemek güzel"]
        assert label_sets == [["Food#quality__positive"]]

    def test_both_fallback_fails_returns_empty(self):
        """Completely unparsable label string returns empty set."""
        df = pd.DataFrame({
            "text": ["yemek güzel"],
            "label": ["completely unparsable garbage"],
        })
        texts, label_sets = labeled_texts_from_data(df, "csv")
        assert texts == ["yemek güzel"]
        assert label_sets == [[]]

    def test_none_label_handling(self):
        """None label in JSON results in empty set."""
        data = [{"text": "test", "label": None}]
        texts, label_sets = labeled_texts_from_data(data, "json")
        assert texts == ["test"]
        assert label_sets == [[]]


# ---------------------------------------------------------------------------
# train_labeled_data
# ---------------------------------------------------------------------------


class TestTrainLabeledData:
    """Tests for train_labeled_data — multi-label pipeline training."""

    def test_returns_model_with_label_columns(self):
        texts = ["yemek güzel", "servis hızlı"]
        labels = [
            ["Food#quality__positive"],
            ["Service#general__positive"],
        ]
        result = train_labeled_data(texts, labels)
        assert result is not None
        assert "model" in result
        assert "label_columns" in result
        assert result["label_columns"] == [
            "Food#quality__positive",
            "Service#general__positive",
        ]

    def test_returns_none_when_no_labels(self):
        texts = ["yemek güzel", "servis hızlı"]
        labels = [[], []]
        result = train_labeled_data(texts, labels)
        assert result is None

    def test_returns_none_when_fewer_than_2_labeled(self):
        texts = ["yemek güzel", "servis hızlı"]
        labels = [["Food#quality__positive"], []]
        result = train_labeled_data(texts, labels)
        assert result is None

    def test_multilabel_binary_matrix_shape(self):
        texts = ["great food", "bad service", "decent place"]
        labels = [
            ["Food#quality__positive", "Service#general__positive"],
            ["Food#quality__positive"],
            ["Service#general__positive"],
        ]
        result = train_labeled_data(texts, labels)
        assert result is not None
        model = result["model"]
        label_columns = result["label_columns"]
        assert len(label_columns) == 2
        proba = model.predict_proba(texts)
        assert proba.shape == (3, 2)

    @pytest.mark.parametrize(
        "texts, labels",
        [
            (
                ["tasty food", "yummy dish"],
                [["Food__positive"], ["Food__positive"]],
            ),
            (
                ["tasty food", "awful service", "decent ambiance"],
                [["Food__positive"], ["Service__negative"], ["Food__positive", "Service__negative"]],
            ),
        ],
    )
    def test_model_is_fitted_pipeline(self, texts, labels):
        """Trained model can produce predictions without errors."""
        result = train_labeled_data(texts, labels)
        assert result is not None
        model = result["model"]
        label_columns = result["label_columns"]
        proba = model.predict_proba(texts)
        assert proba.shape[0] == len(texts)
        # For 1 label, OneVsRestClassifier returns (n, 2); for 2+ labels, (n, n_labels)
        expected_cols = len(label_columns) if len(label_columns) != 1 else 1
        assert proba.shape[1] == len(label_columns) or (
            len(label_columns) == 1 and proba.shape[1] == 2
        )
        assert np.all((proba >= 0) & (proba <= 1))


# ---------------------------------------------------------------------------
# predict_texts
# ---------------------------------------------------------------------------


class TestPredictTexts:
    """Tests for predict_texts — batch prediction + confidence filtering."""

    def test_predicts_for_multiple_texts(self):
        texts = ["yemek güzel", "servis kötü"]
        labels = [
            ["Food#quality__positive"],
            ["Service#general__negative"],
        ]
        model_data = train_labeled_data(texts, labels)
        assert model_data is not None

        results = predict_texts(model_data, texts)
        assert len(results) == 2
        # Each result should have predictions (at least above threshold)
        for preds in results:
            assert isinstance(preds, list)
            for p in preds:
                assert "aspect_category" in p
                assert "sentiment_polarity" in p
                assert "confidence" in p
                assert "label" in p

    def test_empty_texts_returns_empty_lists(self):
        texts = ["yemek güzel", "servis kötü"]
        labels = [["Food#quality__positive"], ["Service#general__negative"]]
        model_data = train_labeled_data(texts, labels)
        assert model_data is not None

        results = predict_texts(model_data, [])
        assert results == []

    def test_confidence_threshold_filters_low_confidence(self):
        texts = ["yemek güzel", "servis kötü"]
        labels = [["Food#quality__positive"], ["Service#general__negative"]]
        model_data = train_labeled_data(texts, labels)
        assert model_data is not None

        # With threshold 1.0, nothing should pass
        results = predict_texts(model_data, texts, confidence_threshold=1.0)
        assert len(results) == 2
        for preds in results:
            assert len(preds) == 0

    def test_none_model_data_returns_empty(self):
        results = predict_texts(None, ["some text"])
        assert results == [[]]

    def test_predictions_sorted_by_confidence(self):
        texts = [
            "great food and wonderful service and amazing ambiance",
            "bad food terrible service",
        ]
        labels = [
            ["Food#quality__positive", "Service#general__positive"],
            ["Food#quality__negative", "Service#general__negative"],
        ]
        model_data = train_labeled_data(texts, labels)
        assert model_data is not None

        results = predict_texts(model_data, texts, confidence_threshold=0.0)
        for preds in results:
            confidences = [p["confidence"] for p in preds]
            assert confidences == sorted(confidences, reverse=True)


