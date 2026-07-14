# Requirements: AnnoABSA — Phase 7

**Defined:** 2026-07-13
**Core Value:** A researcher can efficiently annotate Turkish reviews for ABSA triplets using manual selection, AI suggestions, or autonomous pipeline actions — and export results in a sharable format.

## v1 Requirements (Phase 7)

### NEWUI — Compare Mode UI Rework

- [x] **NEWUI-01**: Redesign Compare mode as a 2x2 grid (Ground Truth + 3 LLM columns) with a resolution panel. Screen split: review header top, left-side 2x2 grid, right-side resolution panel.
- [x] **NEWUI-02**: Ingest `semeval_tr_llm_annotated.csv` with columns: `text`, `original_label`, `gemma4_31b_label`, `qwen3.6_35b_label`, `gpt_oss_120b_label`, `majority_vote`, `majority_label`, `consensus_intersection`, `original_llm_diff`.
- [x] **NEWUI-03**: 2x2 Grid cards: Top-Left (Ground Truth / `original_label`), Top-Right (Gemma 31B), Bottom-Left (Qwen 35B), Bottom-Right (GPT-OSS 120B). Render unedited triplets from data source.
- [x] **NEWUI-04**: Consensus badge at center intersection of 2x2 grid. Display `majority_vote` integer. Color-code: Green=3, Yellow=2, Red=1.
- [x] **NEWUI-05**: Resolution panel with arrow pointing from 2x2 grid. Primary Suggestion Box shows `majority_label` (vote>1) or `consensus_intersection` (vote=1). Diff Tracker Box shows `original_llm_diff` with monospaced/diff-style rendering.
- [x] **NEWUI-06**: Tier 1 — Auto-Accept: `majority_vote >= 2 AND majority_label == original_label` → green badge, pre-select triplets.
- [x] **NEWUI-07**: Tier 2 — Quick Diff Verification: `majority_vote >= 2 AND majority_label != original_label` → yellow badge, highlight Diff Tracker Box.
- [x] **NEWUI-08**: Tier 3 — High-Confusion Review: `majority_vote == 1` → red badge, hide `majority_label`, prompt manual review of 2x2 grid.
- [x] **NEWUI-09**: Action buttons in resolution panel: accept, edit, manual entry controls.
- [x] **NEWUI-10**: Responsive layout — no overlap with NLP Helper Toolbar or Helper Agent Chatbox. Drag-to-select text span remains intact in review header.

### NEWUI-POLISH — 4-Way Polish (Phase 7.4)

- [x] **NEWUI-11**: CSV column names on 2x2 grid card headers — monospace label below model name. Added `csvColumnNames` prop to FourWayGrid.
- [x] **NEWUI-12**: Demo mode with 6 pre-built sample reviews covering all 3 tiers. Toggle button in mode selector.
- [x] **NEWUI-13**: Tier filter dropdown (All / Tier 1 / 2 / 3) — navigation skips non-matching reviews. 50-iteration loop protection.
- [x] **NEWUI-14**: Auto-save on review navigation (prev and next) with toast confirmation.
- [x] **NEWUI-15**: Save button in resolution panel header — Heroicons save SVG, `aria-label="Kaydet"`, DaisyUI `btn`.
- [x] **NEWUI-16**: `GET /data/export-4way` endpoint returning CSV with all columns + `selected_triplets`, `resolution_tier`, `annotator_notes`. Frontend download button.

### TEST — Testing Coverage

- [x] **TEST-01**: Tests for `services/active_learning.py` — `train_labeled_data()`, `get_uncertainty_scores()`, `labeled_texts_from_data()`. 18 tests covering JSON/CSV extraction, edge cases, entropy scoring.
- [x] **TEST-02**: Tests for `app/routes/learning.py` — `GET /learning/suggestions`, `GET /learning/predict/{idx}` via TestClient. 16 tests covering ranked suggestions, error handling, all-labeled edge case.
- [x] **TEST-03**: Tests for `cli/` package — `cli/config.py` (ABSAAnnotatorConfig), `cli/convert.py` (std_triplets_to_label), `cli/runner.py` (port checks, config update). 31 tests.
- [x] **TEST-04**: Endpoint tests for `app/routes/settings.py` (GET/PATCH /settings), `app/routes/timing.py` (POST /timing, GET /avg-annotation-time), `app/routes/upload.py` (POST /upload-data, POST /auto-add-positions). 16 tests.

### TSFIX — TypeScript Fixes

- [x] **TSFIX-01**: Fix pre-existing TS error: `Property 'rect' does not exist on type` in `App.tsx:447` — added `rect?: DOMRect` to `nlpToolbarSelection` state type.
- [x] **TSFIX-02**: Fix pre-existing TS error: `'global' is deprecated` in `NlpHelperToolbar.test.tsx` — replaced `global.fetch = mockFetch` with `vi.stubGlobal('fetch', mockFetch)`.
- [x] **TSFIX-03**: Verify `tsconfig.json` `includes` pattern covers all source files — fixed by changing target `"es5"` → `"es2016"` and lib `["es2016"]`, which resolves the `includes` method availability.

### AUTOPILOT — Autonomous Annotation Pipeline

- [x] **AUTOPILOT-01**: Backend prompt — added 3 missing `[[action:...]]` directives (`selectTriplet`, `addTriplet`, `annotateAll`) to `DEFAULT_CHAT_TEMPLATE`. Template now has 15 total actions with Turkish descriptions.
- [x] **AUTOPILOT-02**: Keyboard shortcut `Ctrl+Shift+L` toggles Active Learning suggestions panel. Uses ref-forwarded callback pattern for stale closure safety.
- [x] **AUTOPILOT-03**: Auto-suggest banner (`AutoSuggestBanner.tsx`) — DaisyUI `alert alert-info` banner with Heroicons SVG, `role="alert"`, `aria-label` on dismiss, touch targets ≥44×44px, toast notification on first show. Conditionally rendered based on uncertainty > 0.7 and no labels.
- [x] **AUTOPILOT-04**: `selectTriplet(role, id)` — already existed in `AppActions` (line 127), wired at `App.tsx:291`. Verified working for all 6 roles.
- [x] **AUTOPILOT-05**: `addTriplet(aspect_term, aspect_category, polarity)` — new 3-arg wrapper in `AppActions`. Constructs a `TripletItem` with `auto_` ID and delegates to `addManualTriplet`. Fully tested.
- [x] **AUTOPILOT-06**: `GET /chat/predictions/{data_idx}` endpoint in `app/routes/chat_predictions.py` — returns Turkish chat text + raw predictions array. 18 tests covering 200, 404, 400, determinism.
- [x] **AUTOPILOT-07**: `annotateAll(count?)` pipeline action in `AppActions` — predict → filter >0.5 → addTriplet → saveAndNext → loop with abort safety, progress toasts, and N-review limit (default 5).

## v2 Requirements

Deferred to future phases. Tracked but not in current roadmap.

| Requirement | Reason |
|---|---|
| Embedding-based active learning (SentenceTransformer) | Phase 6 plan mentions this; TF-IDF sufficient for v1 |
| Database-backed persistence | CSV/JSON sufficient for research datasets |
| Multi-user support | Single-annotator research tool |
| CI/CD pipeline | Not yet needed |

## Out of Scope

| Feature | Reason |
|---|---|
| Persistent database | File-based CSV/JSON is sufficient for research datasets |
| Multi-user / auth | Single-annotator research tool |
| English UI | Turkish-language research tool |
| Collaborative annotation | Single-annotator workflow |
| E2E browser tests (Playwright) | Requires full stack; deferred |

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| NEWUI-01 through NEWUI-10 | Phase 7.1 | ✅ Complete |
| NEWUI-11 through NEWUI-16 | Phase 7.4 | ✅ Complete |
| TEST-01 through TEST-04 | Phase 7.2 | ✅ Complete |
| TSFIX-01 through TSFIX-03 | Phase 7.2 | ✅ Complete |
| AUTOPILOT-01 through AUTOPILOT-07 | Phase 7.3 | ✅ Complete |

**Coverage:**
- v1 requirements: 10 (NEWUI) + 6 (NEWUI-POLISH) + 4 (TEST) + 3 (TSFIX) + 7 (AUTOPILOT) = 30 total
- Complete: 30/30 ✅ — **Phase 7 fully complete!**
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-13*
*Last updated: 2026-07-14 — Phase 7 fully complete (all 30 requirements done)*
