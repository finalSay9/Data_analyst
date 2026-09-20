"""
Outlier detection via the IQR (interquartile range) method: for each
numeric column, values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] are flagged.

Why IQR over z-score: IQR is based on percentiles, so it isn't skewed by
the very outliers it's trying to detect (z-score's mean/std are both
pulled by extreme values, which can mask the outliers themselves — the
classic "one huge outlier makes the std so large that even that outlier
looks unremarkable" problem). IQR is also the standard, well-known
default for exploratory data analysis (it's literally what a boxplot's
whiskers are built from), so results here map directly onto that
intuition if visualized later.

Notable edge case, deliberately not glossed over: if a column has zero
IQR (Q1 == Q3, meaning at least half its values are identical), the
lower and upper bounds collapse to that single value, and ANY differing
value gets flagged as an outlier. This is mathematically consistent
(a column that's 80% one value really does make any other value
anomalous), but worth knowing about explicitly rather than discovering
by surprise -- see the dedicated test for this.
"""

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset

_NUMERIC_TYPES = {"integer", "float"}
_IQR_MULTIPLIER = 1.5
_MAX_SAMPLE_OUTLIERS = 10


@dataclass
class OutlierPoint:
    row_id: int
    value: float
    distance_from_bound: float  # how far past the nearer bound, always >= 0


@dataclass
class ColumnOutliers:
    column: str
    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    outlier_count: int
    outlier_percentage: float
    sample_outliers: list[OutlierPoint] = field(default_factory=list)


@dataclass
class OutlierResult:
    columns: list[ColumnOutliers] = field(default_factory=list)


def _detect_column_outliers(series: pd.Series, ids: pd.Series, column_name: str) -> ColumnOutliers | None:
    non_null = series.dropna()
    if non_null.empty:
        return None

    q1 = float(non_null.quantile(0.25))
    q3 = float(non_null.quantile(0.75))
    iqr = q3 - q1
    lower_bound = q1 - _IQR_MULTIPLIER * iqr
    upper_bound = q3 + _IQR_MULTIPLIER * iqr

    is_outlier = (series < lower_bound) | (series > upper_bound)
    is_outlier = is_outlier.fillna(False)  # NaN comparisons -> not an outlier, not a crash

    outlier_count = int(is_outlier.sum())
    total = len(non_null)
    outlier_percentage = round((outlier_count / total) * 100, 2) if total else 0.0

    # Distance from the nearer bound -- lets us rank "worst offenders"
    # rather than just listing whichever outliers happen to come first.
    outlier_rows = series[is_outlier]
    outlier_ids = ids[is_outlier]

    distances = outlier_rows.apply(
        lambda v: (lower_bound - v) if v < lower_bound else (v - upper_bound)
    )

    sample_df = pd.DataFrame(
        {"row_id": outlier_ids, "value": outlier_rows, "distance": distances}
    ).sort_values("distance", ascending=False)

    sample_outliers = [
        OutlierPoint(
            row_id=int(row.row_id),
            value=float(row.value),
            distance_from_bound=round(float(row.distance), 4),
        )
        for row in sample_df.head(_MAX_SAMPLE_OUTLIERS).itertuples()
    ]

    return ColumnOutliers(
        column=column_name,
        q1=round(q1, 4),
        q3=round(q3, 4),
        iqr=round(iqr, 4),
        lower_bound=round(lower_bound, 4),
        upper_bound=round(upper_bound, 4),
        outlier_count=outlier_count,
        outlier_percentage=outlier_percentage,
        sample_outliers=sample_outliers,
    )


def detect_outliers(engine: Engine, dataset: Dataset) -> OutlierResult:
    numeric_columns = [c.name for c in dataset.columns if c.inferred_type in _NUMERIC_TYPES]
    if not numeric_columns:
        return OutlierResult(columns=[])

    df = pd.read_sql_table(dataset.table_name, con=engine)

    results: list[ColumnOutliers] = []
    for col_name in numeric_columns:
        numeric_series = pd.to_numeric(df[col_name], errors="coerce")
        column_result = _detect_column_outliers(numeric_series, df["id"], col_name)
        if column_result is not None:
            results.append(column_result)

    return OutlierResult(columns=results)
