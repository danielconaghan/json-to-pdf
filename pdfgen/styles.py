def resolve_styles(styles):
    """Resolve all extends chains. Returns a flat dict of fully-resolved style dicts.

    Shared parent styles are resolved once and cached so a deep extends tree
    doesn't re-resolve the same ancestor repeatedly.
    """
    cache = {}

    def _cached(name, seen):
        if name in cache:
            return cache[name].copy()
        result = _resolve(name, styles, seen, _cached)
        cache[name] = result
        return result.copy()

    return {name: _cached(name, ()) for name in styles}


def _resolve(name, all_styles, seen, resolve_fn):
    if name in seen:
        chain = " → ".join((*seen, name))
        raise ValueError(f"Circular style inheritance: {chain}")
    style = all_styles.get(name)
    if style is None:
        raise ValueError(f"Style '{name}' not found")
    if "extends" not in style:
        return {k: v for k, v in style.items()}
    parent = resolve_fn(style["extends"], (*seen, name))
    parent.update({k: v for k, v in style.items() if k != "extends"})
    return parent
