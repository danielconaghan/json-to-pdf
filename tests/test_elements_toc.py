import pytest
from reportlab.platypus.tableofcontents import TableOfContents

from pdfgen.accessibility import TaggedHeading
from pdfgen.elements.toc import build_toc


class TestBuildToc:
    def test_returns_toc_flowable(self, minimal_styles):
        result = build_toc({}, minimal_styles)
        assert any(isinstance(f, TableOfContents) for f in result)

    def test_no_title_means_no_heading(self, minimal_styles):
        result = build_toc({"title": ""}, minimal_styles)
        assert not any(isinstance(f, TaggedHeading) for f in result)

    def test_title_produces_tagged_heading(self, minimal_styles):
        result = build_toc({"title": "Contents"}, minimal_styles)
        headings = [f for f in result if isinstance(f, TaggedHeading)]
        assert len(headings) == 1

    def test_heading_has_h1_role(self, minimal_styles):
        result = build_toc({"title": "Contents"}, minimal_styles)
        heading = next(f for f in result if isinstance(f, TaggedHeading))
        assert heading._tag_role == "H1"

    def test_depth_controls_toc_level_styles(self, minimal_styles):
        h1 = minimal_styles.get("h1") or minimal_styles["body"]
        styles = {
            **minimal_styles,
            "toc_h1": minimal_styles["body"],
            "toc_h2": minimal_styles["body"],
            "toc_h3": minimal_styles["body"],
        }
        result = build_toc({"depth": 3}, styles)
        toc = next(f for f in result if isinstance(f, TableOfContents))
        assert len(toc.levelStyles) == 3

    def test_depth_capped_at_3(self, minimal_styles):
        styles = {
            **minimal_styles,
            "toc_h1": minimal_styles["body"],
            "toc_h2": minimal_styles["body"],
            "toc_h3": minimal_styles["body"],
        }
        result = build_toc({"depth": 99}, styles)
        toc = next(f for f in result if isinstance(f, TableOfContents))
        assert len(toc.levelStyles) == 3
