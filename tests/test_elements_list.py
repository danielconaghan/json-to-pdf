import pytest

from pdfgen.accessibility import TaggedListFlowable
from pdfgen.elements.list_element import build_list


class TestBuildList:
    def test_returns_list_with_tagged_flowable(self, minimal_styles):
        result = build_list({"items": ["a", "b"]}, minimal_styles)
        assert len(result) == 1
        assert isinstance(result[0], TaggedListFlowable)

    def test_bullet_style_uses_bullet_type(self, minimal_styles):
        result = build_list({"items": ["x"], "style": "bullet"}, minimal_styles)
        assert result[0]._bulletType == "bullet"

    def test_numbered_style_uses_numeric_type(self, minimal_styles):
        result = build_list({"items": ["x"], "style": "numbered"}, minimal_styles)
        assert result[0]._bulletType == "1"

    def test_empty_items_still_returns_flowable(self, minimal_styles):
        result = build_list({"items": []}, minimal_styles)
        assert len(result) == 1
        assert isinstance(result[0], TaggedListFlowable)

    def test_default_style_is_bullet(self, minimal_styles):
        result = build_list({"items": ["a"]}, minimal_styles)
        assert result[0]._bulletType == "bullet"
