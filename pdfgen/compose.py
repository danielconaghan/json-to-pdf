"""Compose engine: resolve a report template into a literal pdfgen document.

This is the step *before* rendering. Where :func:`pdfgen.engine.render_pdf`
takes a fully-resolved document and turns it into a PDF, ``compose`` takes the
three upstream inputs — a template, the client's resolved values, and a
locale-resolved translation map — and produces that fully-resolved document,
with nothing left for the renderer to interpret.

It is kept deliberately separate from rendering. Templates and copy change
often (and are edited by non-engineers); rendering barely changes once it
works. Folding one into the other would couple a fast-moving thing to a stable
one. ``compose`` therefore knows nothing about layout or PDF output — it only
turns template vocabulary into literal strings and structure.

The three inputs (see the brief):

* **template** — a tree with a top-level ``content`` array. Leaves carry a
  translation ``key``; conditional groups carry ``variants``, each guarded by a
  ``when`` object matched against ``values``.
* **values** — the client's resolved data: banded fields for ``when`` matching
  (``{"composure": "low"}``) plus raw fields for interpolation (name, scores).
  Received as-is; this engine never buckets raw scores into bands — that logic
  lives upstream and duplicating it here would let the two drift apart.
* **translations** — a flat ``key -> string`` map, already resolved to the
  correct locale. Strings may contain ``{{placeholder}}`` tokens filled from
  ``values``.

Everything fails loudly. A missing key, an unmatched variant, or a missing
interpolation value raises :class:`ComposeError` identifying the offending
node — this runs server-side with no user in the loop, so a silent gap would
surface as broken text in a client's PDF. The engine is agnostic to how many
templates or data sources feed it in a given call: invoke it once per source or
once over combined input, it neither knows nor cares.
"""
import copy
import re

# Template vocabulary that must never survive into the composed output.
_TEMPLATE_FIELDS = ("when", "variants", "key")

# ``{{ token }}`` where token is a dotted identifier (client_name, score.value).
_PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")

# Resolved translation strings land here — the field the renderer reads text
# from (see pdfgen.renderer._build_paragraph / _build_heading).
_TEXT_FIELD = "text"

_MISSING = object()


class ComposeError(ValueError):
    """A template could not be fully resolved.

    Subclasses :class:`ValueError` so the render endpoints, which already map
    ``ValueError`` to a 400, treat a bad template/values/translations triple as
    a bad request rather than an opaque 500.
    """


def compose(template, values, translations):
    """Resolve ``template`` against ``values`` and ``translations``.

    Returns a fresh pdfgen document dict (the caller's inputs are never
    mutated) with every ``key`` replaced by its interpolated string and every
    conditional group collapsed to its matching variant's content. The result
    contains no ``when``/``variants``/``key`` fields and no unresolved
    ``{{placeholder}}`` tokens; that is asserted before returning.
    """
    if not isinstance(template, dict):
        raise ComposeError("template must be a JSON object")
    content = template.get("content")
    if not isinstance(content, list):
        raise ComposeError("template must have a 'content' array")

    doc = copy.deepcopy(template)
    doc["content"] = _resolve_nodes(content, values, translations, "content")
    _validate(doc)
    return doc


def _resolve_nodes(nodes, values, translations, path):
    """Resolve a list of nodes, flattening each into the output stream."""
    out = []
    for i, node in enumerate(nodes):
        out.extend(_resolve_node(node, values, translations, f"{path}[{i}]"))
    return out


def _resolve_node(node, values, translations, path):
    """Resolve a single node into zero or more literal nodes.

    Returns a list because a group flattens into its variant's content (a
    plain container has no rendered form), while a leaf yields one element.
    """
    if not isinstance(node, dict):
        raise ComposeError(f"{path}: node must be an object, got {type(node).__name__}")

    # Conditional group: pick the matching variant and splice its resolved
    # content in place. The group wrapper itself is template vocabulary and
    # disappears — the renderer has no grouping element, and keeping one would
    # silently drop everything inside it.
    if "variants" in node:
        variant = _select_variant(node, values, path)
        return _resolve_nodes(
            _variant_content(variant, path), values, translations, f"{path}.content"
        )

    # Keyed leaf: look up, interpolate, emit a literal element.
    if "key" in node:
        return [_resolve_leaf(node, values, translations, path)]

    # Plain container (organisational grouping without a condition): resolve
    # its children and flatten. Real elements name their child arrays
    # differently (list ``items``, table ``rows``, chart ``data``), so a
    # ``content`` list unambiguously marks a container.
    if isinstance(node.get("content"), list):
        return _resolve_nodes(node["content"], values, translations, f"{path}.content")

    # Literal element with no template vocabulary — pass through untouched.
    return [copy.deepcopy(node)]


def _select_variant(node, values, path):
    """Return the first variant whose ``when`` matches ``values``.

    No match is a hard error: a client must never get a report with a gap where
    a section should be. A genuine "show nothing here" case must be explicit in
    the template as a variant with empty ``content``, never an implicit
    fall-through.
    """
    variants = node["variants"]
    if not isinstance(variants, list) or not variants:
        raise ComposeError(f"{path}: 'variants' must be a non-empty array")

    for i, variant in enumerate(variants):
        vpath = f"{path}.variants[{i}]"
        if not isinstance(variant, dict):
            raise ComposeError(f"{vpath}: variant must be an object")
        when = variant.get("when")
        if not isinstance(when, dict):
            raise ComposeError(f"{vpath}: variant must have a 'when' object")
        if _matches(when, values):
            return variant

    conditions = [v.get("when") for v in variants if isinstance(v, dict)]
    raise ComposeError(
        f"{path}: no variant matched values; tried {conditions}"
    )


def _matches(when, values):
    """True iff every key in ``when`` is present in ``values`` and equal."""
    return all(k in values and values[k] == expected for k, expected in when.items())


def _variant_content(variant, path):
    content = variant.get("content")
    if not isinstance(content, list):
        raise ComposeError(f"{path}: matched variant must have a 'content' array")
    return content


def _resolve_leaf(node, values, translations, path):
    """Turn a ``{..., "key": ...}`` node into a literal element.

    The ``key`` is replaced by an interpolated ``text`` field; every other
    field (``type``, ``level``, ``style``, ...) passes through unchanged.
    """
    key = node["key"]
    if not isinstance(key, str):
        raise ComposeError(f"{path}: 'key' must be a string")
    if key not in translations:
        raise ComposeError(f"{path}: no translation for key '{key}'")

    text = _interpolate(translations[key], values, path, key)
    resolved = {k: copy.deepcopy(v) for k, v in node.items() if k != "key"}
    resolved[_TEXT_FIELD] = text
    return resolved


def _interpolate(template_string, values, path, key):
    """Fill ``{{placeholder}}`` tokens in a translation string from ``values``.

    A referenced value that is absent is a hard error — a half-filled sentence
    is worse than a loud failure server-side.
    """
    if not isinstance(template_string, str):
        raise ComposeError(f"{path}: translation for '{key}' is not a string")

    def replace(match):
        token = match.group(1)
        value = _lookup(values, token)
        if value is _MISSING:
            raise ComposeError(
                f"{path}: translation '{key}' references "
                f"'{{{{{token}}}}}' but values has no '{token}'"
            )
        return str(value)

    return _PLACEHOLDER.sub(replace, template_string)


def _lookup(values, token):
    """Resolve a dotted token against ``values``; ``_MISSING`` if absent."""
    current = values
    for part in token.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def _validate(obj, path="document"):
    """Assert the composed tree carries no template vocabulary or placeholders.

    A malformed or partially-resolved document fails here rather than showing
    up as broken text in a PDF. This is the minimum guarantee the brief asks
    for: no ``when``/``variants``/``key`` remain, and no ``{{placeholder}}``
    survived interpolation.
    """
    if isinstance(obj, dict):
        for field in _TEMPLATE_FIELDS:
            if field in obj:
                raise ComposeError(
                    f"{path}: composed output still contains template field '{field}'"
                )
        for k, v in obj.items():
            _validate(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        leftover = _PLACEHOLDER.search(obj)
        if leftover:
            raise ComposeError(
                f"{path}: unresolved placeholder '{leftover.group(0)}' in composed output"
            )
