"""
Correlation analysis: pairwise Pearson correlation between all numeric
columns of a dataset.

Design notes:
- Only columns inferred as "integer" or "float" (see type_inference.py)
  are considered -- correlating a boolean or a string column numerically
  would be either meaningless or require a different technique entirely
  (e.g. point-biserial for boolean-vs-numeric), which is out of scope
  here and worth flagging explicitly rather than silently coercing.
- pandas' `.corr()` handles missing values via pairwise deletion
  automatically (a NaN in either column excludes that row from just
  that pair's calculation, not the whole dataset) -- this is standard
  behavior for correlation matrices, not something we need to implement
  ourselves.
- Returns both the full matrix (useful for a heatmap in the frontend
  later) and a flat, sorted list of pairs (useful for "what are the
  strongest relationships in this dataset" at a glance).
"""

from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset

_NUMERIC_TYPES = {"integer", "float"}

# Thresholds for labeling correlation strength -- a common, if somewhat
# arbitrary, convention (Cohen's guidelines). Worth revisiting once real
# datasets show whether these thresholds are actually useful in practice.
_STRONG_THRESHOLD = 0.7
_MODERATE_THRESHOLD = 0.4


def _strength_label(correlation: float) -> str:
    abs_corr = abs(correlation)
    if abs_corr >= _STRONG_THRESHOLD:
        return "strong"
    if abs_corr >= _MODERATE_THRESHOLD:
        return "moderate"
    return "weak"


@dataclass
class CorrelationPair:
    column_a: str
    column_b: str
    correlation: float
    strength: str


@dataclass
class CorrelationResult:
    numeric_columns: list[str]
    matrix: list[list[float | None]] = field(default_factory=list)
    pairs: list[CorrelationPair] = field(default_factory=list)
    insufficient_columns: bool = False


def compute_correlations(engine: Engine, dataset: Dataset) -> CorrelationResult:
    numeric_columns = [c.name for c in dataset.columns if c.inferred_type in _NUMERIC_TYPES]

    if len(numeric_columns) < 2:
        # Not an error -- a dataset can legitimately have 0 or 1 numeric
        # columns. Correlation just isn't a meaningful operation here,
        # so we return an explicit flag rather than an empty-but-valid-
        # looking result the caller might misinterpret as "no correlation
        # found" instead of "couldn't be computed."
        return CorrelationResult(numeric_columns=numeric_columns, insufficient_columns=True)

    df = pd.read_sql_table(dataset.table_name, con=engine)
    numeric_df = df[numeric_columns].apply(pd.to_numeric, errors="coerce")

    corr_matrix = numeric_df.corr(method="pearson")

    matrix: list[list[float | None]] = [
        [
            round(float(value), 4) if pd.notna(value) else None
            for value in row
        ]
        for row in corr_matrix.to_numpy()
    ]

    pairs: list[CorrelationPair] = []
    for i, col_a in enumerate(numeric_columns):
        for j in range(i + 1, len(numeric_columns)):
            col_b = numeric_columns[j]
            coeff = corr_matrix.iloc[i, j]
            if pd.isna(coeff):
                # Happens when a column has zero variance (all identical
                # values) -- correlation is mathematically undefined,
                # not zero. Skip rather than misreport it as "no
                # relationship."
                continue
            rounded = round(float(coeff), 4)
            pairs.append(
                CorrelationPair(
                    column_a=col_a,
                    column_b=col_b,
                    correlation=rounded,
                    strength=_strength_label(rounded),
                )
            )

    pairs.sort(key=lambda p: abs(p.correlation), reverse=True)

    return CorrelationResult(numeric_columns=numeric_columns, matrix=matrix, pairs=pairs)
