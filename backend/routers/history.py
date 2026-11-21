import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    """Upload history — every dataset ever uploaded in this workspace, most recent first."""
    datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    return [
        {
            "dataset_id": d.id,
            "filename": d.filename,
            "uploaded_at": d.uploaded_at.isoformat(),
            "row_count": d.row_count,
            "column_count": d.column_count,
            "category": d.category,
            "status": d.status,
            "available": bool(d.stored_path and os.path.exists(d.stored_path)),
        }
        for d in datasets
    ]


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.stored_path and os.path.exists(dataset.stored_path):
        os.remove(dataset.stored_path)
    db.delete(dataset)
    db.commit()
    return {"deleted": dataset_id}
