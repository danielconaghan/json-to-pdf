import pytest

from pdfgen.accessibility import (
    _StructTracker,
    _group_section_items,
    begin_artifact,
    end_artifact,
    next_mcid,
    setup_document,
)


# ── _StructTracker ────────────────────────────────────────────────────────────

class TestStructTracker:
    def test_initial_state(self):
        t = _StructTracker()
        assert t.pages == [[]]
        assert t.ordered == []

    def test_reset_clears_state(self):
        t = _StructTracker()
        t.record(0, "H1")
        t.new_page()
        t.reset()
        assert t.pages == [[]]
        assert t.ordered == []

    def test_record_stores_to_current_page_and_ordered(self):
        t = _StructTracker()
        t.record(0, "H1", "alt text")
        assert len(t.pages[0]) == 1
        assert len(t.ordered) == 1

    def test_record_page_idx_matches_current_page(self):
        t = _StructTracker()
        t.new_page()
        t.record(5, "P")
        assert t.ordered[0]["page_idx"] == 1

    def test_record_includes_all_fields(self):
        t = _StructTracker()
        t.record(3, "TH", "header", table_id=7, row_no=0, col_no=2)
        rec = t.ordered[0]
        assert rec["mcid"] == 3
        assert rec["role"] == "TH"
        assert rec["alt"] == "header"
        assert rec["table_id"] == 7
        assert rec["row_no"] == 0
        assert rec["col_no"] == 2

    def test_record_defaults_for_optional_fields(self):
        t = _StructTracker()
        t.record(0, "P")
        rec = t.ordered[0]
        assert rec["alt"] == ""
        assert rec["table_id"] is None
        assert rec["row_no"] is None
        assert rec["col_no"] is None

    def test_new_page_appends_empty_list(self):
        t = _StructTracker()
        t.new_page()
        assert len(t.pages) == 2
        assert t.pages[1] == []

    def test_records_on_separate_pages_land_in_correct_buckets(self):
        t = _StructTracker()
        t.record(0, "H1")
        t.new_page()
        t.record(1, "P")
        assert len(t.pages[0]) == 1
        assert len(t.pages[1]) == 1
        assert t.ordered[0]["page_idx"] == 0
        assert t.ordered[1]["page_idx"] == 1

    def test_ordered_preserves_insertion_order(self):
        t = _StructTracker()
        for i, role in enumerate(["H1", "P", "Figure"]):
            t.record(i, role)
        assert [r["role"] for r in t.ordered] == ["H1", "P", "Figure"]


# ── _group_section_items ──────────────────────────────────────────────────────

def _rec(role, mcid=0, table_id=None, row_no=None, col_no=None):
    return {"role": role, "mcid": mcid, "page_idx": 0,
            "table_id": table_id, "row_no": row_no, "col_no": col_no}


class TestGroupSectionItems:
    def test_empty_list(self):
        assert _group_section_items([]) == []

    def test_plain_records_returned_individually(self):
        records = [_rec("H1"), _rec("P"), _rec("Figure")]
        result = _group_section_items(records)
        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)

    def test_table_records_grouped_into_list(self):
        records = [
            _rec("TH", table_id=0, row_no=0, col_no=0),
            _rec("TD", table_id=0, row_no=1, col_no=0),
        ]
        result = _group_section_items(records)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2

    def test_mixed_plain_and_table(self):
        records = [
            _rec("H1"),
            _rec("TH", table_id=1, row_no=0, col_no=0),
            _rec("TD", table_id=1, row_no=1, col_no=0),
            _rec("P"),
        ]
        result = _group_section_items(records)
        assert len(result) == 3
        assert isinstance(result[0], dict)   # H1
        assert isinstance(result[1], list)   # table
        assert isinstance(result[2], dict)   # P

    def test_two_consecutive_tables_produce_two_groups(self):
        records = [
            _rec("TH", table_id=0, row_no=0, col_no=0),
            _rec("TH", table_id=1, row_no=0, col_no=0),
        ]
        result = _group_section_items(records)
        assert len(result) == 2
        assert all(isinstance(r, list) for r in result)

    def test_table_at_end_of_section_is_included(self):
        records = [
            _rec("H1"),
            _rec("TD", table_id=2, row_no=0, col_no=0),
        ]
        result = _group_section_items(records)
        assert isinstance(result[-1], list)


# ── Canvas-level helpers ──────────────────────────────────────────────────────

class TestNextMcid:
    def test_starts_at_zero(self, mock_canvas):
        assert next_mcid(mock_canvas) == 0

    def test_increments_on_each_call(self, mock_canvas):
        assert next_mcid(mock_canvas) == 0
        assert next_mcid(mock_canvas) == 1
        assert next_mcid(mock_canvas) == 2

    def test_works_without_pre_initialised_counter(self, mock_canvas):
        del mock_canvas._mcid_counter
        assert next_mcid(mock_canvas) == 0


class TestArtifactHelpers:
    def test_begin_artifact_default_type(self, mock_canvas):
        begin_artifact(mock_canvas)
        assert mock_canvas._literals == ["/Artifact <</Type /Layout>> BDC"]

    def test_begin_artifact_custom_type(self, mock_canvas):
        begin_artifact(mock_canvas, "Pagination")
        assert "/Pagination" in mock_canvas._literals[0]

    def test_end_artifact_emits_emc(self, mock_canvas):
        end_artifact(mock_canvas)
        assert mock_canvas._literals == ["EMC"]

    def test_artifact_pair_balanced(self, mock_canvas):
        begin_artifact(mock_canvas, "Layout")
        end_artifact(mock_canvas)
        assert mock_canvas._literals[0].endswith("BDC")
        assert mock_canvas._literals[1] == "EMC"


# ── setup_document ────────────────────────────────────────────────────────────

class TestSetupDocument:
    def _config(self, lang="en-GB"):
        return {"document": {"lang": lang}}

    def test_sets_mark_info(self, mock_canvas):
        setup_document(mock_canvas, self._config())
        assert hasattr(mock_canvas._doc.Catalog, "MarkInfo")

    def test_sets_lang(self, mock_canvas):
        setup_document(mock_canvas, self._config("fr-FR"))
        lang = mock_canvas._doc.Catalog.Lang
        assert "fr-FR" in str(lang)

    def test_sets_viewer_preferences(self, mock_canvas):
        setup_document(mock_canvas, self._config())
        assert hasattr(mock_canvas._doc.Catalog, "ViewerPreferences")

    def test_empty_lang_skips_lang_entry(self, mock_canvas):
        setup_document(mock_canvas, self._config(lang=""))
        assert not hasattr(mock_canvas._doc.Catalog, "Lang")
