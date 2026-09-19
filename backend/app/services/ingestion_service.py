"""
Ingestion service: turns an uploaded CSV/Excel file into a real, queryable
Postgres table plus fixed-schema metadata rows (Dataset, DatasetColumn).

Design notes:
- Table/column creation uses SQLAlchemy Core (MetaData + Table + DDL),
  not the ORM — dynamic tables aren't declarative model classes, they're
  built at runtime from inferred types.
- Row insertion uses SAVEPOINTs (nested transactions) so a partial
  failure doesn't roll back the entire upload. We try a fast chunked
  insert first; if a chunk fails, we roll back just that chunk and
  retry it row-by-row to isolate exactly which rows are bad, without
  losing the rows that succeeded elsewhere.
"""

import io
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
    insert,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetColumn, DatasetStatus
from app.services.type_inference import ColumnType, infer_column_type
from app.utils.naming import build_table_name, dedupe_identifiers

# Our ColumnType -> actual SQLAlchemy column type used for dynamic DDL.
_SQLALCHEMY_TYPE_MAP = {
    ColumnType.INTEGER: Integer,
    ColumnType.FLOAT: Float,
    ColumnType.BOOLEAN: Boolean,
    ColumnType.DATETIME: DateTime,
    ColumnType.STRING: Text,
}

_INSERT_CHUNK_SIZE = 500


class UnsupportedFileTypeError(Exception):
    pass


@dataclass
class IngestionResult:
    dataset: Dataset
    inserted_count: int
    failed_rows: list[dict] = field(default_factory=list)  # [{row_index, error}]

    @property
    def had_failures(self) -> bool:
        return len(self.failed_rows) > 0


def _read_file_to_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    buffer = io.BytesIO(file_bytes)

    if lower.endswith(".csv"):
        return pd.read_csv(buffer)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer)

    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}'. Only .csv, .xlsx, .xls are supported."
    )


def _build_dynamic_table(
    metadata: MetaData, table_name: str, column_types: dict[str, ColumnType]
) -> Table:
    """
    Build (but don't yet create) a SQLAlchemy Table object for the
    dynamic table, with one Column per DataFrame column, typed per the
    already-computed column_types mapping.
    """
    columns = [Column("id", Integer, primary_key=True, autoincrement=True)]

    for col_name, column_type in column_types.items():
        sa_type = _SQLALCHEMY_TYPE_MAP[column_type]
        columns.append(Column(col_name, sa_type, nullable=True))

    return Table(table_name, metadata, *columns)


def _coerce_column_values(df: pd.DataFrame, column_types: dict[str, ColumnType]) -> pd.DataFrame:
    """
    Convert column values to match their inferred type, not just detect it.

    infer_column_type only *classifies* a column (e.g. "this object column
    looks like dates") — it doesn't change the underlying values. A column
    inferred as DATETIME still holds plain strings like "2024-01-01" until
    we explicitly parse them. Inserting a raw string into a SQLAlchemy
    DateTime column fails, because the DBAPI driver expects a real
    datetime object to bind. Same idea for INTEGER columns that pandas
    stored as float64 (see type_inference's nullable-integer handling).
    """
    df = df.copy()

    for col_name, column_type in column_types.items():
        if column_type == ColumnType.DATETIME:
            df[col_name] = pd.to_datetime(df[col_name], errors="coerce", format="mixed")
        elif column_type == ColumnType.INTEGER:
            # Nullable-integer columns are float64 in pandas (NaN forces
            # float). Round + cast to Python int for non-null values so
            # we bind real ints, not floats, to an INTEGER column.
            df[col_name] = df[col_name].apply(
                lambda v: int(round(v)) if pd.notna(v) else None
            )

    return df


def _dataframe_to_rows(df: pd.DataFrame) -> list[dict]:
    """
    Convert DataFrame to a list of plain dicts suitable for SQLAlchemy
    Core `insert()`, with pandas NaN/NaT converted to None (Postgres NULL).
    pandas' own `where(pd.notna(df), None)` is the cleanest way to do
    this without per-cell Python loops.
    """
    clean_df = df.where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def _insert_rows_with_savepoints(
    engine: Engine, table: Table, rows: list[dict]
) -> tuple[int, list[dict]]:
    """
    Insert rows in chunks, using a SAVEPOINT per chunk. If a chunk fails,
    roll back just that chunk and retry its rows one at a time so we can
    identify exactly which rows failed and why, without losing rows that
    inserted successfully elsewhere.

    Returns (inserted_count, failed_rows).
    """
    inserted_count = 0
    failed_rows: list[dict] = []

    with engine.begin() as conn:  # outer transaction; commits at the end
        for chunk_start in range(0, len(rows), _INSERT_CHUNK_SIZE):
            chunk = rows[chunk_start : chunk_start + _INSERT_CHUNK_SIZE]

            savepoint = conn.begin_nested()
            try:
                conn.execute(insert(table), chunk)
                savepoint.commit()
                inserted_count += len(chunk)
            except Exception:
                savepoint.rollback()
                # Fall back to row-by-row so a single bad row doesn't
                # sacrifice the rest of a perfectly good chunk.
                for offset, row in enumerate(chunk):
                    row_savepoint = conn.begin_nested()
                    try:
                        conn.execute(insert(table), [row])
                        row_savepoint.commit()
                        inserted_count += 1
                    except Exception as row_error:
                        row_savepoint.rollback()
                        failed_rows.append(
                            {
                                "row_index": chunk_start + offset,
                                "error": str(row_error),
                            }
                        )

    return inserted_count, failed_rows


def ingest_file(db: Session, engine: Engine, file_bytes: bytes, filename: str) -> IngestionResult:
    """
    Full ingestion pipeline: parse file -> sanitize schema -> create
    Dataset row -> create dynamic table -> insert rows -> record
    per-column metadata -> finalize Dataset status.
    """
    df = _read_file_to_dataframe(file_bytes, filename)

    # Sanitize + dedupe column names up front so both the dynamic table
    # and the DataFrame agree on the same safe names.
    original_columns = list(df.columns)
    safe_columns = dedupe_identifiers([str(c) for c in original_columns])
    df.columns = safe_columns

    # Create the Dataset row first so we get a real id to build the
    # table name from (dataset_<id>_<slug>), guaranteeing uniqueness
    # even across identically-named uploads.
    dataset = Dataset(
        name=filename.rsplit(".", 1)[0],
        original_filename=filename,
        table_name="pending",  # placeholder, set below once we have an id
        status=DatasetStatus.PENDING,
    )
    db.add(dataset)
    db.flush()  # assigns dataset.id without committing yet

    table_name = build_table_name(dataset.id, filename)
    dataset.table_name = table_name

    # Compute each column's type ONCE and reuse it everywhere below —
    # for the dynamic table's DDL, for coercing values to match that
    # DDL, and for the DatasetColumn metadata rows. Re-inferring per
    # step risks the classification silently disagreeing with itself.
    column_types: dict[str, ColumnType] = {
        col_name: infer_column_type(df[col_name]) for col_name in safe_columns
    }

    df = _coerce_column_values(df, column_types)

    metadata = MetaData()
    table = _build_dynamic_table(metadata, table_name, column_types)
    metadata.create_all(bind=engine, tables=[table])

    rows = _dataframe_to_rows(df)
    inserted_count, failed_rows = _insert_rows_with_savepoints(engine, table, rows)

    # Record per-column metadata using the SAME column_types computed
    # above (not re-inferred) for consistency with what was actually
    # created and inserted.
    for col_name in safe_columns:
        series = df[col_name]
        db.add(
            DatasetColumn(
                dataset_id=dataset.id,
                name=col_name,
                inferred_type=column_types[col_name].value,
                null_count=int(series.isna().sum()),
                unique_count=int(series.nunique(dropna=True)),
            )
        )

    dataset.row_count = inserted_count
    dataset.status = DatasetStatus.INGESTED if inserted_count > 0 else DatasetStatus.FAILED

    db.commit()
    db.refresh(dataset)

    return IngestionResult(dataset=dataset, inserted_count=inserted_count, failed_rows=failed_rows)
