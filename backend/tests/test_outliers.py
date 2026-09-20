import pandas as pd

from app.analytics.outliers import detect_outliers
from app.services.ingestion_service import ingest_file


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


class TestBasicOutlierDetection:
    def test_obvious_outlier_detected(self, db_session, engine):
        # 1000 is wildly outside the range of the rest of the data.
        df = pd.DataFrame({"value": [10, 12, 11, 13, 12, 11, 1000]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "outlier.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.outlier_count == 1
        assert col.sample_outliers[0].value == 1000

    def test_no_outliers_in_tight_uniform_data(self, db_session, engine):
        df = pd.DataFrame({"value": [10, 11, 12, 11, 10, 12, 11]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "uniform.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.outlier_count == 0
        assert col.sample_outliers == []

    def test_bounds_computed_correctly(self, db_session, engine):
        # Known values -> known quartiles, so bounds are checkable exactly.
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "known.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.q1 == 3.25
        assert col.q3 == 7.75
        assert col.iqr == 4.5


class TestSampleOutliersSortedByDistance:
    def test_worst_offender_listed_first(self, db_session, engine):
        # A large enough "normal" cluster that two extreme values don't
        # meaningfully distort Q1/Q3 themselves -- with too few points,
        # the outliers pull the quartiles along with them and can mask
        # each other (a real, documented property of IQR on small
        # samples, not a bug -- see test_sample_capped_at_ten below for
        # the more dramatic version of this).
        normal = [10, 11, 12, 11, 10, 12, 11, 10, 12, 11] * 3
        df = pd.DataFrame({"value": normal + [500, 900]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "ranked.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.outlier_count == 2
        assert col.sample_outliers[0].value == 900  # further from bound than 500
        assert (
            col.sample_outliers[0].distance_from_bound
            >= col.sample_outliers[1].distance_from_bound
        )

    def test_sample_capped_at_ten(self, db_session, engine):
        # Outliers need to stay a small minority of the data for the IQR
        # method to isolate them meaningfully -- a large normal cluster
        # with a much smaller set of extreme values, not a near-even
        # split (see test_worst_offender_listed_first's comment).
        normal = [10] * 100
        extreme = [1000 + i for i in range(15)]
        df = pd.DataFrame({"value": normal + extreme})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "many_outliers.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.outlier_count == 15  # all counted...
        assert len(col.sample_outliers) == 10  # ...but sample is capped


class TestZeroIQREdgeCase:
    def test_mostly_constant_column_flags_differing_values(self, db_session, engine):
        # At least 50% identical values -> Q1 == Q3 -> IQR == 0 -> bounds
        # collapse to that single value -> any different value is
        # technically "outside bounds." Documented, deliberate behavior.
        df = pd.DataFrame({"value": [5, 5, 5, 5, 5, 5, 7]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "constant.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        assert col.iqr == 0
        assert col.outlier_count == 1
        assert col.sample_outliers[0].value == 7


class TestMultipleColumnsAndNonNumeric:
    def test_only_numeric_columns_included(self, db_session, engine):
        df = pd.DataFrame(
            {"score": [1, 2, 3, 100], "label": ["a", "b", "c", "d"]}
        )
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "mixed.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        column_names = {c.column for c in result.columns}

        assert column_names == {"score"}

    def test_no_numeric_columns_returns_empty(self, db_session, engine):
        df = pd.DataFrame({"label": ["a", "b", "c"]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "no_numeric.csv")

        result = detect_outliers(engine, result_ingest.dataset)

        assert result.columns == []

    def test_row_ids_reference_real_rows(self, db_session, engine):
        df = pd.DataFrame({"value": [10, 11, 12, 999]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "traceable.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        # row_id should be a real, positive primary key from the dynamic table
        assert col.sample_outliers[0].row_id > 0


class TestNullHandling:
    def test_nulls_excluded_from_quartile_calculation(self, db_session, engine):
        df = pd.DataFrame({"value": [10, 11, None, 12, 11, None, 1000]})
        result_ingest = ingest_file(db_session, engine, csv_bytes(df), "with_nulls.csv")

        result = detect_outliers(engine, result_ingest.dataset)
        col = next(c for c in result.columns if c.column == "value")

        # Should still correctly detect the one real outlier despite nulls.
        assert col.outlier_count == 1
