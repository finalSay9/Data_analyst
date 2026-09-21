"""
Distribution analysis: histogram binning for a single numeric column.

Bin count defaults to a simple, well-known rule (min(sqrt(n), 50)) if
not specified -- capped at 50 so a huge dataset doesn't return an
unusably dense histogram. Callers can override via `bins`.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset

_NUMERIC_TYPES = {"integer", "float"}
_MAX_BINS = 50
_MIN_BINS = 5


class ColumnNotFoundError(Exception):
    pass


class InvalidDistributionError(Exception):
    pass


@dataclass
class HistogramBin:
    range_start: float
    range_end: float
    count: int


@dataclass
class DistributionResult:
    column: str
    bins: list[HistogramBin] = field(default_factory=list)
    min_value: float = 0.0
    max_value: float = 0.0
    mean: float = 0.0
    total_count: int = 0


def _default_bin_count(n: int) -> int:
    if n <= 0:
        return _MIN_BINS
    return int(max(_MIN_BINS, min(_MAX_BINS, round(n**0.5))))


def compute_distribution(
    engine: Engine, dataset: Dataset, column: str, bins: int | None = None
) -> DistributionResult:
    column_meta = next((c for c in dataset.columns if c.name == column), None)
    if column_meta is None:
        raise ColumnNotFoundError(f"Column '{column}' not found on this dataset.")
    if column_meta.inferred_type not in _NUMERIC_TYPES:
        raise InvalidDistributionError(
            f"Distributions require a numeric column; '{column}' is "
            f"'{column_meta.inferred_type}'."
        )

    df = pd.read_sql_table(dataset.table_name, con=engine)
    series = pd.to_numeric(df[column], errors="coerce").dropna()

    if series.empty:
        return DistributionResult(column=column)

    bin_count = bins if bins and bins > 0 else _default_bin_count(len(series))
    bin_count = max(_MIN_BINS, min(_MAX_BINS, bin_count))

    counts, edges = np.histogram(series, bins=bin_count)

    histogram_bins = [
        HistogramBin(
            range_start=round(float(edges[i]), 4),
            range_end=round(float(edges[i + 1]), 4),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]

    return DistributionResult(
        column=column,
        bins=histogram_bins,
        min_value=round(float(series.min()), 4),
        max_value=round(float(series.max()), 4),
        mean=round(float(series.mean()), 4),
        total_count=int(len(series)),
    )
