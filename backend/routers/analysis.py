from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset
from services import anomaly_service, report_service, root_cause_service, semantic_engine
from .upload import _read_dataframe

router = APIRouter(prefix="/api", tags=["analysis"])


def _load(dataset_id: int, db: Session):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    return df


@router.get("/dataset/{dataset_id}/anomalies")
def get_anomalies(dataset_id: int, db: Session = Depends(get_db)):
    df = _load(dataset_id, db)
    tags = semantic_engine.tag_columns(df)
    anomalies = anomaly_service.detect_anomalies(df, tags)
    return {"dataset_id": dataset_id, "row_count": len(df), "anomalies": anomalies}


@router.get("/dataset/{dataset_id}/root-cause")
def get_root_cause(dataset_id: int, metric: str = None, db: Session = Depends(get_db)):
    df = _load(dataset_id, db)
    tags = semantic_engine.tag_columns(df)
    date_cols = [c for c, t in tags.items() if t["role"] == "date"]
    if not date_cols:
        raise HTTPException(status_code=400, detail="This dataset has no date column, so a period-over-period breakdown isn't possible.")

    if not metric:
        metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
        if not metric_cols:
            raise HTTPException(status_code=400, detail="No numeric metric found.")
        metric = max(metric_cols, key=lambda c: semantic_engine._metric_priority(c, tags[c]))
    elif metric not in df.columns:
        raise HTTPException(status_code=400, detail=f"Unknown column '{metric}'.")

    result = root_cause_service.analyze(df, tags, metric, date_cols[0])
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough history to compare periods for this metric.")
    return result


@router.get("/dataset/{dataset_id}/report")
def get_report(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    df = _load(dataset_id, db)
    tags = semantic_engine.tag_columns(df)
    return report_service.build_report(df, tags, dataset.filename)
