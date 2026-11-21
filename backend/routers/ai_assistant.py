from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset
from services import ai_assistant_service, semantic_engine
from .upload import _read_dataframe

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/ai/status")
def ai_status():
    return {"configured": ai_assistant_service.is_configured()}


@router.post("/dataset/{dataset_id}/ask")
def ask(dataset_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.stored_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Ask a question first.")

    df = _read_dataframe(dataset.stored_path, dataset.filename)
    df.columns = [str(c).strip() for c in df.columns]
    tags = semantic_engine.tag_columns(df)

    try:
        return ai_assistant_service.ask(df, tags, question, body.get("history"))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
