from pathlib import Path


def parse_width(spec, available):
    """Resolve a width spec to points: "80%" of available, "150pt", or a bare number."""
    try:
        if isinstance(spec, str):
            s = spec.strip()
            if s.endswith("%"):
                return available * float(s[:-1]) / 100
            if s.endswith("pt"):
                return float(s[:-2])
            return float(s)
        return float(spec)
    except (TypeError, ValueError):
        raise ValueError(
            f"invalid width {spec!r}: expected a percentage (\"80%\"), "
            f"points (\"150pt\"), or a number"
        )


def resolve_path(path, base_path):
    """Return an absolute, normalised file path, or None if not found."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return str(p) if p.exists() else None
    if base_path:
        resolved = (Path(base_path) / p).resolve()
        return str(resolved) if resolved.exists() else None
    resolved = p.resolve()
    return str(resolved) if resolved.exists() else None
