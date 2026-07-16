---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-07-16T20:00:50.804Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 0
---

# STATE.md — AnnoABSA Project State

**Last updated:** 2026-07-16

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-07-13)

**Core value:** A researcher can efficiently annotate Turkish reviews for ABSA triplets using manual selection, AI suggestions, or autonomous pipeline actions.

---

**Current Phase**
Phase 7.5 — Active Learning, Filtering & Autopilot Rework

**Last Completed:** Arrow key navigation (← →) with settings toggle

  - `arrow_key_navigation` added to Settings interface + useSettings + SettingsPanel toggle
  - `useEffect` keyboard listener in App.tsx: Left/Right arrows → prev/next review
  - Guards against triggering while typing in INPUT/TEXTAREA/SELECT
  - Toggle in Ayarlar → Section 1 → "Ok tuşlarıyla gezinme (← →)"

---

## Phase Completion Summary

**Phase 7.1 — Compare Mode UI Rework (13 Jul 2026)**

- 5/5 plans executed
- 128 backend + 64 frontend tests passing
- `FourWayGrid.tsx`, `ResolutionPanel.tsx`, `CompactTripletChip.tsx`, `ReviewHeader.tsx` new
- 4-way CSV parser (`_detect_newui_columns`, `_load_4way_row`)

**Phase 7.2 — Testing & TypeScript Fixes (14 Jul 2026)**

- 5/5 plans executed
- 81 new backend tests (128→209), 23 new frontend tests (64→87) = 296 total
- 3 pre-existing TS errors resolved (0 remaining)
- Vite 4→5 upgrade, tsconfig target es5→es2016
- App.tsx split: 770→250 lines → 5 custom hooks
- Bug fix: `app/routes/timing.py` — HTTPException no longer swallowed by generic except

**Phase 7.3 — Autonomous Annotation Pipeline (14 Jul 2026)**

- 6/6 plans executed
- 18 new backend tests (209→227), 1 new frontend test (87→88) = 315 total
- 0 new TS errors, clean build
- 3 new `[[action:...]]` directives added to `DEFAULT_CHAT_TEMPLATE` (selectTriplet, addTriplet, annotateAll)
- `Ctrl+Shift+L` keyboard shortcut to toggle Active Learning panel
- `AutoSuggestBanner.tsx` — DaisyUI alert-info banner with Heroicons SVG, accessibility, touch targets
- `addTriplet(aspect_term, aspect_category, polarity)` 3-arg wrapper in AppActions, fully tested
- `GET /chat/predictions/{data_idx}` endpoint returning predictions as Turkish text + raw data (18 tests)
- `annotateAll(count?)` pipeline: predict → filter → addTriplet → saveAndNext → loop, with abort safety and progress toasts

---

## Phase Completion Summary

**Phase 7.1 — Compare Mode UI Rework (13 Jul 2026)**

- 5/5 plans executed
- 128 backend + 64 frontend tests passing
- `FourWayGrid.tsx`, `ResolutionPanel.tsx`, `CompactTripletChip.tsx`, `ReviewHeader.tsx` new
- 4-way CSV parser (`_detect_newui_columns`, `_load_4way_row`)

**Phase 7.2 — Testing & TypeScript Fixes (14 Jul 2026)**

- 5/5 plans executed
- 81 new backend tests (128→209), 23 new frontend tests (64→87) = 296 total
- 3 pre-existing TS errors resolved (0 remaining)
- Vite 4→5 upgrade, tsconfig target es5→es2016
- App.tsx split: 770→250 lines → 5 custom hooks (`useReviewNavigation`, `useAnnotationState`, `useAIPrediction`, `useSettings`, `useCompareMode`)
- Bug fix: `app/routes/timing.py` — HTTPException no longer swallowed by generic except

---

## Milestone Progress

| Phase | Status | Plans | Progress |
|---|---|---|---|
| 1 (Foundation) | ✓ | 5/5 | 100% |
| 2 (Settings & Suggestions) | ✓ | 2/2 | 100% |
| 3 (NLP Toolbox) | ✓ | 3/3 | 100% |
| 4 (Live Compare) | ✓ | 4/4 | 100% |
| 5 (Cleanup & Breakup) | ✓ | 8/8 | 100% |
| 6 (Polish, Autopilot, ML) | ✓ | 10/10 | 100% |
| 7.1 (Compare UI Rework) | ✓ | 5/5 | 100% |
| **7.2 (Testing & TS Fixes)** | **✓** | **5/5** | **100%** |
| **7.3 (Autonomous Pipeline)** | **✓** | **6/6** | **100%** |
| **7.5 (Active Learning Autopilot)** | **✓** | **4/4 plans** | **100%** |

---

## Test Results

| Suite | Count |
|---|---|
| Backend (pytest) | **237 passed**, 0 failed (was 227) |
| Frontend (vitest) | **88 passed**, 0 failed |
| TypeScript (tsc) | **0 errors** |
| Emoji in modified files | **0** — App.tsx, FourWayGrid.tsx, ResolutionPanel.tsx all clean |

---

## Risk Register

See: `.planning/codebase/` (7 documents, 2,109 lines)

**Map last updated:** 2026-07-13

---

## Phase 7.5 Deliverables

### Backend

- **`predict_texts()`** in `services/active_learning.py` — batch prediction for multiple texts with confidence threshold filtering, returns sorted predictions
- **`AutopilotRequest`** schema in `models/schemas.py` — `count`, `confidence_threshold`, `start_index` parameters
- **`POST /learning/autopilot`** endpoint — trains on labeled data, batch-predicts for unlabeled reviews, saves annotations, returns annotated count + remaining count

### Frontend

- **"Otomatik Etiketle" button** in toolbar — calls batch autopilot endpoint, shows loading spinner + "Etiketleniyor..." during execution
- Success toast: `"{N} inceleme etiketlendi ({M} kaldi)"`
- Error handling: backend offline → error toast, no crash
- Arrow key navigation (← →) with settings toggle (completed earlier)

### Tests

| File | Tests | What it covers |
|------|-------|----------------|
| `tests/test_active_learning.py` | 5 new | `predict_texts` — batch prediction, empty input, confidence filtering, None model data, sorted output |
| `tests/test_learning_routes.py` | 7 new | `POST /learning/autopilot` — happy path, <2 labeled → 400, single labeled → 400, all labeled → annotated=0, count limit, start_index, valid JSON saving |

### Test Results

- Backend: 236 passed (+12 over Phase 7.4)
- Frontend: 94 passed (+6 over Phase 7.3)

### Phase 7.5 Summary

- **Plan 1:** Backend autopilot endpoint (`predict_texts` + `POST /learning/autopilot`) ✅
- **Plan 2:** Frontend batch autopilot button ("Otomatik Etiketle") ✅
- **Plan 3:** Integration tests (12 new backend tests + existing frontend autopilot tests) ✅
- **Plan 4:** 4-way default mode, Tier 1 removed from filter, null-safety, comprehensive tests ✅

### Frontend

- **FourWayGrid.tsx**: CSV column names displayed as subtle monospace labels on grid card headers
- **demoData.ts**: 6-sample demo data covering all 3 tiers (Tier 1/2: 2 each, Tier 3: 2)
- **Demo toggle**: 4th mode button — loads FALLBACK_DATA-style demo reviews instead of backend
- **Tier filter dropdown**: DaisyUI `<select>` with All/Tier 1/2/3 — navigation skips non-matching reviews
- **Auto-save on prev**: `handlePrevReview` now saves annotations before navigating
- **Save button**: Heroicons save SVG button in ResolutionPanel header (next to tier badge)
- **Export button**: "Dışa Aktar" download button in toolbar

### Backend

- **`GET /data/export-4way`**: New endpoint returning CSV with all original columns + `selected_triplets`, `resolution_tier`, `annotator_notes`
- **`tests/test_export.py`**: 9 tests covering CSV format, headers, row count, column presence

### Emoji Remediation

- App.tsx: Removed ◀/▶ from prev/next buttons, all ✅/❌ from toast messages (0 emoji)
- FourWayGrid.tsx: 0 emoji (already clean)
- ResolutionPanel.tsx: 0 emoji (already used Heroicons)

## Final Phase 7 Totals

- Backend tests: 128 → 237 (+109 over Phase 7)
- Frontend tests: 64 → 88 (+24 over Phase 7)
- TypeScript errors: 3 → 0
- Emoji in source: various → 0 in all modified files
- Vite: 4 → 5.4.21
- Components: 16 → 21 (AutoSuggestBanner, 5 hooks, demoData)
- Route modules: 7 → 9 (chat_predictions, export)

---

## Key Paths

| Path | Purpose |
|---|---|
| `main.py` | FastAPI launcher, 50 lines |
| `app/config.py` | Global config state |
| `app/data.py` | Data I/O (CSV/JSON) — NEWUI 4-way CSV parser |
| `app/positions.py` | Position auto-fill |
| `app/routes/` | 7 route modules |
| `services/` | 5 service modules |
| `cli/` | CLI package (config, runner, convert) |
| `cli.py` | Thin wrapper, 6 lines |
| `models/schemas.py` | Pydantic models |
| `frontend/src/App.tsx` | Root React component — 4-way mode, dictionary state |
| `frontend/src/components/` | 21 React components (new: `AutoSuggestBanner`) |
| `frontend/src/hooks/` | 6 hooks: `useTextSelection`, `useReviewNavigation`, `useAnnotationState`, `useAIPrediction`, `useSettings`, `useCompareMode` |
| `frontend/src/types.ts` | TripletItem, Settings (4-way), AppActions (18 methods) |
| `tests/` | 237 pytest tests (was 128 at Phase 6) |
| `app/routes/` | 9 route modules (3 new: `chat_predictions`, `export`, `learning`) |
| `agentdocs/` | Phase plans and reports (being consolidated) |
| `.planning/` | GSD project planning documents |
| `.hermes/plans/` | Historical implementation plans |

---

## Phase 7.1 Deliverables

### New Components

- `CompactTripletChip.tsx` — Single-line triplet chip for 2x2 grid columns
- `ReviewHeader.tsx` — Standalone review text display with NLP toolbar support
- `FourWayGrid.tsx` — 2x2 grid with consensus diamond (color-coded by majority_vote)
- `ResolutionPanel.tsx` — 3-tier curation panel (Auto-Accept/Quick Diff/Manual)

### Backend

- `NEWUI_COLUMNS` — Column name mapping for 4-way CSV
- `_detect_newui_columns()` — Auto-detect NEWUI columns in DataFrame
- `_load_4way_row()` — Parse single NEWUI CSV row into 8 response fields

---

## Phase 7.2 Deliverables

### New Test Files

| File | Tests | Target |
|---|---|---|
| `tests/test_active_learning.py` | 18 | `services/active_learning.py` |
| `tests/conftest.py` | — | Shared fixtures (csv_path, app, TestClient) |
| `tests/test_learning_routes.py` | 16 | `app/routes/learning.py` |
| `tests/test_cli.py` | 31 | `cli/config.py`, `cli/convert.py`, `cli/runner.py` |
| `tests/test_routes_misc.py` | 16 | Settings, timing, upload routes |

### Frontend Refactoring

- `App.tsx` 770→250 lines, 5 custom hooks extracted
- `frontend/src/hooks/useReviewNavigation.ts` — Index/data/save management
- `frontend/src/hooks/useAnnotationState.ts` — Triplet selection state
- `frontend/src/hooks/useAIPrediction.ts` — AI/live prediction state
- `frontend/src/hooks/useSettings.ts` — Settings fetch/PATCH state
- `frontend/src/hooks/useCompareMode.ts` — Mode toggle state

### Infrastructure

- Vite 4→5 (`^5.4.19`), `@vitejs/plugin-react` `^4.4.1`
- tsconfig: `target: "es5"` → `"es2016"`, `lib: ["es2016"]`
- 3 TypeScript errors resolved (TSFIX-01, TSFIX-02, TSFIX-03)

### Bug Fix

- `app/routes/timing.py`: `HTTPException(404)` for out-of-range index was caught by generic `except Exception` and returned as 500. Restructured try/except to pass intentional HTTPExceptions through.

### Test Results

- Backend: 209 passed, 0 failed (was 128)
- Frontend: 87 passed, 0 failed (was 64)
- TypeScript: 0 errors (was 3)

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NEWUI CSV format changes mid-implementation | Low (implemented) | Medium | Data model defined and validated against sample CSV |
| 2x2 grid responsiveness breaks on small screens | Low | Medium | Compact chip approach tested at 1280px minimum |
| Autopilot LLM fails to generate valid `[[action:...]]` directives | Medium | High | Validate generated actions; fallback to manual mode |
| Active learning cold start (<2 labeled reviews) | Low | Medium | Use LLM predictions as pseudo-labels for first iteration |
| React 19 + test library incompatibility | Low | Medium | Already documented workaround (createRoot + flushSync) |
| FastAPI single-thread blocks on LLM calls | Medium | Medium | Add `--workers 4` to uvicorn; document workaround |

---

*STATE.md last updated: 2026-07-14 — Phase 7.5 started (arrow key navigation + toggle)*

## Accumulated Context

### Roadmap Evolution

- Phase 7.6 added: 4-way diff readability: move LLM diff and majority label under LLM-suggested labels; enlarge diffs for readability
