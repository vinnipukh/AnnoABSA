# Tasks

How to use: pick a task, read `CONTRIBUTING.md` for the workflow, then go.

**Status legend:** 🔴 Backlog · 🟡 In Progress · 🟢 Done · ⚪ Blocked

| Status | Task | Area | Difficulty | Affects |
|---|---|---|---|---|
| 🟢 | NLP Helper Toolbar — lexicon lookup, embedding comparer, morphological analyzer | Backend + Frontend | Hard | Phase 3 |
| 🟢 | **Phase 4: Live Compare Mode** — per-model provider/model/prompt/temperature, Live vs CSV mode selector | Backend + Frontend | Hard | Phase 4 |
| 🟢 | **Phase 5: main.py breakup** — extract config, data, positions, 6 route files. main.py 1206→50 lines | Backend | Medium | Phase 5 |
| 🟢 | Delete `annoabsa` entry-point shim | Backend | Easy | Phase 5 |
| 🟢 | Consolidate `pyproject.toml` / `requirements.txt` | Backend | Easy | Phase 5 |
| 🟢 | Update `.gitignore` — add `temp/`, `app/` patterns, `*.log` | Backend | Easy | Phase 5 |
| 🟢 | Move `temp_absa_config.json` to `temp/` directory | Backend | Easy | Phase 5 |
| 🟢 | Logo color — SVG "A" white on `bg-primary` | Frontend | Easy | Phase 5 |
| 🟢 | Keyboard shortcut (Ctrl+Shift+{key}, configurable in Settings) | Frontend | Easy | Phase 5 |
| 🟢 | Smoke tests — 4 compile-only checks | Backend | Medium | Phase 5 |
| 🔴 | **Phase 6: Polish & Features** — see phase6_plan.md | Both | Various | TBD |
| 🔴 | Emoji → SVG in HelperAgentChatbox (`🤖`) and NlpHelperToolbar (`📖🤖🔧📊😊😞😐`) | Frontend | Easy | `HelperAgentChatbox.tsx`, `NlpHelperToolbar.tsx` |
| 🔴 | Fix TSConfig — add `"vite/client"` to tsconfig types to eliminate pre-existing `env` error | Frontend | Easy | `frontend/tsconfig.json` |
| 🔴 | Frontend component tests for SettingsPanel, ModelTripletColumn, HelperAgentChatbox | Frontend | Medium | New `.test.tsx` files |
| 🔴 | CLI flags for Phase 4 Live Compare config (`--model-a-provider`, etc.) | Backend | Easy | `cli.py` |
| 🔴 | Autopilot mode — response parser in HelperAgentChatbox (hybrid text + action directives) | Both | Hard | `HelperAgentChatbox.tsx`, `agent_chat()` |
| 🔴 | RAG extension — add BM25 few-shot retrieval to Helper Agent chat | Backend | Easy | `app/routes/reviews.py`, `services/prediction.py` |
| 🔴 | Active learning ML triplet suggestions — TF-IDF + Logistic Regression uncertainty sampling | Backend | Hard | `services/active_learning.py` (new), `app/routes/learning.py` (new), `scikit-learn` |
| 🔴 | Fix route files importing from `import main` instead of `app.config`/`app.data` | Backend | Easy | `app/routes/ai.py`, `app/routes/reviews.py` |
| 🔴 | Break up `cli.py` (~962 lines) — extract config/argparse/subprocess into separate modules | Backend | Medium | `cli.py` → new modules |
| 🔴 | Clean up `pyproject.toml` — check for stale `[project.scripts]` entry pointing to deleted `annoabsa` | Backend | Easy | `pyproject.toml` |

---

## Notes

- **Phase 1-2**: STD format support, two-model comparison, new LLM providers, prompt improvements.
- **Phase 3**: NLP Helper Toolbar (SentiNet, BERT, NlpToolkit, e5-small) — **completed**.
- **Phase 4**: Live Compare Mode (per-model provider/model/temp/prompt, CSV/Live toggle) — **completed**.
- **Phase 5**: Cleanup tasks + main.py breakup (1206→50 lines) — **completed**.
- **Phase 6**: Remaining polish, tests, features, ML. See `agentdocs/phase6/phase6_plan.md` for details.
- **`Break up main.py`** — DONE. The `app/` scaffolding was populated across 9 modules.
- **Browser smoke tests** — DONE. `tests/test_smoke.py` has 4 compile-only checks.
- **Route files import from `import main`** (ai.py, reviews.py) — works via re-exports but breaks clean layering. Fix in Phase 6 by switching to `from app.config import ...`.
- **`cli.py` is the new `main.py`** (~962 lines) — next big breakup candidate in Phase 6.
- **No more frontend features unless strictly necessary** — state management in 700-line `App.tsx` is already strained. Prefer backend-only features.

---

## Adding a new task

Add a row to the table. Fill all columns:
- **Status:** leave as 🔴 Backlog
- **Task:** one-line description
- **Area:** Backend / Frontend / Both
- **Difficulty:** Easy / Medium / Hard
- **Affects:** files or modules you expect to touch
