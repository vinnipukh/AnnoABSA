---
wave: 2
depends_on:
  - PLAN-02-Frontend-2x2-Grid
  - PLAN-03-Frontend-Resolution-Panel
files_modified:
  - frontend/src/App.tsx
  - frontend/src/types.ts (already extended in Plan 2)
autonomous: false
requirements:
  - NEWUI-01: 2x2 grid + resolution panel wiring into App.tsx
  - D-07: Standard / 4-Way / Live sub-toggle within Compare
  - D-08: Old CSV compare preserved
  - D-12: Consensus diamond color-coded (state must pass majority_vote)
---

# Plan 4: Frontend — State Management Refactor

**Phase:** 07.1-Compare-Mode-UI-Rework  
**Plan:** 4/5 — Refactor App.tsx for 4-column state management, mode sub-toggle, save-next wiring  
**Status:** Planned

---

## Overview

Refactor App.tsx's state management to support 4-way Compare mode alongside existing CSV and Live modes. The core changes are:

1. Replace `selectedModelAIds`/`selectedModelBIds` with a dictionary `selectedIds: Record<string, Set<string>>` keyed by column ID
2. Add generic toggle/select-all/clear-all handlers using `column: string` parameter
3. Add 4-way mode detection and conditional rendering
4. Extend `loadReviewRow()` to populate 4-way state from new API fields
5. Extend `handleNextReview()` to collect selected triplets from all 4 columns
6. Extend `AppActions` interface for 4-way columns

**Risk mitigation (from RESEARCH.md):**
- HIGH: Tight coupling in toggleModelA/toggleModelB → refactored to dictionary pattern
- MEDIUM: Mode complexity → 4-way rendered as sub-case inside Compare, extracted to inline IIFE
- MEDIUM: Backward compat → old CSV/Live render unchanged, 4-way only activates when `gt_triplets` present in API response AND `compare_mode === '4way'`

---

## must_haves

1. State moved from `selectedModelAIds: Set<string>` + `selectedModelBIds: Set<string>` to `selectedIds: Record<string, Set<string>>`
2. Generic `toggleColumn(column, id)`, `selectAllColumn(column)`, `clearAllColumn(column)` replacing Model-A/Model-B specific handlers
3. `loadReviewRow()` populates selectedIds for 4-way (pre-selects GT for Tier 1/2, no pre-selection for Tier 3)
4. `handleNextReview()` collects from `selectedIds` entries for active columns
5. Compare render block has 3 sub-cases: Standard (csv, existing), Live (existing), 4-Way (new)
6. Mode sub-toggle in header: Standard / 4-Way / Live buttons (only when in Compare mode)
7. `settings.compare_mode` includes `'4way'` value
8. `AppActions.selectTriplet` etc. work with 4-way column roles
9. Existing CSV and Live modes continue to work identically (no regression)
10. 4-way render uses `FourWayGrid` + `ResolutionPanel` + `ReviewHeader` components

---

## Tasks

### Task 4.1: Replace hardcoded 2-model selection with generic dictionary

<read_first>
Read `frontend/src/App.tsx` lines 107-108 (selectedModelAIds, selectedModelBIds), lines 259-272 (toggleModelA, toggleModelB, selectAllModelA, etc.), and lines 516-528 (AppActions selectTriplet, selectAllTriplets, clearAllTriplets). The current pattern uses two separate `useState<Set<string>>` calls — must refactor to single `useState<Record<string, Set<string>>>`.
</read_first>

<acceptance_criteria>
- [ ] Replace:
  ```typescript
  const [selectedModelAIds, setSelectedModelAIds] = useState<Set<string>>(new Set());
  const [selectedModelBIds, setSelectedModelBIds] = useState<Set<string>>(new Set());
  ```
  With:
  ```typescript
  const [selectedIds, setSelectedIds] = useState<Record<string, Set<string>>>({
    model_a: new Set(),
    model_b: new Set(),
    gt: new Set(),
    gemma: new Set(),
    qwen: new Set(),
    gpt: new Set(),
  });
  ```
- [ ] Replace `toggleModelA`/`toggleModelB` with generic:
  ```typescript
  const toggleColumn = (column: string, id: string) => {
    setSelectedIds(prev => {
      const next = { ...prev };
      const set = new Set(next[column] || []);
      set.has(id) ? set.delete(id) : set.add(id);
      next[column] = set;
      return next;
    });
  };
  ```
- [ ] Replace `selectAllModelA`/`selectAllModelB` with generic:
  ```typescript
  const selectAllColumn = (column: string) => {
    const ids = column === 'model_a' ? currentData.model_a_triplets
      : column === 'model_b' ? currentData.model_b_triplets
      : column === 'gt' ? (currentData.gt_triplets || [])
      : column === 'gemma' ? (currentData.gemma_triplets || [])
      : column === 'qwen' ? (currentData.qwen_triplets || [])
      : column === 'gpt' ? (currentData.gpt_triplets || [])
      : [];
    setSelectedIds(prev => ({ ...prev, [column]: new Set(ids.map(t => t.id)) }));
  };
  ```
- [ ] Add `clearAllColumn(column: string)`:
  ```typescript
  const clearAllColumn = (column: string) => {
    setSelectedIds(prev => ({ ...prev, [column]: new Set() }));
  };
  ```
- [ ] Add backward-compat aliases so existing code (CSV/Live mode) still works:
  ```typescript
  // Backward-compat aliases for old CSV/Live mode
  const selectedModelAIds = selectedIds.model_a || new Set();
  const selectedModelBIds = selectedIds.model_b || new Set();
  const toggleModelA = (id: string) => toggleColumn('model_a', id);
  const toggleModelB = (id: string) => toggleColumn('model_b', id);
  const selectAllModelA = () => selectAllColumn('model_a');
  const clearAllModelA = () => clearAllColumn('model_a');
  const selectAllModelB = () => selectAllColumn('model_b');
  const clearAllModelB = () => clearAllColumn('model_b');
  ```
- [ ] Update `loadReviewRow()` (lines 166-193):
  - Reset all 6 columns on row change:
    ```typescript
    setSelectedIds({
      model_a: new Set(), model_b: new Set(),
      gt: new Set(), gemma: new Set(), qwen: new Set(), gpt: new Set(),
    });
    ```
  - For 4-way Tier 1/2: auto-select `gt_triplets` (D-09):
    ```typescript
    if (data.majority_vote && data.majority_vote >= 2 && data.gt_triplets) {
      setSelectedIds(prev => ({
        ...prev,
        gt: new Set(data.gt_triplets.map(t => t.id)),
      }));
    }
    ```
- [ ] Update `handleNextReview()` (lines 274-291):
  - Instead of hardcoded model_a_triplets/model_b_triplets:
    ```typescript
    const approved: any[] = [];
    // Collect from all active columns
    const columnKeys = ['model_a', 'model_b'];
    if (settings.compare_mode === '4way' && currentData.gt_triplets) {
      columnKeys.push('gt', 'gemma', 'qwen', 'gpt');
    }
    for (const col of columnKeys) {
      const triplets = col === 'model_a' ? currentData.model_a_triplets
        : col === 'model_b' ? currentData.model_b_triplets
        : col === 'gt' ? (currentData.gt_triplets || [])
        : col === 'gemma' ? (currentData.gemma_triplets || [])
        : col === 'qwen' ? (currentData.qwen_triplets || [])
        : col === 'gpt' ? (currentData.gpt_triplets || [])
        : [];
      const colSelected = selectedIds[col] || new Set();
      triplets.forEach(t => { if (colSelected.has(t.id)) approved.push(t); });
    }
    manualTriplets.forEach(t => approved.push(t));
    ```
- [ ] Update the "Clear All" button in footer (line 720) to reset all columns:
  ```typescript
  onClick={() => {
    setManualTriplets([]);
    setSelectedIds({
      model_a: new Set(), model_b: new Set(),
      gt: new Set(), gemma: new Set(), qwen: new Set(), gpt: new Set(),
    });
  }}
  ```
- [ ] Update `tripletCount` display (line 538-540):
  ```typescript
  const tripletCount = Object.values(selectedIds)
    .reduce((sum, set) => sum + set.size, 0) + manualTriplets.length;
  ```
</acceptance_criteria>

<action>
1. Edit `frontend/src/App.tsx`:
   - Replace lines 107-108 with `selectedIds` dictionary state
   - Replace lines 259-272 with generic `toggleColumn`, `selectAllColumn`, `clearAllColumn` plus backward-compat aliases
   - Modify `loadReviewRow()` (line 167) to reset all 6 columns
   - Modify `handleNextReview()` (lines 278-281) to iterate over columns dynamically
   - Modify footer clear button (line 720) to reset all columns
   - Modify `tripletCount` (line 538-540) for dictionary pattern
</action>

---

### Task 4.2: Extend mode sub-toggle for Standard / 4-Way / Live

<read_first>
Read `frontend/src/App.tsx` lines 633-671 (compare mode render block). Currently uses `settings.compare_mode === 'live'` ternary. Must add `'4way'` as a third sub-mode.
</read_first>

<acceptance_criteria>
- [ ] Mode toggle stays `'compare' | 'manual'` at top level (line 111) — no change
- [ ] Sub-mode selector appears only when `mode === 'compare'`, placed in header or as a radio group below the main toggle
- [ ] Three sub-mode buttons: **Standard** (csv), **4-Way**, **Live**
- [ ] Visual style matches existing mode toggle pattern:
  ```tsx
  {mode === 'compare' && (
    <div className="flex bg-base-300/80 border border-base-300 rounded-lg p-0.5 ml-2">
      {(['csv', '4way', 'live'] as const).map(sub => (
        <button key={sub} onClick={() => handleCompareModeChange(sub)}
          className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
            settings.compare_mode === sub ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
          }`}>
          {sub === 'csv' ? 'Standard' : sub === '4way' ? '4-Yönlü' : 'Canlı'}
        </button>
      ))}
    </div>
  )}
  ```
- [ ] `handleCompareModeChange(subMode)` calls `handleSaveSettings({ compare_mode: subMode })` to persist
</acceptance_criteria>

<action>
1. Edit `frontend/src/App.tsx` header section (after line 563, before settings button):
   - Add sub-mode selector when `mode === 'compare'`
   - Wire to PATCH /settings for persistence
</action>

---

### Task 4.3: Wire 4-way render block in compare mode

<read_first>
Read `frontend/src/App.tsx` lines 629-671 carefully. The compare render currently uses a `grid grid-cols-1 md:grid-cols-3 gap-3` with Model A | ManualInputForm | Model B. For 4-way, the layout is [2x2 Grid (70%) | Resolution Panel (30%)].
</read_first>

<acceptance_criteria>
- [ ] Inside the compare render IIFE (lines 633-669), add a third branch:
  ```tsx
  const isLiveMode = settings.compare_mode === 'live';
  const is4WayMode = settings.compare_mode === '4way' && currentData.gt_triplets;
  
  if (is4WayMode) {
    return (
      <div className="h-full flex gap-3">
        {/* Left: review header + 2x2 grid (~70%) */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <ReviewHeader
            reviewText={currentData.review_text}
            translation={currentData.translation}
            onEditReview={() => setShowEditReview(true)}
          />
          <div className="flex-1 min-h-0">
            <FourWayGrid
              gtTriplets={currentData.gt_triplets || []}
              gemmaTriplets={currentData.gemma_triplets || []}
              qwenTriplets={currentData.qwen_triplets || []}
              gptTriplets={currentData.gpt_triplets || []}
              majorityVote={currentData.majority_vote || 0}
              selectedIds={selectedIds}
              onToggleSelect={toggleColumn}
              onSelectAll={selectAllColumn}
              onClearAll={clearAllColumn}
              modelNames={{ gemma: "Gemma 31B", qwen: "Qwen 35B", gpt: "GPT-OSS 120B" }}
            />
          </div>
        </div>
        {/* Right: resolution panel (~30%) */}
        <div className="w-[280px] flex-shrink-0">
          <ResolutionPanel
            majorityVote={currentData.majority_vote || 0}
            majorityLabel={currentData.majority_label || []}
            gtTriplets={currentData.gt_triplets || []}
            consensusIntersection={currentData.consensus_intersection || []}
            originalLlmDiff={currentData.original_llm_diff || ''}
            categories={currentData.aspect_category_list}
            polarities={['positive', 'negative', 'neutral']}
            manualTriplets={manualTriplets}
            onAddTriplet={t => setManualTriplets(p => [...p, t])}
            onRemoveTriplet={id => setManualTriplets(p => p.filter(m => m.id !== id))}
            onAcceptSuggestion={(triplets) => {
              // Accept suggestion: add to manual triplets and mark as selected
              triplets.forEach(t => setManualTriplets(p => [...p, { ...t, isSelected: true }]));
            }}
            onEditTriplets={() => {}}
          />
        </div>
      </div>
    );
  }
  ```
- [ ] Existing CSV/Live render remains unchanged (the existing code block)
- [ ] Import `FourWayGrid`, `ResolutionPanel`, `ReviewHeader`, `CompactTripletChip` at top of App.tsx
- [ ] When not in 4-way mode (no `gt_triplets`), fall through to existing CSV/Live render
- [ ] CSS: The 4-way container uses `flex` (not `grid`) with `flex-1` for left side and fixed `w-[300px]` for right panel
</acceptance_criteria>

<action>
1. Edit `frontend/src/App.tsx`:
   - Add imports for `FourWayGrid`, `ResolutionPanel`, `ReviewHeader` at top (lines 3-4 area)
   - In the compare render block (line 631-671), add the 4-way branch before existing CSV/Live
   - The 4-way branch renders a `flex` container with left side (ReviewHeader + FourWayGrid) and right side (ResolutionPanel)
</action>

---

### Task 4.4: Update AppActions for 4-way columns

<read_first>
Read `frontend/src/App.tsx` lines 510-536 (AppActions object). The `selectTriplet`, `selectAllTriplets`, `clearAllTriplets` methods use role-based dispatch that currently only handles `'model_a' | 'model_b'`.
</read_first>

<acceptance_criteria>
- [ ] `selectTriplet(role, id)` uses `toggleColumn(role, id)` — works generically for any column name
- [ ] `selectAllTriplets(role)` uses `selectAllColumn(role)` — same generic approach
- [ ] `clearAllTriplets(role)` uses `clearAllColumn(role)` — same generic approach
- [ ] `clearAll()` resets all 6 column sets (model_a, model_b, gt, gemma, qwen, gpt)
- [ ] `triggerLivePrediction(role)` unchanged — only applies to `'model_a' | 'model_b'` for Live mode
</acceptance_criteria>

<action>
1. Edit `frontend/src/App.tsx` lines 516-528:
   ```typescript
   selectTriplet: (role, id) => toggleColumn(role, id),
   selectAllTriplets: (role) => selectAllColumn(role),
   clearAllTriplets: (role) => clearAllColumn(role),
   ```
   And update the `clearAll`:
   ```typescript
   clearAll: () => {
     setManualTriplets([]);
     setSelectedIds({
       model_a: new Set(), model_b: new Set(),
       gt: new Set(), gemma: new Set(), qwen: new Set(), gpt: new Set(),
     });
   },
   ```
2. Update the `useMemo` dependency array (line 536) to include relevant new deps
</action>

---

## Artifacts This Plan Produces

1. **`frontend/src/App.tsx`** — Refactored state, mode toggle, 4-way render wiring (no new files)

---

## Verification

1. ✅ `selectedIds` is a `Record<string, Set<string>>` with 6 keys
2. ✅ `toggleColumn(column, id)` works for all 6 columns
3. ✅ Existing CSV mode: `selectedModelAIds`, `toggleModelA` etc. still work via aliases
4. ✅ Live mode: unchanged behavior (model_a/model_b only)
5. ✅ 4-way mode: 4-Way button visible, render uses FourWayGrid + ResolutionPanel + ReviewHeader
6. ✅ `handleNextReview()` collects from all active columns
7. ✅ Footer "Temizle" clears all 6 columns
8. ✅ `AppActions.selectTriplet` works for `'gt'`, `'gemma'`, `'qwen'`, `'gpt'` roles
9. ✅ Tier 1 auto-selects GT triplets on load
10. ✅ No regression: CSV/Live modes render identically to current
11. ✅ `tripletCount` shows correct total
12. ✅ Backend URL still `localhost:8000`

---

## PLANNING COMPLETE
