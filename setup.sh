#!/usr/bin/env bash
# AnnoABSA — one-click setup for macOS / Linux
# Requires: Python 3.11+, Node.js 18+

set -e

echo ""
echo "============================================"
echo "  AnnoABSA — Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[FAIL] Python 3 not found. Install Python 3.11+ from https://python.org"
    exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
    echo "[FAIL] Node.js not found. Install Node.js 18+ from https://nodejs.org"
    exit 1
fi

echo "[OK] Python & Node found"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/4] Virtual environment already exists"
fi

# Activate and install Python deps
echo "[2/4] Installing Python dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

# Install frontend deps
echo "[3/4] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "[4/4] Setup complete!"
echo ""
echo "============================================"
echo "  How to run"
echo "============================================"
echo ""
echo "  source .venv/bin/activate"
echo "  python cli.py examples/restaurant_reviews.csv"
echo ""
echo "  Or with LLM predictions:"
echo "  python cli.py --data-path examples/restaurant_reviews.csv --llm-provider ollama"
echo ""
