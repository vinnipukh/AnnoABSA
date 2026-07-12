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
    echo "[1/5] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/5] Virtual environment already exists"
fi

# Activate
source .venv/bin/activate

# Pin setuptools before installing StarlangSoftware packages
echo "[2/5] Pinning setuptools (required by NLP toolkit)..."
pip install 'setuptools<75' 2>/dev/null || echo "[WARN] setuptools pin failed, continuing..."

# Install Python deps
echo "[3/5] Installing Python dependencies..."
pip install -e .

# Install frontend deps
echo "[4/5] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "[5/5] Setup complete!"
echo ""
echo "============================================"
echo "  How to run"
echo "============================================"
echo ""
echo "  source .venv/bin/activate"
echo "  python cli.py examples/semeval_reviews.csv"
echo ""
echo "  With LLM predictions:"
echo "  python cli.py --data-path examples/semeval_reviews.csv --llm-provider ollama"
echo ""
echo "  With comparison models:"
echo "  python cli.py --data-path examples/semeval_reviews.csv \\"
echo "      --compare-model-a-csv results/model_a.csv --compare-model-a-name \"GPT-4o\" \\"
echo "      --compare-model-b-csv results/model_b.csv --compare-model-b-name \"Claude 4\""
echo ""
echo "  NLP models (BERT, e5-small) download on first use to ~/.cache/huggingface/"
echo "  First requests to /nlp/sentiment and /nlp/embedding-similarity may be slow."
echo ""
