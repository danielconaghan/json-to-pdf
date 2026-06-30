from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_fonts(fonts_config, base_path=None):
    """Register custom TTF font families from the config fonts list."""
    for font in fonts_config:
        name = font["name"]
        variants = {}

        _VARIANT_KEYS = [
            ("regular",    name),
            ("bold",       f"{name}-Bold"),
            ("italic",     f"{name}-Oblique"),
            ("bold_italic", f"{name}-BoldOblique"),
        ]

        for field, registered_name in _VARIANT_KEYS:
            if field not in font:
                continue
            path = font[field]
            if base_path is not None:
                path = str(Path(base_path) / path)
            pdfmetrics.registerFont(TTFont(registered_name, path))
            variants[field] = registered_name

        pdfmetrics.registerFontFamily(
            name,
            normal=variants.get("regular", name),
            bold=variants.get("bold", variants.get("regular", name)),
            italic=variants.get("italic", variants.get("regular", name)),
            boldItalic=variants.get("bold_italic", variants.get("regular", name)),
        )
