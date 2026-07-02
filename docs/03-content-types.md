# Content Types

The `"content"` array is a sequence of element objects. Each object must have a `"type"` key. Unknown types are silently ignored.

---

## `heading`

A section heading at levels 1–3.

```json
{ "type": "heading", "level": 1, "text": "Executive Summary" }
{ "type": "heading", "level": 2, "text": "Key Findings" }
{ "type": "heading", "level": 3, "text": "Fixed Income Attribution" }
```

| Property | Required | Default | Description |
|---|---|---|---|
| `level` | no | `1` | Heading level 1–3. Maps to styles `h1`, `h2`, `h3`. |
| `text` | yes | — | Heading text. Inline markup (`<b>`, `<i>`) is supported. |

Headings are **automatically registered** with any `toc` element in the document — you do not need to mark them manually.

---

## `paragraph`

Body text. The workhorse element.

```json
{ "type": "paragraph", "text": "Portfolio alpha of <b>+2.4%</b> was driven by sector selection." }
```

```json
{
  "type":  "paragraph",
  "text":  "All regulatory limits were respected throughout the period.",
  "style": "disclaimer"
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `text` | yes | — | Paragraph text. Full inline markup supported. |
| `style` | no | `"body"` | Name of a style from the `styles` block. |

---

## `spacer`

Inserts vertical whitespace. Use sparingly — prefer `space_before`/`space_after` in style definitions for structural spacing; use `spacer` only for one-off adjustments.

```json
{ "type": "spacer", "height": 24 }
```

| Property | Required | Default | Description |
|---|---|---|---|
| `height` | no | `12` | Height in points. |

---

## `rule`

A horizontal dividing line.

```json
{ "type": "rule" }
```

```json
{
  "type":        "rule",
  "color":       "#003366",
  "thickness":   1.5,
  "space_before": 12,
  "space_after":  12
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `color` | no | `"#cccccc"` | Line colour as `"#rrggbb"`. |
| `thickness` | no | `0.5` | Line thickness in points. |
| `space_before` | no | `6` | Space before the rule in points. |
| `space_after` | no | `6` | Space after the rule in points. |

---

## `page_break`

Forces the next content onto a new page.

```json
{ "type": "page_break" }
```

No properties. Use at natural section boundaries — the renderer handles all other pagination automatically.

---

## `list`

A bullet or numbered list.

```json
{
  "type":  "list",
  "style": "bullet",
  "items": [
    "Portfolio alpha: +2.4% vs benchmark",
    "Maximum drawdown: −1.8%",
    "Sharpe ratio improved from 0.82 to 1.04"
  ]
}
```

```json
{
  "type":  "list",
  "style": "numbered",
  "items": [
    "Investment grade: 72% of fixed income allocation",
    "High yield: 18% — within the 25% strategic ceiling",
    "Cash and near-cash: 10%"
  ]
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `style` | no | `"bullet"` | `"bullet"` for bullet points, `"numbered"` for 1. 2. 3. |
| `items` | yes | — | Array of strings. Each string is a list item. Inline markup is supported in items. |

**Limitations:**
- Nested lists are not currently supported.
- Items use the `body` style — there is no per-list style override.

---

## `image`

Embeds a raster image (PNG or JPEG).

```json
{
  "type":  "image",
  "src":   "assets/chart.png",
  "width": "80%",
  "align": "center"
}
```

```json
{
  "type":    "image",
  "src":     "assets/signature.png",
  "width":   "150pt",
  "align":   "left",
  "caption": "Signed by the Chief Investment Officer, 30 June 2026."
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `src` | yes | — | Path to the image file (resolved relative to the JSON file), or an inline base64 data URI. |
| `width` | no | `"100%"` | `"100%"` fills the content width. `"50%"` is half. `"200pt"` is an explicit point value. Fractional percentages (`"66.7%"`) are supported. |
| `align` | no | `"left"` | `"left"`, `"center"`, or `"right"`. |
| `caption` | no | none | Caption text rendered below the image using the `caption` style. |

**Height** is always calculated automatically to preserve the image's aspect ratio. You cannot set an explicit height.

**Path resolution:** Paths are resolved relative to the JSON file's directory, not the working directory from which you run pdfgen. A path like `"assets/logo.png"` works if `assets/` is a sibling of your JSON file.

**Inline base64 images:** Instead of a path, `src` may carry the image itself as a data URI — useful when the JSON is sent to the [HTTP API](10-lambda-api.md) and there is no shared filesystem:

```json
{
  "type": "image",
  "src":  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "alt":  "Quarterly performance chart",
  "width": "80%"
}
```

Supported types are `image/png`, `image/jpeg`, and `image/gif`. A malformed base64 payload raises an error (it is not silently omitted). Any image field accepts a data URI, including `cover.logo`, `cover.background_image`, and `header.logo`.

**Missing files:** If the image file is not found, the element is silently omitted (no crash). Check the path if an image is missing.

---

## `table`

A tabular data block. See [Tables](04-tables.md) for the full reference.

```json
{
  "type":          "table",
  "headers":       ["Fund", "Return YTD", "Volatility"],
  "column_widths": ["50%", "25%", "25%"],
  "column_align":  ["left", "right", "right"],
  "rows": [
    ["Acme Growth",   "+8.4%", "9.1%"],
    ["Acme Balanced", "+5.2%", "6.3%"]
  ]
}
```

---

## `chart`

A bar, line, or pie chart rendered via matplotlib. See [Charts](05-charts.md) for the full reference.

```json
{
  "type":       "chart",
  "chart_type": "bar",
  "title":      "Quarterly Returns (%)",
  "width":      "100%",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "series": [
      { "name": "Portfolio",  "values": [3.2, 4.8, 2.9, 5.1] },
      { "name": "Benchmark",  "values": [2.1, 3.6, 2.4, 4.0] }
    ]
  }
}
```

---

## `toc`

Auto-generated table of contents. Must appear **before** the content it indexes — place it near the top of `"content"`, usually after the cover and before the first heading.

```json
{ "type": "toc", "title": "Contents", "depth": 2 }
```

```json
{ "type": "toc" }
```

| Property | Required | Default | Description |
|---|---|---|---|
| `title` | no | none | Heading rendered above the TOC (uses `h1` style). The title itself does **not** appear as a TOC entry. |
| `depth` | no | `2` | Maximum heading level to include. `1` = h1 only. `2` = h1 and h2. `3` = all three levels. |

**How it works:** When a `toc` element is present, the document is built in two passes (`multiBuild`). The first pass records which page each heading lands on; the second pass renders the TOC with accurate page numbers. Page number accuracy is guaranteed regardless of how much the TOC itself changes the layout between passes.

**Typical usage:**

```json
"content": [
  { "type": "toc",        "title": "Contents", "depth": 2 },
  { "type": "page_break" },
  { "type": "heading",   "level": 1, "text": "Executive Summary" },
  ...
]
```

Always follow the `toc` with a `page_break` so content starts on a fresh page.

---

## Combining elements

Elements are rendered in order. Any combination is valid — you can mix headings, paragraphs, tables, charts, images, and lists freely.

**Typical report structure:**

```json
"content": [
  { "type": "toc",        "title": "Contents", "depth": 2 },
  { "type": "page_break" },

  { "type": "heading",   "level": 1, "text": "Executive Summary" },
  { "type": "paragraph", "text": "Summary text..." },

  { "type": "heading",   "level": 2, "text": "Key Findings" },
  { "type": "list",      "style": "bullet", "items": ["Finding one", "Finding two"] },

  { "type": "rule" },

  { "type": "heading",   "level": 1, "text": "Performance" },
  { "type": "paragraph", "text": "Commentary..." },
  {
    "type":       "chart",
    "chart_type": "bar",
    "title":      "Quarterly Returns",
    "data":       { "labels": ["Q1", "Q2"], "series": [{"name": "Portfolio", "values": [3.2, 4.8]}] }
  },

  { "type": "page_break" },

  { "type": "heading", "level": 1, "text": "Portfolio Holdings" },
  {
    "type":    "table",
    "headers": ["Security", "Weight"],
    "rows":    [["Apple Inc", "3.4%"], ["Microsoft", "3.1%"]]
  },

  { "type": "spacer",    "height": 24 },
  { "type": "rule" },
  { "type": "paragraph", "text": "<i>Past performance is not indicative of future results.</i>", "style": "caption" }
]
```
