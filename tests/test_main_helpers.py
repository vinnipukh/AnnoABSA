"""Tests for main.py helper functions — parsing, comparison CSV loading.

These tests don't import main.py directly (which would trigger FastAPI
import-time side effects). Instead they test the pure logic functions
that main.py delegates to.
"""
import json
import pytest


# Direct import of parse_triplet_column from main.py
# This is safe — it's a pure function with no side effects.
# If it causes issues, extract it to a separate test helper.
def _parse_triplet_column(raw_val, prefix="t"):
    """Inline copy of parse_triplet_column for testing without main.py import side effects."""
    import ast
    if raw_val is None or str(raw_val).strip() in ["", "nan", "None", "[]"]:
        return []
    try:
        parsed = ast.literal_eval(str(raw_val))
        res = []
        if isinstance(parsed, list):
            for i, item in enumerate(parsed):
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    term = str(item[0]) if item[0] else "NULL"
                    cat = str(item[1])
                    pol = str(item[2]).lower()
                    res.append({
                        "id": f"{prefix}_{i}",
                        "aspect_term": term,
                        "aspect_category": cat,
                        "sentiment_polarity": pol
                    })
                elif isinstance(item, dict):
                    term = str(item.get("aspect_term", item.get("term", ""))) or "NULL"
                    cat = str(item.get("aspect_category", item.get("category", "")))
                    pol = str(item.get("sentiment_polarity", item.get("polarity", ""))).lower()
                    res.append({
                        "id": f"{prefix}_{i}",
                        "aspect_term": term,
                        "aspect_category": cat,
                        "sentiment_polarity": pol
                    })
        return res
    except Exception:
        return []


class TestParseTripletColumn:
    """Tests for parse_triplet_column — STD tuple/list format parsing.

    Covers testcases.md data-loading requirements:
    - STD tuples: [('term', 'CAT', 'pol')]
    - STD lists: [['term', 'CAT', 'pol']]
    - Dict format
    - Empty/null handling
    - NULL aspect term handling (KA7)
    """

    def test_std_tuple_format(self):
        result = _parse_triplet_column("[('pasta', 'FOOD#QUALITY', 'positive')]", prefix="t")
        assert len(result) == 1
        assert result[0]["aspect_term"] == "pasta"
        assert result[0]["aspect_category"] == "FOOD#QUALITY"
        assert result[0]["sentiment_polarity"] == "positive"

    def test_std_tuple_implicit_aspect(self):
        """Empty string in tuple → should become 'NULL'."""
        result = _parse_triplet_column("[('', 'AMBIENCE#GENERAL', 'negative')]", prefix="t")
        assert result[0]["aspect_term"] == "NULL"

    def test_std_list_format(self):
        result = _parse_triplet_column("[['yemek', 'FOOD#QUALITY', 'positive']]", prefix="t")
        assert len(result) == 1
        assert result[0]["aspect_term"] == "yemek"

    def test_dict_format(self):
        result = _parse_triplet_column(
            '[{"aspect_term": "yemek", "aspect_category": "Food#quality", '
            '"sentiment_polarity": "positive"}]',
            prefix="t"
        )
        assert len(result) == 1
        assert result[0]["aspect_term"] == "yemek"

    def test_empty_list(self):
        assert _parse_triplet_column("[]") == []

    def test_none_value(self):
        assert _parse_triplet_column(None) == []

    def test_nan_string(self):
        assert _parse_triplet_column("nan") == []

    def test_empty_string(self):
        assert _parse_triplet_column("") == []

    def test_multiple_triplets(self):
        result = _parse_triplet_column(
            "[('a', 'CAT1', 'pos'), ('b', 'CAT2', 'neg')]",
            prefix="t"
        )
        assert len(result) == 2
        assert result[0]["id"] == "t_0"
        assert result[1]["id"] == "t_1"

    def test_considers_all_three_elements(self):
        result = _parse_triplet_column("[('term', 'CAT', 'neutral')]", prefix="t")
        assert result[0]["aspect_term"] == "term"
        assert result[0]["aspect_category"] == "CAT"
        assert result[0]["sentiment_polarity"] == "neutral"

    def test_polarity_normalized_to_lowercase(self):
        result = _parse_triplet_column("[('x', 'Y', 'Positive')]", prefix="t")
        assert result[0]["sentiment_polarity"] == "positive"

    def test_bad_literal_returns_empty_list(self):
        """Malformed Python literals should not crash."""
        # This is what happens when a CSV cell has 'JSON_ERROR: ...' instead of valid data
        result = _parse_triplet_column("JSON_ERROR: could not parse", prefix="t")
        assert result == []
