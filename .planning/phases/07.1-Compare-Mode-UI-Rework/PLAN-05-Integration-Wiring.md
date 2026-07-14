---
wave: 3
depends_on:
  - PLAN-01-Backend-Data-Loading
  - PLAN-02-Frontend-2x2-Grid
  - PLAN-03-Frontend-Resolution-Panel
  - PLAN-04-State-Management-Refactor
files_modified:
  - frontend/src/App.tsx (4-way render + sub-toggle already in Plan 4 — verify integration)
  - frontend/src/components/HelperAgentChatbox.tsx (minor — verify z-index)
  - frontend/src/components/NlpHelperToolbar.tsx (minor — verify positioning)
  - frontend/src/App.css or equivalent (if layout adjustments needed)
autonomous: false
requirements:
  - NEWUI-10: No overlap with NLP toolbar or chatbox; drag-to-select intact
  - D-03: No collapsible/minimizable cards
  - D-07: Standard / 4-Way / Live sub-toggle within Compare mode
  - D-08: Old CSV compare preserved
---

# Plan 5: Integration — Wire Mode Toggle, Ensure No Overlap

**Phase:** 07.1-Compare-Mode-UI-Rework  
**Plan:** 5/5 — Integration wiring, sub-mode toggle, overlap verification, smoke tests  
**Status:** Planned

---

## Overview

This final plan ties everything together: wires the Standard / 4-Way / Live sub-mode toggle into the UI, verifies that the 4-way layout does not overlap with existing UI elements (NLP helper toolbar, floating chat, footer, active learning panel), ensures drag-to-select still works (NEWUI-10), and runs integration smoke tests.

The primary verification targets from RESEARCH.md risk areas:
- Risk #2 (Mode complexity): verify all 6 states (2 main modes × 3 sub-modes) render correctly
- Risk #4 (Resolution panel placement): verify no overlap with footer, floating chat, or NLP toolbar
- Risk #3 (Backward compatibility): verify CSV/Live modes unchanged

---

## must_haves

1. Standard / 4-Way / Live sub-toggle wired and functional in the header
2. All 6 states render without visual overlap or layout breakage
3. NLP Toolbar (selection-based) works in 4-way mode — drag-to-select still triggers it
4. Floating chat (HelperAgentChatbox) does not overlap resolution panel
5. Footer (save & next) is always visible below both grid and panel
6. Active Learning panel (centered popup) does not overlap
7. All existing CSV/Live functionality continues to work without regression
8. Browser at 1280px+ shows correct layout; smaller widths get responsive fallback

---

## Tasks

### Task 5.1: Verify sub-mode toggle wiring

<read_first>
Read `frontend/src/App.tsx` lines 554-563 (mode toggle buttons). The sub-mode toggles (Standard/4-Way/Live) are added between lines 563 and 564 in Plan 4 Task 4.2. Verify they:
- Are only visible when `mode === 'compare'`
- Call `handleSaveSettings({ compare_mode: '4way' })` on click
- Persist via PATCH /settings endpoint
- Survive page refresh (re-fetched via GET /settings)
</read_first>

<acceptance_criteria>
- [ ] Sub-mode toggle renders 3 buttons: **Standard**, **4-Yönlü**, **Canlı**
- [ ] Buttons only visible in Compare mode (hidden in Manual mode)
- [ ] Clicking a button calls PATCH /settings with `{ compare_mode: '4way' | 'csv' | 'live' }`
- [ ] Active button highlighted with `bg-primary text-primary-content shadow`
- [ ] Inactive buttons use `text-base-content/60 hover:text-base-content`
- [ ] On page load, `settings.compare_mode` from GET /settings sets the active button state
- [ ] Switching from 4-Way back to Standard immediately re-renders the old CSV layout
- [ ] Switching from 4-Way to Live immediately re-renders the Live layout
</acceptance_criteria>

<action>
1. Add the sub-toggle JSX in App.tsx header (between lines 563 and 564):
```tsx
{mode === 'compare' && (
  <div className="flex bg-base-300/80 border border-base-300 rounded-lg p-0.5 ml-1">
    {(['csv', '4way', 'live'] as const).map(sub => (
      <button key={sub} onClick={() => handleSaveSettings({ compare_mode: sub })}
        className={`px-2 py-1 text-[9px] font-bold rounded-md transition-all select-none ${
          settings.compare_mode === sub ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
        }`}>
        {sub === 'csv' ? 'Standard' : sub === '4way' ? '4-Yönlü' : 'Canlı'}
      </button>
    ))}
  </div>
)}
```
2. Verify that sub-mode state is read from `settings.compare_mode` (already wired via fetch in useEffect)
</action>

---

### Task 5.2: Verify no overlap with NLP toolbar

<read_first>
Read `frontend/src/App.tsx` lines 754-761 (NLP Helper Toolbar rendering). It renders as a fixed-position overlay based on `nlpToolbarSelection` state. The `onSelectionChange` handler (lines 481-487) fires on drag-to-select.
</read_first>

<acceptance_criteria>
- [ ] In 4-way mode, selecting text in the ReviewHeader (review text) triggers `handleNlpSelectionChange` — same as current behavior
- [ ] NLP Toolbar popup appears near the selection, does NOT overlap resolution panel
- [ ] NLP Toolbar z-index (`z-50` per existing code) is above resolution panel's z-index
- [ ] Drag-to-select still works — `useTextSelection` hook unchanged
- [ ] The resolution panel's own text (manual form inputs, diff text) does not trigger NLP toolbar (not needed)
- [ ] No regression: NLP Toolbar still works in Standard and Live compare modes
</acceptance_criteria>

<action>
1. Verify the ReviewHeader component passes `onSelectionChange` — if not, the ManualInputForm's `onSelectionChange` prop (line 654 in App.tsx) must be adapted
2. For 4-way mode, the ReviewHeader needs a selection handler. Since the extracted ReviewHeader doesn't have one by default, ensure the review text area in 4-way mode still enables text selection for the NLP toolbar:
   - Either pass `onSelectionChange` to ReviewHeader (add a prop)
   - Or use a global `mouseup` handler on the main container (simpler, existing pattern via `handleNlpSelectionChange`)
   - The simplest approach: wrap the entire 4-way left container with `onMouseUp` delegation (same pattern as ManualInputForm line 140)
3. Ensure NlpHelperToolbar positioning (lines 755-761) uses fixed/absolute coordinates — should use `document.elementFromPoint` or selection rectangle. Existing code already uses `getBoundingClientRect()` on the selection range, so it positions relative to viewport — no overlap issue
</action>

---

### Task 5.3: Verify no overlap with floating chat

<read_first>
Read `frontend/src/App.tsx` lines 705-713 (HelperAgentChatbox rendering). It renders as a fixed-position chat overlay at the bottom-right of the screen. The resolution panel is on the right ~30%, so potential overlap exists.
</read_first>

<acceptance_criteria>
- [ ] Floating chat (HelperAgentChatbox) renders at bottom-right with `fixed` positioning — confirm its CSS classes
- [ ] When in 4-way mode, the resolution panel's right edge does not extend past the floating chat's left edge
- [ ] If overlap exists, adjust: move resolution panel to left of chat, or shrink panel width, or adjust chat z-index
- [ ] Floating chat `z-50` is above resolution panel's default stacking context
- [ ] No overlap at 1280px minimum viewport width
- [ ] No overlap at fullscreen (1920px)
- [ ] User can resize chat (if implemented) without panel overlap
</acceptance_criteria>

<action>
1. Check the HelperAgentChatbox component's CSS positioning:
   - Look in frontend/src/components/HelperAgentChatbox.tsx for `fixed` or `absolute` positioning
   - Check `right`, `bottom` values
   - Check z-index value
2. If ResolutionPanel's right edge collides with chat's left edge at 1280px:
   - Option A: Reduce ResolutionPanel width from 300px → 280px
   - Option B: Add `mr-12` (or `mr-14`) to the 4-way container to leave room for the chat
   - Option C: Adjust chat's right offset in 4-way mode
3. The ResolutionPanel uses `w-[300px] flex-shrink-0` — this is ~300px on a 1280px screen (70% = 896px, remaining = 384px). Chatbox typically sits at right edge. 300px panel + ~320px chat = overlaps. **Mitigation**: set panel to `w-[280px]` and adjust as needed
</action>

---

### Task 5.4: Verify footer, header, and responsive behavior

<read_first>
Read `frontend/src/App.tsx` lines 543-627 (header), lines 629-694 (main), lines 715-730 (footer). The 4-way layout must fit within the existing `max-w-[1700px]` container and `h-[calc(100vh-3rem)]` height.
</read_first>

<acceptance_criteria>
- [ ] Footer (h-10) is always visible below the 4-way layout — no scroll overlap
- [ ] Header (h-12) is always visible above
- [ ] The 4-way container fits within `max-w-[1700px]` — at 1700px: 70% = 1190px for grid, 300px for panel = 1490px, fits easily
- [ ] At 1280px: 70% = 896px for grid, 300px for panel = 1196px, still fits
- [ ] At <1280px: responsive fallback — stack grid above panel or use scroll
- [ ] Active Learning panel (lines 696-703, `fixed bottom-14`) does not overlap 4-way content
- [ ] WelcomeOverlay (lines 763-767) still works
- [ ] Save toast (lines 748-752, `fixed bottom-14`) renders above everything
</acceptance_criteria>

<action>
1. Check the 4-way container CSS:
   - Left side (ReviewHeader + FourWayGrid): `flex-1 min-w-0 flex flex-col overflow-hidden`
   - Right side (ResolutionPanel): `w-[300px] flex-shrink-0`
   - Outer: `flex gap-3 h-full`
2. For responsive fallback at <1280px:
   - Consider adding `lg:flex-row flex-col` so below lg breakpoint the panel stacks below the grid
   - Or `overflow-x-auto` with minimum width
3. No changes needed to footer — it sits outside the 4-way container in the normal DOM flow
</acceptance_criteria>

---

### Task 5.5: Run integration smoke tests

<read_first>
Read `tests/` directory for any integration test patterns. Read `tests/test_live_prediction.py` for TestClient pattern.
</read_first>

<acceptance_criteria>
- [ ] Backend integration test verifies `GET /data/{idx}` returns NEWUI fields when CSV has them:
  - Create a temporary NEWUI CSV with all required columns
  - Start app pointing to this CSV
  - Call `GET /data/0` and assert response has `gt_triplets`, `gemma_triplets`, `qwen_triplets`, `gpt_triplets`, `majority_vote`, etc.
- [ ] Backend test verifies backward compat:
  - Create a standard CSV (no NEWUI columns)
  - Call `GET /data/0` and assert no NEWUI fields in response
- [ ] Frontend smoke test:
  - `npx tsc --noEmit` compiles with 0 errors
  - `npx vitest run` passes (existing tests + new ResolutionPanel tests)
- [ ] Manual checklist:
  - [ ] Standard mode: old CSV/Live layout renders identically
  - [ ] 4-Way mode: grid + panel visible, no overlaps
  - [ ] Live mode: unchanged behavior
  - [ ] Switching sub-modes: layout updates instantly
  - [ ] Save & next: collects selected triplets from all 4 columns
  - [ ] NLP Toolbar: text selection triggers toolbar
  - [ ] Floating chat: no panel overlap
  - [ ] Footer: always visible
</acceptance_criteria>

<action>
1. Create `tests/test_newui_routes.py` if time permits, or document manual test checklist
2. Run `cd frontend && npx tsc --noEmit` to verify TypeScript compilation
3. Run `cd frontend && npx vitest run` to verify existing + new tests pass
4. Run `cd /c/Users/arhan/PycharmProjects/AnnoABSA && python -m pytest tests/ -q --tb=short` to verify backend tests still pass
</action>

---

## Artifacts This Plan Produces

1. **No new source files** — integration changes go into existing files
2. **Layout verification checklist** (documented above)
3. **Integration smoke test results** (manual or automated)

---

## Integration Checkpoints

### Checkpoint A: Mode toggle
- [ ] Mode buttons (Standard / 4-Yönlü / Canlı) visible only in Compare mode
- [ ] Clicking each button changes compare_mode in settings
- [ ] Layout re-renders correctly for each sub-mode

### Checkpoint B: Layout integrity
- [ ] 4-way layout fills available height without overflow
- [ ] ReviewHeader at top of left column
- [ ] FourWayGrid fills remaining left space
- [ ] ResolutionPanel fixed at right, ~280-300px wide
- [ ] Footer visible below both columns
- [ ] No horizontal scroll at 1280px+

### Checkpoint C: No overlap
- [ ] NLP Toolbar popup does not overlap resolution panel
- [ ] Floating chat does not overlap resolution panel
- [ ] Active Learning panel does not overlap 4-way content
- [ ] Save toast renders above all elements

### Checkpoint D: Data flow
- [ ] GET /data/{idx} returns NEWUI fields for 4-way CSV
- [ ] GET /data/{idx} returns old fields for standard CSV
- [ ] Save & next sends all selected triplets from all active columns
- [ ] Auto-select GT trips for Tier 1 works

### Checkpoint E: No regression
- [ ] Standard compare mode unchanged
- [ ] Live compare mode unchanged
- [ ] Manual mode unchanged
- [ ] Helper Agent chat works
- [ ] NLP Toolbar works
- [ ] AI Suggestions work
- [ ] Active Learning panel works

---

## Verification

1. ✅ `npx tsc --noEmit` — 0 TypeScript errors
2. ✅ `npx vitest run` — all frontend tests pass (existing + new)
3. ✅ `python -m pytest tests/ -q --tb=short` — all backend tests pass
4. ✅ Sub-mode toggle switches between Standard / 4-Way / Live
5. ✅ No visual overlap between resolution panel and floating chat
6. ✅ NLP Toolbar triggers on text selection in 4-way mode
7. ✅ Footer always visible
8. ✅ All 6 mode states render without layout breakage

---

## PLANNING COMPLETE
