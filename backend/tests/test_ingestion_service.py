import pandas as pd
import pytest
from sqlalchemy import text

from app.models.dataset import DatasetStatus
from app.services.ingestion_service import (
    UnsupportedFileTypeError,
    ingest_file,
)


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestHappyPath:
    def test_simple_csv_creates_dataset_and_table(self, db_session, engine):
        df = pd.DataFrame(
            {
                "Name": ["Alice", "Bob", "Carol"],
                "Age": [30, 25, 35],
                "Signup Date": ["2024-01-01", "2024-02-15", "2024-03-30"],
            }
        )

        result = ingest_file(db_session, engine, csv_bytes(df), "customers.csv")

        assert result.dataset.status == DatasetStatus.INGESTED
        assert result.inserted_count == 3
        assert result.failed_rows == []
        assert result.dataset.table_name.startswith("dataset_")

    def test_column_names_sanitized(self, db_session, engine):
        df = pd.DataFrame({"Total $": [1, 2], "Customer Name!!": ["a", "b"]})
        result = ingest_file(db_session, engine, csv_bytes(df), "weird_headers.csv")

        column_names = {c.name for c in result.dataset.columns}
        assert "total" in column_names
        assert "customer_name" in column_names

    def test_colliding_column_names_deduped(self, db_session, engine):
        # Two headers that sanitize to the same thing
        raw_csv = b"Total $,Total #\n1,2\n3,4\n"
        result = ingest_file(db_session, engine, raw_csv, "collide.csv")

        column_names = [c.name for c in result.dataset.columns]
        assert len(column_names) == len(set(column_names))  # all unique
        assert "total" in column_names
        assert "total_2" in column_names

    def test_rows_actually_queryable_in_dynamic_table(self, db_session, engine):
        df = pd.DataFrame({"value": [10, 20, 30]})
        result = ingest_file(db_session, engine, csv_bytes(df), "numbers.csv")

        with engine.connect() as conn:
            total = conn.execute(
                text(f"SELECT COUNT(*) FROM {result.dataset.table_name}")
            ).scalar()
        assert total == 3

    def test_column_metadata_recorded_with_correct_types(self, db_session, engine):
        df = pd.DataFrame(
            {
                "count": [1, 2, 3],
                "price": [1.5, 2.7, 3.9],
                "active": [True, False, True],
                "label": ["a", "b", "c"],
            }
        )
        result = ingest_file(db_session, engine, csv_bytes(df), "typed.csv")

        types_by_col = {c.name: c.inferred_type for c in result.dataset.columns}
        assert types_by_col["count"] == "integer"
        assert types_by_col["price"] == "float"
        assert types_by_col["active"] == "boolean"
        assert types_by_col["label"] == "string"

    def test_null_and_unique_counts_recorded(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "a", "b", None]})
        result = ingest_file(db_session, engine, csv_bytes(df), "cats.csv")

        col = next(c for c in result.dataset.columns if c.name == "category")
        assert col.null_count == 1
        assert col.unique_count == 2  # "a" and "b", null excluded


class TestUnsupportedFileType:
    def test_unsupported_extension_raises(self, db_session, engine):
        with pytest.raises(UnsupportedFileTypeError):
            ingest_file(db_session, engine, b"whatever", "data.txt")


class TestMultipleUploadsUniqueness:
    def test_same_filename_twice_gets_different_table_names(self, db_session, engine):
        df = pd.DataFrame({"x": [1, 2]})
        r1 = ingest_file(db_session, engine, csv_bytes(df), "data.csv")
        r2 = ingest_file(db_session, engine, csv_bytes(df), "data.csv")

        assert r1.dataset.table_name != r2.dataset.table_name


class TestPartialFailureSavepointRecovery:
    """
    Directly exercises _insert_rows_with_savepoints, the mechanism behind
    "insert what succeeded, report failed rows separately." We force some
    rows to violate a NOT NULL constraint and confirm: (1) good rows in
    the same chunk still get inserted, (2) bad rows are reported with
    their original index, not silently dropped or crashing the batch.
    """

    def test_bad_rows_isolated_good_rows_still_inserted(self, engine):
        from sqlalchemy import Column, Integer, MetaData, String, Table

        from app.services.ingestion_service import _insert_rows_with_savepoints

        metadata = MetaData()
        table = Table(
            "constrained_table",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("required_field", String, nullable=False),  # NOT NULL on purpose
        )
        metadata.create_all(engine)

        rows = [
            {"required_field": "ok-1"},
            {"required_field": None},  # violates NOT NULL -> should fail
            {"required_field": "ok-2"},
            {"required_field": None},  # violates NOT NULL -> should fail
            {"required_field": "ok-3"},
        ]

        inserted_count, failed_rows = _insert_rows_with_savepoints(engine, table, rows)

        assert inserted_count == 3
        assert len(failed_rows) == 2
        assert {f["row_index"] for f in failed_rows} == {1, 3}

        with engine.connect() as conn:
            remaining = conn.execute(
                text("SELECT required_field FROM constrained_table")
            ).fetchall()
        values = {row[0] for row in remaining}
        assert values == {"ok-1", "ok-2", "ok-3"}
