from app.utils.naming import build_table_name, dedupe_identifiers, sanitize_identifier


class TestSanitizeIdentifier:
    def test_spaces_become_underscores(self):
        assert sanitize_identifier("Total Sales") == "total_sales"

    def test_special_characters_stripped(self):
        assert sanitize_identifier("Total $") == "total"
        assert sanitize_identifier("Total #") == "total"

    def test_leading_digit_gets_prefixed(self):
        result = sanitize_identifier("2024_revenue")
        assert not result[0].isdigit()
        assert "2024_revenue" in result

    def test_repeated_special_chars_collapse_to_one_underscore(self):
        assert sanitize_identifier("a!!!b") == "a_b"

    def test_leading_trailing_underscores_stripped(self):
        assert sanitize_identifier("__hello__") == "hello"

    def test_empty_string_uses_fallback(self):
        assert sanitize_identifier("", fallback="col_0") == "col_0"

    def test_all_special_chars_uses_fallback(self):
        assert sanitize_identifier("$$$", fallback="col_0") == "col_0"

    def test_long_name_truncated_to_63_chars(self):
        result = sanitize_identifier("a" * 100)
        assert len(result) <= 63

    def test_uppercase_lowercased(self):
        assert sanitize_identifier("CustomerID") == "customerid"


class TestDedupeIdentifiers:
    def test_no_collisions_unchanged(self):
        result = dedupe_identifiers(["name", "age", "city"])
        assert result == ["name", "age", "city"]

    def test_colliding_names_get_numeric_suffix(self):
        result = dedupe_identifiers(["Total $", "Total #"])
        assert result == ["total", "total_2"]
        assert len(result) == len(set(result))  # all unique

    def test_three_way_collision(self):
        result = dedupe_identifiers(["Total $", "Total #", "Total %"])
        assert result == ["total", "total_2", "total_3"]

    def test_preserves_order_and_count(self):
        raw = ["b", "a", "b", "c"]
        result = dedupe_identifiers(raw)
        assert len(result) == len(raw)
        assert result[1] == "a"  # position preserved

    def test_empty_headers_get_unique_fallbacks(self):
        result = dedupe_identifiers(["", "", ""])
        assert len(result) == len(set(result))  # all unique despite empty input


class TestBuildTableName:
    def test_includes_dataset_id(self):
        name = build_table_name(7, "sales_data.csv")
        assert name.startswith("dataset_7_")

    def test_different_ids_produce_different_names_same_filename(self):
        a = build_table_name(1, "data.csv")
        b = build_table_name(2, "data.csv")
        assert a != b

    def test_result_is_valid_length(self):
        name = build_table_name(999, "a" * 100)
        assert len(name) <= 63

    def test_messy_filename_sanitized(self):
        name = build_table_name(3, "Q3 Sales Report (Final)!!.csv")
        assert " " not in name
        assert "(" not in name
