"""Tests for the programmatic render_pdf entry point."""
import copy

from pdfgen.engine import render_pdf


MINIMAL = {
    "document": {"title": "Engine Test"},
    "content": [
        {"type": "heading", "level": 1, "text": "Hello"},
        {"type": "paragraph", "text": "A paragraph of body text."},
    ],
}


def test_returns_pdf_bytes():
    pdf = render_pdf(MINIMAL)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_does_not_mutate_caller_config():
    config = copy.deepcopy(MINIMAL)
    render_pdf(config)
    assert config == MINIMAL


def test_renders_inline_base64_image(png_data_uri):
    config = {
        "document": {"title": "Inline Image"},
        "content": [
            {"type": "image", "src": png_data_uri, "alt": "red square", "width": 100},
        ],
    }
    pdf = render_pdf(config)
    assert pdf.startswith(b"%PDF-")


def test_renders_chart_with_styling_options():
    config = {
        "document": {"title": "Chart Styles"},
        "content": [
            {
                "type": "chart", "chart_type": "bar", "title": "Styled",
                "alt": "styled bar chart",
                "style": {
                    "show_values": True, "value_format": "{:.1f}%",
                    "y_suffix": "%", "legend_position": "top",
                    "grid_style": "dashed", "tick_size": 8,
                },
                "data": {
                    "labels": ["A", "B"],
                    "series": [
                        {"name": "S1", "values": [1.5, 2.5], "color": "#123456"},
                        {"name": "S2", "values": [1.0, 2.0]},
                    ],
                },
            },
            {
                "type": "chart", "chart_type": "line", "alt": "styled line chart",
                "style": {"legend_position": "bottom", "show_points": True, "marker_size": 3},
                "data": {
                    "labels": ["A", "B", "C"],
                    "series": [
                        {"name": "S1", "values": [1, 2, 3]},
                        {"name": "Bench", "values": [1, 1.5, 2], "color": "#888888", "line_style": "dashed"},
                    ],
                },
            },
        ],
    }
    pdf = render_pdf(config)
    assert pdf.startswith(b"%PDF-")


def test_renders_inline_base64_cover_logo(png_data_uri):
    config = {
        "document": {"title": "Inline Logo"},
        "cover": {"title": "Inline Logo", "logo": png_data_uri},
        "content": [{"type": "paragraph", "text": "Body."}],
    }
    pdf = render_pdf(config)
    assert pdf.startswith(b"%PDF-")
