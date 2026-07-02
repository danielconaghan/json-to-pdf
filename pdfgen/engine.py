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
from .fonts import register_builtin_fonts, register_fonts
from .merger import deep_merge, load_defaults
from .renderer import render
from .styles import resolve_styles


def render_pdf(user_config, base_path=None):
    """Render a pdfgen document config to PDF bytes.

    base_path resolves relative asset paths in the config (the CLI passes
    the input file's directory); inline base64 images need no base_path.
    """
    user_config = copy.deepcopy(user_config)

    with tempfile.TemporaryDirectory(prefix="pdfgen-") as workdir:
        materialise_inline_images(user_config, workdir)

        config = deep_merge(load_defaults(), user_config)
        config["_resolved_styles"] = resolve_styles(config["styles"])
        register_builtin_fonts()
        register_fonts(config.get("fonts", []), base_path=base_path)

        output_path = os.path.join(workdir, "output.pdf")
        render(config, output_path, base_path=base_path)
        return Path(output_path).read_bytes()
