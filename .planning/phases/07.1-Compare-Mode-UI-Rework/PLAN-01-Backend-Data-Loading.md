---
wave: 1
depends_on: []
files_modified:
  - app/data.py
  - app/routes/reviews.py
  - app/config.py
  - models/schemas.py
autonomous: true
requirements:
  - NEWUI-02: Ingest semeval_tr_llm_annotated.csv with specified columns
  - NEWUI-03: 3-tier curation workflow (Auto-Accept, Quick Diff, High-Confusion)
  - D-05: Extend existing GET /data/{idx} endpoint
  - D-06: Response fields for 4-way mode
  - D-08: Old CSV compare preserved
---

# Plan 1: Backend — NEWUI Data Loading

**Phase:** 07.1-Compare-Mode-UI-Rework  
**Plan:** 1/5 — Backend NEWUI CSV detection, parsing, and API extension  
**Status:** Planned

---

## Overview

Extend the backend to detect and parse the NEWUI CSV format (`semeval_tr_llm_annotated.csv`), exposing 4-way comparison data through the existing `GET /data/{idx}` endpoint alongside backward-compatible standard/CSV fields.

The key architectural decision (D-05, D-06) is to extend the **existing endpoint** rather than creating a new one — the frontend will detect 4-way mode from the presence of `gt_triplets` in the response.

---

## must_haves

1. Auto-detect NEWUI columns (`original_label`, `gemma4_31b_label`, `qwen3.6_35b_label`, `gpt_oss_120b_label`, `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff`)
2. Parse all 4 model triplet columns into `TripletItem[]` format using existing `parse_triplet_column()`
3. Add `gt_triplets`, `gemma_triplets`, `qwen_triplets`, `gpt_triplets`, `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff` to API response
4. Set `model_a_name`/`model_b_name` defaults for 4-way mode
5. Backward compatible — standard CSV (no NEWUI columns) returns existing response shape unchanged
6. Support `compare_mode='4way'` config key, default to `'csv'` for existing installs
7. Update `SaveTripletsRequest` schema if needed for 4-way save metadata

---

## Tasks

### Task 1.1: Add `_load_4way_csv()` parser to `app/data.py`

<read_first>
Read `app/data.py` lines 32-123 (parse_triplet_column and _load_comparison_csv). The existing parser handles Python list-literal strings from STD format and per-row CSV. The NEWUI format has triplet strings in each cell that need the same parsing, but mapped to named columns.
</read_first>

<acceptance_criteria>
- [ ] New function `_load_4way_csv()` or equivalent logic that:
  - Accepts a pandas DataFrame row (or dict)
  - Detects NEWUI columns by checking for `original_label` column presence
  - Parses `original_label` → `gt_triplets` via `parse_triplet_column(raw_val, prefix="gt")`
  - Parses `gemma4_31b_label` → `gemma_triplets` via `parse_triplet_column(raw_val, prefix="gm")`
  - Parses `qwen3.6_35b_label` → `qwen_triplets` via `parse_triplet_column(raw_val, prefix="qw")`
  - Parses `gpt_oss_120b_label` → `gpt_triplets` via `parse_triplet_column(raw_val, prefix="gpt")`
  - Returns raw values for `majority_vote` (int), `majority_label` (list or string), `consensus_intersection` (list or string), `original_llm_diff` (string)
  - Returns `None` or empty structure if NEWUI columns absent
- [ ] All triplet IDs use unique prefixes (`gt_`, `gm_`, `qw_`, `gpt_`) to avoid collision
- [ ] Existing `_load_comparison_csv()` is **not modified** — no regression risk
</acceptance_criteria>

<action>
1. Add to `app/data.py` after line 123 (after `_load_comparison_csv`), before `get_total_count`:

```python
NEWUI_COLUMNS = {
    "gt": "original_label",
    "gemma": "gemma4_31b_label",
    "qwen": "qwen3.6_35b_label",
    "gpt": "gpt_oss_120b_label",
}

def _detect_newui_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has NEWUI columns."""
    return "original_label" in df.columns


def _load_4way_row(row: pd.Series, row_dict: dict) -> dict | None:
    """Parse a single row in NEWUI format into 4-way comparison data.
    
    Returns None if NEWUI columns are not present (backward compat).
    """
    if "original_label" not in row_dict:
        return None
    
    result = {}
    result["gt_triplets"] = parse_triplet_column(row_dict.get("original_label"), prefix="gt")
    result["gemma_triplets"] = parse_triplet_column(row_dict.get("gemma4_31b_label"), prefix="gm")
    result["qwen_triplets"] = parse_triplet_column(row_dict.get("qwen3.6_35b_label"), prefix="qw")
    result["gpt_triplets"] = parse_triplet_column(row_dict.get("gpt_oss_120b_label"), prefix="gpt")
    
    # Metadata fields
    raw_vote = row_dict.get("majority_vote", "")
    result["majority_vote"] = int(raw_vote) if str(raw_vote).isdigit() else 0
    result["majority_label"] = parse_triplet_column(row_dict.get("majority_label"), prefix="mj")
    result["consensus_intersection"] = parse_triplet_column(row_dict.get("consensus_intersection"), prefix="ci")
    result["original_llm_diff"] = str(row_dict.get("original_llm_diff", ""))
    
    return result
```
</action>

---

### Task 1.2: Extend `GET /data/{idx}` in `app/routes/reviews.py`

<read_first>
Read `app/routes/reviews.py` lines 13-94 (get_data function). Focus on the CSV branch (lines 47-70) where comparison CSVs are loaded. The NEWUI columns exist in the **primary data CSV**, not in separate comparison files.
</read_first>

<acceptance_criteria>
- [ ] After the existing `comp_a_path`/`comp_b_path` block (line 66-70), add NEWUI detection:
  ```python
  # NEWUI 4-way detection
  newui_data = None
  if DATA_FILE_TYPE != "json":
      newui_data = _load_4way_row(row, row_dict)
  ```
- [ ] In the response dict (lines 77-89), add NEWUI fields **conditionally**:
  ```python
  result = {
      "id": data_idx,
      "text": text_val,
      "review_text": text_val,
      "label": label_val,
      "translation": translation_val,
      "aspect_category_list": aspects_val,
      "model_a_triplets": model_a_triplets,
      "model_b_triplets": model_b_triplets,
      "model_a_name": model_a_name,
      "model_b_name": model_b_name,
      "agent_initial_reasoning": agent_initial_reasoning,
  }
  if newui_data:
      result["gt_triplets"] = newui_data["gt_triplets"]
      result["gemma_triplets"] = newui_data["gemma_triplets"]
      result["qwen_triplets"] = newui_data["qwen_triplets"]
      result["gpt_triplets"] = newui_data["gpt_triplets"]
      result["majority_vote"] = newui_data["majority_vote"]
      result["majority_label"] = newui_data["majority_label"]
      result["consensus_intersection"] = newui_data["consensus_intersection"]
      result["original_llm_diff"] = newui_data["original_llm_diff"]
      # Set meaningful model names for 4-way
      result["model_a_name"] = result.get("model_a_name", "Model A")
      result["model_b_name"] = result.get("model_b_name", "Model B")
  ```
- [ ] When NEWUI data is present, `model_a_triplets`/`model_b_triplets` are still populated from any configured comparison CSVs (D-08: old CSV compare preserved)
- [ ] When NEWUI data is absent, response shape is **identical** to current behavior
- [ ] Import `_load_4way_row` from `app.data` at top of file (add to existing imports)
</acceptance_criteria>

<action>
1. Edit `app/routes/reviews.py`:
   - Add `_load_4way_row` to the import from `app.data` (line 4)
   - After line 70 (comp_b_path block), add the NEWUI detection block
   - Modify the return dict (lines 77-89) to conditionally include NEWUI fields
2. No changes needed to JSON branch — NEWUI is CSV-only per NEWUI-02
</action>

---

### Task 1.3: Support `compare_mode='4way'` in config

<read_first>
Read `app/config.py` lines 60-107 (load_config defaults). The `compare_mode` key at line 92 currently defaults to `"csv"`.
</read_first>

<acceptance_criteria>
- [ ] `compare_mode` default remains `"csv"` for backward compat
- [ ] Backend handles `'4way'` value without error (validation pass-through)
- [ ] Config can be set via PATCH /settings or CLI flags (no new validation rules needed — just string comparison)
</acceptance_criteria>

<action>
1. No code changes to `app/config.py` for the default — the existing `CONFIG_DATA` dict already handles arbitrary string keys
2. The frontend will set `compare_mode: '4way'` via settings PATCH; backend passes it through
3. Add a comment noting `'4way'` is a valid value for documentation
</action>

---

### Task 1.4: Update schemas for 4-way save (minimal)

<read_first>
Read `models/schemas.py` lines 1-16. The SaveTripletsRequest has `triplets: list` and optional `review_text`.
</read_first>

<acceptance_criteria>
- [ ] `SaveTripletsRequest` remains unchanged — the save endpoint just stores the approved triplet list regardless of source
- [ ] Optional: add a `source: str | None = None` field if the frontend wants to tag which column was the source (not critical for MVP — can be deferred)
</acceptance_criteria>

<action>
1. No schema changes required for MVP. The existing save flow:
   - Frontend collects approved triplets from all sources into a single list
   - POSTs to `/review/{idx}/save` with `{ triplets: [...] }`
   - Backend stores as-is
2. This works for 4-way mode unchanged — the resolution panel's accept/edit/manual actions all produce `TripletItem[]` lists
</action>

---

## Artifacts This Plan Produces

1. **`app/data.py`** — New `_load_4way_row()` function and `_detect_newui_columns()` helper
2. **`app/routes/reviews.py`** — Extended `GET /data/{idx}` with conditional NEWUI fields
3. **No new files** — existing endpoints extended

---

## Verification

1. ✅ Load a standard CSV (no NEWUI columns) → response shape identical to before
2. ✅ Load a NEWUI CSV with all 8 columns → response includes all new fields
3. ✅ `majority_vote` is integer (3, 2, or 1)
4. ✅ `gt_triplets`/`gemma_triplets`/`qwen_triplets`/`gpt_triplets` are `TripletItem[]` with unique IDs
5. ✅ `model_a_triplets`/`model_b_triplets` still populated from comparison CSVs when configured
6. ✅ `compare_mode='4way'` accepted by config without error

---

## PLANNING COMPLETE
