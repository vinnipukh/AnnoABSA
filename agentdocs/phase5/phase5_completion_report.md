# Phase 5 — Completion Report: Cleanup, Polish & main.py Breakup

**Date:** 2026-07-12
**Goal:** Execute all backlog tasks — 4 easy cleanup items, 2 UI fixes, 1 frontend enhancement, 1 test automation, and the major main.py architectural breakup.
**Status:** ✅ Complete (8 tasks, 15 files)

---

## What this is (for the academic reader)

Phase 5 addressed the project's accumulated technical debt and laid the groundwork for future development. The most significant change was the **main.py breakup**: a single 1206-line FastAPI monolith was decomposed into 9 focused modules (a thin 50-line launcher, 3 service modules, and 6 route files), following the Separation of Concerns principle from the [python-design-patterns](../python-design-patterns/SKILL.md) skill.

In addition, four cleanup tasks reduced repo clutter (deleted redundant shim, consolidated dependency tracking, updated `.gitignore`, moved runtime artifacts), two UI improvements were made (logo SVG and configurable keyboard shortcut), and compile-only smoke tests were added for reliable CI regression detection.

---

## Task breakdown

| # | Task | Files | Difficulty | Status |
|---|---|---|---|---|
| 1 | Delete `annoabsa` entry-point shim | `annoabsa` (delete), `README.md` (check) | Easy | ✅ |
| 2 | Consolidate deps (`pyproject.toml` / `requirements.txt`) | `requirements.txt` (delete), `setup.sh`, `setup.bat`, `README.md` | Easy | ✅ |
| 3 | Update `.gitignore` | `.gitignore` (+4 patterns) | Easy | ✅ |
| 4 | Move `temp_absa_config.json` to `temp/` | `cli.py` (2 lines) | Easy | ✅ |
| 5 | Logo color — SVG "A" on `bg-primary` | `App.tsx` (1 line replaced) | Easy | ✅ |
| 6 | Configurable keyboard shortcut Ctrl+Shift+{key} | `App.tsx`, `SettingsPanel.tsx`, `types.ts`, `app/config.py`, `app/routes/settings.py` | Easy | ✅ |
| 7 | Smoke tests (4 compile-only) | `tests/test_smoke.py` (new, 83 lines) | Medium | ✅ |
| 8 | **main.py breakup** — 1206 → 50 lines | `main.py`, `app/config.py`, `app/data.py`, `app/positions.py`, `app/routes/{settings,reviews,ai,timing,upload}.py` | Medium | ✅ |

---

## Task 8: main.py Breakup — Before & After

### Before (1206 lines)

```
main.py — global state, data I/O, 11 endpoints, position logic, startup, all in one file
```

### After (50 lines + 9 extracted modules)

```
main.py               50 lines   — thin launcher: imports + mounts routers + startup
app/config.py        111 lines   — global state + config functions
app/data.py          195 lines   — data I/O + navigation helpers
app/positions.py     147 lines   — position auto-fill logic
app/routes/
  settings.py         96 lines   — GET/PATCH /settings
  reviews.py         190 lines   — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat
  ai.py              180 lines   — GET /ai_prediction/{idx}, GET /live_prediction/{idx}
  timing.py           82 lines   — POST /timing/{idx}, GET /avg-annotation-time
  upload.py           53 lines   — POST /upload-data, POST /auto-add-positions
  nlp.py              51 lines   — 4 NLP endpoints (Phase 3, unchanged)
```

### Key design decisions for the breakup

**1. No circular imports.** Route files import from `app.config` and `app.data`, NOT from `main`. The `main.py` file imports FROM route files (to mount routers), not vice versa. This creates a clean dependency arrow: `main → routes → config/data`.

**2. Backward-compatible re-exports.** `main.py` has `from app.config import *` at the top, which re-exports `CONFIG_DATA`, `DATA_FILE_PATH`, etc. This means existing code that does `import main; main.CONFIG_DATA["key"] = val` (cli.py, test fixtures) continues to work — they're mutating the same dict object.

**3. Helper functions migrated to `app/data.py`.** `get_total_count()`, `get_current_index()`, and `max_number_of_idxs()` were moved to `app/data.py` since they depend on `load_data()`. The settings router imports them from `app.data`.

**4. Each route file is self-contained.** Each `app/routes/*.py` file creates its own `APIRouter`, defines its handlers, and exports `router`. `main.py` simply imports and mounts them. New endpoints can be added to the appropriate route file without touching `main.py`.

---

## Configurable keyboard shortcut

The AI suggestions shortcut was made configurable in Settings:

- **Backend**: `"ai_shortcut_key": "a"` in `load_config()` defaults + exposed in `GET /settings`
- **Frontend**: new text field "AI Kısayol Tuşu (Ctrl+Shift+...)" in Settings section 2
- **Consumer**: keyboard listener in `App.tsx` reads `settings.ai_shortcut_key` instead of hardcoded `'a'`
- **Button tooltip**: dynamically shows `AI Önerisi Al (Ctrl+Shift+{key})`

---

## Files changed (15 files, +1,088 / −1,284 lines)

| File | Δ | What changed |
|---|---|---|
| `main.py` | −1,156 | 1206→50 lines. Removed all state, data I/O, and endpoints. Now a thin launcher. |
| `app/config.py` | +111 | (new) Global state + config functions (extracted from main.py) |
| `app/data.py` | +195 | (new) Data I/O + navigation helpers (extracted from main.py) |
| `app/positions.py` | +147 | (new) Position auto-fill logic (extracted from main.py) |
| `app/routes/settings.py` | +96 | (new) GET/PATCH /settings + ai_shortcut_key |
| `app/routes/reviews.py` | +190 | (new) GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat |
| `app/routes/ai.py` | +180 | (new) GET /ai_prediction/{idx}, GET /live_prediction/{idx} |
| `app/routes/timing.py` | +82 | (new) POST /timing/{idx}, GET /avg-annotation-time |
| `app/routes/upload.py` | +53 | (new) POST /upload-data, POST /auto-add-positions |
| `cli.py` | +14 / −0 | Config path change: `temp_absa_config.json` → `temp/temp_absa_config.json` |
| `.gitignore` | +11 / −0 | Added `temp/`, `app/__pycache__/`, `*.log` patterns |
| `tests/test_smoke.py` | +83 / −0 | (new) 4 compile-only smoke tests |
| `frontend/src/App.tsx` | +6 / −3 | Logo SVG, keyboard shortcut refactor with configurable key |
| `frontend/src/types.ts` | +1 / −0 | `ai_shortcut_key: string` in Settings interface |
| `frontend/src/components/SettingsPanel.tsx` | +2 / −0 | Shortcut key text field |
| `setup.sh` | ~1 | `pip install -r requirements.txt` → `pip install -e .` |
| `setup.bat` | ~1 | Same |
| `README.md` | ~2 | Removed `requirements.txt` reference if present |

Deleted files: `annoabsa` (18 lines), `requirements.txt` (19 lines)

---

## Verification

| Check | Result |
|---|---|
| `python -m py_compile cli.py main.py` | ✅ |
| `python -m py_compile app/config.py app/data.py app/positions.py` | ✅ |
| `python -m py_compile app/routes/settings.py app/routes/reviews.py app/routes/ai.py` | ✅ |
| `python -m py_compile app/routes/timing.py app/routes/upload.py` | ✅ |
| `pytest tests/` | **128 passed, 0 failed** |
| `npx vitest run` (frontend) | **27 passed** |
| `npx tsc --noEmit` | ✅ Only 2 pre-existing errors (TS2339, TS2353) |
| `ls annoabsa` | ✅ File gone |
| `ls requirements.txt` | ✅ File gone |

---

## Tips for future coding agents

### 1. Where to add new code after the breakup

| If you're adding... | Put it here |
|---|---|
| A new HTTP endpoint | `app/routes/<name>.py` (new APIRouter file) |
| Business logic | `services/<name>.py` |
| Pydantic request/response models | `models/schemas.py` |
| A new config key | `app/config.py` `load_config()` defaults + `app/routes/settings.py` GET response |
| A new provider adapter | `services/llm_providers.py` (add to `PROVIDER_REGISTRY`) |

### 2. Route files must import from `app/` modules, not from `main`

Route files that import from `main` create circular imports because `main.py` imports from routes.
Always import state/data from `app.config` and `app.data`:

```python
# CORRECT
from app.config import CONFIG_DATA, DATA_FILE_PATH
from app.data import load_data, save_data

# WRONG — creates circular import
from main import CONFIG_DATA, load_data
```

### 3. Tests can still mutate `main.CONFIG_DATA`

Test fixtures that do `import main; main.CONFIG_DATA["key"] = val` still work because
`from app.config import *` in `main.py` re-exports the same `CONFIG_DATA` dict object.

### 4. The `importlib.reload` trap

If you write TestClient-based tests that run after other tests have already imported `main`,
the module is cached. `importlib.reload(main)` creates a new `FastAPI()` instance, invalidating
all existing `TestClient` references from other test files. For smoke tests that must work
in any test order, prefer compile-only checks over TestClient-based endpoint tests.

### 5. routes/ files exist for settings, reviews, ai, timing, upload, and nlp

The `app/routes/__init__.py` docstring describes the target structure which is now fully
implemented. If you add a new concern group (e.g., `batch`), create a new route file there.

### 6. The keyboard shortcut uses `settings.ai_shortcut_key`

The AI prediction shortcut `Ctrl+Shift+{key}` is configurable in Settings (section 2). Default is `A`.
The key is case-insensitive — the handler normalizes with `.toLowerCase()`.

### 7. Emoji icons in pre-Phase 3 components

`HelperAgentChatbox.tsx` uses `🤖` (3 instances) and `NlpHelperToolbar.tsx` uses emoji for
segment buttons (`📖🤖🔧📊`) and sentiment labels (`😊😞😐`). These violate the
[ui-ux-review](../ui-ux-review/SKILL.md) skill's "no emoji as structural icons" rule and
are slated for SVG replacement in Phase 6.
