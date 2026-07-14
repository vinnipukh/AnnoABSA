# Phase 7.4: 4-Way Polish — Demo, Filters, Auto-Save & Export — Plan

**Phase:** 07.4-4Way-Polish
**Planned:** 2026-07-14
**Execution mode:** Sequential by wave
**Status:** Not started

---

## Plan 1: Column header names + Demo mode toggle

**Goal:** Show CSV column names on 2x2 grid card headers, and add a Demo mode toggle that loads pre-built sample data covering all 3 tiers.

**Est. effort:** Medium
**Files:**
- `frontend/src/components/FourWayGrid.tsx` — card headers
- `frontend/src/App.tsx` — mode toggle, demo data switching
- `frontend/src/hooks/useReviewNavigation.ts` — reuse FALLBACK_DATA pattern

### Implementation Steps

#### 1a. Column header names
1. Read `FourWayGrid.tsx` — find where card headers render the model name (currently `model_a_name`, `model_b_name`, etc.)
2. Add a subtle monospace label below or beside each card header showing the CSV column name (e.g. `gemma4_31b_label`)
3. Column names are available from the existing data structure — `currentData` already has `model_a_name`, `model_b_name`, `gt_triplets`, etc. The CSV column name can be derived from `NEWUI_COLUMNS` mapping or passed as a prop.
4. Keep the existing short display name as the primary header; the column name is a secondary label (`text-xs text-base-content/50 font-mono`).

#### 1b. Demo mode
1. Create a demo data array (in a new file `frontend/src/data/demoData.ts` or extend `useReviewNavigation.ts`) with ~6 reviews covering all 3 tier scenarios:
   - 2 reviews with `majority_vote >= 2 AND majority_label == original_label` (Tier 1 — auto-accept)
   - 2 reviews with `majority_vote >= 2 AND majority_label != original_label` (Tier 2 — quick diff)
   - 2 reviews with `majority_vote == 1` (Tier 3 — high confusion)
   - Each review needs: `id`, `text`, `review_text`, `model_a_triplets`, `model_b_triplets`, `gt_triplets`, `gemma_triplets`, `qwen_triplets`, `gpt_triplets`, `model_a_name`, `model_b_name`, `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff`, `agent_initial_reasoning`
2. Add a 4th mode toggle option in the mode selector in `App.tsx` — "Demo" alongside Compare / Manual / 4-Way
3. When Demo mode is active, load `currentData` from the demo array instead of the backend
4. The demo data pattern should follow `useReviewNavigation`'s `FALLBACK_DATA` — frontend-only, no backend dependency
5. When exiting demo mode, switch back to the last active mode and reload from backend

### UI/UX Constraints
- **No emoji icons** (Priority 4): Every visual indicator in demo toggle and column labels must use Heroicons SVG. Reference `svg-icon-replacements.md` for exact paths. Never use emoji characters.
- **Modified-file emoji scanning**: This plan modifies `App.tsx`, `FourWayGrid.tsx`, and creates `demoData.ts`. Before editing `App.tsx` and `FourWayGrid.tsx`, scan the ENTIRE file for emoji in `setSaveToast`, button text, and labels — fix all found in the same edit. This catches old toast messages (✅/❌) that may have survived previous phases.
- **Touch targets ≥44×44px** (Priority 2): Mode toggle buttons must be ≥44×44px. DaisyUI `btn` class handles this natively.
- **Reduced motion** (Priority 7): Demo data loading transition should not animate. Prefer appear/disappear (no animation).
- **Accessibility** (Priority 1): Icon-only demo toggle must have `aria-label`.
- **Component extraction**: If the demo data array is >50 lines, extract to `frontend/src/data/demoData.ts` to keep `App.tsx` clean.
- **React 19 test workaround**: Any new tests for demo mode must use `createRoot` + `flushSync`, NOT `@testing-library/react`. Test files with JSX must be `.tsx`, not `.ts`.

### UAT Criteria
- [ ] Column names displayed as subtle labels on 2x2 grid card headers
- [ ] Demo toggle button visible in mode selector row
- [ ] Demo mode loads 6+ reviews covering all 3 tiers
- [ ] Demo reviews render correctly in the 4-way grid
- [ ] Exiting demo mode restores backend data without error
- [ ] All 88 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 2: Tier filter dropdown

**Goal:** Add a dropdown filter (All / Tier 1 / Tier 2 / Tier 3) that narrows the review queue — navigation skips reviews not matching the selected tier.

**Est. effort:** Medium
**Files:**
- `frontend/src/App.tsx` — tier filter state, navigation logic
- `frontend/src/components/FourWayGrid.tsx` or `ResolutionPanel.tsx` — filter UI placement

### Implementation Steps
1. Add `tierFilter` state in App.tsx: `const [tierFilter, setTierFilter] = useState<'all' | 1 | 2 | 3>('all');`
2. Add a dropdown/select in the toolbar or resolution panel area with options: "Tümü", "Tier 1", "Tier 2", "Tier 3"
3. Modify `handleNextReview` and `handlePrevReview` to skip reviews that don't match the filter:
   - Check `currentData.majority_vote` against `tierFilter`
   - If no match, continue to next/prev index
   - Max 50 iterations to prevent infinite loop on empty filter
   - Show a toast if no more matching reviews in that direction
4. Show visual indicator: "Tier 2 filtreleniyor" or similar when filter is active
5. The filter state persists across navigation but resets on data reload

### UI/UX Constraints
- **No emoji icons** (Priority 4): Dropdown options must use text labels ("Tümü", "Tier 1", etc.), not emoji badges or icon indicators. Reference `svg-icon-replacements.md` for any needed SVG icons.
- **Modified-file emoji scanning**: This plan modifies `App.tsx` and potentially `FourWayGrid.tsx` or `ResolutionPanel.tsx`. Before editing each file, scan the ENTIRE file for emoji in `setSaveToast`, button text, and labels — fix all found. Old toast messages (✅/❌) are the most common source of residual emoji.
- **Touch targets ≥44×44px** (Priority 2): The filter dropdown/select must meet minimum touch size. DaisyUI `select` class handles this natively.
- **Accessibility** (Priority 1): The filter dropdown needs a visible `<label>` or `aria-label`. The active filter indicator must also have an `aria-live` region so screen readers announce filter changes.
- **8px spacing** (Priority 2): Minimum 8px gap between filter dropdown and adjacent toolbar elements.
- **Empty state** (Priority 8): When filter yields no results, show a clear message ("Bu filtrede inceleme bulunamadı") rather than an empty grid.
- **Color not sole indicator** (Priority 1): The tier filter indicator text ("Tier 2 filtreleniyor") must be readable without color cues. Use text + spacing, not just color.

### UAT Criteria
- [ ] Dropdown with 4 options (All / Tier 1 / 2 / 3) present in UI
- [ ] "All" shows all reviews (no filtering)
- [ ] Selecting a tier skips non-matching reviews on next/prev navigation
- [ ] Toast shown when no more matching reviews in direction
- [ ] Max 50 iterations to prevent infinite loop
- [ ] Visual indicator shows active filter
- [ ] All 88 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 3: Auto-save on navigation + Save button in resolution panel

**Goal:** Auto-save annotations when navigating, and add a visible save button in the resolution panel for mid-review saves.

**Est. effort:** Medium
**Files:**
- `frontend/src/App.tsx` — extend handlePrevReview to save
- `frontend/src/components/ResolutionPanel.tsx` — save button in header

### Implementation Steps

#### 3a. Auto-save on prev navigation
1. Read `handlePrevReview` in App.tsx (currently just goes to previous index)
2. Add save logic: collect approved triplets from `selectedIds` + `manualTriplets`, call `saveReview(approved)`, show toast
3. Use the same save pattern as `handleNextReview` (lines ~150-172) — the pattern already exists, just duplicate for prev

#### 3b. Save button in resolution panel
1. Read `ResolutionPanel.tsx` — find the panel header area
2. Add a save button next to the tier badge (top-right of the panel)
3. Button uses DaisyUI `btn btn-sm btn-outline` with Heroicons save SVG:
   ```tsx
   <button className="btn btn-sm btn-outline gap-1" onClick={onSave} aria-label="Kaydet">
     <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
     </svg>
     Kaydet
   </button>
   ```
4. Add `onSave?: () => void` to `ResolutionPanelProps`
5. Wire in App.tsx: `onSave={() => handleNextReview()}` — save without advancing (just call saveReview internal logic without goToNext)

### UI/UX Constraints
- **No emoji icons** (Priority 4): Save button must use Heroicons save SVG (provided in steps above), NOT 💾 emoji. Reference `svg-icon-replacements.md` for all icon paths.
- **Modified-file emoji scanning**: This plan modifies `App.tsx` and `ResolutionPanel.tsx`. Before editing each file, scan the ENTIRE file for emoji in `setSaveToast`, button text, and labels — fix all found in the same edit. This is particularly important for `App.tsx` which has known lingering emoji in old toast messages.
- **Touch targets ≥44×44px** (Priority 2): Save button must meet minimum touch size. DaisyUI `btn` class handles this natively. 8px minimum gap between save button and adjacent elements.
- **Accessibility** (Priority 1): Save button must have `aria-label="Kaydet"`. The save button should be keyboard-focusable and actionable via Enter key (handled natively by `<button>`).
- **Loading state** (Priority 2): Save button must show spinner (`border-2 border-primary border-t-transparent rounded-full animate-spin`) and disabled state during async save operation. Use `<button disabled>` pattern.
- **Color not sole indicator** (Priority 1): The save confirmation toast must be readable without color cues. Use text (not color) to indicate success.
- **Reduced motion** (Priority 7): Toast appear/disappear should not animate, or respect `prefers-reduced-motion`.
- **Infinite loop prevention**: `handlePrevReview` save must not trigger the auto-save effect again. Use a flag or ref to prevent re-entrance.

### UAT Criteria
- [ ] Navigating previous auto-saves annotations (toast confirmation)
- [ ] Save button visible in resolution panel header next to tier badge
- [ ] Save button triggers save without navigating
- [ ] Save button shows loading state during save
- [ ] Save button is DaisyUI `btn` for touch targets
- [ ] No emoji in save button (Heroicons SVG)
- [ ] All 88 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 4: CSV export endpoint + download button

**Goal:** Create `GET /data/export-4way` backend endpoint returning annotated data as CSV, with a frontend download button.

**Est. effort:** Medium
**Files:**
- `app/routes/export.py` (new) or extend existing route
- `app/data.py` — export helper
- `frontend/src/components/ResolutionPanel.tsx` or toolbar — download button

### Implementation Steps

#### 4a. Backend export endpoint
1. Create `app/routes/export.py` with:
   ```python
   """4-way export endpoint — GET /data/export-4way."""
   import csv, io
   from fastapi import APIRouter
   from fastapi.responses import StreamingResponse
   
   from app.data import load_data
   from app.config import DATA_FILE_PATH
   
   router = APIRouter(tags=["export"])
   
   @router.get("/data/export-4way")
   def export_4way():
       data = load_data()  # returns DataFrame for CSV, list for JSON
       output = io.StringIO()
       writer = csv.writer(output)
       
       # Write headers from original data
       if hasattr(data, 'columns'):
           writer.writerow(list(data.columns) + ['selected_triplets', 'resolution_tier', 'annotator_notes'])
           for _, row in data.iterrows():
               writer.writerow(list(row) + ['[]', '', ''])
       else:
           # JSON path
           if data:
               writer.writerow(list(data[0].keys()) + ['selected_triplets', 'resolution_tier', 'annotator_notes'])
               for row in data:
                   writer.writerow(list(row.values()) + ['[]', '', ''])
       
       output.seek(0)
       return StreamingResponse(
           iter([output.getvalue()]),
           media_type="text/csv",
           headers={"Content-Disposition": "attachment; filename=export-4way.csv"},
       )
   ```
2. Register in `main.py`: `from app.routes.export import router as export_router` + `app.include_router(export_router)`
3. Follow the same pattern as `app/routes/upload.py`

#### 4b. Frontend download button
1. Add an export/download button in the toolbar area or resolution panel
2. Button triggers `window.open(\`${backendUrl}/data/export-4way\`)` or a fetch + download
3. DaisyUI `btn btn-sm btn-outline` with Heroicons download SVG

#### 4c. Tests
1. Create `tests/test_export.py` with 8+ tests:
   - 200 response with correct Content-Type and Content-Disposition
   - CSV contains expected headers (original columns + selected_triplets, resolution_tier, annotator_notes)
   - CSV has correct row count
   - Non-empty CSV body
   - Uses the existing `app` fixture from `tests/conftest.py`

### UI/UX Constraints
- **No emoji**: Use Heroicons download SVG, not emoji
- **Touch targets**: Download button ≥44×44px via DaisyUI `btn` class
- **Loading state**: Download triggers browser download directly (no loading state needed)

### UAT Criteria
- [ ] `GET /data/export-4way` returns CSV with correct headers
- [ ] CSV includes all original columns + `selected_triplets`, `resolution_tier`, `annotator_notes`
- [ ] CSV contains all rows from the data file
- [ ] Content-Type is `text/csv`
- [ ] Content-Disposition includes `export-4way.csv` filename
- [ ] Frontend download button triggers export
- [ ] All 227 backend tests still pass
- [ ] 8+ new tests for export endpoint

---

## Wave execution: Sequential

| Wave | Plans | Description | Dependencies |
|------|-------|-------------|--------------|
| **Wave 1** | Plan 1, Plan 2 | Column headers + demo mode + tier filter | None (frontend only) |
| **Wave 2** | Plan 3 | Auto-save on prev + save button in resolution panel | None (extends existing save) |
| **Wave 3** | Plan 4 | CSV export endpoint + download button | Plan 3 (save flow in place) |

Waves 1 and 2 are independent and could run in parallel if needed. Wave 3 depends on the save flow being established.

---

## Verification

After each wave, run:
```bash
# Backend tests
.venv/Scripts/pytest tests/ -q --tb=short

# Frontend tests
cd frontend && NODE_ENV=development npx vitest run

# TypeScript check
NODE_ENV=development npx tsc --noEmit

# Build
NODE_ENV=development npx vite build
```

After full phase execution:
- **+8+ backend tests** (Plan 4 export tests)
- All 227 existing backend tests still pass
- All 88 existing frontend tests still pass
- 0 TS errors
- Clean build
- **Modified files scanned** — all existing files touched this phase (`App.tsx`, `FourWayGrid.tsx`, `ResolutionPanel.tsx`) have been scanned for residual emoji in toast messages, button text, and labels (0 emoji remaining)
