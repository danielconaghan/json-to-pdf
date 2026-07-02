"""Tests for inline base64 asset materialisation."""
from pathlib import Path

import pytest

from pdfgen.assets import is_image_data_uri, materialise_inline_images


class TestIsImageDataUri:
    def test_png_uri(self, png_data_uri):
        assert is_image_data_uri(png_data_uri)

    def test_jpeg_uri(self):
        assert is_image_data_uri("data:image/jpeg;base64,abcd")

    def test_plain_path_is_not(self):
        assert not is_image_data_uri("assets/logo.png")

    def test_non_image_mime_is_not(self):
        assert not is_image_data_uri("data:application/pdf;base64,abcd")

    def test_non_string_is_not(self):
        assert not is_image_data_uri(None)
        assert not is_image_data_uri(42)


class TestMaterialiseInlineImages:
    def test_rewrites_nested_uris_to_files(self, png_data_uri, tmp_path):
        config = {
            "cover": {"logo": png_data_uri},
            "content": [{"type": "image", "src": png_data_uri, "alt": "chart"}],
        }
        materialise_inline_images(config, tmp_path)

        logo = Path(config["cover"]["logo"])
        src = Path(config["content"][0]["src"])
        assert logo.exists() and logo.suffix == ".png"
        # identical payloads dedupe to one file
        assert logo == src
        assert config["content"][0]["alt"] == "chart"

    def test_plain_paths_untouched(self, tmp_path):
        config = {"header": {"logo": "assets/logo.png"}}
        materialise_inline_images(config, tmp_path)
        assert config["header"]["logo"] == "assets/logo.png"

    def test_invalid_base64_raises(self, tmp_path):
        config = {"cover": {"logo": "data:image/png;base64,not-valid-base64!!!"}}
        with pytest.raises(ValueError, match="invalid base64"):
            materialise_inline_images(config, tmp_path)

    def test_empty_payload_raises(self, tmp_path):
        config = {"cover": {"logo": "data:image/png;base64,"}}
        with pytest.raises(ValueError, match="empty"):
            materialise_inline_images(config, tmp_path)
