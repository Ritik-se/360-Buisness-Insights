import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401 (registers models with Base before create_all)
from routers import upload, dashboard, history, cleaning, ai_assistant, analysis

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Business Insights 360 API")

# FRONTEND_URL lets the deployed frontend's origin be configured without a code
# change; localhost origins stay allowed for local development either way.
_extra_origins = [o.strip() for o in os.environ.get("FRONTEND_URL", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *_extra_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(dashboard.router)
app.include_router(history.router)
app.include_router(cleaning.router)
app.include_router(ai_assistant.router)
app.include_router(analysis.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
