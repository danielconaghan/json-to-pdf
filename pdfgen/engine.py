"""Programmatic entry point: render a config dict to PDF bytes.

This is the API the Lambda handler (and any other embedder) calls. It owns
the full pipeline the CLI previously ran inline — defaults merge, style
resolution, font registration, inline-asset materialisation, render — and
works entirely in a temporary directory so it is safe on read-only
filesystems where only the system temp dir is writable.
"""
import copy
import os
import tempfile
from pathlib import Path

from .assets import materialise_inline_images
from .compose import compose
from .fonts import register_builtin_fonts, register_fonts
from .merger import deep_merge, load_defaults
from .renderer import render
from .sourcemap import SourceMap
from .styles import resolve_styles


def render_pdf(user_config, base_path=None):
    """Render a pdfgen document config to PDF bytes.

    base_path resolves relative asset paths in the config (the CLI passes
    the input file's directory); inline base64 images need no base_path.
    """
    pdf, _ = _render(user_config, base_path=base_path, source_map=None)
    return pdf


def render_pdf_with_map(user_config, base_path=None):
    """Render to PDF bytes plus an element-to-page position map.

    Returns ``(pdf_bytes, bands)`` where ``bands`` is a list of
    ``{index, page, y0, y1}`` records (see :mod:`pdfgen.sourcemap`) linking each
    top-level ``content`` element to where it landed in the PDF. Used by the web
    UI to sync the JSON editor with the preview; the normal render path
    (``render_pdf``) never builds the map.
    """
    source_map = SourceMap()
    pdf, _ = _render(user_config, base_path=base_path, source_map=source_map)
    return pdf, source_map.bands()


def compose_and_render_pdf(template, values, translations, base_path=None):
    """Compose a template into a document, then render that document to PDF.

    A convenience over calling :func:`pdfgen.compose.compose` and
    :func:`render_pdf` in turn. Returns ``(pdf_bytes, composed)`` — the composed
    JSON is handed back, never discarded, so it can be logged as an audit trail
    and used to tell a compose failure (wrong text, wrong branch) apart from a
    render failure (bad layout). compose and render stay independently callable;
    this only chains them.
    """
    composed = compose(template, values, translations)
    pdf = render_pdf(composed, base_path=base_path)
    return pdf, composed


def _render(user_config, base_path=None, source_map=None):
    user_config = copy.deepcopy(user_config)

    with tempfile.TemporaryDirectory(prefix="pdfgen-") as workdir:
        materialise_inline_images(user_config, workdir)

        config = deep_merge(load_defaults(), user_config)
        config["_resolved_styles"] = resolve_styles(config["styles"])
        register_builtin_fonts()
        register_fonts(config.get("fonts", []), base_path=base_path)

        output_path = os.path.join(workdir, "output.pdf")
        render(config, output_path, base_path=base_path, source_map=source_map)
        return Path(output_path).read_bytes(), source_map
