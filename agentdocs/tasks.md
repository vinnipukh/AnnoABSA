# Tasks

How to use: pick a task, read `CONTRIBUTING.md` for the workflow, then go.

**Status legend:** 🔴 Backlog · 🟡 In Progress · 🟢 Done · ⚪ Blocked

| Status | Task | Area | Difficulty | Affects |
|---|---|---|---|---|
| 🔴 | Reproduce Label Studio active learning module and add it to AnnoABSA | Backend + Frontend | Hard | `main.py`, new route, new UI component |
| 🔴 | Add lexicon-based sentiment analysis wizard | Backend | Medium | `services/`, new route |
| 🔴 | Add contextual vector embedding comparer | Backend + Frontend | Hard | `services/`, new route, new UI component |
| 🔴 | Add temperature option to settings | Frontend + Backend | Easy | `SettingsPanel.tsx`, `main.py` config, `cli.py` |
| 🔴 | System prompt for Model A, B and Helper Agent | Frontend + Backend | Medium | `SettingsPanel.tsx`, `main.py`, `services/prediction.py` |
| 🔴 | Shortcut for AI suggestions | Frontend | Easy | `App.tsx` or keyboard handler |

---

## Adding a new task

Add a row to the table. Fill all columns:
- **Status:** leave as 🔴 Backlog
- **Task:** one-line description
- **Area:** Backend / Frontend / Both
- **Difficulty:** Easy / Medium / Hard
- **Affects:** files or modules you expect to touch
