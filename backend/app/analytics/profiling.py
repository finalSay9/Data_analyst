"""
Profiling service: computes deeper per-column statistics for an already-
ingested dataset.

Deliberately separate from ingestion, and reads from the dynamic table
via the engine (pd.read_sql_table) rather than reusing the original
upload's in-memory DataFrame. This matters for two reasons:
1. It proves profiling works as a standalone operation on any existing
   dataset, not just immediately after upload (e.g. "re-profile dataset
   #3" is a real, separate use case later).
2. It's the more honest test of the pipeline -- data as it actually
   landed in Postgres, not data still held in Python memory.

Stats computed depend on the column's inferred_type (recorded at
ingestion time in DatasetColumn), not on pandas' dtype after reading
back -- see the note in ingestion_service about why raw dtype alone
isn't trustworthy for this.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset



_TOP_VALUES_LIMIT = 5


@dataclass
class ColumnProfile:
    name: str
    inferred_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    # Type-specific fields, populated depending on inferred_type; left as
    # None/empty for types where they don't apply rather than using
    # separate subclasses -- simpler to serialize for the API response.
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None
    true_count: int | None = None
    false_count: int | None = None
    min_date: str | None = None
    max_date: str | None = None
    top_values: list[dict[str, Any]] = field(default_factory=list)


def _profile_numeric(series: pd.Series, profile: ColumnProfile) -> None:
    numeric = pd.to_numeric(series, errors="coerce")
    non_null = numeric.dropna()
    if non_null.empty:
        return
    profile.min_value = float(non_null.min())
    profile.max_value = float(non_null.max())
    profile.mean = round(float(non_null.mean()), 4)
    profile.median = float(non_null.median())
    # std of a single value is NaN, not an error -- guard explicitly.
    profile.std_dev = round(float(non_null.std()), 4) if len(non_null) > 1 else 0.0


def _profile_boolean(series: pd.Series, profile: ColumnProfile) -> None:
    counts = series.value_counts(dropna=True)
    profile.true_count = int(counts.get(True, 0))
    profile.false_count = int(counts.get(False, 0))


def _profile_datetime(series: pd.Series, profile: ColumnProfile) -> None:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    non_null = parsed.dropna()
    if non_null.empty:
        return
    profile.min_date = non_null.min().isoformat()
    profile.max_date = non_null.max().isoformat()


def _profile_string(series: pd.Series, profile: ColumnProfile) -> None:
    top = series.value_counts(dropna=True).head(_TOP_VALUES_LIMIT)
    profile.top_values = [{"value": str(value), "count": int(count)} for value, count in top.items()]


_TYPE_PROFILERS = {
    "integer": _profile_numeric,
    "float": _profile_numeric,
    "boolean": _profile_boolean,
    "datetime": _profile_datetime,
    "string": _profile_string,
}


def profile_dataset(engine: Engine, dataset: Dataset) -> list[ColumnProfile]:
    """
    Read the dataset's dynamic table and compute a ColumnProfile per
    column, using the inferred_type recorded at ingestion time to decide
    which stats apply.
    """
    df = pd.read_sql_table(dataset.table_name, con=engine)
    row_count = len(df)

    profiles: list[ColumnProfile] = []

    for column in dataset.columns:
        series = df[column.name]
        null_count = int(series.isna().sum())

        profile = ColumnProfile(
            name=column.name,
            inferred_type=column.inferred_type,
            null_count=null_count,
            null_percentage=round((null_count / row_count) * 100, 2) if row_count else 0.0,
            unique_count=int(series.nunique(dropna=True)),
        )

        profiler_fn = _TYPE_PROFILERS.get(column.inferred_type)
        if profiler_fn is not None:
            profiler_fn(series, profile)

        profiles.append(profile)

    return profiles
