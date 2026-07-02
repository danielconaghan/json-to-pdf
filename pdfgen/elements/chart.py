import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.ticker import FuncFormatter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Spacer

from ..accessibility import TaggedCaption, TaggedChart
from ..utils import parse_width

_DEFAULT_COLORS = [
    "#1a1a2e",  # deep navy
    "#2e6da4",  # steel blue
    "#c69b3a",  # amber
    "#4a8b6e",  # sage green
    "#8b5a6e",  # mauve
    "#4b8fcf",  # sky blue
]

_LINE_STYLES = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}


def build_chart(element, rl_styles, doc, config):
    """Return a list of flowables for a bar, line, pie, or donut chart."""
    style = {**config.get("chart_style", {}), **element.get("style", {})}
    data = element.get("data", {})

    width_pt = parse_width(element.get("width", "100%"), doc.width)

    width_in = width_pt / 72
    height_in = width_in * style.get("height_ratio", 0.55)
    dpi = style.get("dpi", 300)
    bg = style.get("background", "#ffffff")

    fig = Figure(figsize=(width_in, height_in), facecolor=bg)
    ax = fig.add_subplot(111, facecolor=bg)

    chart_type = element.get("chart_type", "bar")
    _DRAW = {"bar": _draw_bar, "line": _draw_line, "pie": _draw_pie, "donut": _draw_donut}
    draw = _DRAW.get(chart_type)
    if draw:
        draw(ax, data, style)

    title = element.get("title", "")
    if title:
        # Extra pad clears a top-positioned legend, which sits between title and plot
        pad = 30 if style.get("legend_position", "best") == "top" else 12
        # Pie/donut keep a centred title; axis charts read better editorial-style
        loc = "center" if chart_type in ("pie", "donut") else "left"
        ax.set_title(title, fontsize=style.get("title_size", 12),
                     color=style.get("title_color", "#1a1a2e"), pad=pad, loc=loc)

    _apply_style(ax, style, chart_type)

    buf = io.BytesIO()
    FigureCanvasAgg(fig).print_figure(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=bg)
    buf.seek(0)

    # Use actual rendered dimensions — bbox_inches='tight' can change height
    iw, ih = ImageReader(buf).getSize()
    buf.seek(0)
    height_pt = width_pt * ih / iw

    img = TaggedChart(buf, width=width_pt, height=height_pt)
    img.hAlign = element.get("align", "left").upper()
    img.spaceBefore = style.get("space_before", 12)
    img.spaceAfter = style.get("space_after", 12)
    img._tag_alt = element.get("alt", "")

    flowables = [img]
    caption = element.get("caption")
    if caption:
        cap_style = rl_styles.get("caption") or rl_styles.get("body")
        flowables.append(Spacer(1, 4))
        flowables.append(TaggedCaption(caption, cap_style))

    return flowables


# ── Chart drawers ─────────────────────────────────────────────────────────────


def _draw_bar(ax, data, style):
    labels = data.get("labels", [])
    series = data.get("series", [])
    if not series:
        return

    n = len(series)
    x_pos = list(range(len(labels)))
    slot = style.get("bar_width", 0.7) / n
    colors = style.get("colors", _DEFAULT_COLORS)

    for i, s in enumerate(series):
        offset = (i - (n - 1) / 2) * slot
        rects = ax.bar(
            [xi + offset for xi in x_pos],
            s.get("values", []),
            width=slot * 0.88,
            color=s.get("color", colors[i % len(colors)]),
            label=s.get("name", ""),
            zorder=3,
        )
        if style.get("show_values", False):
            ax.bar_label(
                rects,
                fmt=style.get("value_format", "{:g}").format,
                fontsize=style.get("tick_size", 9) - 1,
                color=style.get("tick_color", "#555555"),
                padding=2,
            )

    rot = _label_rotation(labels, ax.figure.get_figwidth())
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center")


def _draw_line(ax, data, style):
    labels = data.get("labels", [])
    series = data.get("series", [])
    if not series:
        return

    x_pos = list(range(len(labels)))
    colors = style.get("colors", _DEFAULT_COLORS)

    show_points = style.get("show_points", False)
    show_area   = style.get("show_area",   False)

    for i, s in enumerate(series):
        color = s.get("color", colors[i % len(colors)])
        values = s.get("values", [])
        ax.plot(
            x_pos, values,
            color=color,
            linewidth=style.get("line_width", 2.0),
            linestyle=_LINE_STYLES.get(s.get("line_style", "solid"), "-"),
            marker="o" if show_points else "none",
            markersize=style.get("marker_size", 4),
            markeredgewidth=0,
            label=s.get("name", ""),
            zorder=3,
        )
        if show_area:
            ax.fill_between(x_pos, values, alpha=style.get("area_alpha", 0.07), color=color)

    rot = _label_rotation(labels, ax.figure.get_figwidth())
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center")


def _draw_pie(ax, data, style):
    _draw_pie_or_donut(ax, data, style, is_donut=False)


def _draw_donut(ax, data, style):
    _draw_pie_or_donut(ax, data, style, is_donut=True)


def _draw_pie_or_donut(ax, data, style, is_donut=False):
    series = data.get("series", [])
    if not series:
        return

    values = series[0].get("values", [])
    labels = list(data.get("labels", []))
    # Pad labels to match values length
    while len(labels) < len(values):
        labels.append("")

    if not values:
        return

    colors = style.get("colors", _DEFAULT_COLORS)
    colors_cycle = [colors[i % len(colors)] for i in range(len(values))]

    # Draw wedges — no built-in labels or percentages
    wedges, _ = ax.pie(
        values,
        labels=None,
        colors=colors_cycle,
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )

    # Donut hole
    if is_donut:
        donut_r = style.get("donut_ratio", 0.5)
        ax.add_patch(Circle((0, 0), donut_r, fc="white", zorder=5))

    # Leader lines + labels with percentages
    total = sum(v for v in values if v)
    for wedge, label, value in zip(wedges, labels, values):
        if not value or total == 0:
            continue
        pct = value / total * 100
        mid_rad = np.radians((wedge.theta1 + wedge.theta2) / 2)

        # Three-point leader: edge of wedge → radial elbow → short horizontal
        ex = 1.05 * np.cos(mid_rad)
        ey = 1.05 * np.sin(mid_rad)
        kx = 1.22 * np.cos(mid_rad)
        ky = 1.22 * np.sin(mid_rad)
        tx = kx + (0.12 if kx >= 0 else -0.12)
        ty = ky

        ax.plot([ex, kx, tx], [ey, ky, ty],
                color="#aaaaaa", linewidth=0.7, zorder=4)

        ha = "left" if tx >= 0 else "right"
        pad = 0.025
        lx = tx + (pad if ha == "left" else -pad)
        txt = f"{label}\n{pct:.1f}%" if label else f"{pct:.1f}%"
        ax.text(lx, ty, txt, ha=ha, va="center",
                fontsize=8, color="#333333", zorder=4, multialignment=ha)

    ax.axis("equal")


# ── Shared styling ────────────────────────────────────────────────────────────


def _apply_style(ax, style, chart_type):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    if chart_type in ("pie", "donut"):
        for spine in ("bottom", "left"):
            ax.spines[spine].set_visible(False)
        return

    axis_color = style.get("axis_color", "#cccccc")
    ax.spines["bottom"].set_color(axis_color)
    ax.spines["left"].set_color(axis_color)

    if style.get("grid", True):
        ax.yaxis.grid(
            True,
            color=style.get("grid_color", "#eeeeee"),
            linestyle=_LINE_STYLES.get(style.get("grid_style", "solid"), "-"),
            linewidth=0.7,
            zorder=0,
        )
        ax.set_axisbelow(True)

    tick_size = style.get("tick_size", 9)
    ax.tick_params(axis="both", which="both", length=0,
                   labelsize=tick_size, colors=style.get("tick_color", "#555555"))

    y_prefix = style.get("y_prefix", "")
    y_suffix = style.get("y_suffix", "")
    if y_prefix or y_suffix:
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{y_prefix}{v:g}{y_suffix}")
        )

    if style.get("legend", True):
        handles, leg_labels = ax.get_legend_handles_labels()
        if handles and any(leg_labels):
            _place_legend(ax, handles, leg_labels, style, tick_size)


def _place_legend(ax, handles, labels, style, fontsize):
    position = style.get("legend_position", "best")
    common = {
        "fontsize": fontsize,
        "frameon": False,
        # Compact swatches: matplotlib's defaults dominate the row
        "handlelength": 1.2,
        "handleheight": 0.9,
        "handletextpad": 0.5,
        "columnspacing": 1.4,
    }
    if position == "top":
        ax.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1.0),
                  ncol=min(len(handles), 4), borderaxespad=0.4, **common)
    elif position == "bottom":
        ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.15),
                  ncol=min(len(handles), 4), **common)
    elif position == "right":
        ax.legend(handles, labels, loc="center left", bbox_to_anchor=(1.02, 0.5), **common)
    else:
        ax.legend(handles, labels, loc="best", **common)


def _label_rotation(labels, fig_width_in):
    # Rotate only when horizontal labels would genuinely collide — slanted
    # labels cost more in readability than they save in space. ~0.07in per
    # character approximates 9pt DejaVu; +2 chars per label for breathing room.
    total_chars = sum(len(str(l)) + 2 for l in labels)
    if total_chars * 0.07 > fig_width_in:
        return 45
    return 0
