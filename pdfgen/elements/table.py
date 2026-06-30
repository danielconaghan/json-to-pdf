"""
Table element builder.

Cells use Paragraph objects so long text wraps correctly. Column alignment
is controlled per-column via `column_align`; the header row has its own
`header_align` setting. Style properties merge: element-level `style` wins
over the global `table_style` in defaults.json (shallow merge is correct
here because the table style is a flat dict of scalars).
"""
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

_ALIGN_RL = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}
_STYLE_CACHE: dict = {}


def build_table(element, ctx):
    """Return a Table flowable, or None if the element has no usable data."""
    # Merge global table_style with per-table style override (element wins)
    style = {**ctx.config.get("table_style", {}), **element.get("style", {})}

    headers = element.get("headers") or []
    rows = element.get("rows") or []

    num_cols = len(headers) if headers else (len(rows[0]) if rows else 0)
    if num_cols == 0:
        return None

    col_widths = _resolve_col_widths(
        element.get("column_widths"), num_cols, ctx.doc.width,
        full_width=style.get("full_width", True),
    )
    col_aligns = _resolve_col_aligns(
        element.get("column_align"), num_cols, style.get("align", "left")
    )

    header_ps, body_ps = _make_cell_styles(style)
    data = _build_data(headers, rows, header_ps, body_ps, col_aligns, style)

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1 if headers else 0,   # repeat header on new pages
    )
    table.setStyle(_build_style(style, has_header=bool(headers), num_data_rows=len(rows)))
    table.hAlign = "LEFT"
    table.spaceBefore = style.get("space_before", 12)
    table.spaceAfter = style.get("space_after", 12)

    return [table]


# ── Column widths ────────────────────────────────────────────────────────────


def _resolve_col_widths(spec, num_cols, available, full_width=True):
    """Convert a width spec list into absolute point values.

    Each entry is either a percentage string ("40%") or a numeric point value.
    Trailing columns not covered by spec share the remaining width equally.
    When full_width is True (the default), all widths are scaled proportionally
    so the table always spans the full text width.
    """
    if not spec:
        unit = available / num_cols
        return [unit] * num_cols

    widths = []
    for s in spec:
        if isinstance(s, str) and s.endswith("%"):
            widths.append(available * float(s.rstrip("%")) / 100)
        else:
            widths.append(float(s))

    # Fill any unspecified trailing columns
    if len(widths) < num_cols:
        remaining = max(0.0, available - sum(widths))
        share = remaining / (num_cols - len(widths))
        widths.extend([share] * (num_cols - len(widths)))

    widths = widths[:num_cols]

    # Scale proportionally so all columns together fill the available width
    if full_width:
        total = sum(widths)
        if total > 0 and abs(total - available) > 1.0:   # 1pt tolerance
            scale = available / total
            widths = [w * scale for w in widths]

    return widths


# ── Column alignment ─────────────────────────────────────────────────────────


def _resolve_col_aligns(spec, num_cols, default):
    """Return a list of alignment strings, one per column."""
    base = list(spec) if spec else []
    return (base + [default] * num_cols)[:num_cols]


# ── Cell paragraph styles ────────────────────────────────────────────────────


def _make_cell_styles(style):
    """Build base ParagraphStyles for header and body cells."""
    size = style.get("font_size", 10)
    leading = round(size * 1.35)
    shared = dict(fontSize=size, leading=leading, spaceBefore=0, spaceAfter=0)

    header_ps = ParagraphStyle(
        "_th",
        fontName=style.get("header_font", "Helvetica-Bold"),
        textColor=HexColor(style.get("header_color", "#ffffff")),
        **shared,
    )
    body_ps = ParagraphStyle(
        "_td",
        fontName=style.get("body_font", "Helvetica"),
        textColor=HexColor(style.get("body_color", "#333333")),
        **shared,
    )
    return header_ps, body_ps


def _with_align(ps, align):
    """Return ps unchanged if alignment already matches, else a cached derived copy."""
    rl_align = _ALIGN_RL.get(align, TA_LEFT)
    if ps.alignment == rl_align:
        return ps
    key = (id(ps), align)
    if key not in _STYLE_CACHE:
        _STYLE_CACHE[key] = ParagraphStyle(f"{ps.name}_{align}", parent=ps, alignment=rl_align)
    return _STYLE_CACHE[key]


# ── Data assembly ────────────────────────────────────────────────────────────


def _build_data(headers, rows, header_ps, body_ps, col_aligns, style):
    """Wrap every cell in a Paragraph so text wraps correctly."""
    data = []
    header_align = style.get("header_align", "left")

    if headers:
        data.append([
            Paragraph(str(h), _with_align(header_ps, header_align))
            for h in headers
        ])

    for row in rows:
        data.append([
            Paragraph(
                str(cell),
                _with_align(body_ps, col_aligns[i] if i < len(col_aligns) else "left"),
            )
            for i, cell in enumerate(row)
        ])

    return data


# ── TableStyle ───────────────────────────────────────────────────────────────


def _build_style(style, has_header, num_data_rows):
    padding = style.get("cell_padding", 8)
    grid_color = HexColor(style.get("grid_color", "#dddddd"))
    grid_thick = style.get("grid_thickness", 0.5)
    data_start = 1 if has_header else 0

    cmds = [
        # Padding — explicit so every side can be tuned
        ("TOPPADDING",    (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING",   (0, 0), (-1, -1), padding),
        ("RIGHTPADDING",  (0, 0), (-1, -1), padding),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Outer border
        ("BOX",           (0, 0), (-1, -1), grid_thick, grid_color),
    ]

    if has_header:
        header_bg = HexColor(style.get("header_background", "#1a1a2e"))
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), header_bg))

    if style.get("alternate_rows", True) and num_data_rows > 0:
        alt = HexColor(style.get("alternate_color", "#f5f7fa"))
        # ROWBACKGROUNDS cycles [white, alt] over every data row
        cmds.append(("ROWBACKGROUNDS", (0, data_start), (-1, -1), [white, alt]))

    # Thin horizontal rule between data rows (skip the last row — BOX covers it)
    if num_data_rows > 1:
        cmds.append(
            ("LINEBELOW", (0, data_start), (-1, -2), grid_thick, grid_color)
        )

    return TableStyle(cmds)
