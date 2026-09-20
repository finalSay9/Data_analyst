"""
Group-by aggregation: group rows by one column's values, compute one
aggregate function over another column within each group.

Design notes:
- group_by accepts ANY column type, including numeric (e.g. grouping by
  a "rating" or "year" column is a completely normal use case even
  though those columns are inferred as integer, not string).
- The caller picks exactly one function per request (count/sum/mean/
  min/max/median), not "compute everything" -- keeps each response
  focused and matches how this will actually be used (e.g. "average
  price by category", not "every possible stat by category" every time).
- `count` is special: it doesn't need an agg_column at all (it's just
  group size), so agg_column is optional only for that function.
- Cardinality guard: grouping by a column with very high cardinality
  (e.g. accidentally grouping by an ID-like column) would return a
  near-useless wall of one-row groups. Rather than silently returning
  a huge payload, we cap it and flag `too_many_groups` so the caller
  (API/frontend) can show a clear message instead of a giant table.
- Null group values are kept as an explicit "(missing)" group rather
  than silently dropped -- how much of a category is unlabeled is
  itself useful information, not noise to discard.
"""

import enum
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset

_NUMERIC_TYPES = {"integer", "float"}
_MAX_GROUPS = 100
_MISSING_LABEL = "(missing)"


class AggregationFunction(str, enum.Enum):
    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"


class ColumnNotFoundError(Exception):
    pass


class InvalidAggregationError(Exception):
    pass


@dataclass
class GroupResult:
    group_value: str
    row_count: int
    value: float | None  # the computed aggregate; None only if the group had no valid data


@dataclass
class AggregationResult:
    group_by_column: str
    agg_column: str | None
    function: AggregationFunction
    groups: list[GroupResult] = field(default_factory=list)
    total_groups: int = 0
    too_many_groups: bool = False


def _column_names(dataset: Dataset) -> set[str]:
    return {c.name for c in dataset.columns}


def _column_type(dataset: Dataset, name: str) -> str | None:
    for c in dataset.columns:
        if c.name == name:
            return c.inferred_type
    return None


def compute_aggregation(
    engine: Engine,
    dataset: Dataset,
    group_by_column: str,
    function: AggregationFunction,
    agg_column: str | None = None,
) -> AggregationResult:
    known_columns = _column_names(dataset)

    if group_by_column not in known_columns:
        raise ColumnNotFoundError(f"Column '{group_by_column}' not found on this dataset.")

    if function == AggregationFunction.COUNT:
        # agg_column is optional for COUNT -- counting rows per group
        # doesn't require looking at any particular column's values.
        if agg_column is not None and agg_column not in known_columns:
            raise ColumnNotFoundError(f"Column '{agg_column}' not found on this dataset.")
    else:
        if agg_column is None:
            raise InvalidAggregationError(
                f"agg_column is required for the '{function.value}' function."
            )
        if agg_column not in known_columns:
            raise ColumnNotFoundError(f"Column '{agg_column}' not found on this dataset.")
        if _column_type(dataset, agg_column) not in _NUMERIC_TYPES:
            raise InvalidAggregationError(
                f"'{function.value}' requires a numeric column; "
                f"'{agg_column}' is '{_column_type(dataset, agg_column)}'."
            )

    df = pd.read_sql_table(dataset.table_name, con=engine)

    # dropna=False keeps null group values visible as their own group
    # instead of silently discarding those rows from the result.
    grouped = df.groupby(group_by_column, dropna=False)

    total_groups = grouped.ngroups
    too_many_groups = total_groups > _MAX_GROUPS

    if too_many_groups:
        return AggregationResult(
            group_by_column=group_by_column,
            agg_column=agg_column,
            function=function,
            groups=[],
            total_groups=total_groups,
            too_many_groups=True,
        )

    results: list[GroupResult] = []

    if function == AggregationFunction.COUNT:
        # Row count per group. We deliberately use .size() (counts every
        # row) rather than .count() on a specific column (which excludes
        # that column's own nulls) -- COUNT with no agg_column means
        # "how many rows in this group," full stop.
        sizes = grouped.size()
        for group_key, row_count in sizes.items():
            label = _MISSING_LABEL if pd.isna(group_key) else str(group_key)
            results.append(
                GroupResult(group_value=label, row_count=int(row_count), value=float(row_count))
            )
    else:
        agg_func_name = function.value  # matches pandas' own method names
        numeric_series = pd.to_numeric(df[agg_column], errors="coerce")
        temp_df = pd.DataFrame({group_by_column: df[group_by_column], "_agg": numeric_series})
        grouped_numeric = temp_df.groupby(group_by_column, dropna=False)

        sizes = grouped_numeric.size()
        aggregated = getattr(grouped_numeric["_agg"], agg_func_name)()

        for group_key in sizes.index:
            label = _MISSING_LABEL if pd.isna(group_key) else str(group_key)
            row_count = int(sizes.loc[group_key])
            agg_value = aggregated.loc[group_key]
            results.append(
                GroupResult(
                    group_value=label,
                    row_count=row_count,
                    value=round(float(agg_value), 4) if pd.notna(agg_value) else None,
                )
            )

    # Sort by the computed value descending -- surfaces the most
    # interesting groups (highest total, highest average, etc.) first.
    # None values (a group with no valid numeric data) sort last.
    results.sort(key=lambda r: (r.value is None, -(r.value or 0)))

    return AggregationResult(
        group_by_column=group_by_column,
        agg_column=agg_column,
        function=function,
        groups=results,
        total_groups=total_groups,
        too_many_groups=False,
    )
