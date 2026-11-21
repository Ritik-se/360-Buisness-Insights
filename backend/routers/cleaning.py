import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset
from services import semantic_engine, cleaning_service
from .upload import _read_dataframe, UPLOAD_DIR

router = APIRouter(prefix="/api", tags=["cleaning"])


def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/dataset/{dataset_id}/profile-issues")
def profile_issues(dataset_id: int, db: Session = Depends(get_db)):
    dataset = _get_dataset(dataset_id, db)
    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    issues = cleaning_service.profile_issues(df)
    return {"dataset_id": dataset_id, "row_count": len(df), "issues": issues}


@router.post("/dataset/{dataset_id}/cleaning-preview")
def cleaning_preview(dataset_id: int, operations: list = Body(...), db: Session = Depends(get_db)):
    dataset = _get_dataset(dataset_id, db)
    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    cleaned = cleaning_service.apply_cleaning(df, operations)
    summary = cleaning_service.quality_summary(df, cleaned)
    before_quality = semantic_engine.data_quality_score(df)
    after_quality = semantic_engine.data_quality_score(cleaned)
    return {
        "summary": summary,
        "quality_before": before_quality,
        "quality_after": after_quality,
        "preview_rows": cleaned.head(10).astype(object).where(cleaned.head(10).notna(), None).to_dict(orient="records"),
    }


@router.post("/dataset/{dataset_id}/clean")
def clean_dataset(dataset_id: int, operations: list = Body(...), db: Session = Depends(get_db)):
    dataset = _get_dataset(dataset_id, db)
    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    cleaned = cleaning_service.apply_cleaning(df, operations)

    if cleaned.empty:
        raise HTTPException(status_code=400, detail="Cleaning would remove all rows — adjust your selections.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    base_name = dataset.filename.rsplit(".", 1)[0]
    stored_name = f"{uuid.uuid4().hex}_{base_name}_cleaned.csv"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    cleaned.to_csv(stored_path, index=False)

    analysis = semantic_engine.analyze_dataframe(cleaned)
    new_dataset = Dataset(
        filename=f"{base_name}_cleaned.csv",
        category=", ".join(sorted({c["role"] for c in analysis["columns"]})),
        confidence=100,
        row_count=analysis["row_count"],
        column_count=analysis["column_count"],
        status="cleaned",
        uploaded_at=datetime.utcnow(),
        stored_path=stored_path,
        source_dataset_id=dataset.id,
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    return {
        "dataset_id": new_dataset.id,
        "filename": new_dataset.filename,
        "uploaded_at": new_dataset.uploaded_at.isoformat(),
        **analysis,
    }
