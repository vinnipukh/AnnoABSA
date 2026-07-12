"""Data I/O and parsing for AnnoABSA."""
import os
import json
import ast
import pandas as pd
from fastapi import HTTPException
from app.config import DATA_FILE_PATH, DATA_FILE_TYPE


def load_data():
    """Load data from CSV or JSON file with UTF-8 encoding."""
    if DATA_FILE_TYPE == "json":
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return pd.read_csv(DATA_FILE_PATH, encoding='utf-8')


def save_data(data):
    """Save data to CSV or JSON file with UTF-8 encoding."""
    if DATA_FILE_TYPE == "json":
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        if isinstance(data, list):
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(data)
        else:
            df = data
        df.to_csv(DATA_FILE_PATH, index=False, encoding='utf-8')


def parse_triplet_column(raw_val, prefix="t"):
    """Parse a Python list-literal string into a list of triplet dicts.

    Handles multiple input formats:
    - STD tuples: ``[('term', 'CATEGORY', 'polarity'), ...]``
    - STD lists: ``[['term', 'CATEGORY', 'polarity'], ...]``
    - Dict format: ``[{'aspect_term': ..., 'aspect_category': ..., 'sentiment_polarity': ...}, ...]``
    - Empty values: ``None``, ``"nan"``, ``"None"``, ``"[]"``, ``""``

    Used by:
    - get_data() to parse inline comparison columns (aspect_triplets / new_triplets)
    - _load_comparison_csv() to parse STD-format comparison CSVs

    Args:
        raw_val: Raw cell value from a CSV (string, NaN, or None).
        prefix: Prefix for generated triplet IDs (e.g. 'ma' for Model A, 'mb' for Model B).

    Returns:
        List of dicts with keys: id, aspect_term, aspect_category, sentiment_polarity.
    """
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
    except Exception as e:
        print("Parse error:", e)
        return []


def _load_comparison_csv(csv_path: str, data_idx: int, review_text: str, prefix: str) -> list:
    """Load triplets from a comparison CSV, auto-detecting format.

    Supports:
    - STD format (columns: review, triplet) — matched by review text
    - Per-row format (columns: review_id, aspect_term, aspect_category, sentiment_polarity) — matched by index
    """
    if not csv_path or not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except Exception as e:
        print(f"Warning: Could not read comparison CSV '{csv_path}': {e}")
        return []

    # Auto-detect: STD format has 'review' and 'triplet' columns
    if 'review' in df.columns and 'triplet' in df.columns:
        # STD format — match by review text
        match = df[df['review'] == review_text]
        results = []
        for i, (_, r) in enumerate(match.iterrows()):
            triplets = parse_triplet_column(r.get('triplet'), prefix=f"{prefix}_{i}")
            results.extend(triplets)
        return results
    else:
        # Per-row format — match by review_id index
        if 'review_id' in df.columns:
            match = df[df['review_id'] == data_idx]
        else:
            return []
        results = []
        for i, (_, r) in enumerate(match.iterrows()):
            results.append({
                "id": f"{prefix}_{i}",
                "aspect_term": str(r.get("aspect_term", "")),
                "aspect_category": str(r.get("aspect_category", "")),
                "sentiment_polarity": str(r.get("sentiment_polarity", ""))
            })
        return results


def get_total_count():
    """Return the total number of data items (reviews) in the current dataset.

    Returns:
        Total row/item count (int).

    Raises HTTPException (500) on read errors, (404) if file missing.
    """
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_current_index():
    """Find the index of the first unannotated data item.

    For JSON: returns the first entry without a 'label' key.
    For CSV: returns the first row whose label column is empty/NaN.
    If all items are annotated, returns len(data) (the count, not a valid index).

    Used by:
    - get_settings() to report current_index to the frontend
    - The frontend to decide which row to display on initial load

    Returns:
        int: Index of the first unannotated item, or total count if all done.
    """
    try:
        data = load_data()
        if DATA_FILE_TYPE == "json":
            # Find first entry that doesn't have a "label" key (not annotated yet)
            for idx, item in enumerate(data):
                if 'label' not in item:
                    return idx
            return len(data)  # All entries have been annotated
        else:
            # CSV handling
            df = data
            for idx in range(len(df)):
                if pd.isna(df.iloc[idx]['label']) or df.iloc[idx]['label'] == "":
                    return idx
            return len(df)
    except FileNotFoundError:
        return 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def max_number_of_idxs():
    """Return the total number of data items (alias for get_total_count).

    Returns the maximum valid index + 1. Used by the frontend for pagination.

    Returns:
        int: Total number of data items.
    """
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
