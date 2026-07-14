"""Tests for /settings, /timing, and /upload routes.

Uses the shared fixtures from ``conftest.py`` (``csv_path``, ``app``,
``reset_config``).  The CSV contains 5 rows: indices 0 and 2 are labeled,
indices 1, 3, 4 are unlabeled.
"""
import os
import csv
import json
import tempfile
import pytest
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════════
# GET /settings & PATCH /settings
# ═══════════════════════════════════════════════════════════════════════════

class TestSettings:
    """Tests for GET /settings and PATCH /settings."""

    # ── GET /settings ────────────────────────────────────────────────────

    def test_get_settings_returns_all_keys(self, app):
        """GET /settings returns 200 with all expected config keys."""
        response = app.get("/settings")
        assert response.status_code == 200
        data = response.json()

        expected_keys = {
            "sentiment elements", "total_count", "sentiment_polarity options",
            "aspect_categories", "implicit_aspect_term_allowed",
            "implicit_opinion_term_allowed", "auto_clean_phrases",
            "save_phrase_positions", "click_on_token",
            "enable_pre_prediction", "disable_ai_automatic_prediction",
            "enable_helper_agent", "annotation_guideline", "theme",
            "llm_provider", "llm_model", "vllm_model", "vllm_url",
            "n_few_shot", "compare_model_a_name", "compare_model_b_name",
            "compare_mode", "model_a_provider", "model_a_model",
            "model_a_prompt", "model_a_temperature",
            "model_b_provider", "model_b_model", "model_b_prompt",
            "model_b_temperature",
            "helper_agent_provider", "helper_agent_model",
            "helper_agent_prompt", "helper_agent_temperature",
            "ai_shortcut_key",
            "current_index", "max_number_of_idxs",
        }
        assert expected_keys.issubset(data.keys())

    def test_get_settings_includes_current_index(self, app):
        """Response contains current_index and max_number_of_idxs."""
        response = app.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert "current_index" in data
        assert "max_number_of_idxs" in data

    def test_get_settings_includes_session_id_when_set(self, app):
        """When CONFIG_DATA has session_id, GET /settings returns it."""
        import app.config as cfg  # noqa: PLC0415
        cfg.CONFIG_DATA["session_id"] = "test-session-123"

        response = app.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"

    # ── PATCH /settings ──────────────────────────────────────────────────

    def test_patch_settings_updates_config(self, app):
        """PATCH with a single key updates CONFIG_DATA in-memory."""
        import app.config as cfg  # noqa: PLC0415

        response = app.patch("/settings", json={"theme": "light"})
        assert response.status_code == 200
        assert cfg.CONFIG_DATA.get("theme") == "light"

    def test_patch_settings_persists_to_file(self, app, tmp_path):
        """PATCH writes the updated config to the CONFIG_PATH file."""
        import app.config as cfg  # noqa: PLC0415
        import app.routes.settings as settings_mod  # noqa: PLC0415

        config_file = tmp_path / "test_config.json"
        # Patch the reference used inside settings.py directly
        settings_mod.CONFIG_PATH = str(config_file)

        response = app.patch("/settings", json={"theme": "light"})
        assert response.status_code == 200

        assert config_file.exists()
        saved = json.loads(config_file.read_text(encoding="utf-8"))
        assert saved.get("theme") == "light"

    def test_patch_settings_returns_ok(self, app):
        """PATCH returns {'status': 'ok'}."""
        response = app.patch("/settings", json={"theme": "dark"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_multiple_keys_can_be_updated_at_once(self, app):
        """PATCH with multiple keys updates all of them."""
        import app.config as cfg  # noqa: PLC0415

        response = app.patch("/settings", json={
            "theme": "light",
            "enable_helper_agent": False,
            "n_few_shot": 5,
        })
        assert response.status_code == 200
        assert cfg.CONFIG_DATA["theme"] == "light"
        assert cfg.CONFIG_DATA["enable_helper_agent"] is False
        assert cfg.CONFIG_DATA["n_few_shot"] == 5


# ═══════════════════════════════════════════════════════════════════════════
# POST /timing/{data_idx} & GET /avg-annotation-time
# ═══════════════════════════════════════════════════════════════════════════

class TestTiming:
    """Tests for POST /timing/{data_idx} and GET /avg-annotation-time."""

    # ── POST /timing/{data_idx} ──────────────────────────────────────────

    def test_post_timing_adds_entry(self, app, csv_path):
        """POST timing for a valid index persists the duration to the CSV."""
        response = app.post("/timing/0", json={"duration": 5.0, "change": True})
        assert response.status_code == 200
        assert response.json() == {"message": "Timing gespeichert"}

        # Verify the entry was written to the CSV
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        timings = json.loads(rows[0]["timings"])
        assert len(timings) == 1
        assert timings[0]["duration"] == 5.0
        assert timings[0]["change"] is True

    def test_post_timing_out_of_range_404(self, app):
        """POST with an index beyond the data returns 404."""
        response = app.post("/timing/999", json={"duration": 1.0})
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "out of range" in data["detail"].lower()

    # ── GET /avg-annotation-time ─────────────────────────────────────────

    def test_get_avg_annotation_time_empty(self, app):
        """With no timing entries, avg_time=0.0 and total_entries=0."""
        response = app.get("/avg-annotation-time")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_annotation_time"] == 0.0
        assert data["total_entries"] == 0
        assert data["total_duration"] == 0.0

    def test_get_avg_annotation_time_with_data(self, app):
        """Multiple timing entries produce the correct average."""
        app.post("/timing/0", json={"duration": 10.0, "change": True})
        app.post("/timing/1", json={"duration": 20.0, "change": False})
        app.post("/timing/2", json={"duration": 30.0, "change": True})

        response = app.get("/avg-annotation-time")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 3
        assert data["total_duration"] == 60.0
        assert data["avg_annotation_time"] == 20.0


# ═══════════════════════════════════════════════════════════════════════════
# POST /upload-data & POST /auto-add-positions
# ═══════════════════════════════════════════════════════════════════════════

class TestUpload:
    """Tests for POST /upload-data and POST /auto-add-positions."""

    # ── POST /upload-data ────────────────────────────────────────────────

    def test_upload_csv_file(self, app):
        """Upload a valid CSV file returns 200 with row count."""
        csv_content = "review_id,text,label\n0,Test review one,\n1,Test review two,\n"
        response = app.post(
            "/upload-data",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert "Loaded" in data["message"]
        assert "test.csv" in data["message"]

    def test_upload_json_file(self, app):
        """Upload a valid JSON file returns 200 with item count."""
        json_content = json.dumps([
            {"review_id": 0, "text": "JSON review one", "label": ""},
            {"review_id": 1, "text": "JSON review two", "label": ""},
        ])
        response = app.post(
            "/upload-data",
            files={"file": ("data.json", json_content, "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert "Loaded" in data["message"]

    def test_upload_unsupported_format_400(self, app):
        """Upload a .txt file returns 400."""
        response = app.post(
            "/upload-data",
            files={"file": ("notes.txt", b"some text content", "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unsupported" in data["detail"]

    def test_upload_no_file_400(self, app):
        """Request without a file returns 422 (FastAPI validation error)."""
        response = app.post("/upload-data")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    # ── POST /auto-add-positions ─────────────────────────────────────────

    def test_auto_add_positions(self, app):
        """POST /auto-add-positions returns 200 with success message."""
        response = app.post("/auto-add-positions")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()
