"""Data I/O and parsing for AnnoABSA."""
import os
import json
import ast
import pandas as pd
from fastapi import HTTPException
import app.config as cfg


def load_data():
    """Load data from CSV or JSON file with UTF-8 encoding."""
    if cfg.DATA_FILE_TYPE == "json":
        with open(cfg.DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return pd.read_csv(cfg.DATA_FILE_PATH, encoding='utf-8')


def save_data(data):
    """Save data to CSV or JSON file with UTF-8 encoding."""
    if cfg.DATA_FILE_TYPE == "json":
        with open(cfg.DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        df.to_csv(cfg.DATA_FILE_PATH, index=False, encoding='utf-8')


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


# ---------------------------------------------------------------------------
# NEWUI 4-way comparison constants and parsers (Phase 7.1)
# ---------------------------------------------------------------------------
NEWUI_COLUMNS = {
    "gt": {"label_col": "original_label", "prefix": "gt"},
    "gm": {"label_col": "gemma4_31b_label", "prefix": "gm"},
    "qw": {"label_col": "qwen3.6_35b_label", "prefix": "qw"},
    "gpt": {"label_col": "gpt_oss_120b_label", "prefix": "gpt"},
}


def _detect_newui_columns(df: pd.DataFrame) -> bool:
    """Check if the DataFrame has NEWUI 4-way comparison columns.

    Returns True if all four model label columns exist in the DataFrame.
    """
    required_cols = {v["label_col"] for v in NEWUI_COLUMNS.values()}
    return required_cols.issubset(set(df.columns))


def _load_4way_row(row: pd.Series, row_dict: dict) -> dict | None:
    """Parse a single CSV row with NEWUI 4-way comparison columns.

    Detects columns: original_label, gemma4_31b_label, qwen3.6_35b_label,
    gpt_oss_120b_label and parses each through ``parse_triplet_column()``.

    Also extracts metadata fields: majority_vote (int),
    majority_label (list), consensus_intersection (list),
    original_llm_diff (string).

    Returns None if the row does not have the required NEWUI columns
    (safe to call on any CSV row — it will short-circuit fast).

    Returns:
        dict with keys: gt_triplets, gemma_triplets, qwen_triplets,
        gpt_triplets, majority_vote, majority_label,
        consensus_intersection, original_llm_diff
        or None if NEWUI columns are absent.
    """
    # Quick check: do the label columns exist in this row?
    label_cols = {v["label_col"] for v in NEWUI_COLUMNS.values()}
    if not label_cols.issubset(set(row_dict.keys())):
        return None

    result = {}

    # Parse each model's triplets through the existing parser
    result["gt_triplets"] = parse_triplet_column(
        row_dict.get("original_label"), prefix="gt")
    result["gemma_triplets"] = parse_triplet_column(
        row_dict.get("gemma4_31b_label"), prefix="gm")
    result["qwen_triplets"] = parse_triplet_column(
        row_dict.get("qwen3.6_35b_label"), prefix="qw")
    result["gpt_triplets"] = parse_triplet_column(
        row_dict.get("gpt_oss_120b_label"), prefix="gpt")

    # Parse metadata fields
    raw_mv = row_dict.get("majority_vote", "")
    if raw_mv not in (None, "", "nan", "None"):
        try:
            result["majority_vote"] = int(raw_mv)
        except (ValueError, TypeError):
            result["majority_vote"] = 0
    else:
        result["majority_vote"] = 0

    def _parse_list_field(raw):
        if raw is None or str(raw).strip() in ("", "nan", "None"):
            return []
        try:
            return ast.literal_eval(str(raw))
        except Exception:
            return []

    def _tuples_to_triplets(raw_items, prefix: str) -> list[dict]:
        """Convert raw tuple/list items from CSV into TripletItem dicts with unique IDs.
        Handles: [('term', 'CAT', 'pol'), ...] or [{'aspect_category': ...}, ...]
        """
        result = []
        for i, item in enumerate(raw_items):
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                result.append({
                    "id": f"{prefix}_{i}",
                    "aspect_term": str(item[0]) if item[0] else "NULL",
                    "aspect_category": str(item[1]),
                    "sentiment_polarity": str(item[2]).lower(),
                })
            elif isinstance(item, dict):
                result.append({
                    "id": f"{prefix}_{i}",
                    "aspect_term": str(item.get("aspect_term", item.get("term", ""))) or "NULL",
                    "aspect_category": str(item.get("aspect_category", item.get("category", ""))),
                    "sentiment_polarity": str(item.get("sentiment_polarity", item.get("polarity", ""))).lower(),
                })
        return result

    result["majority_label"] = _tuples_to_triplets(
        _parse_list_field(row_dict.get("majority_label")), "ml")
    result["consensus_intersection"] = _tuples_to_triplets(
        _parse_list_field(row_dict.get("consensus_intersection")), "ci")

    raw_diff = row_dict.get("original_llm_diff", "")
    result["original_llm_diff"] = "" if str(raw_diff) in (
        "nan", "None", "") else str(raw_diff)

    return result


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
            status_code=404, detail=f"{cfg.DATA_FILE_PATH} not found")
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
        if cfg.DATA_FILE_TYPE == "json":
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
            status_code=404, detail=f"{cfg.DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
