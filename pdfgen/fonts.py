from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_VARIANT_SUFFIXES = [
    ("regular",     ""),
    ("bold",        "-Bold"),
    ("italic",      "-Oblique"),
    ("bold_italic", "-BoldOblique"),
]


def register_fonts(fonts_config, base_path=None):
    """Register custom TTF font families from the config fonts list."""
    for font in fonts_config:
        name = font["name"]
        variants = {}

        for field, suffix in _VARIANT_SUFFIXES:
            if field not in font:
                continue
            path = font[field]
            if base_path is not None:
                path = str(Path(base_path) / path)
            registered_name = name if not suffix else f"{name}{suffix}"
            try:
                pdfmetrics.registerFont(TTFont(registered_name, path))
            except Exception as e:
                raise ValueError(f"Font '{name}' ({field}): cannot load '{path}'") from e
            variants[field] = registered_name

        pdfmetrics.registerFontFamily(
            name,
            normal=variants.get("regular", name),
            bold=variants.get("bold", variants.get("regular", name)),
            italic=variants.get("italic", variants.get("regular", name)),
            boldItalic=variants.get("bold_italic", variants.get("regular", name)),
        )
