import json
import os
import uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset
from services import semantic_engine

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads")
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 25 * 1024 * 1024


def _read_dataframe(path: str, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(path)
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    raise HTTPException(status_code=400, detail="Unsupported file type. Upload .csv or .xlsx.")


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx or .xls files are supported.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 25MB limit.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(contents)

    try:
        df = _read_dataframe(stored_path, file.filename)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if df.empty or len(df.columns) == 0:
        raise HTTPException(status_code=400, detail="The uploaded dataset is empty.")

    df.columns = [str(c).strip() for c in df.columns]

    analysis = semantic_engine.analyze_dataframe(df)

    dataset = Dataset(
        filename=file.filename,
        category=", ".join(sorted({c["role"] for c in analysis["columns"]})),
        confidence=100,
        row_count=analysis["row_count"],
        column_count=analysis["column_count"],
        status="processed",
        uploaded_at=datetime.utcnow(),
        stored_path=stored_path,
        profile_json=json.dumps(analysis["columns"]),
        mapping_json=json.dumps({c["name"]: c["role"] for c in analysis["columns"]}),
        kpi_json=json.dumps(analysis["kpis"]),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {
        "dataset_id": dataset.id,
        "filename": file.filename,
        "uploaded_at": dataset.uploaded_at.isoformat(),
        **analysis,
    }
