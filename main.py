"""AnnoABSA FastAPI backend — thin launcher."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Re-export for backward compat (cli.py, tests mutate main.CONFIG_DATA etc.)
from app.config import *  # noqa: F401, F403
from app.data import load_data, save_data, parse_triplet_column, _load_comparison_csv, get_total_count, get_current_index, max_number_of_idxs  # noqa: F401, E501
from app.positions import auto_add_missing_positions  # noqa: F401

from app.routes.nlp import router as nlp_router
from app.routes.settings import router as settings_router
from app.routes.reviews import router as reviews_router
from app.routes.ai import router as ai_router
from app.routes.timing import router as timing_router
from app.routes.upload import router as upload_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nlp_router)
app.include_router(settings_router)
app.include_router(reviews_router)
app.include_router(ai_router)
app.include_router(timing_router)
app.include_router(upload_router)


@app.on_event("startup")
async def startup_event():
    """Run startup tasks including auto-adding missing position data."""
    print(f"🚀 Starting AnnoABSA Backend...")
    print(f"📄 Data file: {DATA_FILE_PATH} (type: {DATA_FILE_TYPE})")
    if CONFIG_PATH:
        print(f"⚙️  Config file: {CONFIG_PATH}")

    if AUTO_POSITIONS:
        print("🔧 Auto-positions feature enabled - scanning for missing position data...")
        auto_add_missing_positions()
    else:
        print("ℹ️  Auto-positions feature disabled (use --auto-positions to enable)")

    print("✨ Backend ready!")
