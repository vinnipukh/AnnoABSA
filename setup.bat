@echo off
REM AnnoABSA — one-click setup for Windows
REM Requires: Python 3.11+, Node.js 18+

echo.
echo ============================================
echo   AnnoABSA — Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Python not found. Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Node.js not found. Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo [OK] Python ^& Node found
echo.

REM Create virtual environment
if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment already exists
)

REM Activate and install Python deps
echo [2/4] Installing Python dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [FAIL] pip install failed
    pause
    exit /b 1
)

REM Install frontend deps
echo [3/4] Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [FAIL] npm install failed
    cd ..
    pause
    exit /b 1
)
cd ..

echo [4/4] Setup complete!
echo.
echo ============================================
echo   How to run
echo ============================================
echo.
echo   .venv\Scripts\activate
echo   python cli.py examples/restaurant_reviews.csv
echo.
echo   Or with LLM predictions:
echo   python cli.py --data-path examples/restaurant_reviews.csv --llm-provider ollama
echo.
pause
