# Contributing to AnnoABSA

Welcome! This document outlines the standard workflow for contributing. Follow these steps in order for every task.

---

## Workflow

### 1. Pick a task

Browse [`tasks.md`](tasks.md). Tasks are ordered by priority. Claim one by moving it to **In Progress** (or just start — no formal assignment needed).

If you're adding something not on the list, add a new row first so everyone can see what's being worked on.

### 2. Read the orientation docs

Before writing any code, read these in order:

| Doc | What it tells you |
|---|---|
| [`ProjectPrimer.md`](ProjectPrimer.md) | Stack, data format, how to run, working style rules |
| [`../docs/architecture_map.md`](../docs/architecture_map.md) | Module graph, process flow, file-to-task map, known landmines |
| [`session_reports/backend_reference.md`](session_reports/backend_reference.md) | Every function, endpoint, and module (one-page reference) |
| [`../tests/testcases.md`](../tests/testcases.md) | Regression test cases — what must keep working |

**Key rule:** read the **Known landmines** section in `../docs/architecture_map.md` before touching anything. Several past bugs are documented there and cost hours to rediscover.

### 3. Plan (then confirm)

Write a short plan covering:

```
1. [What you'll change] → verify: [how you'll check it worked]
2. [What you'll change] → verify: [how you'll check it worked]
```

Post it and wait for confirmation before coding. For small changes this can be brief.

### 4. Make changes

- **Surgical** — touch only what the task requires. No drive-by refactors.
- **Match style** — look at surrounding code and match its patterns.
- **One task at a time** — no scope creep.

### 5. Run verification

Execute the [Post-Feature Checklist](post_feature_checklist.md) in order:

```
1. Clean        — remove debug prints, unused imports, dead code
2. Compile      — py_compile all changed files
3. Test         — pytest tests/ (expected: 81 passed)
4. Smoke test   — if you changed an endpoint: start backend + frontend,
                  confirm the UI loads without console errors
5. Update docs  — backend_reference.md, docs/architecture_map.md,
                  ProjectPrimer.md, testcases.md (if applicable)
```

### 6. Commit

```
git add -A
git diff --cached --stat   # review what you're about to commit
git commit -m "short description of what and why"
```

Commit messages follow the conventional format: start with a verb in imperative mood, keep the subject under 72 characters, add a blank line then bullet points for details if needed.

---

## Project layout at a glance

```
main.py               — FastAPI app: global state, endpoints, data I/O (to be broken up)
cli.py                — CLI launcher: argparse, config, subprocess management
app/                  — Scaffold for future main.py breakup (empty, docstrings only)
models/schemas.py     — Pydantic request models
services/
  prediction.py       — Prompt building, BM25 retrieval, position helpers
  llm_providers.py    — Provider adapters (Ollama, OpenAI, Anthropic, vLLM) + dispatch
tests/
  test_prediction.py      — 38 tests: prompt, positions, BM25, reasoning
  test_llm_providers.py   — 31 tests: registry, derivation, validation, factory
  test_main_helpers.py    — 12 tests: CSV parsing
  testcases.md            — Full regression walkthrough (manual Tiers 1–6)
frontend/src/         — React + TypeScript + Vite + Tailwind + DaisyUI
|docs/                 — Architecture map, CLI table (for LREC paper)
|evaluation/           — Eval scripts + predictions + user study results
```

---

## Agent/Coding-Tool Notes

If you're working via an AI coding agent (like Hermes, Claude Code, or similar):

- Include the full content of `agentdocs/ProjectPrimer.md` in your first prompt — it has the working style rules the agent needs.
- Reference `docs/architecture_map.md` for module structure and landmines.
- Reference `tests/testcases.md` for the regression baseline.
- The agent should read `agentdocs/post_feature_checklist.md` after implementing and follow it step by step.

---

## Code review expectations

- All 81 pytest tests must pass before merge.
- New features should include new tests (add to the appropriate `tests/test_*.py` file).
- If you change an endpoint or data format: smoke test the UI at `localhost:3000`.
- No new `# Removed _` comments, no duplicate imports, no German/English mixed docstrings.
- Any change that does not comply with the instructions given above will not be added to the project and the contributors will be removed from permenantly if they do not abide these instructions.
