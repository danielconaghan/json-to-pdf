import pytest

from pdfgen.fonts import register_fonts


def test_missing_font_file_raises_value_error(tmp_path):
    fonts_config = [{"name": "MyFont", "regular": "nonexistent.ttf"}]
    with pytest.raises(ValueError, match="MyFont"):
        register_fonts(fonts_config, base_path=str(tmp_path))


def test_error_message_includes_path(tmp_path):
    fonts_config = [{"name": "MyFont", "regular": "missing/path/font.ttf"}]
    with pytest.raises(ValueError, match="missing/path/font.ttf"):
        register_fonts(fonts_config, base_path=str(tmp_path))


def test_empty_fonts_list_does_nothing():
    register_fonts([])  # should not raise


def test_font_without_variants_does_nothing():
    register_fonts([{"name": "Empty"}])  # no regular/bold/etc keys
