"""Tests for GET /live_prediction/{data_idx} endpoint (Phase 4: Live Compare Mode).

Tests the full HTTP endpoint behavior including validation, provider dispatch,
temperature/prompt propagation, position data, and error handling.
Uses FastAPI TestClient with mocked provider calls.
"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── Test data ──

TEST_REVIEWS_CSV = (
    "review_id,text,review_text,translation,label\n"
    '0,"Manzara şahane ama servis rezalet","Manzara şahane ama servis rezalet","The view is wonderful but the service is terrible",""\n'
    '1,"Yemekler sıcacık ve çok lezzetliydi","Yemekler sıcacık ve çok lezzetliydi","The food was warm and very delicious",""\n'
)

MOCK_PREDICTION_RESULT = {
    "aspects": [
        {
            "aspect_term": "Manzara",
            "aspect_category": "AMBIENCE#GENERAL",
            "sentiment_polarity": "positive",
        },
        {
            "aspect_term": "servis",
            "aspect_category": "SERVICE#GENERAL",
            "sentiment_polarity": "negative",
        },
    ]
}

MOCK_PREDICTION_WITH_POSITIONS = {
    "aspects": [
        {
            "aspect_term": "Manzara",
            "aspect_category": "AMBIENCE#GENERAL",
            "sentiment_polarity": "positive",
        },
    ]
}


# ── Fixtures ──

@pytest.fixture(scope="module")
def csv_path():
    """Create a temporary CSV file with test review data."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(TEST_REVIEWS_CSV)
    path = tmp.name
    tmp.close()
    yield path
    os.unlink(path)


@pytest.fixture(scope="module")
def app(csv_path):
    """Set up environment and import the FastAPI app.

    The env var must be set BEFORE importing main, because main reads
    ABSA_DATA_PATH at module level. This fixture runs once per module
    and mutates globals directly instead of using reload.
    """
    os.environ["ABSA_DATA_PATH"] = csv_path
    if "ABSA_CONFIG_PATH" in os.environ:
        del os.environ["ABSA_CONFIG_PATH"]

    # Import main after env is set
    import main
    from app.config import CONFIG_DATA as _cfg

    # Ensure the data file is properly set
    main.DATA_FILE_PATH = csv_path
    main.DATA_FILE_TYPE = "csv"
    # Seed with few-shot example on row 1 — mutate in-place so
    # app.config.CONFIG_DATA (imported by route files) stays in sync
    _cfg.clear()
    _cfg.update({
        "sentiment_elements": ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
        "sentiment_polarity_options": ["positive", "negative", "neutral"],
        "aspect_categories": ["AMBIENCE#GENERAL", "SERVICE#GENERAL", "FOOD#QUALITY"],
        "implicit_aspect_term_allowed": True,
        "implicit_opinion_term_allowed": False,
        "save_phrase_positions": True,
        "n_few_shot": 3,
        "llm_provider": "ollama",
        "llm_model": "gemma3:4b",
    })
    client = TestClient(main.app)
    return client


@pytest.fixture(autouse=True)
def reset_config(app):
    """Reset CONFIG_DATA to a clean base state before each test.

    This ensures test isolation — each test starts with only the
    per-model config it explicitly sets.
    """
    import main
    main.CONFIG_DATA["model_a_provider"] = None
    main.CONFIG_DATA["model_a_model"] = None
    main.CONFIG_DATA["model_a_prompt"] = None
    main.CONFIG_DATA["model_a_temperature"] = 0.7
    main.CONFIG_DATA["model_b_provider"] = None
    main.CONFIG_DATA["model_b_model"] = None
    main.CONFIG_DATA["model_b_prompt"] = None
    main.CONFIG_DATA["model_b_temperature"] = 0.7
    main.CONFIG_DATA["save_phrase_positions"] = True
    yield


def _mock_predict(provider_name="ollama"):
    """Return a mock provider predict() that returns MOCK_PREDICTION_RESULT."""
    mock_provider = MagicMock()
    mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
    return mock_provider


# ── Tests ──

class TestLivePredictionValidation:
    """Tests for input validation — invalid roles, missing config."""

    @pytest.mark.parametrize("invalid_role", ["model_c", "model_c", "helper_agent", "", "abc"])
    def test_unknown_role_returns_400(self, app, invalid_role):
        """Invalid role query param returns 400 with descriptive message."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        response = app.get(f"/live_prediction/0?role={invalid_role}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "model_a" in data["detail"].lower() or "model_b" in data["detail"].lower()

    def test_no_provider_returns_400(self, app):
        """When model_a_provider is None, endpoint returns 400."""
        import main
        main.CONFIG_DATA["model_a_provider"] = None
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        response = app.get("/live_prediction/0?role=model_a")
        assert response.status_code == 400
        data = response.json()
        assert "provider" in data["detail"].lower()

    def test_no_model_returns_400(self, app):
        """When model_a_model is None, endpoint returns 400."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = None

        response = app.get("/live_prediction/0?role=model_a")
        assert response.status_code == 400
        data = response.json()
        assert "model" in data["detail"].lower()

    def test_both_missing_returns_400(self, app):
        """Neither provider nor model set returns 400."""
        response = app.get("/live_prediction/0?role=model_a")
        assert response.status_code == 400

    def test_out_of_range_index_returns_404(self, app):
        """Requesting a non-existent row index returns 404."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        response = app.get("/live_prediction/999?role=model_a")
        assert response.status_code == 404

    def test_openai_provider_without_key_returns_400(self, app):
        """OpenAI provider selected but no openai_key configured → 400."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "openai"
        main.CONFIG_DATA["model_a_model"] = "gpt-4o"

        response = app.get("/live_prediction/0?role=model_a")
        assert response.status_code == 400
        data = response.json()
        assert "openai-key" in data["detail"].lower() or "openai" in data["detail"].lower()

    def test_model_b_config_is_independent(self, app):
        """Model B uses its own config, not Model A's."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"
        # Model B has no config
        main.CONFIG_DATA["model_b_provider"] = None
        main.CONFIG_DATA["model_b_model"] = None

        # Model A should work
        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            resp_a = app.get("/live_prediction/0?role=model_a")
            assert resp_a.status_code == 200

        # Model B should fail (not configured)
        resp_b = app.get("/live_prediction/0?role=model_b")
        assert resp_b.status_code == 400


class TestLivePredictionHappyPath:
    """Tests for successful live predictions."""

    def test_model_a_returns_predictions(self, app):
        """Fully configured model_a returns triplet list."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            response = app.get("/live_prediction/0?role=model_a")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["aspect_term"] == "Manzara"
            assert data[0]["aspect_category"] == "AMBIENCE#GENERAL"
            assert data[1]["aspect_term"] == "servis"

    def test_model_b_returns_predictions(self, app):
        """Fully configured model_b returns triplet list (independent of Model A)."""
        import main
        main.CONFIG_DATA["model_b_provider"] = "ollama"
        main.CONFIG_DATA["model_b_model"] = "gemma3:4b"

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            response = app.get("/live_prediction/0?role=model_b")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

    def test_empty_predictions_returns_empty_list(self, app):
        """When the provider returns empty aspects, endpoint returns []."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = ({"aspects": []}, [])
            mock_get.return_value = mock_provider

            response = app.get("/live_prediction/0?role=model_a")
            assert response.status_code == 200
            assert response.json() == []


class TestLivePredictionConfigPropagation:
    """Tests that per-model config is correctly passed to the provider."""

    def test_calls_provider_with_temperature(self, app):
        """The configured temperature is passed to provider.predict()."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"
        main.CONFIG_DATA["model_a_temperature"] = 1.5

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            app.get("/live_prediction/0?role=model_a")

            # Verify temperature was passed
            call_kwargs = mock_provider.predict.call_args.kwargs
            assert call_kwargs.get("temperature") == 1.5

    def test_calls_provider_with_custom_prompt(self, app):
        """A custom per-model prompt is passed to provider.predict()."""
        import main
        custom_prompt = "Custom labeling prompt for Model A: {text}"
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"
        main.CONFIG_DATA["model_a_prompt"] = custom_prompt

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            app.get("/live_prediction/0?role=model_a")

            call_kwargs = mock_provider.predict.call_args.kwargs
            assert call_kwargs.get("prompt_template") == custom_prompt

    def test_calls_provider_with_default_temperature(self, app):
        """Default temperature (0.7) is used when none is configured."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"
        # Deliberately not setting model_a_temperature

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            app.get("/live_prediction/0?role=model_a")

            call_kwargs = mock_provider.predict.call_args.kwargs
            assert call_kwargs.get("temperature") == 0.7

    def test_calls_provider_with_correct_model_name(self, app):
        """The per-model model name is passed as llm_model."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "deepseek-v4-flash"

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_RESULT, [])
            mock_get.return_value = mock_provider

            app.get("/live_prediction/0?role=model_a")

            call_kwargs = mock_provider.predict.call_args.kwargs
            assert call_kwargs.get("llm_model") == "deepseek-v4-flash"


class TestLivePredictionPositionData:
    """Tests for position data inclusion."""

    def test_adds_position_data_when_enabled(self, app):
        """When save_phrase_positions is True, predictions get at_start/at_end."""
        import main
        main.CONFIG_DATA["model_a_provider"] = "ollama"
        main.CONFIG_DATA["model_a_model"] = "gemma3:4b"

        with patch("services.llm_providers.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.predict.return_value = (MOCK_PREDICTION_WITH_POSITIONS, [])
            mock_get.return_value = mock_provider

            response = app.get("/live_prediction/0?role=model_a")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            aspect = data[0]
            # "Manzara" starts at position 0 in "Manzara şahane ama servis rezalet"
            assert aspect["at_start"] == 0
            assert aspect["at_end"] == 6
            assert "at_start" in aspect
            assert "at_end" in aspect
