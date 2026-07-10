# Post-Feature Checklist (what to do after adding a new feature)

Run these in order after implementing any feature.

## 1. Clean

- [ ] Remove debug prints, commented-out code, TODO stubs
- [ ] Remove unused imports (check with `ruff` or manual review)
- [ ] Remove dead code paths (e.g. if/else where one branch is now unreachable)
- [ ] Verify no regressions in untouched files (grep for accidentally-changed imports)

## 2. Verify compilation

- [ ] `python -m py_compile main.py`
- [ ] `python -m py_compile cli.py`
- [ ] `python -m py_compile services/llm_providers.py`
- [ ] `python -m py_compile services/prediction.py`

## 3. Run tests

- [ ] `pytest tests/` — all 81 pass (add new tests for the feature if applicable)
- [ ] If you changed an endpoint or data format: start backend + frontend, load `localhost:3000`, confirm the app still renders without console errors (Tier 1 smoke tests)

## 4. Update docs

- [ ] **`agentdocs/backend_reference.md`** — if you added/renamed/removed a function, endpoint, or module
- [ ] **`docs/architecture_map.md`** — if you changed the module graph, added a file, or changed an endpoint contract
- [ ] **`agentdocs/ProjectPrimer.md`** — if you changed the data format, CLI flags, dependencies, or how-to-run instructions
- [ ] **`tests/testcases.md`** — if the feature affects behavior that has a dedicated test case (add a new row or update an existing one)

## 5. Commit

- [ ] `git add -A`
- [ ] `git diff --cached --stat` — review what you're about to commit
- [ ] `git commit -m "short description of what and why"`
