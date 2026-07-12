# Tasks

How to use: pick a task, read `CONTRIBUTING.md` for the workflow, then go.

**Status legend:** 🔴 Backlog · 🟡 In Progress · 🟢 Done · ⚪ Blocked

| Status | Task | Area | Difficulty | Affects |
|---|---|---|---|---|
| 🟢 | NLP Helper Toolbar — lexicon lookup, embedding comparer, morphological analyzer | Backend + Frontend | Hard | `nlp_helpers.py`, `NlpHelperToolbar.tsx`, `PhraseAnnotator.tsx`, both modes |
| 🔴 | Break up `main.py` into `app/` package (scaffolding exists) | Backend | Medium | `app/` modules, `main.py` → thin import |
| 🟢 | **Phase 4: Live Compare Mode** — per-model provider/model/prompt/temperature for Model A, Model B, and Helper Agent. Live vs CSV mode selector. | Backend + Frontend | Hard | See `agentdocs/phase4/phase4_plan.md` for full list |
| 🔴 | Logo color — make logo respect dark/light theme | Frontend | Easy | `App.tsx` or header SVG |
| 🔴 | Shortcut for AI suggestions | Frontend | Easy | `App.tsx` or keyboard handler |
| 🔴 | Automate browser smoke tests (S1 app-load, S5 backend-reachable) | Backend + Frontend | Medium | `tests/`, new test file |
| 🔴 | Clean up root runtime artifact `temp_absa_config.json` — write to `temp/` | Backend | Easy | `cli.py` |
| 🔴 | Consolidate `pyproject.toml` and `requirements.txt` to one source of truth | Backend | Easy | `pyproject.toml`, `requirements.txt` |
| 🔴 | Update `.gitignore` — add `uploads/`, `app/`, missing patterns | Backend | Easy | `.gitignore` |
| 🔴 | Delete `annoabsa` entry-point shim (redundant, README uses `python cli.py`) | Backend | Easy | `annoabsa` file, `README.md` |

## Notes

- **NLP Helper Toolbar** — **completed**. See `agentdocs/phase3/phase3_completion_report.md` for full details. Backend uses SentiNet (word lexicon), `savasy/bert-base-turkish-sentiment-cased` (sentence sentiment), `TurkishMorphologicalAnalysis-Py` (morphology), and `intfloat/multilingual-e5-small` (embeddings). All confirmed working on Python 3.11 with `setuptools<75`.
- **Break up `main.py`** — the `app/` scaffolding is ready with docstrings describing what goes where. Actual code move is the remaining work. The main challenge is global state (`CONFIG_DATA`, `DATA_FILE_PATH`).
- **Browser smoke tests** — currently only verified manually (Tiers 1–6 in `tests/testcases.md`). Automating S1 (app loads) and S5 (backend reachable) would catch the most common regression class.

---

## Adding a new task

Add a row to the table. Fill all columns:
- **Status:** leave as 🔴 Backlog
- **Task:** one-line description
- **Area:** Backend / Frontend / Both
- **Difficulty:** Easy / Medium / Hard
- **Affects:** files or modules you expect to touch