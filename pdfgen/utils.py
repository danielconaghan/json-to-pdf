from pathlib import Path


def resolve_path(path, base_path):
    """Return an absolute file path, or None if the path is empty or the file cannot be found."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return str(p) if p.exists() else None
    if base_path:
        resolved = Path(base_path) / p
        return str(resolved) if resolved.exists() else None
    return str(p) if p.exists() else None
