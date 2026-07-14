"""Tests for GET /data/export-4way.

Uses the shared fixtures from ``conftest.py`` (``app``).
The CSV has 5 rows (review_id 0-4), so the exported CSV should have
1 header + 5 data rows = 6 lines.
"""
import csv
import io
import pytest
from fastapi.testclient import TestClient


class TestExport4Way:
    """4-way CSV export endpoint tests."""

    # ── Response shape ───────────────────────────────────────────────────

    def test_export_returns_csv(self, app: TestClient):
        """GET /data/export-4way returns 200 with text/csv content type."""
        resp = app.get("/data/export-4way")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_content_disposition(self, app: TestClient):
        """Response includes an attachment Content-Disposition with the
        expected filename."""
        resp = app.get("/data/export-4way")
        disposition = resp.headers["content-disposition"]
        assert "attachment" in disposition
        assert "export-4way.csv" in disposition

    def test_export_body_not_empty(self, app: TestClient):
        """Response body is not empty."""
        resp = app.get("/data/export-4way")
        assert len(resp.text.strip()) > 0

    def test_export_has_correct_row_count(self, app: TestClient):
        """CSV has 1 header row + 5 data rows = 6 lines."""
        resp = app.get("/data/export-4way")
        lines = resp.text.strip().split("\n")
        assert len(lines) == 6  # 1 header + 5 data rows

    # ── Header / column checks ───────────────────────────────────────────

    def test_export_preserves_original_columns(self, app: TestClient):
        """Original columns (review_id, text, label) are present in the
        exported CSV header."""
        resp = app.get("/data/export-4way")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "review_id" in header
        assert "text" in header
        assert "label" in header

    def test_export_appends_new_columns(self, app: TestClient):
        """Extra 4-way columns appear in the header."""
        resp = app.get("/data/export-4way")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "selected_triplets" in header
        assert "resolution_tier" in header
        assert "annotator_notes" in header

    def test_export_extra_columns_have_default_values(self, app: TestClient):
        """Every row's extra columns hold default empty values."""
        resp = app.get("/data/export-4way")
        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            assert row["selected_triplets"] == "[]"
            assert row["resolution_tier"] == ""
            assert row["annotator_notes"] == ""

    def test_export_each_row_has_extra_columns(self, app: TestClient):
        """Every data row has exactly 6 columns (3 original + 3 extra)."""
        resp = app.get("/data/export-4way")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert len(header) == 6  # review_id, text, label + 3 extra
        col_count = len(header)
        for row in reader:
            assert len(row) == col_count

    def test_export_data_matches_input(self, app: TestClient):
        """Original data values are preserved in the export."""
        resp = app.get("/data/export-4way")
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        # Check first and third review text are preserved
        assert rows[0]["text"] == "Manzara güzel"
        assert rows[2]["text"] == "Servis kötü"
        assert rows[4]["text"] == "Ortam harika"

    # ── Error handling ──────────────────────────────────────────────────

    def test_export_400_when_no_data_file(self, app: TestClient):
        """Returns 400 when the data file does not exist."""
        import app.config as cfg
        original = cfg.DATA_FILE_PATH
        cfg.DATA_FILE_PATH = "/nonexistent/path.csv"
        try:
            resp = app.get("/data/export-4way")
            assert resp.status_code == 400
            assert "Veri dosyası bulunamadı" in resp.json()["detail"]
        finally:
            cfg.DATA_FILE_PATH = original
