# Task 5 Kickoff — Restore Original AnnoABSA manual screen + mode toggle

This is the final task for Phase 1. Full context is below. Read carefully before proposing a plan.

## Task

The current UI is a fixed three-column layout designed for LLM comparison. We need to restore the "original" AnnoABSA experience: a click-to-select-phrase manual annotator. This requires a new UI mode that is toggleable and does not disrupt the existing comparison view.

### Current state (Verify before coding)

- **ManualInputForm.tsx:** This exists but is a simple form. It lacks the logic to handle character spans (start/end positions).
- **Backend Readiness:** The backend already computes and stores `at_start`, `at_end`, `ot_start`, `ot_end`. 
- **Configuration:** Check `main.py` settings. The flags `click_on_token`, `auto_clean_phrases`, and `save_phrase_positions` are already exposed via `/settings`.
- **Constraint:** Do not touch the backend position-logic. Your job is to make the frontend consume/produce these fields correctly.

### What to build

1. **`PhraseAnnotator` Component:**
   - Implement click/drag-select functionality on the `review_text`.
   - Implement "Token mode" (snapping selection to word boundaries) vs. "Character mode" based on the `click_on_token` config flag.
   - Popup/Inline form for assigning attributes (`aspect_term`, `opinion_term`, `aspect_category`, `sentiment_polarity`).
   - Inline highlighters using existing polarity color coding (Emerald/Rose/Amber).
   - Support for `NULL`/implicit aspect terms.
2. **Mode Toggle:**
   - A toggle in the header: "Compare 2 LLMs" vs "Manual".
   - State should be per-review (UI `useState`), not persisted to config.
   - Middle-of-review toggling must NOT lose triplets (only `loadReviewRow` clears the state).
3. **Chat Panel Toggle:**
   - Independent toggle to show/hide `HelperAgentChatbox`.
   - Layout should reflow to fill the space when the chatbox is hidden.
   - Default: Visible.

### Critical Notes

- **Position Convention:** **Read `main.py` position-finding logic (~L529-603 and ~L1023-1034) before writing any frontend code.** You must ensure your frontend offsets match the backend's 0-indexed, inclusive-end convention exactly.
- **Save Contract:** Ensure your new annotator produces the exact `TripletItem` JSON structure that the existing `handleNextReview` save flow expects.
- **Helper Agent:** Confirm by inspecting `App.tsx` whether the chat panel needs to persist in Manual mode or if it should be restricted. If the code implies ambiguity, assume it stays visible as an "orthogonal display preference" unless it breaks the layout.

### Definition of done

- Manual mode renders a functional, span-based click/drag annotator with inline highlighting.
- Saving an annotation results in a valid `TripletItem` with `at_start`/`at_end` that correctly maps to the backend's expectations.
- Toggling modes maintains current-review progress.
- Chat panel toggles independently and the layout reflows cleanly.
- `click_on_token` and other relevant flags (from `/settings`) dynamically adjust the annotator behavior.

---

## What I need from you

1. A step-by-step execution plan in the `[Step] → verify: [how I'll check this worked]` format. 
2. A brief note confirming you have read the position-finding logic in `main.py` and understand the offset convention.
3. Wait for my go-ahead.
4. Once approved, provide the full file contents (or clearly marked diffs) for every file you change.

If you need to see the exact current contents of `main.py` (position logic) or `App.tsx` (JSX layout) before formulating your plan, explicitly ask for them now.