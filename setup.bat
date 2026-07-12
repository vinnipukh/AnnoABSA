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
    echo [1/5] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/5] Virtual environment already exists
)

REM Activate
call .venv\Scripts\activate.bat

REM Pin setuptools before installing StarlangSoftware packages
echo [2/5] Pinning setuptools (required by NLP toolkit)...
pip install "setuptools<75"
if %errorlevel% neq 0 (
    echo [WARN] setuptools pin failed, continuing anyway...
)

REM Install Python deps
echo [3/5] Installing Python dependencies...
pip install -e .
if %errorlevel% neq 0 (
    echo [FAIL] pip install failed
    pause
    exit /b 1
)

REM Install frontend deps
echo [4/5] Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [FAIL] npm install failed
    cd ..
    pause
    exit /b 1
)
cd ..

echo [5/5] Setup complete!
echo.
echo ============================================
echo   How to run
echo ============================================
echo.
echo   .venv\Scripts\activate
echo   python cli.py examples/semeval_reviews.csv
echo.
echo   With LLM predictions:
echo   python cli.py --data-path examples/semeval_reviews.csv --llm-provider ollama
echo.
echo   With comparison models:
echo   python cli.py --data-path examples/semeval_reviews.csv ^
echo       --compare-model-a-csv results/model_a.csv --compare-model-a-name "GPT-4o" ^
echo       --compare-model-b-csv results/model_b.csv --compare-model-b-name "Claude 4"
echo.
echo   NLP models (BERT, e5-small) download on first use to ^~/.cache/huggingface/
echo   First requests to /nlp/sentiment and /nlp/embedding-similarity may be slow.
echo.
pause
