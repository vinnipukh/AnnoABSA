"""Timing endpoints — POST /timing/{idx}, GET /avg-annotation-time."""
from fastapi import APIRouter, HTTPException
from app.config import DATA_FILE_PATH, DATA_FILE_TYPE
from app.data import load_data, save_data
import json

router = APIRouter(tags=["timing"])


@router.post("/timing/{data_idx}")
def post_timing(data_idx: int, timing: dict):
    """Store timing information for a data item (appended to a list)."""
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")
        timing_entry = {"duration": timing.get(
            "duration", 0), "change": timing.get("change", False)}
        if DATA_FILE_TYPE == "json":
            item = data[data_idx]
            if "timings" not in item or not isinstance(item["timings"], list):
                item["timings"] = []
            item["timings"].append(timing_entry)
            save_data(data)
        else:
            df = data
            timings_col = df.at[data_idx,
                                "timings"] if "timings" in df.columns else None
            try:
                timings = json.loads(timings_col) if timings_col else []
            except Exception:
                timings = []
            timings.append(timing_entry)
            df.at[data_idx, "timings"] = json.dumps(
                timings, ensure_ascii=False)
            save_data(df)
        return {"message": "Timing gespeichert"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/avg-annotation-time")
def get_avg_annotation_time():
    """Calculate and return the average annotation time across all examples with timing data."""
    try:
        data = load_data()
        total_duration = 0.0
        total_entries = 0

        for idx, item in enumerate(data):
            if DATA_FILE_TYPE == "json":
                timings = item.get("timings", []) if isinstance(
                    item.get("timings"), list) else []
            else:
                timings_str = item.get("timings") if hasattr(item, 'get') and callable(item.get) else (
                    data.iloc[idx]["timings"] if "timings" in data.columns and idx < len(
                        data) else None
                )
                try:
                    timings = json.loads(
                        timings_str) if timings_str and timings_str != '' else []
                except Exception:
                    timings = []

            for timing_entry in timings:
                if isinstance(timing_entry, dict) and "duration" in timing_entry:
                    total_duration += timing_entry["duration"]
                    total_entries += 1

        avg_time = total_duration / total_entries if total_entries > 0 else 0.0

        return {
            "avg_annotation_time": round(avg_time, 2),
            "total_entries": total_entries,
            "total_duration": round(total_duration, 2)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating average annotation time: {str(e)}")
