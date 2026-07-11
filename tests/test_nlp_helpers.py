"""Tests for services/nlp_helpers.py — handler logic without model loading.

Each test mocks the lazy-loaded model/analyzer so tests run
instantly without any model files downloaded.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


# ── lexicon_polarity ──────────────────────────────────────────────────

@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_single_word(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {"güzel": ("positive", 1.0)}
    result = lexicon_polarity("güzel")
    assert result["aggregate"] == "positive"
    assert result["words"][0]["word"] == "güzel"
    assert result["words"][0]["polarity"] == "positive"


@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_multi_word(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {
        "güzel": ("positive", 1.0),
        "kötü": ("negative", 1.0),
    }
    result = lexicon_polarity("güzel kötü")
    assert len(result["words"]) == 2
    assert result["aggregate"] in ("positive", "negative")


@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_unknown(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {}
    result = lexicon_polarity("xyzzy")
    assert result["words"][0]["polarity"] == "unknown"
    assert result["aggregate"] == "neutral"


@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_punctuation(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    mock_get_lexicon.return_value = {"güzel": ("positive", 1.0)}
    result = lexicon_polarity("güzel!")
    assert result["words"][0]["word"] == "güzel"
    assert result["words"][0]["polarity"] == "positive"


@patch("services.nlp_helpers.get_lexicon")
def test_lexicon_polarity_empty(mock_get_lexicon):
    from services.nlp_helpers import lexicon_polarity
    result = lexicon_polarity("")
    assert result["words"] == []
    assert result["aggregate"] == "neutral"


# ── sentiment_classify ────────────────────────────────────────────────

@patch("services.nlp_helpers.get_sentiment_classifier")
def test_sentiment_classify_positive(mock_get_classifier):
    from services.nlp_helpers import sentiment_classify
    mock_clf = MagicMock()
    mock_clf.return_value = [{"label": "POSITIVE", "score": 0.98}]
    mock_get_classifier.return_value = mock_clf
    result = sentiment_classify("Harika bir yemek")
    assert result["label"] == "positive"
    assert result["score"] == 0.98


@patch("services.nlp_helpers.get_sentiment_classifier")
def test_sentiment_classify_negative(mock_get_classifier):
    from services.nlp_helpers import sentiment_classify
    mock_clf = MagicMock()
    mock_clf.return_value = [{"label": "NEGATIVE", "score": 0.95}]
    mock_get_classifier.return_value = mock_clf
    result = sentiment_classify("Berbat servis")
    assert result["label"] == "negative"


# ── morphology ────────────────────────────────────────────────────────

def _make_mock_parse(root="güzel", igs=None, pos="ADJ"):
    """Helper: create a mock FsmParse."""
    mock = MagicMock()
    mock.getWord.return_value = root
    igs = igs or ["ADJ"]
    mock.size.return_value = len(igs)
    mock.getInflectionalGroup.side_effect = lambda i: MagicMock(
        __str__=lambda self: igs[i]
    )
    return mock


@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_single_parse(mock_get_analyzer):
    from services.nlp_helpers import morphology
    mock_analyzer = MagicMock()
    mock_parse = _make_mock_parse(root="güzel", igs=["ADJ"], pos="ADJ")
    mock_parse_list = MagicMock()
    mock_parse_list.size.return_value = 1
    mock_parse_list.getFsmParse.return_value = mock_parse
    mock_analyzer.morphologicalAnalysis.return_value = mock_parse_list
    mock_get_analyzer.return_value = mock_analyzer

    result = morphology("güzel")
    assert result["word"] == "güzel"
    assert len(result["parses"]) == 1
    assert result["parses"][0]["root"] == "güzel"


@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_empty_word(mock_get_analyzer):
    from services.nlp_helpers import morphology
    mock_analyzer = MagicMock()
    mock_parse_list = MagicMock()
    mock_parse_list.size.return_value = 0
    mock_analyzer.morphologicalAnalysis.return_value = mock_parse_list
    mock_get_analyzer.return_value = mock_analyzer

    result = morphology("")
    assert result["word"] == ""
    assert result["parses"] == []


# ── embedding_similarity ──────────────────────────────────────────────

@patch("services.nlp_helpers.get_embedding_model")
def test_embedding_similarity_identical(mock_get_model):
    from services.nlp_helpers import embedding_similarity
    mock_model = MagicMock()
    mock_model.encode.side_effect = [
        np.array([1.0, 0.0]),
        np.array([1.0, 0.0]),
    ]
    mock_get_model.return_value = mock_model
    result = embedding_similarity("lezzetli", "lezzetli yemek")
    assert result["similarity"] == 1.0
    assert result["selection_length"] == 8


@patch("services.nlp_helpers.get_embedding_model")
def test_embedding_similarity_orthogonal(mock_get_model):
    from services.nlp_helpers import embedding_similarity
    mock_model = MagicMock()
    mock_model.encode.side_effect = [
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
    ]
    mock_get_model.return_value = mock_model
    result = embedding_similarity("a", "b")
    assert result["similarity"] == 0.0


# ── Error handling ────────────────────────────────────────────────────

@patch("services.nlp_helpers.get_morphological_analyzer")
def test_morphology_analyzer_error(mock_get_analyzer):
    from services.nlp_helpers import morphology
    mock_get_analyzer.side_effect = RuntimeError("Model not found")
    with pytest.raises(RuntimeError):
        morphology("test")
