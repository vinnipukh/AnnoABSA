# PLAN-04-State-Management-Refactor — SUMMARY

## Objective
Refactor `App.tsx` to support 4-way compare mode: replace hardcoded 2-model selection with a generic `Record<string, Set<string>>` dictionary, add generic `toggleColumn`/`selectAllColumn`/`clearAllColumn` functions, wire the 4-way render block with `FourWayGrid` + `ResolutionPanel` + `ReviewHeader`, add a Standard/4-Way/Live sub-mode toggle, and update `AppActions`.

## Changes Made

### `frontend/src/App.tsx` — 12 targeted edits

1. **Added imports** for `ReviewHeader`, `FourWayGrid`, `ResolutionPanel` (line 13-15)

2. **Replaced state** (lines 110-116):
   - `selectedModelAIds` / `selectedModelBIds` → `selectedIds: Record<string, Set<string>>` with 6 columns: `model_a`, `model_b`, `gt`, `gemma`, `qwen`, `gpt`

3. **Replaced toggle/selectAll/clearAll functions** (lines 265-308):
   - `toggleColumn(column, id)` — generic toggle for any column
   - `selectAllColumn(column)` — select all triplets for a column by name
   - `clearAllColumn(column)` — clear a column
   - Backward-compat aliases: `selectedModelAIds`, `selectedModelBIds`, `toggleModelA/B`, `selectAllModelA/B`, `clearAllModelA/B`

4. **Updated `loadReviewRow`** — resets all 6 columns on row change

5. **Updated `handleNextReview`** — dynamically iterates over 6 columns to collect approved triplets

6. **Updated `AppActions`** — `selectTriplet`, `selectAllTriplets`, `clearAllTriplets` now delegate to generic `toggleColumn`/`selectAllColumn`/`clearAllColumn`

7. **Updated `clearAll` action** — resets all 6 columns

8. **Updated `tripletCount`** — sums across all 6 columns

9. **Updated appActions dependency array** — includes all 6 column data arrays

10. **Added compare mode sub-toggle** — Standard / 4-Yönlü / Canlı buttons visible only in compare mode, wired to `handleSaveSettings({ compare_mode: ... })`

11. **Wired 4-way render block** — when `settings.compare_mode === '4way'` and `currentData.gt_triplets` is present, renders:
    - Left side: `ReviewHeader` + `FourWayGrid` (2×2 grid of gt/gemma/qwen/gpt)
    - Right side: `ResolutionPanel` (280px, with tier logic, manual form, accept buttons)
    - Falls back to existing CSV/Live 3-column layout otherwise

12. **Updated footer clear button** — resets all 6 columns via `setSelectedIds`

## Verification

| Check | Result |
|---|---|
| `npx tsc --noEmit` | No new errors (only 1 pre-existing error in App.tsx: line 530 `rect` not in type) |
| `npx vitest run` | **6 test files, 64 tests — ALL PASS** |

## Notes

- Backward compatibility is fully maintained — CSV and Live modes continue using the same old `selectedModelAIds`/`selectedModelBIds` aliases
- The 4-way branch uses `(currentData as any)` casting for `majority_label`, `consensus_intersection`, and `original_llm_diff` fields since their types in `types.ts` don't perfectly match `ResolutionPanel` props (pre-existing type discrepancy)
- Three pre-existing TS errors outside App.tsx remain unchanged (`global` in test file, `includes` on `string[]` in SettingsPanel, `rect` in state type)

## PLAN COMPLETE
