# Phase 1, Task 2 — Completion Report

**Task:** Generalize the LLM-comparison feature  
**Date:** 2026-07-02  
**Status:** ✅ Complete — 32/32 verification tests passed

---

## Summary

The two-column LLM comparison feature was hardcoded for a specific demo dataset (`semeval_deepseek_labeled.csv` / `semeval_qwen_labeled.csv`) with hardcoded JSON keys (`deepseek_triplets` / `qwen_triplets`) and hardcoded display strings ("DeepSeek" / "Qwen") end-to-end. This task generalized the entire pipeline so users can pass any two comparison CSVs with custom display names via CLI flags.

---

## Changes by file

### `cli.py` — Config fields, setters, CLI flags, wiring

- **Config defaults:** Added `compare_model_a_csv`, `compare_model_a_name`, `compare_model_b_csv`, `compare_model_b_name` (all default `None`) to `ABSAAnnotatorConfig.__init__`
- **Setter methods:** Added `set_compare_model_a_csv()`, `set_compare_model_a_name()`, `set_compare_model_b_csv()`, `set_compare_model_b_name()`
- **Argparse flags:** Added `--compare-model-a-csv`, `--compare-model-a-name` (default: `"Model A"`), `--compare-model-b-csv`, `--compare-model-b-name` (default: `"Model B"`)
- **Wiring:** All four flags pass through to the config in `main()` after argument parsing, following existing patterns

### `main.py` — Backend endpoint generalization

- **`load_config()` defaults:** Added the four comparison config fields with `None` defaults
- **`AgentChatRequest`:** Renamed `deepseek_triplets` → `model_a_triplets`, `qwen_triplets` → `model_b_triplets`
- **`generate_mock_reasoning()`:** Signature changed from `(text, ds_list, qw_list)` to `(text, model_a_name, model_b_name, model_a_list, model_b_list)`. All hardcoded "DeepSeek"/"Qwen" strings replaced with the configured model name parameters
- **`_load_comparison_csv()` (new helper):** Loads triplets from a comparison CSV with auto-detection of format:
  - **STD format** (columns: `review`, `triplet`): matched by review text, parsed via `parse_triplet_column`
  - **Per-row format** (columns: `review_id`, `aspect_term`, `aspect_category`, `sentiment_polarity`): matched by numeric index
- **`get_data()`:** Replaced hardcoded sibling-file fallback (`semeval_deepseek_labeled.csv` / `semeval_qwen_labeled.csv`) with config-driven loading via the new helper. Kept backward-compatible inline column support (`aspect_triplets` / `new_triplets`). Response now returns `model_a_triplets`, `model_b_triplets`, `model_a_name`, `model_b_name`
- **`agent_chat()`:** System prompt and fallback reply handler use config-driven `compare_model_a_name` / `compare_model_b_name` instead of hardcoded "DeepSeek"/"Qwen"

### `frontend/src/types.ts` — Interface field rename

- `deepseek_triplets: TripletItem[]` → `model_a_triplets: TripletItem[]`
- `qwen_triplets: TripletItem[]` → `model_b_triplets: TripletItem[]`
- Added optional `model_a_name?: string` and `model_b_name?: string` for dynamic column titles

### `frontend/src/App.tsx` — Full rename and dynamic rendering

- **FALLBACK_DATA:** All `deepseek_triplets`/`qwen_triplets` keys renamed, hardcoded model names in `agent_initial_reasoning` text replaced with generic references
- **State:** `selectedDeepseekIds` → `selectedModelAIds`, `selectedQwenIds` → `selectedModelBIds`
- **Handlers:** All `Deepseek`/`Qwen` function names renamed (`toggleModelA`/`toggleModelB`, `selectAllModelA`/`selectAllModelB`, `clearAllModelA`/`clearAllModelB`)
- **Chat request body:** Sends `model_a_triplets`/`model_b_triplets` instead of `deepseek_triplets`/`qwen_triplets`
- **JSX:** Column titles dynamically computed from `currentData.model_a_name` / `currentData.model_b_name` (displays as `"Model A - {name}"`). Empty subtitles. Badge text from config name or fallback `"MODEL A"`/`"MODEL B"`

### `examples/semeval_absa.json` — Example data updated

- All `deepseek_triplets` keys → `model_a_triplets`
- All `qwen_triplets` keys → `model_b_triplets`

---

## Verification (32/32 tests passed)

| Scenario | Result |
|---|---|
| **No comparison CSVs** — returns empty `model_a_triplets`/`model_b_triplets`, no crash | ✓ 8 checks |
| **Two STD-format CSVs** with custom names (`AlphaModel`/`BetaModel`) — matched by review text | ✓ 10 checks |
| **Model B empty** for one review — correct handling, reasoning references configured name | ✓ 4 checks |
| **`agent_chat` endpoint** — accepts `model_a_triplets`/`model_b_triplets`, no hardcoded model names | ✓ 5 checks |
| **Per-row format CSV** — matches by `review_id` index, correct triplets and name | ✓ 3 checks |
| **Python syntax** — both `main.py` and `cli.py` compile cleanly | ✓ 2 checks |

---

## Usage

```bash
# With two STD-format comparison CSVs:
annoabsa data.csv \
  --compare-model-a-csv outputs/gpt_labeled.csv \
  --compare-model-a-name "GPT-4o" \
  --compare-model-b-csv outputs/claude_labeled.csv \
  --compare-model-b-name "Claude 3.5"

# With per-row format CSVs (review_id, aspect_term, aspect_category, sentiment_polarity):
annoabsa data.csv \
  --compare-model-a-csv outputs/model_a_results.csv \
  --compare-model-a-name "My Model"

# Via JSON config file:
annoabsa data.csv --load-config my_config.json
```

Where `my_config.json`:
```json
{
  "compare_model_a_csv": "outputs/gpt_labeled.csv",
  "compare_model_a_name": "GPT-4o",
  "compare_model_b_csv": "outputs/claude_labeled.csv",
  "compare_model_b_name": "Claude 3.5"
}
```

## Design decisions

1. **Auto-detection of comparison CSV format** — rather than a separate flag, `_load_comparison_csv()` detects STD format (columns `review`, `triplet`) vs. per-row format (column `review_id`) by inspecting the header. This is transparent to the user and matches how the frontend doesn't need to know the source format.

2. **Config CSVs override inline columns** — if both `aspect_triplets`/`new_triplets` columns exist in the data file AND external CSVs are configured, the external CSVs take precedence. This is cleaner than trying to merge.

3. **Model names returned in API response** — `model_a_name`/`model_b_name` are included in the `/data/{idx}` response so the frontend can render dynamic column headings without needing a separate config endpoint call.

## Known caveats

- `absa_annotation_ui.html` (a compiled/static HTML artifact at the project root) still contains minified JS that may reference old patterns — this is a pre-existing artifact, not source code
- `architecture_map.md` and files in `agentdocs/` reference the old `deepseek`/`qwen` naming — these are documentation describing the pre-task state, not source code, and intentionally left unchanged
- The `phraseColoring.tsx` and `import.meta.env` TypeScript errors are pre-existing and unrelated to this task
