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

## Phase 7.2 — Testing & TypeScript Fixes

**Goal:** Close testing gaps and fix pre-existing TS errors.

**Requirements:** TEST-01 through TEST-04, TSFIX-01 through TSFIX-03

**Plans:**
| Plan | Description | Est. effort |
|---|---|---|
| 1 | Tests for `services/active_learning.py` | Easy |
| 2 | Tests for `app/routes/learning.py` | Easy |
| 3 | Tests for `cli/` package (config, convert, runner) | Easy |
| 4 | Endpoint tests for settings/timing/upload routes | Medium |
| 5 | Fix 3 pre-existing TS errors | Easy |

**Wave execution:** Parallel (all independent)

---

## Phase 7.3 — Autonomous Annotation Pipeline

**Goal:** Enable the Helper Agent to fully annotate reviews autonomously — predict, select, save, advance — without human intervention.

**Requirements:** AUTOPILOT-01 through AUTOPILOT-07

**Plans:**
| Plan | Description | Est. effort |
|---|---|---|
| 1 | Backend prompt: teach LLM to generate `[[action:...]]` directives in chat | Easy |
| 2 | Keyboard shortcut for Active Learning panel (Ctrl+Shift+L) | Easy |
| 3 | Auto-suggest banner on uncertain reviews | Medium |
| 4 | `selectTriplet(role, id)` and `addTriplet(...)` actions + AppActions wiring | Medium |
| 5 | Endpoint returning AI predictions in chat response for agent consumption | Hard |
| 6 | `annotateAll()` pipeline action: predict → select → save → next | Hard |

**Wave execution:** Sequential (pipeline depends on per-triplet actions and prediction endpoint)

---

## Phase 7.4 — 4-Way Polish: Demo, Filters, Auto-Save & Export

**Goal:** Polish the 4-Way compare mode with a demo data viewer, categorical tier filtering, auto-save on navigation, and CSV export for annotated outputs.

**Requirements:** NEWUI-11 through NEWUI-16

**Plans:**
| Plan | Description | Est. effort |
|------|-------------|-------------|
| 1 | Frontend: Column header names + Demo data mode toggle with pre-built sample cases | Medium |
| 2 | Frontend: Tier filter dropdown (All / Tier 1 / Tier 2 / Tier 3) on review navigation | Medium |
| 3 | Frontend+Backend: Auto-save on review navigation + visible save button in resolution panel | Medium |
| 4 | Backend: 4-way output export endpoint + frontend export button | Medium |

**Wave execution:** Sequential (filter depends on tier data available, export depends on save flow)

---

## Milestone Completion Criteria

- [ ] NEWUI: 4-way Compare mode renders correctly with all 3 curation tiers functional
- [ ] TEST: 24+ new tests added (160→184+), all pass
- [ ] TSFIX: 0 pre-existing TS errors
- [ ] AUTOPILOT: Helper Agent can fully annotate a review autonomously (predict → select → save → next)
- [ ] All 133 existing backend tests still pass
- [ ] All 51 existing frontend tests still pass

---

## Future Milestones (beyond Phase 7)

| Milestone | Description | Dependencies |
|---|---|---|
| Phase 8 | Embedding-based active learning (SentenceTransformer over TF-IDF) | Phase 7.2 test coverage |
| Phase 9 | Export/import annotation progress, undo support | None |
| Phase 10 | Multi-user / lightweight auth for shared deployment | Architecture review |

---
*ROADMAP last updated: 2026-07-13 after Phase 7 initialization*
