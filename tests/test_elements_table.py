import pytest

from pdfgen.accessibility import TaggedTable
from pdfgen.elements.table import (
    _resolve_col_aligns,
    _resolve_col_widths,
    build_table,
)


# ── _resolve_col_widths ───────────────────────────────────────────────────────

class TestResolveColWidths:
    def test_no_spec_equal_widths(self):
        result = _resolve_col_widths(None, 3, 300)
        assert result == [100.0, 100.0, 100.0]

    def test_percentage_spec(self):
        result = _resolve_col_widths(["50%", "50%"], 2, 200, full_width=False)
        assert result == [100.0, 100.0]

    def test_numeric_spec(self):
        result = _resolve_col_widths([80, 120], 2, 200, full_width=False)
        assert result == [80.0, 120.0]

    def test_partial_spec_fills_remaining_equally(self):
        result = _resolve_col_widths(["100"], 3, 300, full_width=False)
        assert len(result) == 3
        assert result[0] == 100.0
        assert result[1] == result[2]

    def test_full_width_scales_to_available(self):
        result = _resolve_col_widths([50, 50], 2, 300, full_width=True)
        assert abs(sum(result) - 300) < 1.0

    def test_full_width_false_no_scaling(self):
        result = _resolve_col_widths([50, 50], 2, 300, full_width=False)
        assert sum(result) == 100.0

    def test_extra_spec_entries_truncated(self):
        result = _resolve_col_widths([100, 200, 300], 2, 400, full_width=False)
        assert len(result) == 2

    def test_single_column(self):
        result = _resolve_col_widths(None, 1, 200)
        assert result == [200.0]


# ── _resolve_col_aligns ───────────────────────────────────────────────────────

class TestResolveColAligns:
    def test_no_spec_all_default(self):
        result = _resolve_col_aligns(None, 3, "left")
        assert result == ["left", "left", "left"]

    def test_partial_spec_padded_with_default(self):
        result = _resolve_col_aligns(["center"], 3, "left")
        assert result == ["center", "left", "left"]

    def test_full_spec_returned_as_given(self):
        spec = ["left", "center", "right"]
        result = _resolve_col_aligns(spec, 3, "left")
        assert result == spec

    def test_extra_spec_truncated(self):
        result = _resolve_col_aligns(["left", "right", "center"], 2, "left")
        assert len(result) == 2


# ── build_table ───────────────────────────────────────────────────────────────

class TestBuildTable:
    def test_empty_element_returns_empty_list(self, mock_ctx):
        result = build_table({}, mock_ctx)
        assert result == []

    def test_no_headers_no_rows_returns_empty_list(self, mock_ctx):
        result = build_table({"headers": [], "rows": []}, mock_ctx)
        assert result == []

    def test_returns_list_with_tagged_table(self, mock_ctx):
        element = {
            "headers": ["Name", "Value"],
            "rows": [["Alice", "1"], ["Bob", "2"]],
        }
        result = build_table(element, mock_ctx)
        assert len(result) == 1
        assert isinstance(result[0], TaggedTable)

    def test_has_header_set_true_when_headers_present(self, mock_ctx):
        element = {"headers": ["A", "B"], "rows": [["x", "y"]]}
        result = build_table(element, mock_ctx)
        assert result[0]._has_header is True

    def test_has_header_set_false_when_no_headers(self, mock_ctx):
        element = {"rows": [["x", "y"], ["a", "b"]]}
        result = build_table(element, mock_ctx)
        assert result[0]._has_header is False

    def test_each_table_gets_unique_tag_id(self, mock_ctx):
        element = {"headers": ["A"], "rows": [["x"]]}
        t1 = build_table(element, mock_ctx)[0]
        t2 = build_table(element, mock_ctx)[0]
        assert t1._table_tag_id != t2._table_tag_id

    def test_col_widths_sum_to_doc_width(self, mock_ctx):
        element = {"headers": ["A", "B", "C"], "rows": [["1", "2", "3"]]}
        table = build_table(element, mock_ctx)[0]
        assert abs(sum(table._colWidths) - mock_ctx.doc.width) < 1.0
