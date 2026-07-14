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

- [ ] **NEWUI-11**: Display CSV column names (e.g. `gemma4_31b_label`) on 2x2 grid card headers alongside short names.
- [ ] **NEWUI-12**: Demo mode that auto-loads pre-built sample data showing all 3 tier scenarios.
- [ ] **NEWUI-13**: Tier filter dropdown (All / Tier 1 / Tier 2 / Tier 3) filters review queue by tier.
- [ ] **NEWUI-14**: Auto-save on review navigation (next/previous) with toast confirmation.
- [ ] **NEWUI-15**: Visible save button in resolution panel (`💾 Kaydet ve İlerle`).
- [ ] **NEWUI-16**: CSV export endpoint `GET /data/export-4way` and frontend download button.

### TEST — Testing Coverage

- [ ] **TEST-01**: Tests for `services/active_learning.py` — `train_labeled_data()`, `get_uncertainty_scores()`, `labeled_texts_from_data()`.
- [ ] **TEST-02**: Tests for `app/routes/learning.py` — `GET /learning/suggestions`, `GET /learning/predict/{idx}` via TestClient.
- [ ] **TEST-03**: Tests for `cli/` package — `cli/config.py` (ABSAAnnotatorConfig), `cli/convert.py` (std_triplets_to_label), `cli/runner.py` (smoke tests).
- [ ] **TEST-04**: Endpoint tests for `app/routes/settings.py` (GET/PATCH /settings), `app/routes/timing.py` (POST /timing, GET /avg-annotation-time), `app/routes/upload.py` (POST /upload-data, POST /auto-add-positions).

### TSFIX — TypeScript Fixes

- [ ] **TSFIX-01**: Fix pre-existing TS error: `Property 'rect' does not exist on type` in `App.tsx:447`.
- [ ] **TSFIX-02**: Fix pre-existing TS error: `'global' is deprecated` in `NlpHelperToolbar.test.tsx`.
- [ ] **TSFIX-03**: Verify `tsconfig.json` `includes` pattern covers all source files.

### AUTOPILOT — Autonomous Annotation Pipeline

- [ ] **AUTOPILOT-01**: Backend prompt — teach the Helper Agent's LLM to generate `[[action:...]]` directives in chat responses. Update `DEFAULT_CHAT_TEMPLATE` or system prompt with action instruction examples.
- [ ] **AUTOPILOT-02**: Keyboard shortcut `Ctrl+Shift+L` to toggle Active Learning suggestions panel.
- [ ] **AUTOPILOT-03**: Auto-suggest banner — when a review has high uncertainty (from active learning model), show a small banner in the UI suggesting the user annotate this review next.
- [ ] **AUTOPILOT-04**: `selectTriplet(role, id)` action — per-triplet selection from Helper Agent, allowing the agent to individually select/deselect specific triplets.
- [ ] **AUTOPILOT-05**: `addTriplet(aspect_term, aspect_category, polarity)` action — allow Helper Agent to create manual triplets programmatically.
- [ ] **AUTOPILOT-06**: Endpoint returning AI predictions formatted as part of the chat response — so the Helper Agent can read predictions, reason about them, and act on them.
- [ ] **AUTOPILOT-07**: `annotateAll()` pipeline action — predict → select all predicted triplets → save → advance to next review. Full autonomous annotation cycle.

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
| NEWUI-11 through NEWUI-16 | Phase 7.4 | Pending |
| TEST-01 through TEST-04 | Phase 7.2 | Pending |
| TSFIX-01 through TSFIX-03 | Phase 7.2 | Pending |
| AUTOPILOT-01 through AUTOPILOT-07 | Phase 7.3 | Pending |

**Coverage:**
- v1 requirements: 10 (NEWUI) + 6 (NEWUI-POLISH) + 4 (TEST) + 3 (TSFIX) + 7 (AUTOPILOT) = 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-13*
*Last updated: 2026-07-13 after Phase 7.1 completion and Phase 7.4 definition*
