# PLAN-01-Backend-Data-Loading — Execution Summary

## Objective

Add NEWUI 4-way CSV parsing to `app/data.py`, extend `GET /data/{idx}` in `app/routes/reviews.py`, verify config/schema compatibility, and run backend tests.

## Files Modified

### `app/data.py` — NEWUI 4-way CSV parsing (3 new constructs)

| Symbol | Type | Description |
|--------|------|-------------|
| `NEWUI_COLUMNS` | `dict` | Constants mapping short prefixes (`gt`, `gm`, `qw`, `gpt`) to CSV column names (`original_label`, `gemma4_31b_label`, `qwen3.6_35b_label`, `gpt_oss_120b_label`) and triplet ID prefixes |
| `_detect_newui_columns(df)` | `function` | Returns `True` if all four NEWUI label columns exist in the DataFrame |
| `_load_4way_row(row, row_dict)` | `function` | Parses a single CSV row with NEWUI columns. Delegates triplet parsing to existing `parse_triplet_column()` with unique prefixes (`gt_`, `gm_`, `qw_`, `gpt_`). Also extracts `majority_vote` (int), `majority_label` (list), `consensus_intersection` (list), `original_llm_diff` (string). Returns `None` if the row lacks NEWUI columns (safe to call on any CSV row). |

**Key constraints honored:**
- `_load_comparison_csv()` is NOT modified — only new functions added after line 124
- All parsing goes through existing `parse_triplet_column()`

### `app/routes/reviews.py` — GET /data/{idx} extended

- **Import**: Added `_load_4way_row` to the `app.data` import line
- **Initialization**: `newui_data = None` initialized before the JSON/CSV branch
- **Detection**: After the `comp_b_path` block, calls `_load_4way_row(row, row_dict)` for CSV rows
- **Response**: Built as a dict variable, then conditionally adds 8 NEWUI fields when `newui_data is not None`:
  - `gt_triplets`, `gemma_triplets`, `qwen_triplets`, `gpt_triplets`
  - `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff`
- **Backward compat**: Existing `model_a_triplets`/`model_b_triplets` remain untouched; JSON path unchanged

### Config & Schema Verification

| Check | Result |
|-------|--------|
| PATCH `/settings` accepts `compare_mode='4way'` | ✅ Already accepted — endpoint `update_settings(updates: dict)` merges any key-value pairs with no validation |
| `SaveTripletsRequest` schema compatibility | ✅ Schema stores whatever triplets the frontend sends — no changes needed |
| Backend tests | ✅ **128 passed**, 0 failed (3 deprecation warnings only) |
| Python import syntax | ✅ Both `app.data` and `app.routes.reviews` import cleanly |

## Notes

- The `agent_initial_reasoning` calculation needs `row_dict` after the else block — line 76 references `row_dict.get("reasoning", ...)`. This only has `row_dict` in scope for the CSV (non-JSON) path, matching the original behavior.
- NEWUI fields are **only** populated for CSV rows with the four label columns. JSON rows and regular CSVs get the exact same response as before.
