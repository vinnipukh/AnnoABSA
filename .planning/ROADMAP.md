# ROADMAP: AnnoABSA Phase 7

**Defined:** 2026-07-13
**Milestone:** Phase 7 — Polish, Hardening & Autonomous Annotation Pipeline

---

## Phase 7.1 — Compare Mode UI Rework (NEWUI)

**Goal:** Redesign the Compare mode from a 2-column (Model A / Model B) layout to a 4-way 2x2 grid with consensus resolution panel.

**Requirements:** NEWUI-01 through NEWUI-10

**Plans (estimated):**
| Plan | Description | Est. effort |
|---|---|---|
| 1 | Backend: modify data loading to support 4-column CSV (`semeval_tr_llm_annotated.csv`), new endpoint(s) for consensus data | Medium |
| 2 | Frontend: 2x2 grid component with 4 model cards, review header, consensus badge | Hard |
| 3 | Frontend: Resolution panel with Primary Suggestion Box, Diff Tracker Box, action buttons | Medium |
| 4 | Frontend: 3-tier state logic (Auto-Accept, Quick Diff, High-Confusion) with color-coded badges | Medium |
| 5 | Integration: wire new mode into existing mode toggle (Compare/Manual), ensure no overlap with NLP toolbar/chat | Medium |

**Wave execution:** Sequential (layout depends on data model, resolution panel depends on grid)

---

## Phase 7.2 — Testing & TypeScript Fixes (✅ COMPLETE)

**Goal:** Close testing gaps and fix pre-existing TS errors.

**Requirements:** TEST-01 through TEST-04, TSFIX-01 through TSFIX-03

**Results:**
- 81 new backend tests + 23 new frontend tests
- 3 TS errors resolved (0 remaining)
- Vite 4→5, tsconfig es5→es2016, App.tsx → 5 hooks
- Bug fix: timing route 404→500 swallowing

**Plans:**
| Plan | Description | Est. effort | Status |
|---|---|---|---|
| 1 | Tests for `services/active_learning.py` | Easy | ✅ 18 tests |
| 2 | Tests for `app/routes/learning.py` | Easy | ✅ 16 tests |
| 3 | Tests for `cli/` package (config, convert, runner) | Easy | ✅ 31 tests |
| 4 | Endpoint tests for settings/timing/upload routes | Medium | ✅ 16 tests |
| 5 | Fix 3 pre-existing TS errors + hardening | Medium | ✅ 0 TS errors |

---

## Phase 7.3 — Autonomous Annotation Pipeline (✅ COMPLETE)

**Goal:** Enable the Helper Agent to fully annotate reviews autonomously — predict, select, save, advance — without human intervention.

**Requirements:** AUTOPILOT-01 through AUTOPILOT-07

**Results:**
- 18 new backend tests (209→227), 1 new frontend test (87→88)
- 3 new `[[action:...]]` directives in `DEFAULT_CHAT_TEMPLATE`
- `Ctrl+Shift+L` shortcut, `AutoSuggestBanner`, `addTriplet(term, category, polarity)` wrapper
- `GET /chat/predictions/{idx}` endpoint with 18 tests
- `annotateAll(count?)` pipeline action with abort safety and progress toasts

**Plans:**
| Plan | Description | Est. effort | Status |
|---|---|---|---|
| 1 | Backend prompt: add 3 missing `[[action:...]]` directives to `DEFAULT_CHAT_TEMPLATE` | Easy | ✅ |
| 2 | Keyboard shortcut for Active Learning panel (Ctrl+Shift+L) | Easy | ✅ |
| 3 | Auto-suggest banner on uncertain reviews (inline banner + toast) | Medium | ✅ |
| 4 | `selectTriplet(role, id)` verification + `addTriplet(term, category, polarity)` wrapper + AppActions wiring | Medium | ✅ |
| 5 | `GET /chat/predictions/{data_idx}` endpoint returning chat-formatted ML predictions | Hard | ✅ 18 tests |
| 6 | `annotateAll()` pipeline action: predict → select → save → next (N reviews) | Hard | ✅ |

---

## Phase 7.4 — 4-Way Polish: Demo, Filters, Auto-Save & Export (✅ COMPLETE)

**Goal:** Polish the 4-Way compare mode with a demo data viewer, categorical tier filtering, auto-save on navigation, and CSV export for annotated outputs.

**Requirements:** NEWUI-11 through NEWUI-16

**Results:**
- 9 new backend tests (227→237), 0 new frontend tests needed
- CSV column names on grid card headers; Demo mode toggle (6-sample data, all 3 tiers)
- Tier filter dropdown (All/Tier 1/2/3) filtering review queue
- Auto-save on prev navigation + save button in resolution panel
- `GET /data/export-4way` endpoint with 9 tests + frontend download button
- All modified files scanned: 0 emoji remaining (App.tsx, FourWayGrid.tsx, ResolutionPanel.tsx)

**Plans (estimated):**
| Plan | Description | Est. effort |
|---|---|---|
| 1 | Tier filter fix: reference equality bug in getReviewTier, NaN handling, backend tier endpoint for fast navigation | Medium |
| 2 | Active learning rework: stable suggestions pipeline, tuple/dict label parsing, consensus-based filtering, reliable navigation from suggestions | Medium |
| 3 | Autopilot rework: reliable auto-annotation loop, decoupled from tier filter, progress tracking | Medium |

**Wave execution:** Parallel (3 independent workstreams)

---

## Phase 7.5 — Active Learning, Filtering & Autopilot Rework (✅ COMPLETE)

**Goal:** Fix tier filtering (reference equality bug, NaN handling, slow sequential fetches), stabilize active learning suggestions, and make the autopilot annotation pipeline reliable.

**Requirements:** AL-01 through AL-09

**Results:**
- 12 new backend tests (224→236), 0 new frontend tests needed (existing 94 still pass)
- `predict_texts()` service function for batch prediction with confidence threshold filtering
- `POST /learning/autopilot` endpoint for batch auto-annotation of unlabeled reviews
- "Otomatik Etiketle" button in toolbar calling batch autopilot endpoint
- Arrow key navigation (← →) with settings toggle
- 4-way mode is now the default on fresh start (config.py + useCompareMode)
- Tier 1 removed from filter dropdown (only All/Tier 2/Tier 3 shown)
- All modified files: 0 emoji, 0 TS errors

---

## Phase 7.6: 4-Way Diff Readability

**Goal:** Improve the 4-way compare resolution layout by moving the right-hand LLM diff and majority label content under the LLM-suggested labels, and increasing diff display size so users can read reported differences more easily.

**Depends on:** Phase 7.5

**Requirements:** UX-01 through UX-03

**Plans:** 3 plans

| Plan | Description | Est. effort |
|---|---|---|
| 1 | Frontend: reposition majority label and LLM diff content beneath LLM-suggested labels in the 4-way resolution area | Medium |
| 2 | Frontend: enlarge diff display typography/spacing while preserving responsive layout and no-toolbar-overlap constraints | Medium |
| 3 | Tests and accessibility: update component tests and verify readable diff layout, touch targets, reduced-motion behavior, and no emoji regressions | Medium |

**Wave execution:** Sequential (layout move first, readability sizing second, tests last)

---

## Milestone Completion Criteria

- [x] NEWUI: 4-way Compare mode renders correctly with all 3 curation tiers functional
- [x] TEST: 24+ new tests added (160→184+), all pass — actual: 81 backend + 23 frontend = 104 new
- [x] TSFIX: 0 pre-existing TS errors
- [x] AUTOPILOT: Helper Agent can fully annotate a review autonomously (predict → select → save → next)
- [x] NEWUI-POLISH: Demo mode, tier filter, auto-save, save button, CSV export
- [ ] UX: 4-way diff and majority label readability improvements
- [x] All 237 backend tests still pass
- [x] All 88 frontend tests still pass
- [x] 0 emoji in any modified source file

---

## Future Milestones (beyond Phase 7)

| Milestone | Description | Dependencies |
|---|---|---|
| Phase 8 | Embedding-based active learning (SentenceTransformer over TF-IDF) | Phase 7.2 test coverage |
| Phase 9 | Export/import annotation progress, undo support | None |
| Phase 10 | Multi-user / lightweight auth for shared deployment | Architecture review |

---
*ROADMAP last updated: 2026-07-16 after Phase 7.6 readability phase was added*
