"""
Fixed-schema models: metadata *about* uploaded datasets.

The actual row-level data from an upload does NOT live here — it lives in
a dynamically created table (e.g. `dataset_7_sales_data`) whose name is
stored on `Dataset.table_name`. This table only tracks *what exists*:
dataset identity, source file info, and per-column profiling metadata.

Why split it this way: it keeps the fixed schema small, Alembic-manageable,
and queryable regardless of how many dynamic tables pile up.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # Name of the dynamically created Postgres table holding the actual rows.
    # e.g. "dataset_7_sales_data" — generated at ingestion time.
    table_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus), default=DatasetStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base):
    """
    Per-column metadata + profiling results for a dataset.

    Populated in two stages:
    1. At ingestion: name, inferred_type (from pandas dtype -> our own enum)
    2. At profiling: null_count, unique_count, min/max/mean etc. (Phase 1 step 4)
    """

    __tablename__ = "dataset_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "integer" | "float" | "string" | "boolean" | "datetime"

    null_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, default=0)

    dataset: Mapped["Dataset"] = relationship(back_populates="columns")
