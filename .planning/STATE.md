# STATE.md — AnnoABSA Project State

**Last updated:** 2026-07-13

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-07-13)

**Core value:** A researcher can efficiently annotate Turkish reviews for ABSA triplets using manual selection, AI suggestions, or autonomous pipeline actions.

---

## Current Phase

**Phase 7.4 — 4-Way Polish: Demo, Filters, Auto-Save & Export**

Plans: 0/4 complete

**Status:** ○ Not started

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
| 7.2 (Testing & TS Fixes) | ◐ (planned) | 0/5 | 0% |
| 7.3 (Autonomous Pipeline) | ○ | 0/6 | 0% |
| 7.4 (4-Way Polish) | ○ | 0/4 | 0% |

---

## Codebase Map

See: `.planning/codebase/` (7 documents, 2,109 lines)

**Map last updated:** 2026-07-13

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
| `frontend/src/components/` | 20 React components |
| `frontend/src/hooks/` | useTextSelection, useDarkMode |
| `frontend/src/types.ts` | TripletItem, Settings (4-way), AppActions |
| `tests/` | 128 pytest tests |
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

### Test Results
- Backend: 128 passed, 0 failed
- Frontend: 64 passed, 0 failed (51 existing + 13 new ResolutionPanel tests)
- TypeScript: 0 new errors (3 pre-existing, unchanged)

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

*STATE.md last updated: 2026-07-13 after Phase 7.1 completion and Phase 7.4 definition*