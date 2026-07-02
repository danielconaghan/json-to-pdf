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


def test_renders_inline_base64_cover_logo(png_data_uri):
    config = {
        "document": {"title": "Inline Logo"},
        "cover": {"title": "Inline Logo", "logo": png_data_uri},
        "content": [{"type": "paragraph", "text": "Body."}],
    }
    pdf = render_pdf(config)
    assert pdf.startswith(b"%PDF-")
