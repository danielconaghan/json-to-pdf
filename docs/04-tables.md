# Tables

Tables are one of the most configurable elements in pdfgen. A minimal table needs only `headers` and `rows`; a fully styled table can have custom colours, per-column alignment, controlled widths, and alternating row bands.

---

## Minimal table

```json
{
  "type": "table",
  "headers": ["Fund", "Return", "Risk"],
  "rows": [
    ["Acme Growth",   "+8.4%", "9.1%"],
    ["Acme Balanced", "+5.2%", "6.3%"],
    ["Acme Income",   "+3.1%", "4.2%"]
  ]
}
```

Without any additional configuration: the table fills the full content width, the header row has a dark navy background with white text, body rows alternate between white and a light grey, and all text is left-aligned.

---

## Headerless table

Omit `"headers"` entirely. The table begins directly with data rows. Useful for key–value layouts.

```json
{
  "type": "table",
  "column_widths": ["40%", "60%"],
  "rows": [
    ["Report date",   "30 June 2026"],
    ["Portfolio",     "Acme Growth"],
    ["Base currency", "GBP"],
    ["Benchmark",     "MSCI World (£)"]
  ]
}
```

---

## Column widths

Specify `"column_widths"` as a list of percentages or point values. Percentages are relative to the content width (the page width minus margins).

```json
"column_widths": ["40%", "20%", "20%", "20%"]
```

```json
"column_widths": ["200pt", "100pt", "100pt"]
```

**Rules:**
- Percentages and points can be mixed in the same table.
- If fewer widths are given than columns, the remaining columns share the leftover space equally.
- When `full_width` is `true` (the default), all column widths are scaled proportionally so the table always fills the content width — even if your percentages do not sum to exactly 100%.
- Set `full_width: false` in the per-table `style` to preserve exact widths.

```json
{
  "type":          "table",
  "column_widths": ["50%", "30%"],
  "style":         { "full_width": false },
  "rows":          [["Only 80% wide", "because full_width is off"]]
}
```

---

## Column alignment

Control text alignment per column with `"column_align"`. Specify one alignment string per column: `"left"`, `"center"`, or `"right"`.

```json
{
  "type":         "table",
  "headers":      ["Security", "Weight %", "YTD %", "VaR"],
  "column_widths":["50%", "17%", "17%", "16%"],
  "column_align": ["left", "right", "right", "right"],
  "rows": [
    ["Apple Inc",    "3.4", "+18.7", "1.2"],
    ["Microsoft",    "3.1", "+22.1", "1.4"]
  ]
}
```

Right-align all numeric columns. If `"column_align"` has fewer entries than columns, remaining columns use the default alignment (`"left"`, or whatever `table_style.align` is set to).

---

## Header alignment

Control how text inside the **header row** is aligned, independently of the body alignment:

```json
"style": { "header_align": "center" }
```

Default is `"left"`.

---

## Styling the table

Every table can carry an inline `"style"` block that overrides the global `table_style` defaults. Only the keys you specify are changed — all others remain at their defaults.

```json
{
  "type": "table",
  "headers": ["Metric", "Portfolio", "Benchmark"],
  "style": {
    "header_background": "#003366",
    "alternate_rows":    false,
    "cell_padding":      6
  },
  "rows": [...]
}
```

### All style keys

| Key | Default | Description |
|---|---|---|
| `header_background` | `"#1a1a2e"` | Header row background colour. |
| `header_color` | `"#ffffff"` | Header row text colour. |
| `header_font` | `"Helvetica-Bold"` | Header row font. |
| `header_align` | `"left"` | Header row text alignment. |
| `body_font` | `"Helvetica"` | Data row font. |
| `body_color` | `"#333333"` | Data row text colour. |
| `font_size` | `10` | Font size in points for all cells. |
| `cell_padding` | `8` | Padding in points applied to all four sides of every cell. |
| `alternate_rows` | `true` | Alternate row background between white and `alternate_color`. |
| `alternate_color` | `"#f5f7fa"` | Background colour for the alternating rows. |
| `grid_color` | `"#dddddd"` | Colour of the horizontal grid lines between data rows and the outer border. |
| `grid_thickness` | `0.5` | Thickness of grid lines in points. |
| `align` | `"left"` | Default body cell alignment (overridden per-column by `column_align`). |
| `full_width` | `true` | Scale all column widths proportionally to fill the content width. |
| `space_before` | `12` | Space before the table in points. |
| `space_after` | `12` | Space after the table in points. |

---

## Global table defaults

Set defaults for **all tables** in the document using the top-level `table_style` key. Per-table `style` overrides these shallowly.

```json
"table_style": {
  "header_background": "#003366",
  "font_size":         9,
  "cell_padding":      6
}
```

Every table in the document will use the Acme Navy header, 9pt text, and 6pt padding — unless a specific table overrides those keys.

---

## Large tables and page breaks

Tables that span multiple pages are handled automatically. When a table breaks across a page boundary:

- The header row is reprinted at the top of the continuation page automatically.
- Row backgrounds, borders, and column alignment are all preserved on every page.

You do not need to do anything special — just include all rows in one table and let the renderer paginate it.

```json
{
  "type":    "table",
  "headers": ["Security", "ISIN", "Weight %"],
  "rows":    [
    ["Apple Inc",      "US0378331005", "3.42"],
    ["Microsoft Corp", "US5949181045", "3.18"],
    ...50 more rows...
  ]
}
```

---

## No-header table with custom alternating colour

```json
{
  "type": "table",
  "column_widths": ["60%", "40%"],
  "style": {
    "alternate_rows":   true,
    "alternate_color":  "#eef2f7",
    "grid_color":       "#c8d4e0"
  },
  "rows": [
    ["Total Assets Under Management", "£5.7bn"],
    ["Number of Portfolios",          "1,240"],
    ["Average Portfolio Size",        "£4.6m"]
  ]
}
```

---

## Cell content and wrapping

All cell content is automatically wrapped if it is too long for the column width. You do not need to manage line breaks manually.

Inline markup (`<b>`, `<i>`, `<u>`) works inside cell values:

```json
"rows": [
  ["<b>Total</b>", "<b>£5.7bn</b>", "<b>100%</b>"]
]
```

---

## Practical patterns

**Financial data table (numbers right, labels left):**
```json
{
  "type":          "table",
  "headers":       ["Asset Class", "Strategic %", "Current %", "Over/Under"],
  "column_widths": ["40%", "20%", "20%", "20%"],
  "column_align":  ["left", "right", "right", "right"],
  "rows": [
    ["Global Equities", "45%", "47.2%", "+2.2%"],
    ["Fixed Income",    "30%", "28.6%", "−1.4%"],
    ["Alternatives",    "15%", "14.1%", "−0.9%"],
    ["Cash",             "5%",  "4.3%", "−0.7%"]
  ]
}
```

**Status table (centred status column):**
```json
{
  "type":          "table",
  "headers":       ["Metric", "Value", "Limit", "Status"],
  "column_widths": ["35%", "20%", "20%", "25%"],
  "column_align":  ["left", "center", "center", "center"],
  "style":         { "header_background": "#4a0072" },
  "rows": [
    ["Value-at-Risk (99%)", "1.82%", "2.50%", "✓ Pass"],
    ["Max Drawdown YTD",    "−3.1%", "−5.0%", "✓ Pass"],
    ["Tracking Error",      "2.8%",  "4.0%",  "✓ Pass"]
  ]
}
```
