# STATE.md — AnnoABSA Project State

**Last updated:** 2026-07-13

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-07-13)

**Core value:** A researcher can efficiently annotate Turkish reviews for ABSA triplets using manual selection, AI suggestions, or autonomous pipeline actions.

**Current focus:** Phase 7 — Polish, Hardening & Autonomous Annotation Pipeline

---

## Current Phase

**Phase 7.1 — Compare Mode UI Rework**

Plans: 0/5 complete

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
| 7.1 (Compare UI Rework) | ○ | 0/5 | 0% |
| 7.2 (Testing & TS Fixes) | ○ | 0/5 | 0% |
| 7.3 (Autonomous Pipeline) | ○ | 0/6 | 0% |

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
| `app/data.py` | Data I/O (CSV/JSON) |
| `app/positions.py` | Position auto-fill |
| `app/routes/` | 7 route modules |
| `services/` | 5 service modules |
| `cli/` | CLI package (config, runner, convert) |
| `cli.py` | Thin wrapper, 6 lines |
| `models/schemas.py` | Pydantic models |
| `frontend/src/App.tsx` | Root React component |
| `frontend/src/components/` | 15 React components |
| `frontend/src/hooks/` | useTextSelection, useDarkMode |
| `frontend/src/types.ts` | TripletItem, Settings, AppActions |
| `tests/` | 133 pytest tests |
| `agentdocs/` | Phase plans and reports (being consolidated) |
| `.planning/` | GSD project planning documents |
| `.hermes/plans/` | Historical implementation plans |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NEWUI CSV format changes mid-implementation | Medium | Medium | Define data model upfront; validate against sample CSV |
| 2x2 grid responsiveness breaks on small screens | Medium | Medium | Mobile-first CSS; test at 1280px minimum |
| Autopilot LLM fails to generate valid `[[action:...]]` directives | Medium | High | Validate generated actions; fallback to manual mode |
| Active learning cold start (<2 labeled reviews) | Low | Medium | Use LLM predictions as pseudo-labels for first iteration |
| React 19 + test library incompatibility | Low | Medium | Already documented workaround (createRoot + flushSync) |
| FastAPI single-thread blocks on LLM calls | Medium | Medium | Add `--workers 4` to uvicorn; document workaround |

---
*STATE.md last updated: 2026-07-13 after Phase 7 initialization*
