"""STD format conversion utilities for AnnoABSA CLI."""

import json
import ast


def std_triplets_to_label(raw_triplet_str: str) -> list:
    """Convert STD format triplet string to internal label list of dicts.

    STD format: Python list-literal string with single quotes, e.g.
    \"[['NULL', 'course general', 'positive']]\"
    Returns: list of dicts with keys aspect_term, aspect_category,
             sentiment_polarity, opinion_term (empty string).
    Empty or unparseable input returns [] and logs a warning.
    """
    if raw_triplet_str is None or str(raw_triplet_str).strip() in ["", "nan", "None", "[]"]:
        return []
    try:
        parsed = ast.literal_eval(str(raw_triplet_str))
        res = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    res.append({
                        "aspect_term": str(item[0]) if item[0] else "NULL",
                        "aspect_category": str(item[1]),
                        "sentiment_polarity": str(item[2]).lower(),
                        "opinion_term": ""
                    })
        return res
    except Exception as e:
        print(f"Warning: Could not parse STD triplet string: {e}")
        return []
