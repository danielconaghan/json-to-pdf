"""Integration tests: render a real PDF and verify its structure.

These tests call the full render pipeline and inspect the output file,
so they catch wiring problems that unit tests cannot see.
"""
import zlib

import pikepdf
import pytest

from pdfgen.merger import deep_merge, load_defaults
from pdfgen.renderer import render
from pdfgen.styles import resolve_styles


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_config(content):
    config = deep_merge(load_defaults(), {"content": content})
    config["_resolved_styles"] = resolve_styles(config["styles"])
    return config


def _read_page_stream(pdf, page_idx):
    """Return the decompressed content stream for a page."""
    contents = pdf.pages[page_idx].obj.get("/Contents")
    if contents is None:
        return b""
    raw = contents.read_bytes()
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return raw


def _count_in_stream(pdf, token: bytes) -> int:
    """Count occurrences of a byte token across all page streams."""
    return sum(
        _read_page_stream(pdf, i).count(token)
        for i in range(len(pdf.pages))
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def output_path(tmp_path):
    return str(tmp_path / "out.pdf")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestMinimalRender:
    def test_file_is_created(self, output_path):
        config = _make_config([])
        render(config, output_path)
        import os
        assert os.path.getsize(output_path) > 0

    def test_file_is_valid_pdf(self, output_path):
        config = _make_config([])
        render(config, output_path)
        # pikepdf.open raises on corrupt or non-PDF file
        with pikepdf.open(output_path):
            pass


class TestStructTree:
    def test_struct_tree_root_present(self, output_path):
        config = _make_config([{"type": "heading", "text": "Hello", "level": 1}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            assert hasattr(pdf.Root, "StructTreeRoot")

    def test_marked_content_in_catalog(self, output_path):
        config = _make_config([{"type": "paragraph", "text": "Test"}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            mark_info = pdf.Root.MarkInfo
            # ReportLab writes the string "true"; pikepdf may surface it as
            # a boolean True or the string "true" depending on version.
            assert str(mark_info.get("/Marked", "")).lower() == "true"

    def test_lang_set_in_catalog(self, output_path):
        config = _make_config([])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            assert hasattr(pdf.Root, "Lang")


class TestTaggedContent:
    def test_heading_produces_bdc_emc_pair(self, output_path):
        config = _make_config([{"type": "heading", "text": "Chapter One", "level": 1}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            bdc = _count_in_stream(pdf, b"BDC")
            emc = _count_in_stream(pdf, b"EMC")
            assert bdc > 0
            assert bdc == emc  # every BDC must have a matching EMC

    def test_paragraph_produces_bdc_emc_pair(self, output_path):
        config = _make_config([{"type": "paragraph", "text": "Body text."}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            assert _count_in_stream(pdf, b"BDC") == _count_in_stream(pdf, b"EMC")

    def test_table_produces_th_and_td_markers(self, output_path):
        config = _make_config([{
            "type": "table",
            "headers": ["Name", "Score"],
            "rows": [["Alice", "95"], ["Bob", "82"]],
        }])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            assert _count_in_stream(pdf, b"/TH ") > 0
            assert _count_in_stream(pdf, b"/TD ") > 0
            assert _count_in_stream(pdf, b"BDC") == _count_in_stream(pdf, b"EMC")

    def test_table_struct_tree_contains_table_tr_th_td(self, output_path):
        config = _make_config([{
            "type": "table",
            "headers": ["A", "B"],
            "rows": [["1", "2"]],
        }])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            roles = set()
            def collect_roles(elem):
                s = str(getattr(elem, "S", ""))
                if s:
                    roles.add(s.lstrip("/"))
                kids = getattr(elem, "K", None)
                if kids and hasattr(kids, "__iter__") and not isinstance(kids, pikepdf.String):
                    for k in kids:
                        try:
                            if hasattr(k, "S"):
                                collect_roles(k)
                        except Exception:
                            pass
            collect_roles(pdf.Root.StructTreeRoot)
            assert "Table" in roles
            assert "TR" in roles
            assert "TH" in roles
            assert "TD" in roles


class TestPageStructure:
    def test_struct_parents_set_on_each_page(self, output_path):
        config = _make_config([{"type": "paragraph", "text": "p"}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            for page in pdf.pages:
                assert "/StructParents" in page.obj

    def test_parent_tree_present_in_struct_root(self, output_path):
        config = _make_config([{"type": "paragraph", "text": "p"}])
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            root = pdf.Root.StructTreeRoot
            assert hasattr(root, "ParentTree")


class TestMultipleElements:
    def test_mixed_content_bdc_emc_balanced(self, output_path):
        content = [
            {"type": "heading", "text": "Title", "level": 1},
            {"type": "paragraph", "text": "Intro."},
            {"type": "rule"},
            {"type": "spacer", "height": 12},
            {"type": "table", "headers": ["X"], "rows": [["1"], ["2"]]},
            {"type": "paragraph", "text": "End."},
        ]
        config = _make_config(content)
        render(config, output_path)
        with pikepdf.open(output_path) as pdf:
            bdc = _count_in_stream(pdf, b"BDC")
            emc = _count_in_stream(pdf, b"EMC")
            assert bdc > 0
            assert bdc == emc
