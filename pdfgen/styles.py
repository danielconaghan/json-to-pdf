def resolve_styles(styles):
    """Resolve all extends chains. Returns a flat dict of fully-resolved style dicts."""
    return {name: _resolve(name, styles, frozenset()) for name in styles}


def _resolve(name, all_styles, seen):
    if name in seen:
        chain = " -> ".join(sorted(seen)) + f" -> {name}"
        raise ValueError(f"Circular style inheritance: {chain}")
    style = all_styles.get(name)
    if style is None:
        raise ValueError(f"Style '{name}' not found")
    if "extends" not in style:
        return {k: v for k, v in style.items()}
    parent_name = style["extends"]
    parent = _resolve(parent_name, all_styles, seen | {name})
    result = parent.copy()
    result.update({k: v for k, v in style.items() if k != "extends"})
    return result
