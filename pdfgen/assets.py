"""Inline base64 image assets: decode data URIs from a config into real files.

Configs delivered over an API have no filesystem for their images to live on,
so any image field may carry a ``data:image/...;base64,`` URI instead of a
path. Before rendering, ``materialise_inline_images`` walks the config,
writes each data URI to a file in a caller-owned directory, and rewrites the
field to that path — downstream code only ever sees ordinary file paths.
"""
import base64
import hashlib
import re
from pathlib import Path

_DATA_URI_RE = re.compile(r"^data:image/(png|jpe?g|gif);base64,(.*)$", re.IGNORECASE | re.DOTALL)

_EXTENSIONS = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpg", "gif": ".gif"}


def is_image_data_uri(value):
    """Return True if value is a string carrying a base64 image data URI."""
    return isinstance(value, str) and bool(_DATA_URI_RE.match(value))


def materialise_inline_images(config, target_dir):
    """Rewrite every image data URI in config to a file path under target_dir.

    Mutates config in place. Identical images are written once (content-hash
    filenames). Raises ValueError for malformed base64 payloads.
    """
    target = Path(target_dir)

    def walk(node):
        if isinstance(node, dict):
            items = node.items()
        elif isinstance(node, list):
            items = enumerate(node)
        else:
            return
        for key, value in items:
            if is_image_data_uri(value):
                node[key] = _write_asset(value, target)
            else:
                walk(value)

    walk(config)


def _write_asset(data_uri, target):
    subtype, payload = _DATA_URI_RE.match(data_uri).groups()
    try:
        data = base64.b64decode(payload, validate=True)
    except Exception as e:
        raise ValueError(f"invalid base64 image data: {e}") from e
    if not data:
        raise ValueError("base64 image data is empty")

    ext = _EXTENSIONS[subtype.lower()]
    path = target / f"{hashlib.sha256(data).hexdigest()[:16]}{ext}"
    if not path.exists():
        path.write_bytes(data)
    return str(path)
