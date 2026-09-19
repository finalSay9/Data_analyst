"""
Pydantic schemas: API request/response shapes.

Deliberately separate from app.models (SQLAlchemy ORM classes). Keeping
these distinct means the API contract can evolve independently of the
database schema -- e.g. we can hide internal fields (table_name might
become internal-only later) or reshape output without touching models.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.dataset import DatasetStatus


class DatasetColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    inferred_type: str
    null_count: int
    unique_count: int


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    table_name: str
    row_count: int
    status: DatasetStatus
    created_at: datetime
    columns: list[DatasetColumnRead] = []


class DatasetSummary(BaseModel):
    """Lighter-weight shape for list endpoints -- no per-column detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    row_count: int
    status: DatasetStatus
    created_at: datetime


class FailedRow(BaseModel):
    row_index: int
    error: str


class DatasetUploadResponse(BaseModel):
    dataset: DatasetRead
    inserted_count: int
    failed_rows: list[FailedRow] = []

    @property
    def had_failures(self) -> bool:
        return len(self.failed_rows) > 0
