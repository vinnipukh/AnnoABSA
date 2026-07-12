"""Upload endpoints — POST /upload-data, POST /auto-add-positions."""
from fastapi import APIRouter, HTTPException, UploadFile, File
import main
from app.positions import auto_add_missing_positions
import os
import time
import shutil

router = APIRouter(tags=["upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-data")
async def upload_data(file: UploadFile = File(...)):
    """Upload a CSV or JSON data file to use for annotation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.csv', '.json'):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload .csv or .json files only."
        )

    safe_name = f"uploaded_{int(time.time())}{ext}"
    dest = os.path.join(UPLOAD_DIR, safe_name)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    main.set_data_file(dest)

    try:
        data = main.load_data()
        count = len(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading uploaded file: {e}")

    print(f"📤 Uploaded data file: {dest} ({count} rows)")
    return {"message": f"Loaded {file.filename} ({count} satır)", "total_count": count, "file_path": dest}


@router.post("/auto-add-positions")
def manual_auto_add_positions():
    """HTTP-triggerable endpoint to auto-fill missing position data."""
    try:
        auto_add_missing_positions()
        return {"message": "Position data auto-addition completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding position data: {str(e)}")
