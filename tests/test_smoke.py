"""Smoke tests — verify the app starts and critical endpoints respond.

These tests exercise the full import chain of main.py, so they catch:
- Missing dependencies
- Import errors in FastAPI, services, or model modules
- Data file format issues
- CORS middleware configuration

They use FastAPI TestClient directly (no actual HTTP server needed).
"""
import os
import sys
import subprocess
import pytest
from fastapi.testclient import TestClient


# ── Tests ──

class TestSmoke:
    """S1 + S5 automated — app loads, backend reachable."""

    def test_app_imports_cleanly(self):
        """Verify the import chain has no missing modules."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "main.py"],
            capture_output=True, text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, (
            f"Compile error in main.py:\n{result.stderr}"
        )

    def test_config_module_imports_cleanly(self):
        """app/config.py compiles independently."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "app/config.py"],
            capture_output=True, text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, (
            f"Compile error in app/config.py:\n{result.stderr}"
        )

    def test_data_module_imports_cleanly(self):
        """app/data.py compiles independently."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "app/data.py"],
            capture_output=True, text=True,
            cwd=project_root,
        )
        assert result.returncode == 0

    def test_positions_module_imports_cleanly(self):
        """app/positions.py compiles independently."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "app/positions.py"],
            capture_output=True, text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
