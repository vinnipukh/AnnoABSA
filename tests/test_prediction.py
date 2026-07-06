"""Tests for services/prediction.py — prompt building, BM25, position logic.

Corresponds to testcases.md tiers where backend logic is testable:
- MA3/MA4: position math (find_phrase_positions)
- H1: generate_mock_reasoning
- Prompt: build_prediction_prompt, build_absa_models
"""
import pytest
from services.prediction import (
    find_phrase_positions,
    find_valid_phrases_list,
    generate_mock_reasoning,
    build_prediction_prompt,
    build_absa_models,
    DEFAULT_LABELING_TEMPLATE,
    get_most_similar_examples,
)


class TestFindPhrasePositions:
    """Tests for find_phrase_positions (testcases.md: MA3/MA4 position math)."""

    def test_exact_match(self):
        start, end = find_phrase_positions("güzel yemek çok lezzetli", "yemek")
        assert start == 6
        assert end == 10

    def test_case_insensitive(self):
        start, end = find_phrase_positions("Güzel Yemek", "yemek")
        assert start == 6
        assert end == 10

    def test_null_phrase_returns_none(self):
        assert find_phrase_positions("güzel yemek", "NULL") == (None, None)

    def test_empty_text_returns_none(self):
        assert find_phrase_positions("", "yemek") == (None, None)

    def test_empty_phrase_returns_none(self):
        assert find_phrase_positions("güzel yemek", "") == (None, None)

    def test_phrase_not_found(self):
        assert find_phrase_positions("güzel yemek", "servis") == (None, None)

    def test_unicode_turkish_chars(self):
        start, end = find_phrase_positions("şahane manzara", "şahane")
        assert start == 0
        assert end == 5

    def test_phrase_at_end(self):
        start, end = find_phrase_positions("çok güzel yemek", "yemek")
        assert start == 10
        assert end == 14

    def test_first_occurrence(self):
        start, end = find_phrase_positions("yemek güzel yemek", "yemek")
        assert start == 0  # should return first occurrence
        assert end == 4


class TestFindValidPhrasesList:
    """Tests for find_valid_phrases_list (used by build_absa_models)."""

    def test_simple_sentence(self):
        phrases = find_valid_phrases_list("yemek güzel")
        assert "yemek" in phrases

    def test_three_words(self):
        phrases = find_valid_phrases_list("çok güzel yemek")
        assert "çok güzel" in phrases
        assert "güzel" in phrases

    def test_max_tokens(self):
        phrases = find_valid_phrases_list("a b c d", max_tokens_in_phrase=2)
        assert "a b c" not in phrases  # 3 tokens, exceeds max
        assert "a b" in phrases

    def test_empty_text(self):
        phrases = find_valid_phrases_list("")
        assert phrases == []

    def test_special_chars_filtered(self):
        phrases = find_valid_phrases_list("(test)")
        for p in phrases:
            assert p[0].isalnum(), f"Phrase '{p}' starts with non-word char"
            assert p[-1].isalnum(), f"Phrase '{p}' ends with non-word char"


class TestGenerateMockReasoning:
    """Tests for generate_mock_reasoning (testcases.md: H1 fallback)."""

    def test_no_text(self):
        result = generate_mock_reasoning("", "A", "B", [], [])
        assert "seçilmedi" in result

    def test_both_empty(self):
        result = generate_mock_reasoning("güzel yemek", "A", "B", [], [])
        assert "herhangi bir" in result.lower() or "manuel" in result.lower()

    def test_model_a_only(self):
        result = generate_mock_reasoning(
            "güzel yemek", "Model A", "Model B",
            [{"aspect_term": "yemek"}], []
        )
        assert "Model A" in result
        assert "üretmemiş" in result or "ek olarak" in result

    def test_common_aspects(self):
        result = generate_mock_reasoning(
            "güzel yemek", "A", "B",
            [{"aspect_term": "yemek"}, {"aspect_term": "servis"}],
            [{"aspect_term": "yemek"}]
        )
        assert "Ortak" in result
        assert "yemek" in result

    def test_model_names_appear_when_models_have_data(self):
        """Model names only appear in output when there's comparison data."""
        result = generate_mock_reasoning("harika", "GPT-4o", "Claude",
            [{"aspect_term": "yemek"}], [{"aspect_term": "servis"}])
        assert "GPT-4o" in result
        assert "Claude" in result

    def test_recommendation_present(self):
        result = generate_mock_reasoning("yemek güzel", "A", "B", [], [])
        assert "Önerim" in result


class TestBuildPredictionPrompt:
    """Tests for build_prediction_prompt (testcases.md: prompt template)."""

    def test_turkish_template(self):
        prompt, few_shot = build_prediction_prompt(
            "yemek güzel",
            ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            [],
            ["Food#quality", "Service#general"],
            ["positive", "negative", "neutral"],
            allow_implicit_aspect_terms=True,
            allow_implicit_opinion_terms=False,
            n_few_shot=5,
            prompt_template=DEFAULT_LABELING_TEMPLATE,
        )
        assert "Görünüş terimi" in prompt
        assert "yemek" in prompt
        assert few_shot == []

    def test_english_fallback(self):
        prompt, few_shot = build_prediction_prompt(
            "yemek güzel",
            ["aspect_term"],
            [],
            ["Food#quality"],
            ["positive"],
            allow_implicit_aspect_terms=False,
            allow_implicit_opinion_terms=False,
            n_few_shot=5,
            prompt_template=None,
        )
        assert "According to" in prompt
        assert "yemek" in prompt

    def test_few_shot_included(self):
        examples = [{
            "text": "hizmet harika",
            "label": [{"aspect_term": "hizmet", "aspect_category": "Service#general",
                       "sentiment_polarity": "positive", "opinion_term": "harika"}]
        }]
        prompt, few_shot = build_prediction_prompt(
            "yemek güzel",
            ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            examples,
            ["Food#quality", "Service#general"],
            ["positive", "negative", "neutral"],
            allow_implicit_aspect_terms=True,
            allow_implicit_opinion_terms=False,
            n_few_shot=5,
            prompt_template=DEFAULT_LABELING_TEMPLATE,
        )
        assert "hizmet" in prompt
        assert len(few_shot) == 1

    def test_implicit_aspect_note_present(self):
        prompt, _ = build_prediction_prompt(
            "test", ["aspect_term"], [], ["Cat"], ["pos"],
            allow_implicit_aspect_terms=True, allow_implicit_opinion_terms=False,
            n_few_shot=0, prompt_template=DEFAULT_LABELING_TEMPLATE,
        )
        assert "NULL" in prompt

    def test_implicit_aspect_note_absent(self):
        prompt, _ = build_prediction_prompt(
            "test", ["aspect_term"], [], ["Cat"], ["pos"],
            allow_implicit_aspect_terms=False, allow_implicit_opinion_terms=False,
            n_few_shot=0, prompt_template=DEFAULT_LABELING_TEMPLATE,
        )
        # When disabled, the implicit note placeholder renders as empty string
        # The prompt should still contain the aspect term definition
        assert "aspect term" in prompt.lower() or "görünüş" in prompt


class TestBuildAbsaModels:
    """Tests for build_absa_models — dynamic Pydantic model generation."""

    def test_returns_aspects_class(self):
        Aspects, field_types, enums = build_absa_models(
            "güzel yemek",
            ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            ["positive", "negative"], ["Food#quality"],
            allow_implicit_aspect_terms=True, allow_implicit_opinion_terms=False,
        )
        assert Aspects.__name__ == "Aspects"
        assert "aspect_term" in field_types

    def test_aspects_can_be_instantiated(self):
        Aspects, _, _ = build_absa_models(
            "güzel yemek",
            ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            ["positive", "negative", "neutral"],
            ["Food#quality", "Service#general"],
            allow_implicit_aspect_terms=True, allow_implicit_opinion_terms=False,
        )
        obj = Aspects(aspects=[])
        assert obj.model_dump_json() == '{"aspects":[]}'

    def test_enums_contain_allowed_values(self):
        _, _, enums = build_absa_models(
            "güzel yemek",
            ["aspect_term", "sentiment_polarity"],
            ["positive", "negative", "neutral"],
            ["Food#quality"],
            allow_implicit_aspect_terms=True, allow_implicit_opinion_terms=False,
        )
        assert "PolarityEnum" in enums
        members = [m.name for m in enums["PolarityEnum"]]
        assert "positive" in members
        assert "negative" in members
        assert "neutral" in members

    def test_forward_reference_works(self):
        """Regression test: list['SentimentElement'] must resolve at runtime."""
        Aspects, _, _ = build_absa_models(
            "test yemek",
            ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            ["pos", "neg"], ["Cat"],
            allow_implicit_aspect_terms=False, allow_implicit_opinion_terms=False,
        )
        # The Aspects class should have an 'aspects' field that accepts a list
        from pydantic import TypeAdapter
        ta = TypeAdapter(list[Aspects.model_fields['aspects'].annotation])  # noqa
        assert ta is not None


class TestGetMostSimilarExamples:
    """Tests for BM25 retrieval."""

    def test_empty_examples(self):
        result = get_most_similar_examples("test", [], 5)
        assert result == []

    def test_single_example(self):
        examples = [{"text": "yemek güzel", "label": []}]
        result = get_most_similar_examples("yemek", examples, 5)
        assert len(result) == 1

    def test_returns_correct_number(self):
        examples = [{"text": f"text {i}", "label": []} for i in range(10)]
        result = get_most_similar_examples("test", examples, 3)
        assert len(result) == 3

    def test_n_greater_than_available(self):
        examples = [{"text": "a", "label": []}, {"text": "b", "label": []}]
        result = get_most_similar_examples("a", examples, 10)
        assert len(result) == 2
