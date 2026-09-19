import pandas as pd

from app.analytics.profiling import profile_dataset
from app.services.ingestion_service import ingest_file


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestNumericProfiling:
    def test_integer_column_stats(self, db_session, engine):
        df = pd.DataFrame({"score": [10, 20, 30, 40, 50]})
        result = ingest_file(db_session, engine, csv_bytes(df), "scores.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["score"]

        assert p.min_value == 10
        assert p.max_value == 50
        assert p.mean == 30.0
        assert p.median == 30.0
        assert p.std_dev > 0

    def test_float_column_stats(self, db_session, engine):
        df = pd.DataFrame({"price": [1.5, 2.5, 3.5]})
        result = ingest_file(db_session, engine, csv_bytes(df), "prices.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["price"]

        assert p.min_value == 1.5
        assert p.max_value == 3.5
        assert p.mean == 2.5

    def test_single_value_std_dev_is_zero_not_nan(self, db_session, engine):
        df = pd.DataFrame({"lonely": [1.0, None, None]})
        result = ingest_file(db_session, engine, csv_bytes(df), "lonely.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["lonely"]

        assert p.std_dev == 0.0  # not NaN, not None


class TestBooleanProfiling:
    def test_true_false_counts(self, db_session, engine):
        df = pd.DataFrame({"active": [True, True, False, True, False]})
        result = ingest_file(db_session, engine, csv_bytes(df), "active.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["active"]

        assert p.true_count == 3
        assert p.false_count == 2


class TestDatetimeProfiling:
    def test_min_max_dates(self, db_session, engine):
        df = pd.DataFrame(
            {"signup": ["2024-01-01", "2024-06-15", "2024-03-10"]}
        )
        result = ingest_file(db_session, engine, csv_bytes(df), "signups.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["signup"]

        assert p.min_date is not None
        assert p.max_date is not None
        assert p.min_date < p.max_date


class TestStringProfiling:
    def test_top_values_computed(self, db_session, engine):
        df = pd.DataFrame(
            {"category": ["a", "a", "a", "b", "b", "c"]}
        )
        result = ingest_file(db_session, engine, csv_bytes(df), "cats.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["category"]

        assert p.top_values[0]["value"] == "a"
        assert p.top_values[0]["count"] == 3

    def test_top_values_limited_to_five(self, db_session, engine):
        df = pd.DataFrame({"label": [f"val_{i}" for i in range(10)]})
        result = ingest_file(db_session, engine, csv_bytes(df), "labels.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["label"]

        assert len(p.top_values) <= 5


class TestNullHandling:
    def test_null_count_and_percentage(self, db_session, engine):
        df = pd.DataFrame({"maybe": ["a", None, "b", None]})
        result = ingest_file(db_session, engine, csv_bytes(df), "maybe.csv")

        profiles = {p.name: p for p in profile_dataset(engine, result.dataset)}
        p = profiles["maybe"]

        assert p.null_count == 2
        assert p.null_percentage == 50.0

    def test_all_columns_present_in_profile(self, db_session, engine):
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "c": [True, False]})
        result = ingest_file(db_session, engine, csv_bytes(df), "multi.csv")

        profiles = profile_dataset(engine, result.dataset)
        names = {p.name for p in profiles}

        assert names == {"a", "b", "c"}
