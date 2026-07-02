# Charts

Charts are rendered by matplotlib into a high-resolution PNG and embedded as an image in the PDF. Four chart types are supported: `bar`, `line`, `pie`, and `donut`.

---

## Common structure

Every chart shares these top-level properties:

```json
{
  "type":       "chart",
  "chart_type": "bar",
  "title":      "Quarterly Returns (%)",
  "width":      "100%",
  "align":      "left",
  "caption":    "Fig. 1 — Optional caption text.",
  "style":      { ... },
  "data":       { ... }
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `chart_type` | yes | `"bar"` | `"bar"`, `"line"`, `"pie"`, or `"donut"`. |
| `title` | no | none | Title rendered inside the chart, above the plot area. |
| `width` | no | `"100%"` | Content width as a percentage (`"80%"`) or absolute points (`"300pt"`). |
| `align` | no | `"left"` | `"left"`, `"center"`, or `"right"`. Most useful when `width` is less than 100%. |
| `caption` | no | none | Caption below the chart, using the `caption` style. |
| `style` | no | `{}` | Per-chart overrides of `chart_style` defaults. |
| `data` | yes | — | Chart data object (see each type below). |

---

## Bar chart

Grouped vertical bars. Supports one or more data series — multiple series are plotted side-by-side within each group.

```json
{
  "type":       "chart",
  "chart_type": "bar",
  "title":      "Quarterly Total Return (%)",
  "data": {
    "labels": ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"],
    "series": [
      { "name": "Portfolio",  "values": [3.2, 4.8, 2.9, 5.1] },
      { "name": "Benchmark",  "values": [2.1, 3.6, 2.4, 4.0] }
    ]
  }
}
```

**Single-series bar (no legend):**
```json
{
  "type":       "chart",
  "chart_type": "bar",
  "title":      "Risk Contribution by Asset Class (%)",
  "style":      { "bar_width": 0.5 },
  "data": {
    "labels": ["Equities", "Fixed Income", "Alternatives", "Real Assets", "Cash"],
    "series": [
      { "name": "", "values": [6.2, 1.4, 1.8, 0.6, 0.1] }
    ]
  }
}
```

Setting `"name": ""` suppresses the legend entry for that series.

---

## Line chart

One line per series, with subtle area fill below each line. Best for time-series data.

```json
{
  "type":       "chart",
  "chart_type": "line",
  "title":      "NAV Progression — Rebased to 100",
  "data": {
    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "series": [
      { "name": "Growth",   "values": [100, 102.4, 105.1, 103.8, 107.2, 110.6, 113.1, 111.8, 115.4, 118.2, 120.1, 122.4] },
      { "name": "Balanced", "values": [100, 101.4, 103.2, 102.3, 104.8, 107.1, 109.0, 108.2, 111.1, 113.4, 114.8, 116.6] }
    ]
  }
}
```

The number of values in each series must equal the number of labels.

Two optional style flags control decorations:

```json
{
  "type":       "chart",
  "chart_type": "line",
  "style": {
    "show_points": true,
    "show_area":   true
  },
  "data": { ... }
}
```

| Flag | Default | Effect |
|---|---|---|
| `show_points` | `false` | Show a filled circle marker at each data point. |
| `show_area` | `false` | Fill the area below each line with a semi-transparent tint. |

---

## Pie chart

Single data series. Values are segment sizes (they do not need to sum to 100 — matplotlib normalises them). Each wedge has a **leader line** connecting it to a label showing the segment name and percentage outside the chart.

```json
{
  "type":       "chart",
  "chart_type": "pie",
  "title":      "Strategic Asset Allocation",
  "width":      "65%",
  "align":      "center",
  "style":      { "height_ratio": 0.9 },
  "data": {
    "labels": ["Global Equities", "Fixed Income", "Alternatives", "Real Assets", "Cash"],
    "series": [
      { "values": [45, 30, 15, 5, 5] }
    ]
  }
}
```

`"name"` is not used on pie series since there is only one. Set `"height_ratio"` to `0.9` or higher to give the leader-line labels enough room.

---

## Donut chart

Identical to `pie` but with a hollow centre. The hole size is controlled by `donut_ratio` (0–1, default `0.5`), where `0.5` means the inner radius is half the outer radius.

```json
{
  "type":       "chart",
  "chart_type": "donut",
  "title":      "Strategic Asset Allocation",
  "width":      "65%",
  "align":      "center",
  "style": {
    "height_ratio": 1.0,
    "donut_ratio":  0.45
  },
  "data": {
    "labels": ["Global Equities", "Fixed Income", "Alternatives", "Real Assets", "Cash"],
    "series": [
      { "values": [45, 30, 15, 5, 5] }
    ]
  }
}
```

A `height_ratio` of `1.0` (square) works well for donuts with leader-line labels — it gives more vertical room than the default `0.55`.

**`donut_ratio` guidance:**

| Value | Effect |
|---|---|
| `0.3` | Thin ring — inner circle is 30% of outer radius |
| `0.5` | Standard donut (default) |
| `0.65` | Wide ring — only a narrow band of colour |

---

## Label and leader line behaviour (pie and donut)

Both `pie` and `donut` use the same external label placement. For each wedge:

1. A short line extends radially from the wedge edge.
2. The line bends at an elbow and ends with a short horizontal segment.
3. The segment name and percentage (`"Label\n25.0%"`) are placed at the end.

Labels on the right half of the chart are left-aligned; labels on the left half are right-aligned. There is no separate legend for pie or donut charts — the leader lines serve that purpose. Setting `"legend": true` in the style has no effect on these chart types.

---

## Data format

```json
"data": {
  "labels": ["Label 1", "Label 2", "Label 3"],
  "series": [
    { "name": "Series A", "values": [10.0, 20.5, 15.3] },
    { "name": "Series B", "values": [8.1,  18.2, 12.7] }
  ]
}
```

- `labels` — array of strings, one per group (bar/line) or segment (pie/donut).
- `series` — array of series objects. Bar and line support multiple series; pie and donut use only the first.
- `name` — series label, shown in the legend for bar and line charts. Use `""` to suppress the legend entry.
- `values` — array of numbers. Must be the same length as `labels`.
- `color` — optional per-series colour override (`"#rrggbb"`). Takes precedence over the `colors` cycle. Useful for pairing a mandate with a muted tone of the same hue for its benchmark.
- `line_style` — optional, line charts only: `"solid"` (default), `"dashed"`, `"dotted"`, or `"dashdot"`. The classic use is a dashed grey benchmark against solid portfolio lines.

```json
{ "name": "Benchmark", "values": [100, 101.2, 102.8], "color": "#888888", "line_style": "dashed" }
```

---

## Styling charts

Set global defaults in `chart_style` (top-level) and override per-chart in the element's `"style"` block. Both are shallow merges — specify only what you want to change.

### Global defaults

```json
"chart_style": {
  "colors":       ["#003366", "#c69b3a", "#4a8b6e"],
  "grid_color":   "#e8e8e8",
  "height_ratio": 0.5
}
```

### Per-chart override

```json
{
  "type":       "chart",
  "chart_type": "donut",
  "style": {
    "colors":       ["#003366", "#2e6da4"],
    "donut_ratio":  0.5,
    "height_ratio": 1.0
  },
  "data": { ... }
}
```

### All `chart_style` keys

| Key | Default | Description |
|---|---|---|
| `colors` | `["#1a1a2e", "#2e6da4", "#c69b3a", "#4a8b6e", "#8b5a6e", "#4b8fcf"]` | Ordered colour list. Series assigned by index; cycles if more series than colours. |
| `background` | `"#ffffff"` | Chart and axes background colour. |
| `grid` | `true` | Horizontal grid lines on bar and line charts. No effect on pie or donut. |
| `grid_color` | `"#eeeeee"` | Grid line colour. |
| `grid_style` | `"solid"` | Grid line style: `"solid"`, `"dashed"`, `"dotted"`, or `"dashdot"`. |
| `axis_color` | `"#cccccc"` | Colour of the bottom and left axis lines. |
| `tick_size` | `9` | Axis tick label font size. The legend uses this size too. |
| `tick_color` | `"#555555"` | Axis tick label colour. |
| `title_size` | `11` | Chart title font size. |
| `title_color` | `"#222222"` | Chart title colour. |
| `legend` | `true` | Show a legend when series have non-empty names. No effect on pie or donut. |
| `legend_position` | `"best"` | `"best"` (matplotlib picks a spot inside the plot), `"top"` (horizontal row between title and plot), `"bottom"`, or `"right"`. |
| `bar_width` | `0.7` | Total grouped bar width as a fraction of slot width (0–1). |
| `line_width` | `2.0` | Line width in points for line charts. |
| `show_points` | `false` | Show circle markers at each data point on line charts. |
| `marker_size` | `4` | Marker size when `show_points` is on. |
| `show_area` | `false` | Fill the area below each line with a semi-transparent tint. The fill extends down to zero, so this suits zero-anchored data — avoid it for series that hover far above zero (e.g. NAV rebased to 100). |
| `area_alpha` | `0.07` | Opacity of the area fill (0–1). |
| `show_values` | `false` | Bar charts only: print each bar's value above it. Best with a single series or few bars — grouped charts with many bars get crowded. |
| `value_format` | `"{:g}"` | Python format string for `show_values` labels, e.g. `"{:.1f}%"`. |
| `y_prefix` | `""` | Text before each y-axis tick label, e.g. `"£"`. |
| `y_suffix` | `""` | Text after each y-axis tick label, e.g. `"%"`. |
| `dpi` | `150` | Render resolution. 150 is appropriate for print-quality PDFs. |
| `height_ratio` | `0.55` | Chart height as a multiple of width. `1.0` = square. |
| `donut_ratio` | `0.5` | Inner hole radius as a fraction of outer radius. Only used by `donut`. |
| `space_before` | `12` | Space above the chart in points. |
| `space_after` | `12` | Space below the chart in points. |

---

## Chart width and alignment

```json
{
  "type":       "chart",
  "chart_type": "donut",
  "width":      "60%",
  "align":      "center"
}
```

- `width` accepts `"100%"` (default), a percentage like `"60%"`, or an absolute value like `"300pt"`.
- `align` controls horizontal alignment when `width` is less than 100%.
- Height is derived from `width × height_ratio` before rendering, then corrected to the actual rendered image height so titles and leader lines are never clipped.

---

## Practical patterns

**Compact side annotation** — narrow chart beside a table:
```json
{ "type": "chart", "chart_type": "bar", "width": "65%", "align": "left", "data": { ... } }
```

**Two charts on one page** — reduce `height_ratio` so both fit:
```json
{ "type": "chart", "chart_type": "line", "style": { "height_ratio": 0.4 }, "data": { ... } }
{ "type": "spacer", "height": 8 }
{ "type": "chart", "chart_type": "bar",  "style": { "height_ratio": 0.4 }, "data": { ... } }
```

**Matching brand colours** — override the default palette across all charts:
```json
"chart_style": {
  "colors": ["#003366", "#c69b3a", "#4a8b6e", "#005599", "#8b5a6e"]
}
```

**Performance vs benchmark** — dashed grey benchmark, horizontal legend above the plot, percentage axis:
```json
{
  "type":       "chart",
  "chart_type": "line",
  "title":      "Cumulative Return",
  "style":      { "legend_position": "top", "y_suffix": "%", "show_points": true },
  "data": {
    "labels": ["Jan", "Feb", "Mar", "Apr"],
    "series": [
      { "name": "Portfolio", "values": [1.2, 2.8, 2.1, 3.9] },
      { "name": "Benchmark", "values": [0.9, 2.1, 1.8, 3.0], "color": "#888888", "line_style": "dashed" }
    ]
  }
}
```

**Labelled single-series bar** — value on each bar, no legend needed:
```json
{
  "type":       "chart",
  "chart_type": "bar",
  "title":      "Risk Contribution by Asset Class",
  "style": {
    "show_values":  true,
    "value_format": "{:.1f}%",
    "y_suffix":     "%",
    "legend":       false
  },
  "data": { ... }
}
```

**Asset allocation donut** — square, centred, moderate hole:
```json
{
  "type":       "chart",
  "chart_type": "donut",
  "width":      "70%",
  "align":      "center",
  "style": { "height_ratio": 1.0, "donut_ratio": 0.45 },
  "data": {
    "labels": ["Equities", "Bonds", "Alternatives", "Cash"],
    "series": [{ "values": [55, 30, 10, 5] }]
  }
}
```

---

## Limitations

- **Pie and donut use only the first series.** Additional series in `data.series` are silently ignored.
- **No horizontal bars.** Bars are always vertical.
- **No stacked bars.** Multiple series are always grouped (side-by-side).
- **No axis titles or limits.** Axis limits use matplotlib's automatic range; there is no named y-axis label. Tick text can be decorated with `y_prefix`/`y_suffix`, but not reformatted beyond that.
- **No interactive elements.** Charts are static images embedded in the PDF.
- **Leader line overlap on crowded charts.** When a pie or donut has many small segments, the external labels may overlap. Reduce the number of segments (merge small values into "Other"), increase `height_ratio`, or increase `width` to give the labels more room.
