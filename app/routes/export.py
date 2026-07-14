"""4-way export endpoint — GET /data/export-4way.

Adds selected_triplets, resolution_tier, and annotator_notes columns
to the base CSV/JSON data and returns a downloadable CSV file.
"""
import csv
import io
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.data import load_data
import app.config as cfg

router = APIRouter(tags=["export"])


@router.get("/data/export-4way")
def export_4way():
    """Export the current data as CSV with 4-way annotation columns appended."""
    if not os.path.isfile(cfg.DATA_FILE_PATH):
        raise HTTPException(status_code=400, detail="Veri dosyası bulunamadı. Önce bir CSV/JSON yükleyin.")
    data = load_data()  # DataFrame (CSV) or list (JSON)
    output = io.StringIO()
    writer = csv.writer(output)

    extra_columns = ["selected_triplets", "resolution_tier", "annotator_notes"]

    if hasattr(data, "columns"):
        # DataFrame path (CSV source)
        writer.writerow(list(data.columns) + extra_columns)
        for _, row in data.iterrows():
            writer.writerow(list(row) + ["[]", "", ""])
    else:
        # List-of-dicts path (JSON source)
        if data:
            writer.writerow(list(data[0].keys()) + extra_columns)
            for row in data:
                writer.writerow(list(row.values()) + ["[]", "", ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=export-4way.csv",
        },
    )
