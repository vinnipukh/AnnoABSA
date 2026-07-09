# Session Analysis — Phase 1, Task 5 (AnnoABSA)

> Full-session retrospective: PhraseAnnotator rebuild, floating chat widget, CSV upload, and layout fixes.

## SCHEMA/DATA MODEL

- Extended `TripletItem` with `opinion_term`, `at_start`, `at_end`, `ot_start`, `ot_end` fields — `frontend/src/types.ts`
- Added `AspectItem` interface and `ColorClasses` type alias required by the existing `phraseColoring.tsx` module — `frontend/src/types.ts`

## UI/UX DECISION

- Mode toggle (Compare LLMs / Manual) added to header, state is per-review `useState` not persisted — `frontend/src/App.tsx`
- Floating chat widget positioned `fixed bottom-14 right-4` with `z-50`, independent of main flex layout — `frontend/src/components/HelperAgentChatbox.tsx`
- 4-corner resize handles (tl/tr/bl/br) with distinct cursors (`nwse-resize` / `nesw-resize`) tracking `right`/`bottom` offset state for left/top edge drag — `frontend/src/components/HelperAgentChatbox.tsx`
- Header bar acts as drag-to-move handle (`cursor-move`, `onMouseDown={startMove}`, updates `right`/`bottom` clamped ≥ 0) — `frontend/src/components/HelperAgentChatbox.tsx`
- Save/Clear buttons moved from inline workspace to a thin `h-10` footer bar below the annotation area — `frontend/src/App.tsx`
- UI language unified to Turkish (button labels, instructions, status text) — `frontend/src/App.tsx`, `frontend/src/components/PhraseAnnotator.tsx`
- Annotation popup rendered as a centered fixed modal (`fixed z-50 inset-x-4 top-1/2 -translate-y-1/2 max-w-sm`) with backdrop overlay and scrollable body (`max-h-[70vh] overflow-y-auto`) — `frontend/src/components/PhraseAnnotator.tsx`
- CSV/JSON file upload button added to header, POSTs to `/upload-data` endpoint via hidden `<input type="file">` — `frontend/src/App.tsx`

## BUG/ISSUE

- Annotation popup rendered behind other elements because `position: absolute` was clipped by `overflow-hidden` on parent containers; fixed by changing to `position: fixed` with viewport coordinates and `z-50` — `frontend/src/components/PhraseAnnotator.tsx`
- Cannot select text because `onMouseUp` + `window.getSelection()` approach broke normal cursor interaction and inline `<span>` elements fragmented the DOM selection; root cause was using drag-select instead of the original AnnoABSA's two-click character-selection pattern — fixed by rewriting to character-by-character click handlers — `frontend/src/components/PhraseAnnotator.tsx`
- Text highlight rendering showed visible vertical borders between adjacent characters because each character was its own `<span>` with individual background; fixed by grouping consecutive same-style characters into continuous runs using run-length encoding — `frontend/src/components/PhraseAnnotator.tsx`
- Minimize and close buttons in the chat header both called `setMinimized(true)`, causing user confusion; removed the close (✕) button — `frontend/src/components/HelperAgentChatbox.tsx`
- Save button in main layout overlapped with chat input; fixed by moving the button to a dedicated footer bar and making the chat a floating overlay — `frontend/src/App.tsx`
- Floating chat badge at `bottom-4` collided with the footer bar buttons; raised to `bottom-14` — `frontend/src/components/HelperAgentChatbox.tsx`

## AGENT BEHAVIOR

- First implementation of PhraseAnnotator used `window.getSelection()` drag-select instead of the original AnnoABSA's two-click-per-character approach; this broke text selection entirely. Required user report ("can't even mark it with my cursor") and consulting the original GitHub repo to discover the correct character-by-character click pattern — `frontend/src/components/PhraseAnnotator.tsx` (initial vs rewritten)
- Import pruning was too aggressive: removed `useMemo` from imports without noticing it was still used by `renderedText`, causing a TypeScript error — `frontend/src/components/PhraseAnnotator.tsx`

## DEVIATION FROM ORIGINAL

- Original AnnoABSA opened phrase selection popup as a side panel/form alongside the text; this implementation uses a centered fixed modal with backdrop overlay — `frontend/src/components/PhraseAnnotator.tsx`
- Original AnnoABSA had separate click handlers for aspect term and opinion term selection; this implementation combines both into a single popup form — `frontend/src/components/PhraseAnnotator.tsx`
- Helper Agent chat converted from an inline layout panel to a floating, draggable, 4-corner resizable window with minimize-to-badge — `frontend/src/components/HelperAgentChatbox.tsx`
- Added CSV/JSON file upload directly from the UI (the original only loads data via CLI at startup) — `main.py` (`POST /upload-data`), `frontend/src/App.tsx`

## OPEN WORK

- Duplicate detection added only for exact span+category match; overlapping but non-identical spans are not deduplicated — `frontend/src/components/PhraseAnnotator.tsx`
- `import.meta.env` TypeScript error (line 97 of App.tsx) is pre-existing and not resolved; requires Vite client type declarations — `frontend/src/App.tsx`
- `predict_llm`/`predict_openai` backward-compat wrappers default to `prompt_template=None` (English prompt); evaluation scripts (`eval.py`) bypass the Turkish prompt template — noted in Task 4 completion report
- Template constants are duplicated between `main.py` and `cli.py`; any future edits must update both copies — noted in Task 4 completion report
