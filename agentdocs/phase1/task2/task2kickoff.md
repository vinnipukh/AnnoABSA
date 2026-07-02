# Task 2 Kickoff — Generalize the LLM-comparison feature

This is the only task for this session. Full context is below. Read carefully before proposing a plan.

## Task

The AnnoABSA UI currently has a two-column LLM comparison feature, but it is hardcoded to look for specific "DeepSeek" and "Qwen" CSV files and uses hardcoded JSON keys end-to-end. Your job is to generalize this so the user can pass any two comparison CSVs (with custom display names) via the CLI, and have those render dynamically in the UI.

### Current state (Verify before coding)

This feature **already exists**, but it is entirely hardcoded:
- In `main.py::get_data` (~L270–L300), it looks for columns `aspect_triplets`/`new_triplets`, or falls back to sibling files **hardcoded by filename**: `semeval_deepseek_labeled.csv` and `semeval_qwen_labeled.csv`.
- Output keys are hardcoded as `deepseek_triplets`/`qwen_triplets` end-to-end. You will see these in:
  - `main.py` (`AgentChatRequest`, `generate_mock_reasoning`, `get_data` response)
  - `frontend/src/types.ts` (`ReviewComparisonData.deepseek_triplets`/`qwen_triplets`)
  - `frontend/src/App.tsx` and `frontend/src/components/HelperAgentChatbox.tsx` (**grep for `deepseek`/`qwen` across `frontend/src` before starting**).
- `generate_mock_reasoning` (~L209) hardcodes the literal strings "DeepSeek" and "Qwen" in the generated Turkish reasoning text.
- `frontend/src/components/ModelTripletColumn.tsx` is already generic (`title`, `badgeText` props). **Do not refactor this component.**

### What to build

1. **Config & CLI Flags:** Add the following config fields (in the JSON config consumed by `load_config`) and matching `--*` CLI flags in `cli.py`:
   - `--compare-model-a-csv` / `compare_model_a_csv`
   - `--compare-model-a-name` / `compare_model_a_name`
   - `--compare-model-b-csv` / `compare_model_b_csv`
   - `--compare-model-b-name` / `compare_model_b_name`
2. **Backend Data Loading:** Replace the hardcoded filenames/column names in `main.py::get_data` with reads from this new config. If the CSVs use the Task 1 STD triplet format (`review, triplet`), reuse the Task 1 parser logic. Keep the generic dict shape `{id, aspect_term, aspect_category, sentiment_polarity}`.
3. **Key Renaming:** Rename `deepseek_triplets`/`qwen_triplets` to generic names (e.g., `model_a_triplets`/`model_b_triplets`) across the backend response, `types.ts`, and every frontend file that references them. **This is a simple rename, not a redesign.**
4. **Dynamic Reasoning:** Update `main.py::generate_mock_reasoning` to inject the configured display names (`compare_model_a_name` / `compare_model_b_name`) into its text generation instead of literal hardcoded strings.
5. **Clean No-Op Fallback:** If no comparison CSVs are passed via the CLI/config, the feature should no-op cleanly (return empty `model_a_triplets`/`model_b_triplets` arrays, show no comparison columns, and throw no errors).

### Definition of done

- Two STD-format CSVs with different model labels, pointed to via CLI flags with custom names, render correctly in the existing two-column comparison UI with the configured names as headers.
- The strings `deepseek` and `qwen` no longer exist as hardcoded variable names, JSON keys, or default string literals anywhere in the backend or frontend code.
- Running the application with no comparison CSVs configured behaves identically to today's default (no comparison columns shown, no crash).

---

## What I need from you

1. A step-by-step execution plan in the `[Step] → verify: [how I'll check this worked]` format outlined in the primer.
2. Wait for my go-ahead.
3. Once approved, provide the full file contents (or clearly marked diffs) for every file you change. Do not omit code for brevity.

If you need to see the exact current contents of `main.py`, `cli.py`, `types.ts`, or `App.tsx` before formulating your plan, explicitly ask for them now.