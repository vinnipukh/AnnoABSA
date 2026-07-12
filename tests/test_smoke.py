"""Smoke tests — verify the app starts and critical endpoints respond.

These tests exercise the full import chain of main.py, so they catch:
- Missing dependencies
- Import errors in FastAPI, services, or model modules
- Data file format issues
- CORS middleware configuration

They use FastAPI TestClient directly (no actual HTTP server needed).
Parameterized over CSV and JSON data file formats.
"""
import os
import json
import sys
import subprocess
import tempfile
import pytest
from fastapi.testclient import TestClient


# ── Test data ──

SMOKE_CSV = (
    "review_id,text,review_text,translation,label\n"
    '0,"Test review","Test review","Test translation",""\n'
)

SMOKE_JSON = json.dumps([
    {
        "review_id": 0,
        "text": "Test review",
        "review_text": "Test review",
        "translation": "Test translation",
    }
], ensure_ascii=False)


# ── Fixtures ──

@pytest.fixture(params=["csv", "json"])
def data_file(request):
    """Create temp data file in CSV or JSON format."""
    suffix = ".csv" if request.param == "csv" else ".json"
    content = SMOKE_CSV if request.param == "csv" else SMOKE_JSON
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    tmp.write(content)
    path = tmp.name
    tmp.close()
    yield path, request.param
    os.unlink(path)


@pytest.fixture
def app(data_file):
    """Import main with a test data file.

    The env var ABSA_DATA_PATH must be set BEFORE importing main,
    because main.py reads it at module level (line 33). This fixture
    handles that ordering.
    """
    path, file_type = data_file
    os.environ["ABSA_DATA_PATH"] = path
    if "ABSA_CONFIG_PATH" in os.environ:
        del os.environ["ABSA_CONFIG_PATH"]

    # Import main after env vars are set
    import main

    main.DATA_FILE_PATH = path
    main.DATA_FILE_TYPE = file_type
    main.CONFIG_DATA = {
        "sentiment_elements": [
            "aspect_term", "aspect_category",
            "sentiment_polarity", "opinion_term",
        ],
        "aspect_categories": ["TEST#GENERAL"],
        "sentiment_polarity_options": ["positive", "negative", "neutral"],
        "implicit_aspect_term_allowed": True,
        "implicit_opinion_term_allowed": False,
        "save_phrase_positions": True,
        "n_few_shot": 3,
        "llm_provider": "ollama",
        "llm_model": "gemma3:4b",
    }
    return TestClient(main.app)


# ── Tests ──

class TestSmoke:
    """S1 + S5 automated — app loads, backend reachable."""

    def test_settings_endpoint_returns_200(self, app):
        """S5 equivalent: GET /settings returns 200 with config data."""
        response = app.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert data["total_count"] == 1
        assert "sentiment elements" in data
        assert "aspect_categories" in data

    def test_data_endpoint_returns_review(self, app):
        """GET /data/0 returns review text and standard fields."""
        response = app.get("/data/0")
        assert response.status_code == 200
        data = response.json()
        assert data["review_text"] == "Test review"
        assert "text" in data
        assert "model_a_triplets" in data
        assert "model_b_triplets" in data

    def test_app_imports_cleanly(self):
        """Verify the import chain has no missing modules."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "main.py"],
            capture_output=True, text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, (
            f"Compile error in main.py:\n{result.stderr}"
        )

    def test_unknown_route_returns_404(self, app):
        """Unknown endpoint returns 404 (not a crash)."""
        response = app.get("/nonexistent")
        assert response.status_code == 404

    def test_cors_headers_present(self, app):
        """CORS middleware is active (important for frontend)."""
        response = app.options("/settings", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
