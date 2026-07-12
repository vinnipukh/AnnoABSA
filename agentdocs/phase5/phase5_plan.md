# Phase 5 — Cleanup, Polish & Architectural Debt Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Each task is 2-5 minutes of focused work.

**Goal:** Execute all remaining backlog tasks: 4 easy cleanup items, 1 UI fix, 1 frontend enhancement, 1 test automation, and the major `main.py` architectural breakup.

**Architecture:** Tasks are ordered by dependency and complexity — easy standalone tasks first (no risk of blocking harder ones), then the medium-difficulty tasks, finally the main.py breakup which requires deep understanding of the codebase.

**Tech Stack:** Python 3.11, FastAPI, React 19 + TypeScript, pytest, vitest, Playwright (for smoke tests)

**Prerequisite reading:**
- `agentdocs/CONTRIBUTING.md` — workflow, landmines
- `agentdocs/ProjectPrimer.md` — stack overview
- `docs/architecture_map.md` — module graph
- `agentdocs/session_reports/backend_reference.md` — function reference

---

## Task 1: Delete `annoabsa` entry-point shim

**Objective:** Remove the redundant `annoabsa` shell script (18 lines). The canonical way to run the app is `python cli.py` (documented in README).

**Files:**
- Delete: `annoabsa`
- Read: `README.md`, `pyproject.toml` (check for references)

**Step 1: Check for references to `./annoabsa` or the shim file**

Run:
```bash
grep -rn 'annoabsa' README.md agentdocs/ --include="*.md" | grep -vi 'AnnoABSA\|annoabsa.png'
grep -A3 'scripts' pyproject.toml
```

Expected: The only references to `annoabsa` are the project name `AnnoABSA` or `name = "annoabsa"` in `pyproject.toml`.

**Step 2: Delete the file**

```bash
git rm annoabsa
```

**Step 3: If pyproject.toml has a `[project.scripts]` entry pointing to `annoabsa`, remove it**

If `pyproject.toml` has:
```toml
[project.scripts]
annoabsa = "cli:main"
```

Remove it. The user runs via `python cli.py` not `annoabsa` command.

**Step 4: Verify**

```bash
ls annoabsa 2>&1 | head -1
# Expected: "ls: cannot access 'annoabsa': No such file or directory"
python -m py_compile cli.py
# Expected: OK (cli.py should not import annoabsa)
```

---

## Task 2: Consolidate `pyproject.toml` and `requirements.txt`

**Objective:** Eliminate dual-source-of-truth. `pyproject.toml` is the canonical source used by `uv sync`. `requirements.txt` is a stale copy used only by `setup.sh`/`setup.bat`.

**Files:**
- Modify: `setup.sh`, `setup.bat`
- Delete: `requirements.txt`
- Read: `pyproject.toml` (verify it has all deps)

**Current state:**
- `pyproject.toml` has 15 deps under `[project] dependencies`
- `requirements.txt` lists the same 15 deps as a flat list
- `setup.sh` line ~? runs `pip install -r requirements.txt`
- `setup.bat` line ~? runs `pip install -r requirements.txt`

**Step 1: Read setup scripts to find the exact lines**

```bash
grep -n 'requirements.txt\|pip install' setup.sh setup.bat
```

**Step 2: Update `setup.sh`**

Replace the line that does:
```bash
pip install -r requirements.txt
```
or similar, with:
```bash
pip install -e .
```

`pip install -e .` reads `[project] dependencies` from `pyproject.toml` (editable install).

**Step 3: Update `setup.bat`**

Same change for the batch file:
```bat
pip install -e .
```

**Step 4: Delete `requirements.txt`**

```bash
git rm requirements.txt
```

**Step 5: Verify**

```bash
# Check no script still references requirements.txt
grep -c 'requirements.txt' setup.sh setup.bat
# Expected: 0

# Confirm pyproject.toml parses correctly
python -c "import tomllib; d = tomllib.load(open('pyproject.toml', 'rb')); print(f'{len(d[\"project\"][\"dependencies\"])} deps')"
# Expected: "15 deps"
```

**Step 6: Update README if it references `requirements.txt`**

```bash
grep -n 'requirements.txt' README.md
```
If found, replace with `pyproject.toml` guidance.

---

## Task 3: Update `.gitignore`

**Objective:** Add missing patterns for the `temp/` directory (used by Task 4), `app/` module build artifacts, and generic log files.

**Files:**
- Modify: `.gitignore`

**Current state:** Has `__pycache__/`, `.venv/`, `node_modules/`, `uploads/`, `temp_absa_config.json`. Missing `temp/`, `app/__pycache__/`, `*.log`.

**Step 1: Add before `# ── Agent / tooling ──────────────────────────`**

```gitignore

# ── Runtime temp directory ────────────────────
temp/

# ── App module build artifacts ────────────────
app/__pycache__/
app/**/__pycache__/
app/*.py[cod]

# ── Log files ─────────────────────────────────
*.log
```

**Step 2: Verify**

```bash
# Confirm no syntax issue — git reads as-is
wc -l .gitignore
# Expected: ~62 lines (was 58, added ~4)
```

**Note:** The `temp/` directory must exist at runtime (created by `os.makedirs` in Task 4), but since it's gitignored, it won't appear in git status.

---

## Task 4: Move `temp_absa_config.json` to `temp/` directory

**Objective:** Stop writing runtime artifacts to the project root. Write into `temp/` directory (gitignored by Task 3).

**Files:**
- Modify: `cli.py` (the `start_backend` function)

**Current code (cli.py lines ~304-306):**
```python
if config:
    config_file = "temp_absa_config.json"
    config.save_config(config_file)
    os.environ['ABSA_CONFIG_PATH'] = config_file
```

**Step 1: Find the exact lines**

```bash
grep -n 'temp_absa_config\|config_file' cli.py
```

Expected: The `config_file = "temp_absa_config.json"` assignment in the `start_backend` function.

**Step 2: Update the path**

Replace:
```python
config_file = "temp_absa_config.json"
```
with:
```python
os.makedirs("temp", exist_ok=True)
config_file = os.path.join("temp", "temp_absa_config.json")
```

**Step 3: Verify**

```bash
python -m py_compile cli.py
# Expected: OK

# Create the directory and test
python -c "import os; os.makedirs('temp', exist_ok=True); print('ok')"
# Expected: ok
# (the temp/ dir will be gitignored)
```

---

## Task 5: Fix Logo Color Theme Issue

**Objective:** The "A" logo in the header uses `bg-primary` + `text-primary-content` which can produce low-contrast on certain DaisyUI themes. Replace with an inline SVG that has a hardcoded white "A" on the theme-aware `bg-primary` background.

**Files:**
- Modify: `frontend/src/App.tsx` (line 510)

**Current code:**
```tsx
<div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center font-black text-primary-content shadow text-sm">A</div>
```

**Step 1: Replace with SVG letterform**

```tsx
<div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shadow-sm">
  <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 1L2 15h3l1-3h4l1 3h3L8 1zM7.5 4.5L10 10H5l2.5-5.5z" />
  </svg>
</div>
```

This renders a standard "A" letterform in SVG, hardcoded white (`text-white`), on a theme-aware `bg-primary` background. The `text-white` ensures the letter is always visible regardless of which theme's `primary-content` color is in use.

**Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Only 2 pre-existing errors (TS2339, TS2353 — landmine #16 from CONTRIBUTING.md).

---

## Task 6: Shortcut for AI Suggestions

**Objective:** Add keyboard shortcut `Ctrl+Shift+A` (or `Cmd+Shift+A` on Mac) to trigger AI prediction. The AI prediction button already exists in the header; this just adds a keyboard listener.

**Files:**
- Modify: `frontend/src/App.tsx` (add `useEffect` for keyboard listener)

**Design:** Add a global `useEffect` in `App.tsx` that listens for `keydown` events. When `Ctrl+Shift+A` (or `Cmd+Shift+A`) is pressed and AI predictions are enabled (`enablePrePrediction`), call `fetchAIPrediction()`. Show a brief toast confirming the shortcut worked.

**Step 1: Add keyboard shortcut `useEffect` in App.tsx**

Insert after the existing `useEffect` for auto-trigger AI prediction (around line 393-405):

```typescript
// ── Keyboard shortcuts ──

useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Ctrl+Shift+A (or Cmd+Shift+A) → trigger AI prediction
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
      e.preventDefault();
      if (enablePrePrediction && !isAIPredicting) {
        fetchAIPrediction();
        setSaveToast('⌨️ AI tahmini başlatıldı (Ctrl+Shift+A)');
        setTimeout(() => setSaveToast(null), 2000);
      }
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [enablePrePrediction, isAIPredicting, fetchAIPrediction]);
```

**Important:** `fetchAIPrediction` must be in the dependency array. It's defined with `useCallback` (check line ~304) so it won't cause unnecessary re-subscriptions as long as its own deps don't change.

**Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: Only 2 pre-existing errors.

**Step 3: Add indicator in the button title**

Optionally update the AI prediction button's `title` attribute (line 551) to mention the shortcut:
```tsx
title={isAIPredicting ? 'AI tahmin ediyor...' : 'AI Önerisi Al (Ctrl+Shift+A)'}
```

**Verification:**
- `npx vitest run` — 27 passed (no new tests needed for a useEffect-only change)
- Manual: Focus the app window, press Ctrl+Shift+A, observe toast + prediction trigger

---

## Task 7: Automate Browser Smoke Tests

**Objective:** Automate the two most critical manual test cases (S1: app loads, S5: backend reachable) using Playwright or a lightweight HTTP-based approach so they can run in CI without a browser.

**Files:**
- Create: `tests/test_smoke.py` (backend-only smoke tests via requests library)
- Read: `tests/testcases.md` (S1, S5 definitions)

**Approach:** Two levels of automation:
1. **Backend smoke test** — use `httpx` or `requests` to verify `GET /settings` returns 200. No browser needed. Runs in pytest.
2. **Full-stack smoke test** — use Playwright to open the frontend and verify no console errors. This requires the full stack (backend + frontend) running.

We'll implement level 1 (backend-only) first as it's faster and catches the most common regression (backend crash, missing deps, file format issues).

**Step 1: Install `httpx` test dependency**

Add `httpx` to dev dependencies or use `TestClient` from FastAPI directly (already installed):

```bash
# Already available — FastAPI's TestClient is sufficient
```

**Step 2: Create `tests/test_smoke.py`**

```python
"""Smoke tests — verify the app starts and critical endpoints respond.

These tests exercise the full import chain of main.py, so they catch:
- Missing dependencies
- Import errors in FastAPI, services, or model modules
- Data file format issues
- CORS middleware configuration

They use FastAPI TestClient directly (no actual HTTP server needed).
"""
import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient


# ── Test data ──

SMOKE_CSV = (
    "review_id,text,review_text,translation,label\n"
    '0,"Test review","Test review","Test translation",""\n'
)

SMOKE_JSON = json.dumps([
    {
        "review_id": 0,
        "text": "Test review",
        "review_text": "Test review",
        "translation": "Test translation",
    }
], ensure_ascii=False)


@pytest.fixture(params=["csv", "json"])
def data_file(request):
    """Create temp data file in CSV or JSON format."""
    suffix = ".csv" if request.param == "csv" else ".json"
    content = SMOKE_CSV if request.param == "csv" else SMOKE_JSON
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=suffix,
                                       delete=False, encoding="utf-8")
    tmp.write(content)
    path = tmp.name
    tmp.close()
    yield path, request.param
    os.unlink(path)


@pytest.fixture
def app(data_file):
    """Import main with a test data file."""
    path, file_type = data_file
    os.environ["ABSA_DATA_PATH"] = path
    if "ABSA_CONFIG_PATH" in os.environ:
        del os.environ["ABSA_CONFIG_PATH"]

    import main
    main.DATA_FILE_PATH = path
    main.DATA_FILE_TYPE = file_type
    main.CONFIG_DATA = {
        "sentiment_elements": ["aspect_term", "aspect_category",
                                "sentiment_polarity", "opinion_term"],
        "aspect_categories": ["TEST#GENERAL"],
        "sentiment_polarity_options": ["positive", "negative", "neutral"],
        "implicit_aspect_term_allowed": True,
        "implicit_opinion_term_allowed": False,
        "save_phrase_positions": True,
        "n_few_shot": 3,
        "llm_provider": "ollama",
        "llm_model": "gemma3:4b",
    }
    return TestClient(main.app)


# ── Tests ──

class TestSmoke:
    """S1 + S5 automated — app loads, backend reachable."""

    def test_settings_endpoint_returns_200(self, app):
        """S5 equivalent: GET /settings returns 200 with config data."""
        response = app.get("/settings")
        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert data["total_count"] == 1
        assert "sentiment elements" in data
        assert "aspect_categories" in data

    def test_data_endpoint_returns_review(self, app):
        """GET /data/0 returns review text and label."""
        response = app.get("/data/0")
        assert response.status_code == 200
        data = response.json()
        assert data["review_text"] == "Test review"
        assert "text" in data
        assert "model_a_triplets" in data
        assert "model_b_triplets" in data

    def test_app_imports_cleanly(self):
        """Verify import chain has no missing modules."""
        # The TestClient import above already exercises this.
        # This test ensures main.py can be imported in a clean environment.
        import subprocess
        result = subprocess.run(
            ["python", "-c", "import py_compile; py_compile.compile('main.py', doraise=True)"],
            capture_output=True, text=True, cwd=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0, f"Import error: {result.stderr}"

    def test_unknown_route_returns_404(self, app):
        """Unknown endpoint returns 404 (not a crash)."""
        response = app.get("/nonexistent")
        assert response.status_code == 404

    def test_cors_headers_present(self, app):
        """CORS middleware is active (important for frontend)."""
        response = app.options("/settings", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
```

**Step 3: Run the tests**

```bash
source .venv/Scripts/activate
pytest tests/test_smoke.py -v
```

Expected: 5 or more passed (parameterized by csv/json = 2×).

**Step 4: Update `testcases.md` coverage summary**

Add to the automated tests table:
```markdown
| `tests/test_smoke.py` | ~5 | `GET /settings`, `GET /data/0`, import chain, 404, CORS | S1/S5 smoke tests |
```

**Verification:**
```bash
pytest tests/ -q
# Expected: 129+ passed (124 existing + 5 new)
```

---

## Task 8: Break Up `main.py` into `app/` Package

**Objective:** This is the largest architectural change remaining. `main.py` is currently ~1206 lines doing everything: config, data I/O, 11 endpoints, position logic, validation imports. The `app/` scaffolding already exists with docstrings describing the target structure. This task moves code out one module at a time.

**Duration:** ~10 sub-tasks, each 2-5 minutes. This is best delegated to subagents with deep codebase context.

**Files to create/modify:**
- Create: `app/config.py` — global state + config functions
- Create: `app/data.py` — data I/O (load_data, save_data, parse_triplet_column, _load_comparison_csv)
- Create: `app/positions.py` — auto_add_missing_positions
- Create: `app/routes/settings.py` — GET /settings, PATCH /settings
- Create: `app/routes/reviews.py` — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat
- Create: `app/routes/ai.py` — GET /ai_prediction/{idx}, GET /live_prediction/{idx}
- Create: `app/routes/timing.py` — POST /timing/{idx}
- Create: `app/routes/upload.py` — POST /upload-data, POST /auto-add-positions
- Modify: `main.py` — thin import + mount
- Modify: `app/__init__.py` — updated docstring
- Modify: `app/routes/__init__.py` — maybe not needed (each route file self-registers)
- Update: `cli.py` — update import paths if needed
- Update: `tests/` — update import paths for functions that moved

### Sub-task 8.1: Extract `app/config.py`

**Objective:** Move global state declarations and config functions from `main.py` lines 32-137 into `app/config.py`.

**What moves:**
```python
# main.py lines 32-48 — global state
DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', "annotations.csv")
DATA_FILE_TYPE = "json" if DATA_FILE_PATH.endswith('.json') else "csv"
CONFIG_PATH = os.environ.get('ABSA_CONFIG_PATH', None)
CONFIG_DATA = {}
# ... CONFIG_PATH loading logic ...
AUTO_POSITIONS = CONFIG_DATA.get('auto_positions', False)

# main.py lines 51-77 — set_data_file, set_config_file
# main.py lines 80-132 — load_config, set_config
```

**After extraction, `app/config.py` contains:**
```python
"""Global state and configuration for AnnoABSA.

Usage:
    from app.config import DATA_FILE_PATH, CONFIG_DATA, load_config
"""
import os
import json

# ── Global state ──

DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', "annotations.csv")
DATA_FILE_TYPE = "json" if DATA_FILE_PATH.endswith('.json') else "csv"
CONFIG_PATH = os.environ.get('ABSA_CONFIG_PATH', None)
CONFIG_DATA = {}

# Load configuration if provided
CONFIG_PATH_env = os.environ.get('ABSA_CONFIG_PATH')
if CONFIG_PATH_env and os.path.exists(CONFIG_PATH_env):
    try:
        with open(CONFIG_PATH_env, 'r', encoding='utf-8') as f:
            CONFIG_DATA = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config from {CONFIG_PATH_env}: {e}")

AUTO_POSITIONS = CONFIG_DATA.get('auto_positions', False)

# ... plus set_data_file, set_config_file, load_config, set_config moved verbatim ...
```

**`main.py` then imports:**
```python
from app.config import (
    DATA_FILE_PATH, DATA_FILE_TYPE, CONFIG_PATH, CONFIG_DATA, AUTO_POSITIONS,
    set_data_file, set_config_file, load_config, set_config,
)
```

**Verify:**
```bash
python -m py_compile app/config.py
# Expected: OK
```

### Sub-task 8.2: Extract `app/data.py`

**Objective:** Move data I/O and parsing functions from `main.py`.

**What moves:** `load_data()` (line 140), `save_data()` (line 149), `parse_triplet_column()` (line 270), `_load_comparison_csv()` (line 322).

**After extraction, `main.py` imports:**
```python
from app.data import load_data, save_data, parse_triplet_column, _load_comparison_csv
```

**Note:** These functions reference `DATA_FILE_PATH` and `DATA_FILE_TYPE` from `app.config`. The imports in `app/data.py` should do `from app.config import DATA_FILE_PATH, DATA_FILE_TYPE`.

### Sub-task 8.3: Extract `app/positions.py`

**Objective:** Move `auto_add_missing_positions()` from `main.py` lines 569-708.

**What moves:** The entire `auto_add_missing_positions()` function.

**Dependencies:** Uses `load_data()`, `save_data()`, `DATA_FILE_PATH`, `DATA_FILE_TYPE`, `AUTO_POSITIONS`, `find_phrase_positions`.

**After extraction, `main.py` imports:**
```python
from app.positions import auto_add_missing_positions
```

**Note:** The `manual_auto_add_positions()` endpoint stays in `main.py` (or moves to a route file in sub-task 8.6) — it calls `auto_add_missing_positions()`.

### Sub-task 8.4: Extract settings routes

**Objective:** Move `GET /settings` and `PATCH /settings` into `app/routes/settings.py`.

**Create `app/routes/settings.py`:**
```python
"""Settings endpoints — GET and PATCH configuration."""
from fastapi import APIRouter, HTTPException
from app.config import CONFIG_DATA, CONFIG_PATH, load_config, get_total_count, get_current_index

router = APIRouter(tags=["settings"])

@router.get("/settings")
def get_settings():
    # ... copied from main.py lines 180-236 ...
    pass

@router.patch("/settings")
def update_settings(updates: dict):
    # ... copied from main.py lines 238-266 ...
    pass
```

**In `main.py`, add:**
```python
from app.routes.settings import router as settings_router
app.include_router(settings_router)
```

Then remove the `@app.get("/settings")` and `@app.patch("/settings")` decorators from main.py.

### Sub-task 8.5: Extract review/agent routes

**Objective:** Move `GET /data/{idx}`, `POST /review/{idx}/save`, `POST /agent/chat` into `app/routes/reviews.py`.

**Create `app/routes/reviews.py`:**
```python
"""Review and agent endpoints."""
from fastapi import APIRouter, HTTPException
from app.config import CONFIG_DATA, load_config
from app.data import load_data, save_data, parse_triplet_column, _load_comparison_csv
from models.schemas import SaveTripletsRequest, AgentChatRequest
from services.prediction import generate_mock_reasoning
from services.llm_providers import get_provider, _derive_provider, validate_provider_config
from services.prediction import DEFAULT_CHAT_TEMPLATE

router = APIRouter(tags=["reviews"])

@router.get("/data/{data_idx}")
def get_data(data_idx: int):
    # ... copied from main.py lines 363-454 ...
    pass

@router.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest):
    # ... find and copy from main.py ...
    pass

@router.post("/agent/chat")
def agent_chat(req: AgentChatRequest):
    # ... copied from main.py lines 1129-1206 ...
    pass
```

### Sub-task 8.6: Extract AI prediction routes

**Objective:** Move `GET /ai_prediction/{idx}` and `GET /live_prediction/{idx}` into `app/routes/ai.py`.

**Create `app/routes/ai.py`:**
- Move `get_ai_prediction()` (~115 lines, main.py lines 736-850)
- Move `get_live_prediction()` (~100 lines, main.py lines 853-950+)

### Sub-task 8.7: Extract timing and upload routes

**Objective:** Move remaining single-endpoint routes into dedicated files or group them.

**Create `app/routes/timing.py`:**
- Move `POST /timing/{idx}` (main.py lines 533-565)

**Create `app/routes/upload.py`:**
- Move `POST /upload-data` (find in main.py)
- Move `POST /auto-add-positions` (main.py lines 713-726)

### Sub-task 8.8: Wire everything in `main.py`

After all extractions, `main.py` becomes a thin importer:

```python
"""AnnoABSA FastAPI backend — thin launcher that mounts route modules."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CONFIG_DATA, DATA_FILE_PATH, DATA_FILE_TYPE, AUTO_POSITIONS
from app.data import load_data, save_data  # keep if startup_event uses them

from app.routes.settings import router as settings_router
from app.routes.reviews import router as reviews_router
from app.routes.ai import router as ai_router
from app.routes.timing import router as timing_router
from app.routes.upload import router as upload_router
from app.routes.nlp import router as nlp_router  # existing, stays

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(settings_router)
app.include_router(reviews_router)
app.include_router(ai_router)
app.include_router(timing_router)
app.include_router(upload_router)
app.include_router(nlp_router)

@app.on_event("startup")
async def startup_event():
    """Log data file and config paths; optionally auto-fill positions."""
    ...  # ~10 lines
```

**Expected result:** `main.py` drops from ~1206 lines to ~40 lines.

### Sub-task 8.9: Update imports in tests

**Objective:** Update any test file that imports from `main` directly.

**Check:**
```bash
grep -rn 'from main import\|from main import\|import main' tests/
```

Tests to update:
- `tests/test_live_prediction.py` — imports `main` for `main.app`, `main.CONFIG_DATA`, `main.DATA_FILE_PATH`. Still need the module-level `main` object for `TestClient(main.app)` and for mutating `main.CONFIG_DATA`. This import stays valid because `main.py` still exists — it's just thinner now.
- `tests/test_main_helpers.py` — has an inline `_parse_triplet_column` copy; doesn't import from main.

**Verdict:** Most tests that import `main` use it as a module object (`main.app`, `main.CONFIG_DATA`). Since `main.py` still exists (just thinner), these imports continue to work. No test changes needed unless a function was deleted from `main.py` without a re-export.

### Sub-task 8.10: Update documentation

**Update files:**
- `agentdocs/session_reports/backend_reference.md` — update file sizes, function locations
- `docs/architecture_map.md` — update module graph to show `app/config.py`, `app/data.py`, etc.
- `agentdocs/ProjectPrimer.md` — update stack description
- `tests/testcases.md` — update automated test list if file counts change

---

## Verification Plan

After all tasks are complete, run these checks in order:

```bash
# 1. Python compilation
python -m py_compile cli.py
python -m py_compile main.py
for f in app/*.py app/routes/*.py; do python -m py_compile "$f"; done

# 2. Backend tests
pytest tests/ -q
# Expected: all existing + new smoke tests pass

# 3. Frontend TypeScript
cd frontend && npx tsc --noEmit
# Expected: only 2 pre-existing errors

# 4. Frontend tests
cd frontend && npx vitest run
# Expected: 27 passed

# 5. Frontend build
cd frontend && npx vite build
# Expected: builds successfully
```

---

## Risks and open questions

1. **Circular imports in main.py breakup.** `app/config.py` must not import from `app/data.py` (which depends on config). `app/data.py` imports from `app/config.py` — that's fine (downward dependency). `app/routes/*.py` imports from both config and data — also fine. The rule: config → data → positions → routes (each layer depends only on layers above it).

2. **`test_live_prediction.py` imports `main` as a module.** After the breakup, `main` still exists as a thin launcher. `import main` still works, and `main.app`, `main.CONFIG_DATA`, etc. are still accessible because they're re-exported via `from app.config import CONFIG_DATA`. However, if `CONFIG_DATA` is no longer defined at `main` module level (only imported), mutating `main.CONFIG_DATA` in tests will NOT work — it will mutate the local reference in `main.py`, not the canonical dict in `app.config`. 

   **Fix:** Tests should mutate `app.config.CONFIG_DATA` directly or both. Safer: add `from app.config import CONFIG_DATA` in test fixtures and mutate that.

3. **`cli.py` calls `main.set_config()` and `main.set_data_file()`.** After the breakup, these functions live in `app/config.py`. `cli.py` must import from `app.config` instead. Add a backward-compat re-export in `main.py`:
   ```python
   from app.config import set_data_file, set_config_file, set_config
   ```

4. **Task 6 (keyboard shortcut) dependencies.** `fetchAIPrediction` in `App.tsx` is defined with `useCallback`. Make sure the keyboard shortcut `useEffect` includes it in its dependency array. If `fetchAIPrediction` changes reference on every render (not wrapped in `useCallback`), the effect will fire on every render, adding/removing the listener.

5. **Playwright for full-stack smoke tests.** Task 7 currently only automates backend smoke tests via TestClient. True end-to-end browser tests (Playwright) are left for future work because they require the full stack (backend + frontend) running, which complicates CI setup.
