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

# Install Python deps (includes scikit-learn, rank-bm25, transformers, sentence-transformers, etc.)
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
echo "  python cli.py examples/semeval_tr_llm_annotated.csv"
echo ""
echo "  The app opens in 4-Way Comparison mode by default."
echo "  Use the 'Tahmin Et' button to get ML-based label"
echo "  suggestions for the current review."
echo ""
echo "  With LLM predictions:"
echo "  python cli.py --data-path examples/semeval_reviews.csv --llm-provider ollama"
echo ""
echo "  With comparison models:"
echo "  python cli.py --data-path examples/semeval_reviews.csv \\"
echo "      --compare-model-a-csv results/model_a.csv --compare-model-a-name \"GPT-4o\" \\"
echo "      --compare-model-b-csv results/model_b.csv --compare-model-b-name \"Claude 4\""
echo ""
echo "  With Live Compare per-model config:"
echo "  python cli.py --data-path examples/reviews.csv \\"
echo "      --model-a-provider openai --model-a-model gpt-4o --model-a-temperature 0.3 \\"
echo "      --model-b-provider anthropic --model-b-model claude-sonnet-4-20250514"
echo ""
echo "  With Custom OpenAI-compatible provider:"
echo "  python cli.py --data-path examples/reviews.csv \\"
echo "      --llm-provider custom_openai --llm-model my-model \\"
echo "      --custom-openai-url http://localhost:8001/v1 --custom-openai-key my-key"
echo ""
echo "============================================"
echo "  Running tests"
echo "============================================"
echo ""
echo "  # Backend tests (224 pytest)"
echo "  pytest tests/ -q"
echo ""
echo "  # Frontend tests (94 vitest)"
echo "  cd frontend && npx vitest run"
echo ""
echo "============================================"
echo "  First-time setup notes"
echo "============================================"
echo ""
echo "  • NLP models (BERT savasy/bert-base-turkish-sentiment-cased,"
echo "    e5-small sentence-transformer) download on first use"
echo "    to ~/.cache/huggingface/ (about 1.3 GB total)"
echo "  • First requests to /nlp/sentiment and /nlp/embedding-similarity"
echo "    may be slow while models load."
echo "  • The Welcome Overlay on first load shows quick start options."
echo "  • ML predictions (Tahmin Et button) train on user-annotated"
echo "    reviews using TF-IDF + LogisticRegression."
echo ""
