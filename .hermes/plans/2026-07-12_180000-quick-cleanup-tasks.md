# Quick Cleanup Tasks Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Execute 5 quick cleanup tasks that reduce repo clutter, consolidate dependency tracking, and fix a minor UI issue.

**Architecture:** Each task touches a small number of files independently. Tasks are ordered from most impactful (cleaning up how dependencies are managed) to simplest (single-line fixes). No task depends on another — they can be done in any order.

**Tech Stack:** Python, Markdown, git

**Prerequisites:** None — these are self-contained cleanup tasks.

---

## Task 1: Consolidate `pyproject.toml` and `requirements.txt`

**Objective:** Eliminate the dual-source-of-truth by deleting `requirements.txt` and adding a comment in `pyproject.toml` directing users to the canonical source.

**Files:**
- Modify: `pyproject.toml`
- Delete: `requirements.txt`
- Read: `setup.sh`, `setup.bat` — check they don't reference `requirements.txt`

**Current state:** Both files list the same 15 dependencies. `pyproject.toml` is the canonical source used by `uv` and modern tooling. `requirements.txt` is a stale copy used only by `pip install -r requirements.txt` in setup scripts.

**Step 1: Check setup scripts for `requirements.txt` references**

Run:
```bash
grep -n 'requirements.txt' setup.sh setup.bat
grep -n 'requirements' setup.sh setup.bat
```

Expected output: both scripts reference `requirements.txt` in `pip install -r` commands.

**Step 2: Update `pyproject.toml` to add a comment noting it's the canonical source**

Add at the top of `pyproject.toml`:
```toml
# CANONICAL dependency source. If you add a dep here, `uv sync` installs it.
# requirements.txt was deleted — it was a stale copy of this list.
```

**Step 3: Delete `requirements.txt`**

```bash
git rm requirements.txt
```

**Step 4: Update `setup.sh` and `setup.bat` to use `pyproject.toml`**

In `setup.sh`, replace:
```bash
pip install -r requirements.txt
```
with:
```bash
pip install -e .
```

In `setup.bat`, replace:
```bat
pip install -r requirements.txt
```
with:
```bat
pip install -e .
```

This uses `pyproject.toml` as the dependency source. `pip install -e .` reads `[project] dependencies` from `pyproject.toml`.

**Step 5: Update README if it references `requirements.txt`**

Run:
```bash
grep -n 'requirements.txt' README.md
```

If found, replace with `pyproject.toml` or `pip install -e .` references.

**Step 6: Verify**

Run:
```bash
# Check setup.sh no longer references requirements.txt
grep -c 'requirements.txt' setup.sh setup.bat
# Expected: 0
```

**Verification:**
```bash
# Confirm pyproject.toml can be parsed
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

---

## Task 2: Delete `annoabsa` entry-point shim

**Objective:** Remove the redundant `annoabsa` shell script. `README.md` already documents `python cli.py` as the canonical way to run the app.

**Files:**
- Delete: `annoabsa`
- Modify: `README.md` (maybe — check if it references `./annoabsa`)

**Current state:** `annoabsa` is a 18-line Python script that does `from cli import main; main()`. It's redundant because `python cli.py` does the same thing. `README.md` already uses `python cli.py` in all examples.

**Step 1: Check for references to `./annoabsa` or `annoabsa` in docs**

Run:
```bash
grep -rn 'annoabsa' README.md agentdocs/ --include="*.md" | grep -v 'AnnoABSA\|annoabsa.png\|entry-point'
```

Expected: The only references to `annoabsa` (lowercase) are in the project name `AnnoABSA` or in the `pyproject.toml`'s `name = "annoabsa"`.

**Step 2: Verify `cli.py` has a `main()` function that can be called directly**

The script already works: `python cli.py examples/semeval_reviews.csv`. No changes needed.

**Step 3: Delete the file**

```bash
git rm annoabsa
```

**Step 4: Update pyproject.toml if it has a [project.scripts] entry pointing to annoabsa**

Run:
```bash
grep -A2 'project.scripts' pyproject.toml
```

If present and points to `annoabsa`, remove the entry.

**Verification:**
```bash
# Confirm the file is gone
ls -la annoabsa 2>&1 | head -1
# Expected: "ls: cannot access 'annoabsa': No such file or directory"
```

---

## Task 3: Update `.gitignore`

**Objective:** Add missing patterns for `app/` build artifacts, `temp/` directory (used by Task 4), and other runtime artifacts.

**Files:**
- Modify: `.gitignore`

**Current hole:** `.gitignore` already has `_pycache__/`, `.venv/`, `node_modules/`, `uploads/`, and `temp_absa_config.json`. What's missing:
- `temp/` — will be used by Task 4 for runtime artifacts
- `app/__pycache__/` — if `app/` ever gets Python files
- `*.log` — generic log files
- `.hermes/plans/*.md` — but actually plans should be tracked (they're doc). Don't add.

**Step 1: Add missing patterns**

Append to `.gitignore` before the existing `# ── Agent / tooling ──────────────────────────` section:

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

**Verification:**
```bash
# Confirm file parses correctly — git reads it as-is
cat .gitignore | head -65
```

---

## Task 4: Move `temp_absa_config.json` to `temp/` directory

**Objective:** Stop writing runtime artifacts to the project root. Write `temp_absa_config.json` into a `temp/` directory (already gitignored by Task 3).

**Files:**
- Modify: `cli.py` (the `start_backend` function where the config file is written)
- Create: `temp/.gitkeep` (to keep the directory tracked)

**Current state:** In `cli.py:start_backend()`, line ~305:
```python
config_file = "temp_absa_config.json"
```
This writes to the repo root. Multiple `absa_config.json` variants also appear.

**Step 1: Find all places that write `temp_absa_config.json`**

Run:
```bash
grep -rn 'temp_absa_config\|absa_config\.json' cli.py main.py
grep -rn 'temp_absa_config\|absa_config\.json' --include="*.py" .
```

**Step 2: Add `temp/` directory creation in `cli.py`**

At the top of `start_backend()` (before the config file path), add:

```python
# Ensure temp directory exists for runtime artifacts
os.makedirs("temp", exist_ok=True)
```

**Step 3: Change the config file path**

Replace:
```python
config_file = "temp_absa_config.json"
```
with:
```python
config_file = os.path.join("temp", "temp_absa_config.json")
```

**Step 4: Create `temp/.gitkeep`**

Create the file with empty content. The `temp/` directory is gitignored (Task 3), but `temp/.gitkeep` is needed so the directory exists on fresh clones. Actually — if the directory is gitignored, we can't track `.gitkeep` in it. Instead, create the directory at runtime in the `os.makedirs` call above, which handles it.

**Actually:** Since `temp/` will be gitignored, we can't commit `temp/.gitkeep`. The runtime `os.makedirs("temp", exist_ok=True)` handles this. No `.gitkeep` needed.

**Step 5: Verify**

Run:
```bash
python -m py_compile cli.py
# Expected: OK
```

---

## Task 5: Fix Logo Color Theme Issue

**Objective:** The "A" logo in the header uses `bg-primary` which should be theme-aware, but the task reports it doesn't change with dark/light mode. This likely means `bg-primary` renders poorly on certain DaisyUI themes. Fix by using inline SVG with a hardcoded white "A" and `bg-primary` (theme-aware background).

**Files:**
- Modify: `frontend/src/App.tsx` (the header logo at line 510)

**Current state (line 510):**
```tsx
<div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center font-black text-primary-content shadow text-sm">A</div>
```

This uses `bg-primary` (theme-aware) and `text-primary-content` (theme-aware). The issue might be that on certain themes, `bg-primary` + `text-primary-content` produces low contrast or the "A" is invisible.

**Step 1: Replace with inline SVG**

Replace the `div` logo with a standalone SVG that has:
- `bg-primary` background (theme-aware)
- Hardcoded white "A" text (always visible regardless of `primary-content` color)
- Rounded corners

```tsx
<div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shadow-sm">
  <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 1L2 15h3l1-3h4l1 3h3L8 1zM7.5 4.5L10 10H5l2.5-5.5z" />
  </svg>
</div>
```

This uses a standard "A" letterform SVG with `text-white` (always white regardless of theme). The background `bg-primary` adapts to the theme.

**Step 2: Verify the build**

```bash
cd frontend && npx tsc --noEmit
# Expected: only 2 pre-existing errors (TS2339, TS2353)
```

No tests need updating since this is purely cosmetic.

---

## Risks and open questions

1. **`setup.sh` and `setup.bat` after pip install -e .**: Some systems might need build tools (`setuptools`, `wheel`) for editable installs. `pip install -e .` installs from `pyproject.toml`. If the StarlangSoftware packages fail to install this way, fall back to `pip install -r requirements.txt` (keeping `requirements.txt`).

2. **`temp_absa_config.json` still at root if someone runs without CLI**: If the backend is started directly via `uvicorn main:app` (not through `cli.py`), the config path is set by `ABSA_CONFIG_PATH` env var, not by the temp file path. No change needed — the temp file is only created by `cli.py:start_backend()`.

3. **Logo color fix is speculative**: The actual issue reported ("Logo color does not change when the user's browser theme is dark or light") might need a different solution depending on which theme(s) produce poor contrast. The SVG replacement ensures the "A" is always white on `bg-primary`. If the issue is specifically about the `bg-primary` color changing drastically between themes (e.g., blue on light vs green on dark), that's a DaisyUI theme design choice and likely intentional.
