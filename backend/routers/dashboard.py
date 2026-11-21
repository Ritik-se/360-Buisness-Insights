import io
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset
from services import semantic_engine, forecasting, simulation_service
from .upload import _read_dataframe

router = APIRouter(prefix="/api", tags=["dashboard"])


def _load_and_filter(dataset: Dataset, start_date, end_date, dimension_value, search):
    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    tags = semantic_engine.tag_columns(df)
    meta = semantic_engine.filter_metadata(df, tags)
    filtered = semantic_engine.apply_filters(
        df,
        date_col=meta["date_column"], start_date=start_date, end_date=end_date,
        dimension_col=meta["dimension_column"], dimension_value=dimension_value,
        search=search,
    )
    return df, tags, meta, filtered


@router.get("/dashboard/{dataset_id}")
def get_dashboard(
    dataset_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimension_value: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    _, tags, meta, filtered = _load_and_filter(dataset, start_date, end_date, dimension_value, search)

    if filtered.empty:
        raise HTTPException(status_code=400, detail="No records match the selected filters.")

    analysis = semantic_engine.analyze_dataframe(filtered)
    analysis["filters"] = meta  # keep full-dataset filter options stable across requests
    return {
        "dataset_id": dataset.id,
        "filename": dataset.filename,
        "uploaded_at": dataset.uploaded_at.isoformat(),
        **analysis,
    }


@router.get("/dashboard/{dataset_id}/forecast")
def get_forecast(dataset_id: int, periods: int = 3, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    df, tags, meta, _ = _load_and_filter(dataset, None, None, None, None)
    date_col = meta["date_column"]
    if not date_col:
        raise HTTPException(status_code=400, detail="This dataset has no date column, so trends can't be forecast.")

    metric_cols = [c for c, t in tags.items() if t["role"] in ("metric", "currency_metric", "count_metric", "rating_metric")]
    if not metric_cols:
        raise HTTPException(status_code=400, detail="No numeric metric was found to forecast.")

    primary_metric = max(metric_cols, key=lambda c: semantic_engine._metric_priority(c, tags[c]))
    result = forecasting.forecast_metric(df, date_col, primary_metric, periods=min(max(periods, 1), 12))
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough monthly history (need at least 4 months) to forecast reliably.")
    return result


@router.get("/dashboard/{dataset_id}/chart-options")
def get_chart_options(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    df, tags, _, _ = _load_and_filter(dataset, None, None, None, None)
    return semantic_engine.available_chart_options(tags)


@router.post("/dashboard/{dataset_id}/custom-chart")
def custom_chart(dataset_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    df, tags, _, _ = _load_and_filter(dataset, None, None, None, None)
    try:
        return semantic_engine.build_custom_chart(
            df, tags,
            chart_type=body.get("chart_type"),
            metric=body.get("metric"),
            dimension=body.get("dimension"),
            metric2=body.get("metric2"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/dashboard/{dataset_id}/simulate")
def simulate_whatif(dataset_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    df, tags, _, _ = _load_and_filter(dataset, None, None, None, None)
    try:
        return simulation_service.simulate(df, tags, body.get("adjustments", []))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/dashboard/{dataset_id}/export")
def export_dashboard_data(
    dataset_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimension_value: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exports the currently filtered view of the dataset as a CSV download."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    _, _, _, filtered = _load_and_filter(dataset, start_date, end_date, dimension_value, search)
    if filtered.empty:
        raise HTTPException(status_code=400, detail="No records match the selected filters.")

    buffer = io.StringIO()
    filtered.to_csv(buffer, index=False)
    buffer.seek(0)
    base_name = dataset.filename.rsplit(".", 1)[0]
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{base_name}_export.csv"'},
    )
