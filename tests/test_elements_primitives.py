import pytest
from reportlab.platypus import PageBreak, Spacer

from pdfgen.accessibility import ArtifactRule
from pdfgen.elements.primitives import build_page_break, build_rule, build_spacer


class TestBuildSpacer:
    def test_returns_list_with_one_spacer(self):
        result = build_spacer({"height": 20})
        assert len(result) == 1
        assert isinstance(result[0], Spacer)

    def test_custom_height(self):
        result = build_spacer({"height": 48})
        assert result[0].height == 48

    def test_default_height(self):
        result = build_spacer({})
        assert result[0].height == 12


class TestBuildPageBreak:
    def test_returns_list_with_page_break(self):
        result = build_page_break({})
        assert len(result) == 1
        assert isinstance(result[0], PageBreak)


class TestBuildRule:
    def test_returns_list_with_artifact_rule(self):
        result = build_rule({})
        assert len(result) == 1
        assert isinstance(result[0], ArtifactRule)

    def test_default_thickness(self):
        result = build_rule({})
        assert result[0].lineWidth == 0.5

    def test_custom_thickness(self):
        result = build_rule({"thickness": 2.0})
        assert result[0].lineWidth == 2.0

    def test_custom_spacing(self):
        result = build_rule({"space_before": 10, "space_after": 20})
        assert result[0].spaceBefore == 10
        assert result[0].spaceAfter == 20
