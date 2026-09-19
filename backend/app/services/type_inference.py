"""
Column type inference: pandas Series -> our own ColumnType -> Postgres type.

Why this exists instead of just using df.to_sql() or a raw pandas dtype:
- pandas' `object` dtype is ambiguous (strings, mixed types, dates-as-strings)
- pandas reads "mostly-integer" columns with any nulls as float64 (NaN forces
  float), which would silently create FLOAT columns for what are really
  nullable integer columns unless we check for it explicitly
- pandas won't detect dates unless asked — a column of "2024-01-15" strings
  is just `object` by default

This module is deliberately decision-explicit: every branch below is a
judgment call we're making on purpose, not something pandas decided for us.
"""

import enum

import pandas as pd
from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.types import TypeEngine


class ColumnType(str, enum.Enum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    STRING = "string"


# Maps our type system -> actual Postgres column type name (for display/docs).
POSTGRES_TYPE_MAP: dict[ColumnType, str] = {
    ColumnType.INTEGER: "INTEGER",
    ColumnType.FLOAT: "FLOAT",
    ColumnType.BOOLEAN: "BOOLEAN",
    ColumnType.DATETIME: "TIMESTAMP",
    ColumnType.STRING: "TEXT",
}

# Maps our type system -> SQLAlchemy Core type object, used to actually
# build dynamic table DDL. Dialect-agnostic on purpose: this lets us test
# the ingestion pipeline against SQLite in-memory, while it still produces
# correct DDL against the real Postgres engine in production.
SQLALCHEMY_TYPE_MAP: dict[ColumnType, type[TypeEngine]] = {
    ColumnType.INTEGER: Integer,
    ColumnType.FLOAT: Float,
    ColumnType.BOOLEAN: Boolean,
    ColumnType.DATETIME: DateTime,
    ColumnType.STRING: Text,
}

# Threshold for treating an `object` column as datetime: at least this
# fraction of non-null values must successfully parse as dates.
_DATETIME_PARSE_THRESHOLD = 0.9


def _is_whole_number_float_column(series: pd.Series) -> bool:
    """
    True if a float64 column contains only whole numbers (ignoring NaN).

    This catches the classic "integer column with missing values" case:
    pandas reads [1, 2, NaN, 4] as float64 even though semantically it's
    a nullable integer column.
    """
    non_null = series.dropna()
    if non_null.empty:
        return False
    return (non_null == non_null.round()).all()


def _looks_like_datetime(series: pd.Series) -> bool:
    """
    True if enough non-null values in an `object` column parse as dates
    to treat the whole column as datetime.

    We sample rather than parse the full column for performance on large
    datasets, and require a high success rate (not 100%) so a handful of
    genuinely malformed rows don't block correct type detection.
    """
    non_null = series.dropna()
    if non_null.empty:
        return False

    sample = non_null.sample(min(len(non_null), 200), random_state=0)

    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    success_rate = parsed.notna().mean()

    return success_rate >= _DATETIME_PARSE_THRESHOLD


def infer_column_type(series: pd.Series) -> ColumnType:
    """
    Infer our own ColumnType for a pandas Series (one column of an
    uploaded CSV/Excel file).

    Order of checks matters:
    1. bool must be checked before int/float (bool is a subclass of int
       in numpy, so a naive numeric check would misclassify it)
    2. integer dtype -> INTEGER directly
    3. float dtype -> check if it's actually a nullable-integer column
       masquerading as float, else FLOAT
    4. object dtype -> attempt datetime detection, else STRING
    5. anything else (e.g. pandas' own datetime64 dtype, if parse_dates
       was used upstream) -> DATETIME
    """
    if pd.api.types.is_bool_dtype(series):
        return ColumnType.BOOLEAN

    if pd.api.types.is_integer_dtype(series):
        return ColumnType.INTEGER

    if pd.api.types.is_float_dtype(series):
        if _is_whole_number_float_column(series):
            return ColumnType.INTEGER
        return ColumnType.FLOAT

    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnType.DATETIME

    # `object` covers pandas < 3.0's default string storage; `is_string_dtype`
    # additionally catches pandas >= 3.0's new dedicated StringDtype. Both
    # need the same datetime-sniffing treatment, since either can hold
    # date strings that pandas didn't auto-parse.
    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        if _looks_like_datetime(series):
            return ColumnType.DATETIME
        return ColumnType.STRING

    # Fallback for any dtype we haven't explicitly handled (e.g. category,
    # complex, timedelta) — safest default is TEXT rather than guessing.
    return ColumnType.STRING


def postgres_type_for(column_type: ColumnType) -> str:
    return POSTGRES_TYPE_MAP[column_type]


def sqlalchemy_type_for(column_type: ColumnType) -> TypeEngine:
    """Returns an *instance* of the SQLAlchemy type, ready to use in a Column()."""
    return SQLALCHEMY_TYPE_MAP[column_type]()
