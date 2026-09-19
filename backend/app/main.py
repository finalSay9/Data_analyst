from fastapi import FastAPI

from app.api.v1 import datasets
from app.core.config import settings

app = FastAPI(
    title="AI Data Analyst Platform",
    description="Phase 1: data ingestion, schema inference, and profiling.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
