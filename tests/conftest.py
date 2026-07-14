"""Shared fixtures for learning route tests (and other test modules).

Provides:
- ``csv_path``: A temporary CSV with 5 rows (2 labeled, 3 unlabeled).
- ``app``: FastAPI TestClient with env / config wired for the temp CSV.
- ``reset_config``: Autouse fixture that clears and re-seeds CONFIG_DATA
  between every test for isolation.
"""
import os
import csv
import tempfile
import pytest
from fastapi.testclient import TestClient

# ── Test data ──────────────────────────────────────────────────────────────
# 5 rows: rows 0 and 2 have JSON label annotations; 1, 3, 4 are unlabeled.
TEST_REVIEWS_CSV_ROWS = [
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
        "label": (
            '[{"aspect_category": "SERVICE#GENERAL", '
            '"sentiment_polarity": "negative"}]'
        ),
    },
    {
        "review_id": 3,
        "text": "Fiyatlar uygun",
        "label": "",
    },
    {
        "review_id": 4,
        "text": "Ortam harika",
        "label": "",
    },
]

BASE_CONFIG = {
    "DATA_FILE_TYPE": "csv",
    "sentiment_elements": [
        "aspect_term",
        "aspect_category",
        "sentiment_polarity",
        "opinion_term",
    ],
    "sentiment_polarity_options": ["positive", "negative", "neutral"],
    "aspect_categories": [
        "AMBIENCE#GENERAL",
        "SERVICE#GENERAL",
        "FOOD#QUALITY",
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────

def write_csv(rows, path):
    """Write *rows* (list[dict]) to *path* as UTF-8 CSV."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["review_id", "text", "label"])
        writer.writeheader()
        writer.writerows(rows)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def csv_path():
    """Create a temporary CSV file with test review data."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    path = tmp.name
    tmp.close()
    write_csv(TEST_REVIEWS_CSV_ROWS, path)
    yield path
    os.unlink(path)


@pytest.fixture
def app(csv_path):
    """Set up environment, import the FastAPI app, return a TestClient.

    ``ABSA_DATA_PATH`` is set *before* importing ``main`` so that the
    module-level ``DATA_FILE_PATH`` / ``DATA_FILE_TYPE`` are populated
    correctly from the environment.

    Saves and restores the original ``CONFIG_DATA`` state so that other
    test modules (e.g. ``test_live_prediction.py``) are not affected by
    global state mutations.
    """
    os.environ["ABSA_DATA_PATH"] = csv_path
    if "ABSA_CONFIG_PATH" in os.environ:
        del os.environ["ABSA_CONFIG_PATH"]

    import main  # noqa: PLC0415 — must import after env is set
    import app.config as app_cfg  # noqa: PLC0415
    from app.config import CONFIG_DATA as _cfg  # noqa: PLC0415

    # Save original state for restoration after the test session
    original_path = app_cfg.DATA_FILE_PATH
    original_type = app_cfg.DATA_FILE_TYPE
    original_cfg = dict(_cfg)

    # Ensure the data file globals are correct (belt-and-suspenders with
    # the env var above).  ``main.DATA_FILE_PATH`` is a *copy* of the
    # string — updating it alone does NOT propagate to ``app.config``,
    # which is what ``app.data.load_data()`` actually reads.
    app_cfg.DATA_FILE_PATH = csv_path
    app_cfg.DATA_FILE_TYPE = "csv"

    # Seed CONFIG_DATA in-place (so all ``from app.config import CONFIG_DATA``
    # references — including in app.routes.learning — see the same dict).
    _cfg.clear()
    _cfg.update(BASE_CONFIG)

    yield TestClient(main.app)

    # Restore original state to avoid leaking into other test modules
    app_cfg.DATA_FILE_PATH = original_path
    app_cfg.DATA_FILE_TYPE = original_type
    _cfg.clear()
    _cfg.update(original_cfg)
