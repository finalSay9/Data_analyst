import pandas as pd
import pytest

from app.analytics.distributions import (
    ColumnNotFoundError,
    InvalidDistributionError,
    compute_distribution,
)
from app.services.ingestion_service import ingest_file


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestBasicDistribution:
    def test_histogram_bins_sum_to_total_count(self, db_session, engine):
        df = pd.DataFrame({"value": list(range(100))})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "range.csv")

        result = compute_distribution(engine, result_ingest.dataset, "value")

        assert sum(b.count for b in result.bins) == 100
        assert result.total_count == 100

    def test_min_max_mean_reported(self, db_session, engine):
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "simple.csv")

        result = compute_distribution(engine, result_ingest.dataset, "value")

        assert result.min_value == 1
        assert result.max_value == 5
        assert result.mean == 3.0

    def test_custom_bin_count_respected(self, db_session, engine):
        df = pd.DataFrame({"value": list(range(50))})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "custom_bins.csv")

        result = compute_distribution(engine, result_ingest.dataset, "value", bins=10)

        assert len(result.bins) == 10

    def test_bin_count_capped_at_max(self, db_session, engine):
        df = pd.DataFrame({"value": list(range(50))})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "excessive_bins.csv")

        result = compute_distribution(engine, result_ingest.dataset, "value", bins=500)

        assert len(result.bins) == 50  # capped


class TestNullHandling:
    def test_nulls_excluded_from_histogram(self, db_session, engine):
        df = pd.DataFrame({"value": [1, 2, None, 3, None, 4]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "with_nulls.csv")

        result = compute_distribution(engine, result_ingest.dataset, "value")

        assert result.total_count == 4  # nulls excluded


class TestValidation:
    def test_unknown_column_raises(self, db_session, engine):
        df = pd.DataFrame({"value": [1, 2, 3]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate1.csv")

        with pytest.raises(ColumnNotFoundError):
            compute_distribution(engine, result_ingest.dataset, "nonexistent")

    def test_string_column_raises(self, db_session, engine):
        df = pd.DataFrame({"label": ["a", "b", "c"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate2.csv")

        with pytest.raises(InvalidDistributionError):
            compute_distribution(engine, result_ingest.dataset, "label")
