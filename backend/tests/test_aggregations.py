import pandas as pd
import pytest

from app.analytics.aggregations import (
    AggregationFunction,
    ColumnNotFoundError,
    InvalidAggregationError,
    compute_aggregation,
)
from app.services.ingestion_service import ingest_file


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestBasicAggregation:
    def test_sum_by_category(self, db_session, engine):
        df = pd.DataFrame(
            {
                "category": ["a", "a", "b", "b", "b"],
                "price": [10, 20, 5, 5, 5],
            }
        )
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "sales.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.SUM, "price"
        )

        groups = {g.group_value: g.value for g in result.groups}
        assert groups["a"] == 30
        assert groups["b"] == 15

    def test_mean_by_category(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "a", "b"], "score": [10, 20, 100]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "scores.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.MEAN, "score"
        )
        groups = {g.group_value: g.value for g in result.groups}

        assert groups["a"] == 15.0
        assert groups["b"] == 100.0

    def test_min_max_by_category(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "a", "a"], "value": [3, 1, 9]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "minmax.csv")

        min_result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.MIN, "value"
        )
        max_result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.MAX, "value"
        )

        assert min_result.groups[0].value == 1
        assert max_result.groups[0].value == 9

    def test_median_by_category(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "a", "a"], "value": [1, 2, 100]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "median.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.MEDIAN, "value"
        )

        assert result.groups[0].value == 2  # median of [1,2,100], not skewed by 100


class TestCountFunction:
    def test_count_without_agg_column(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "a", "b", "b", "b"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "counts.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.COUNT
        )
        groups = {g.group_value: g.row_count for g in result.groups}

        assert groups["a"] == 2
        assert groups["b"] == 3

    def test_count_ignores_agg_column_values_counts_rows(self, db_session, engine):
        # Even with nulls in an unrelated column, COUNT with no
        # agg_column should count full rows, not filter by that column.
        df = pd.DataFrame({"category": ["a", "a", "b"], "optional_field": [1, None, 5]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "count_nulls.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.COUNT
        )
        groups = {g.group_value: g.row_count for g in result.groups}

        assert groups["a"] == 2  # both rows counted despite the null


class TestNumericGroupBy:
    def test_group_by_numeric_column_allowed(self, db_session, engine):
        # Grouping by "rating" (an integer column) should work -- any
        # column type is a valid group-by target.
        df = pd.DataFrame({"rating": [5, 5, 3, 3, 3], "price": [10, 20, 5, 5, 5]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "ratings.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "rating", AggregationFunction.SUM, "price"
        )
        groups = {g.group_value: g.value for g in result.groups}

        assert groups["5"] == 30
        assert groups["3"] == 15


class TestNullGrouping:
    def test_null_group_values_become_explicit_missing_label(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", None, "a", None], "value": [1, 2, 3, 4]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "nulls_group.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.SUM, "value"
        )
        group_labels = {g.group_value for g in result.groups}

        assert "(missing)" in group_labels
        missing_group = next(g for g in result.groups if g.group_value == "(missing)")
        assert missing_group.value == 6  # 2 + 4


class TestValidation:
    def test_unknown_group_by_column_raises(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "b"], "value": [1, 2]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate1.csv")

        with pytest.raises(ColumnNotFoundError):
            compute_aggregation(
                engine, result_ingest.dataset, "nonexistent", AggregationFunction.SUM, "value"
            )

    def test_unknown_agg_column_raises(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "b"], "value": [1, 2]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate2.csv")

        with pytest.raises(ColumnNotFoundError):
            compute_aggregation(
                engine, result_ingest.dataset, "category", AggregationFunction.SUM, "nonexistent"
            )

    def test_sum_on_string_column_raises(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "b"], "label": ["x", "y"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate3.csv")

        with pytest.raises(InvalidAggregationError):
            compute_aggregation(
                engine, result_ingest.dataset, "category", AggregationFunction.SUM, "label"
            )

    def test_mean_without_agg_column_raises(self, db_session, engine):
        df = pd.DataFrame({"category": ["a", "b"], "value": [1, 2]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "validate4.csv")

        with pytest.raises(InvalidAggregationError):
            compute_aggregation(engine, result_ingest.dataset, "category", AggregationFunction.MEAN)


class TestTooManyGroups:
    def test_high_cardinality_group_by_flagged(self, db_session, engine):
        # 150 distinct values -- above the 100-group cap.
        df = pd.DataFrame({"id_like": [f"user_{i}" for i in range(150)], "value": range(150)})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "high_cardinality.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "id_like", AggregationFunction.SUM, "value"
        )

        assert result.too_many_groups is True
        assert result.total_groups == 150
        assert result.groups == []


class TestSorting:
    def test_groups_sorted_by_value_descending(self, db_session, engine):
        df = pd.DataFrame(
            {"category": ["a", "b", "c"], "value": [10, 100, 50]}
        )
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "sort_test.csv")

        result = compute_aggregation(
            engine, result_ingest.dataset, "category", AggregationFunction.SUM, "value"
        )
        values = [g.value for g in result.groups]

        assert values == sorted(values, reverse=True)
