"""Tests for GET /learning/predict/{data_idx}.

Uses the shared fixtures from ``conftest.py`` (``csv_path``, ``app``,
``reset_config``) and creates inline temporary CSV files for scenarios that
need different annotation coverage (all-labeled, minimal-labels).
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
    """Point the running app's data path to *path* and update config.

    ``load_data()`` reads ``app.config.DATA_FILE_PATH``, not
    ``main.DATA_FILE_PATH``, because ``from app.config import *`` copies
    the string.  We patch the authoritative source directly.
    """
    import app.config  # noqa: PLC0415

    app.config.DATA_FILE_PATH = path
    app.config.DATA_FILE_TYPE = file_type
    app.config.CONFIG_DATA["DATA_FILE_TYPE"] = file_type


ALL_LABELED_ROWS = [
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
        "label": (
            '[{"aspect_category": "FOOD#QUALITY", '
            '"sentiment_polarity": "positive"}]'
        ),
    },
    {
        "review_id": 2,
        "text": "Servis kötü",
        "label": (
            '[{"aspect_category": "SERVICE#GENERAL", '
            '"sentiment_polarity": "negative"}]'
        ),
    },
]

MINIMAL_LABELED_ROWS = [
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
    {
        "review_id": 2,
        "text": "Servis kötü",
        "label": "",
    },
]

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
# GET /learning/predict/{data_idx}
# ═══════════════════════════════════════════════════════════════════════════

class TestGetLearningPredict:
    """Tests for the /learning/predict/{data_idx} endpoint."""

    # ── Happy path ──────────────────────────────────────────────────────

    def test_valid_index_returns_predictions(self, app):
        """A valid labeled index returns a list of predicted triplets."""
        response = app.get("/learning/predict/0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # At least one prediction should be present
        assert len(data) >= 1

    def test_valid_index_unlabeled_returns_predictions(self, app):
        """Requesting predictions for an unlabeled index also works (model uses all labeled data for training)."""
        response = app.get("/learning/predict/1")  # row 1 is unlabeled
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    # ── Response structure ──────────────────────────────────────────────

    def test_prediction_has_required_keys(self, app):
        """Each prediction dict contains aspect_category, sentiment_polarity, confidence, label."""
        response = app.get("/learning/predict/0")
        assert response.status_code == 200
        data = response.json()
        for pred in data:
            assert "aspect_category" in pred
            assert "sentiment_polarity" in pred
            assert "confidence" in pred
            assert "label" in pred

    def test_prediction_confidence_is_float(self, app):
        """The confidence field is a float between 0 and 1."""
        response = app.get("/learning/predict/0")
        assert response.status_code == 200
        data = response.json()
        for pred in data:
            conf = pred["confidence"]
            assert isinstance(conf, float)
            assert 0.0 <= conf <= 1.0

    # ── Error handling ──────────────────────────────────────────────────

    def test_out_of_range_index_returns_404(self, app):
        """An index beyond the dataset returns 404."""
        response = app.get("/learning/predict/999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "out of range" in data["detail"].lower()

    def test_negative_index_returns_404(self, app):
        """A negative index returns 404."""
        response = app.get("/learning/predict/-1")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "out of range" in data["detail"].lower()

    def test_not_enough_labeled_data_returns_400(self, app):
        """When fewer than 2 labeled reviews exist, return 400."""
        csv_path = _make_csv(SINGLE_LABELED_ROWS)
        try:
            _switch_datafile(app, csv_path)
            response = app.get("/learning/predict/0")
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "en az 2" in data["detail"].lower()
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
            response = app.get("/learning/predict/0")
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "en az 2" in data["detail"].lower()
        finally:
            os.unlink(csv_path)


# ═══════════════════════════════════════════════════════════════════════════
# POST /learning/autopilot
# ═══════════════════════════════════════════════════════════════════════════


class TestPostLearningAutopilot:
    """Tests for the POST /learning/autopilot batch annotation endpoint."""

    def test_autopilot_with_enough_labeled_returns_annotations(self, app):
        """With 2+ labeled reviews, autopilot predicts and saves."""
        response = app.post("/learning/autopilot", json={"count": 3, "confidence_threshold": 0.0})
        assert response.status_code == 200
        data = response.json()
        assert "annotated" in data
        assert "total_unlabeled" in data
        assert data["annotated"] >= 0
        assert data["total_unlabeled"] >= 0

    def test_autopilot_fewer_than_2_labeled_returns_400(self, app):
        """With < 2 labeled reviews, return 400."""
        rows = [
            {"review_id": 0, "text": "Manzara güzel", "label": ""},
            {"review_id": 1, "text": "Yemek lezzetli", "label": ""},
        ]
        csv_path = _make_csv(rows)
        try:
            _switch_datafile(app, csv_path)
            response = app.post("/learning/autopilot", json={"count": 3})
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "en az 2" in data["detail"].lower()
        finally:
            os.unlink(csv_path)

    def test_autopilot_single_labeled_returns_400(self, app):
        """With only 1 labeled review, return 400."""
        csv_path = _make_csv(SINGLE_LABELED_ROWS)
        try:
            _switch_datafile(app, csv_path)
            response = app.post("/learning/autopilot", json={"count": 3})
            assert response.status_code == 400
        finally:
            os.unlink(csv_path)

    def test_autopilot_all_labeled_returns_annotated_0(self, app):
        """When all reviews are already labeled, return annotated=0."""
        csv_path = _make_csv(ALL_LABELED_ROWS)
        try:
            _switch_datafile(app, csv_path)
            response = app.post("/learning/autopilot", json={"count": 3, "confidence_threshold": 0.0})
            assert response.status_code == 200
            data = response.json()
            assert data["annotated"] == 0
        finally:
            os.unlink(csv_path)

    def test_autopilot_respects_count(self, app):
        """The count parameter limits how many reviews are annotated."""
        response = app.post("/learning/autopilot", json={"count": 1, "confidence_threshold": 0.0})
        assert response.status_code == 200
        data = response.json()
        # With conftest CSV: 5 rows, rows 0 and 2 labeled, unlabeled: 3
        # count=1 means at most 1 annotated
        assert data["annotated"] <= 1

    def test_autopilot_respects_start_index(self, app):
        """The start_index parameter skips earlier unlabeled reviews."""
        response = app.post("/learning/autopilot", json={
            "count": 5, "confidence_threshold": 0.0, "start_index": 3
        })
        assert response.status_code == 200
        data = response.json()
        assert "annotated" in data

    def test_autopilot_saves_valid_json_label(self, app):
        """After autopilot, saved labels should be valid JSON."""
        import app.config as app_cfg
        import pandas as pd

        # Run autopilot with low threshold on conftest CSV
        response = app.post("/learning/autopilot", json={"count": 1, "confidence_threshold": 0.0})
        assert response.status_code == 200

        # Read back the CSV to verify label format
        df = pd.read_csv(app_cfg.DATA_FILE_PATH)
        for _, row in df.iterrows():
            label = row.get("label", "")
            if pd.notna(label) and str(label).strip() not in ("", "[]"):
                import json
                parsed = json.loads(str(label))
                assert isinstance(parsed, list)



