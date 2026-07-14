"""Tests for GET /chat/predictions/{data_idx}.

Uses the shared fixtures from ``conftest.py`` (``app``) and follows the
same patterns as ``test_learning_routes.py``.
"""
import os
import csv
import tempfile
import pytest
from fastapi.testclient import TestClient


# ── Test data helpers ──────────────────────────────────────────────────────

def _make_csv(rows):
    """Write a temporary CSV with the given *rows* (list[dict]) and return its path.

    Each dict must have keys ``review_id``, ``text``, ``label``.
    The caller is responsible for calling ``os.unlink(path)``.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    path = tmp.name
    tmp.close()
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["review_id", "text", "label"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def _switch_datafile(app: TestClient, path: str, file_type: str = "csv"):
    """Point the running app's data path to *path* and update config."""
    import app.config  # noqa: PLC0415

    app.config.DATA_FILE_PATH = path
    app.config.DATA_FILE_TYPE = file_type
    app.config.CONFIG_DATA["DATA_FILE_TYPE"] = file_type


SINGLE_LABELED_ROWS = [
    {
        "review_id": 0,
        "text": "Manzara güzel",
        "label": (
            '[{"aspect_category": "AMBIENCE#GENERAL", '
            '"sentiment_polarity": "positive"}]'
        ),
    },
    {
        "review_id": 1,
        "text": "Yemek lezzetli",
        "label": "",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# GET /chat/predictions/{data_idx}
# ═══════════════════════════════════════════════════════════════════════════

class TestGetChatPredictions:
    """Tests for the /chat/predictions/{data_idx} endpoint."""

    # ── Happy path ──────────────────────────────────────────────────────

    def test_valid_index_returns_text_and_predictions(self, app):
        """A valid index returns both 'text' and 'predictions' fields."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "text" in data
        assert "predictions" in data

    def test_valid_index_unlabeled_returns_predictions(self, app):
        """Predictions for an unlabeled index also work (model uses all labeled data)."""
        response = app.get("/chat/predictions/1")  # row 1 is unlabeled
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "text" in data
        assert "predictions" in data

    # ── Response structure ──────────────────────────────────────────────

    def test_predictions_sorted_by_confidence_descending(self, app):
        """Predictions are returned sorted by confidence descending."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        data = response.json()
        predictions = data["predictions"]
        assert len(predictions) >= 1
        confidences = [p["confidence"] for p in predictions]
        assert confidences == sorted(confidences, reverse=True)

    def test_prediction_has_required_keys(self, app):
        """Each prediction dict contains aspect_category, sentiment_polarity, confidence, label."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        data = response.json()
        for pred in data["predictions"]:
            assert "aspect_category" in pred
            assert "sentiment_polarity" in pred
            assert "confidence" in pred
            assert "label" in pred

    def test_prediction_confidence_is_float_between_0_and_1(self, app):
        """The confidence field is a float between 0 and 1."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        data = response.json()
        for pred in data["predictions"]:
            conf = pred["confidence"]
            assert isinstance(conf, float)
            assert 0.0 <= conf <= 1.0

    # ── Turkish text content ────────────────────────────────────────────

    def test_turkish_text_contains_turkish_chars(self, app):
        """The 'text' field contains Turkish characters and words."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        text = response.json()["text"]
        # Turkish-specific characters
        assert any(c in text for c in "çğıöşüÇĞİÖŞÜ")
        # Turkish words expected in the output
        assert "tahmin" in text.lower()

    def test_turkish_text_describes_predictions(self, app):
        """The Turkish text mentions model predictions."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        text = response.json()["text"]
        assert "Kategori" in text
        assert "Kutup" in text or "güven" in text

    def test_high_conf_predictions_included_in_text(self, app):
        """Predictions with confidence > 0.5 appear in the Turkish text."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        data = response.json()
        text = data["text"]
        high_conf = [p for p in data["predictions"] if p["confidence"] > 0.5]
        if high_conf:
            # Should mention model predictions header
            assert "Modelin bu inceleme için tahminleri" in text
            # Should mention saving/editing
            assert "kaydedebilir" in text.lower()
        else:
            # Fallback text for no high-confidence predictions
            assert "yüksek güvenli tahmin bulunamadı" in text.lower()

    def test_text_is_non_empty_string(self, app):
        """The 'text' field is a non-empty string."""
        response = app.get("/chat/predictions/0")
        assert response.status_code == 200
        text = response.json()["text"]
        assert isinstance(text, str)
        assert len(text) > 0

    # ── Determinism ─────────────────────────────────────────────────────

    def test_response_is_deterministic(self, app):
        """Two consecutive calls for the same index return identical results."""
        resp1 = app.get("/chat/predictions/0")
        resp2 = app.get("/chat/predictions/0")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        data1 = resp1.json()
        data2 = resp2.json()
        assert data1["text"] == data2["text"]
        assert data1["predictions"] == data2["predictions"]

    # ── Multiple indices ────────────────────────────────────────────────

    def test_all_indices_return_valid_response(self, app):
        """Indices 0 through 4 all return valid 200 responses."""
        for idx in range(5):
            response = app.get(f"/chat/predictions/{idx}")
            assert response.status_code == 200, f"Index {idx} failed"
            data = response.json()
            assert "text" in data
            assert "predictions" in data

    def test_all_indices_have_turkish_text(self, app):
        """Every valid index returns Turkish text."""
        for idx in range(5):
            response = app.get(f"/chat/predictions/{idx}")
            assert response.status_code == 200, f"Index {idx} failed"
            text = response.json()["text"]
            assert isinstance(text, str) and len(text) > 0

    # ── Error handling: 404 ─────────────────────────────────────────────

    def test_out_of_range_index_returns_404(self, app):
        """An index beyond the dataset returns 404."""
        response = app.get("/chat/predictions/999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "out of range" in data["detail"].lower()

    def test_negative_index_returns_404(self, app):
        """A negative index returns 404."""
        response = app.get("/chat/predictions/-1")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "out of range" in data["detail"].lower()

    # ── Error handling: 400 ─────────────────────────────────────────────

    def test_not_enough_labeled_data_returns_400(self, app):
        """When fewer than 2 labeled reviews exist, return 400."""
        csv_path = _make_csv(SINGLE_LABELED_ROWS)
        try:
            _switch_datafile(app, csv_path)
            response = app.get("/chat/predictions/0")
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "need at least 2" in data["detail"].lower()
        finally:
            os.unlink(csv_path)

    def test_no_labeled_data_returns_400(self, app):
        """When no labeled reviews exist, return 400."""
        all_unlabeled = [
            {"review_id": 0, "text": "Manzara güzel", "label": ""},
            {"review_id": 1, "text": "Yemek lezzetli", "label": ""},
        ]
        csv_path = _make_csv(all_unlabeled)
        try:
            _switch_datafile(app, csv_path)
            response = app.get("/chat/predictions/0")
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "need at least 2" in data["detail"].lower()
        finally:
            os.unlink(csv_path)

    # ── Error handling: 500 ─────────────────────────────────────────────

    def test_error_loading_data_returns_500(self, app):
        """When the data file does not exist, the endpoint returns 500."""
        _switch_datafile(app, "/nonexistent/file.csv")
        response = app.get("/chat/predictions/0")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "error loading data" in data["detail"].lower()

    def test_nonexistent_file_throws_500(self, app):
        """Switching to a non-existent file path yields 500."""
        _switch_datafile(app, "/tmp/does_not_exist_xyz.csv")
        response = app.get("/chat/predictions/0")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
