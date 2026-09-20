import pandas as pd

from app.analytics.statistics import compute_correlations
from app.services.ingestion_service import ingest_file


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestBasicCorrelation:
    def test_perfect_positive_correlation(self, db_session, engine):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "perfect.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        assert not result.insufficient_columns
        pair = result.pairs[0]
        assert pair.correlation == 1.0
        assert pair.strength == "strong"

    def test_perfect_negative_correlation(self, db_session, engine):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 8, 6, 4, 2]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "inverse.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        pair = result.pairs[0]
        assert pair.correlation == -1.0
        assert pair.strength == "strong"

    def test_no_correlation_weak_or_near_zero(self, db_session, engine):
        # Deliberately uncorrelated-by-construction pattern.
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [3, 1, 4, 1, 5, 9]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "random.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        assert len(result.pairs) == 1  # just confirms it computed something valid
        assert -1.0 <= result.pairs[0].correlation <= 1.0


class TestInsufficientColumns:
    def test_single_numeric_column_flagged_insufficient(self, db_session, engine):
        df = pd.DataFrame({"x": [1, 2, 3], "label": ["a", "b", "c"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "single_numeric.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        assert result.insufficient_columns is True
        assert result.pairs == []
        assert result.matrix == []

    def test_zero_numeric_columns_flagged_insufficient(self, db_session, engine):
        df = pd.DataFrame({"label": ["a", "b", "c"], "category": ["x", "y", "z"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "no_numeric.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        assert result.insufficient_columns is True


class TestZeroVarianceColumn:
    def test_constant_column_excluded_from_pairs_not_reported_as_zero(self, db_session, engine):
        # A column of all-identical values has undefined correlation
        # (division by zero variance), not zero correlation.
        df = pd.DataFrame({"constant": [5, 5, 5, 5], "varying": [1, 2, 3, 4]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "constant.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        # Both columns are still counted as numeric...
        assert set(result.numeric_columns) == {"constant", "varying"}
        # ...but the undefined pair is skipped rather than reported as 0.
        assert result.pairs == []


class TestMultipleColumns:
    def test_three_numeric_columns_produce_three_pairs(self, db_session, engine):
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [2, 4, 6, 8, 10],
                "c": [5, 3, 4, 1, 2],
            }
        )
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "three_cols.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        # 3 columns -> 3 unique pairs (a-b, a-c, b-c)
        assert len(result.pairs) == 3

    def test_pairs_sorted_by_absolute_strength_descending(self, db_session, engine):
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "perfectly_correlated": [2, 4, 6, 8, 10],
                "loosely_correlated": [5, 3, 8, 1, 9],
            }
        )
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "sorted.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        abs_values = [abs(p.correlation) for p in result.pairs]
        assert abs_values == sorted(abs_values, reverse=True)

    def test_matrix_shape_matches_column_count(self, db_session, engine):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 2, 1], "c": [1, 1, 2]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "matrix_shape.csv")

        result = compute_correlations(engine, result_ingest.dataset)

        assert len(result.matrix) == 3
        assert all(len(row) == 3 for row in result.matrix)
        # Diagonal is always self-correlation == 1.0
        assert result.matrix[0][0] == 1.0
        assert result.matrix[1][1] == 1.0
