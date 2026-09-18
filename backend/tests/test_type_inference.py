"""
Tests for column type inference.

Each test targets one specific decision made in type_inference.py — the
goal is that if any of these fail, you know exactly which judgment call
broke, not just "something's wrong with types."
"""

import pandas as pd
import pytest

from app.services.type_inference import ColumnType, infer_column_type


class TestBasicDtypes:
    def test_clean_integers(self):
        s = pd.Series([1, 2, 3, 4, 5])
        assert infer_column_type(s) == ColumnType.INTEGER

    def test_clean_floats(self):
        s = pd.Series([1.5, 2.7, 3.14, 4.0])
        assert infer_column_type(s) == ColumnType.FLOAT

    def test_booleans(self):
        s = pd.Series([True, False, True, True])
        assert infer_column_type(s) == ColumnType.BOOLEAN

    def test_plain_strings(self):
        s = pd.Series(["apple", "banana", "cherry"])
        assert infer_column_type(s) == ColumnType.STRING

    def test_pandas_native_datetime_dtype(self):
        s = pd.to_datetime(pd.Series(["2024-01-01", "2024-02-15", "2024-03-30"]))
        assert infer_column_type(s) == ColumnType.DATETIME


class TestNullableIntegerDetection:
    """
    The core edge case: pandas reads integer columns with missing values
    as float64 because NaN forces the whole column to float. We need to
    detect "this float column is actually whole numbers" and classify it
    as INTEGER, not FLOAT.
    """

    def test_integers_with_nulls_detected_as_integer(self):
        s = pd.Series([1.0, 2.0, None, 4.0, 5.0])  # pandas dtype: float64
        assert s.dtype == "float64"  # sanity check on the premise
        assert infer_column_type(s) == ColumnType.INTEGER

    def test_true_decimals_with_nulls_stay_float(self):
        s = pd.Series([1.5, 2.7, None, 4.2, 5.9])
        assert infer_column_type(s) == ColumnType.FLOAT

    def test_all_null_float_column_defaults_to_float(self):
        # Can't infer "whole number" from an entirely empty column —
        # falling back to FLOAT is the safe default, not a guess.
        s = pd.Series([None, None, None], dtype="float64")
        assert infer_column_type(s) == ColumnType.FLOAT

    def test_single_non_null_whole_number_with_nulls(self):
        s = pd.Series([7.0, None, None, None])
        assert infer_column_type(s) == ColumnType.INTEGER


class TestDatetimeDetectionFromStrings:
    """
    pandas never auto-detects dates in object columns — a column of
    "2024-01-15" strings is just `object` unless we explicitly try to
    parse it. This is the second major judgment call in the module.
    """

    def test_iso_date_strings_detected_as_datetime(self):
        s = pd.Series(["2024-01-01", "2024-02-15", "2024-03-30", "2024-04-10"])
        # NOTE: pandas' default string dtype changed across versions —
        # pre-3.0 this is "object", 3.0+ it's a dedicated StringDtype.
        # We deliberately don't assert a specific dtype here; the module
        # under test handles both (see is_object_dtype/is_string_dtype).
        assert infer_column_type(s) == ColumnType.DATETIME

    def test_us_format_date_strings_detected_as_datetime(self):
        s = pd.Series(["01/15/2024", "02/20/2024", "03/25/2024"])
        assert infer_column_type(s) == ColumnType.DATETIME

    def test_mostly_dates_with_few_bad_rows_still_datetime(self):
        # High parse success rate (>= 90%) should still count as datetime
        # even with a couple of malformed entries.
        dates = [f"2024-{m:02d}-01" for m in range(1, 10)]  # 9 good dates
        s = pd.Series(dates + ["not-a-date"])  # 1 bad -> 90% success
        assert infer_column_type(s) == ColumnType.DATETIME

    def test_mixed_garbage_not_detected_as_datetime(self):
        s = pd.Series(["hello", "world", "2024-01-01", "foo", "bar"])
        assert infer_column_type(s) == ColumnType.STRING

    def test_numeric_looking_strings_not_datetime(self):
        # Regression guard: short numeric-like strings shouldn't be
        # misparsed as dates by an overly permissive parser.
        s = pd.Series(["123", "456", "789"])
        assert infer_column_type(s) == ColumnType.STRING


class TestEdgeCases:
    def test_empty_series_defaults_to_string(self):
        s = pd.Series([], dtype="object")
        assert infer_column_type(s) == ColumnType.STRING

    def test_all_null_object_column_defaults_to_string(self):
        s = pd.Series([None, None, None], dtype="object")
        assert infer_column_type(s) == ColumnType.STRING

    def test_mixed_type_object_column_falls_back_to_string(self):
        s = pd.Series(["text", 42, True, None])
        assert infer_column_type(s) == ColumnType.STRING

    def test_single_row_integer_column(self):
        s = pd.Series([42])
        assert infer_column_type(s) == ColumnType.INTEGER

    def test_negative_integers(self):
        s = pd.Series([-5, -3, 0, 3, 5])
        assert infer_column_type(s) == ColumnType.INTEGER

    def test_large_integers_stay_integer(self):
        s = pd.Series([1_000_000, 2_000_000, 3_000_000])
        assert infer_column_type(s) == ColumnType.INTEGER


@pytest.mark.parametrize(
    "values,expected",
    [
        ([1, 2, 3], ColumnType.INTEGER),
        ([1.1, 2.2, 3.3], ColumnType.FLOAT),
        ([True, False], ColumnType.BOOLEAN),
        (["a", "b", "c"], ColumnType.STRING),
    ],
)
def test_parametrized_basic_cases(values, expected):
    assert infer_column_type(pd.Series(values)) == expected
