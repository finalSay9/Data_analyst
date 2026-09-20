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


class ColumnProfileRead(BaseModel):
    name: str
    inferred_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None
    true_count: int | None = None
    false_count: int | None = None
    min_date: str | None = None
    max_date: str | None = None
    top_values: list[dict] = []


class DatasetProfileResponse(BaseModel):
    dataset_id: int
    row_count: int
    columns: list[ColumnProfileRead]


class CorrelationPairRead(BaseModel):
    column_a: str
    column_b: str
    correlation: float
    strength: str


class CorrelationResponse(BaseModel):
    dataset_id: int
    numeric_columns: list[str]
    matrix: list[list[float | None]] = []
    pairs: list[CorrelationPairRead] = []
    insufficient_columns: bool = False


class OutlierPointRead(BaseModel):
    row_id: int
    value: float
    distance_from_bound: float


class ColumnOutliersRead(BaseModel):
    column: str
    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    outlier_count: int
    outlier_percentage: float
    sample_outliers: list[OutlierPointRead] = []


class OutlierResponse(BaseModel):
    dataset_id: int
    columns: list[ColumnOutliersRead] = []


class GroupResultRead(BaseModel):
    group_value: str
    row_count: int
    value: float | None


class AggregationResponse(BaseModel):
    dataset_id: int
    group_by_column: str
    agg_column: str | None
    function: str
    groups: list[GroupResultRead] = []
    total_groups: int = 0
    too_many_groups: bool = False


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
