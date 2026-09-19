"""
Dataset endpoints: upload, list, retrieve.

Note on sync vs async: `upload_dataset` is `async def` only because
reading the UploadFile body requires `await file.read()`. The actual
ingestion (`ingest_file`) is a synchronous, CPU/IO-bound call (pandas
parsing + blocking DB calls) running directly on the event loop here.
That's fine for a learning-stage v1 with one user at a time, but it's a
deliberate simplification worth revisiting in Phase 5: either run it in
a threadpool (`fastapi.concurrency.run_in_threadpool`) or move it to a
background job (Celery/Taskiq) so a large upload doesn't block other
requests.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, get_engine
from app.models.dataset import Dataset
from app.schemas.dataset import (
    ColumnProfileRead,
    DatasetProfileResponse,
    DatasetRead,
    DatasetSummary,
    DatasetUploadResponse,
)
from app.services.ingestion_service import UnsupportedFileTypeError, ingest_file
from app.analytics.profiling import profile_dataset

router = APIRouter()

_ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")


@router.post("/upload", response_model=DatasetUploadResponse, status_code=201)
async def upload_dataset(
    file: UploadFile,
    db: Session = Depends(get_db),
    engine: Engine = Depends(get_engine),
) -> DatasetUploadResponse:
    if not file.filename or not file.filename.lower().endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = ingest_file(db, engine, file_bytes, file.filename)
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Anything unexpected (malformed CSV pandas can't parse at all,
        # etc.) rolls back whatever the session hadn't committed and
        # surfaces as a 500 rather than a half-committed Dataset row.
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}") from e

    return DatasetUploadResponse(
        dataset=DatasetRead.model_validate(result.dataset),
        inserted_count=result.inserted_count,
        failed_rows=result.failed_rows,
    )


@router.get("", response_model=list[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)) -> list[Dataset]:
    # Order by created_at, with id as a tiebreaker: two uploads landing
    # within the same timestamp tick (real risk under load, or on
    # backends with second-level timestamp precision) would otherwise
    # sort unpredictably. id is monotonically increasing regardless of
    # clock resolution, so it's a reliable secondary sort key.
    return list(
        db.scalars(select(Dataset).order_by(Dataset.created_at.desc(), Dataset.id.desc()))
    )


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    return dataset


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    dataset_id: int,
    db: Session = Depends(get_db),
    engine: Engine = Depends(get_engine),
) -> DatasetProfileResponse:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    profiles = profile_dataset(engine, dataset)

    return DatasetProfileResponse(
        dataset_id=dataset.id,
        row_count=dataset.row_count,
        columns=[ColumnProfileRead(**vars(p)) for p in profiles],
    )
