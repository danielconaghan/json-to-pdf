# Document Structure

Every pdfgen document is a single JSON object. The top-level keys control the document as a whole — its metadata, page setup, visual identity, and content.

```json
{
  "document":    { ... },
  "fonts":       [ ... ],
  "styles":      { ... },
  "cover":       { ... },
  "header":      { ... },
  "footer":      { ... },
  "table_style": { ... },
  "chart_style": { ... },
  "pagination":  true,
  "content":     [ ... ]
}
```

Every key is optional. A document with only `"content"` is valid — everything else falls back to the built-in defaults.

---

## `document`

Controls PDF metadata and page layout.

```json
"document": {
  "title":    "Q2 2026 Investment Report",
  "author":   "Oxford Risk",
  "subject":  "Quarterly Performance Review",
  "keywords": ["quarterly", "performance", "Oxford Risk"],
  "page": {
    "size":        "A4",
    "orientation": "portrait",
    "margins": {
      "top":    72,
      "bottom": 72,
      "left":   72,
      "right":  72
    }
  }
}
```

### `title`, `author`, `subject`

Strings written to the PDF document properties (visible in Preview → Tools → Show Inspector, or Adobe Acrobat → File → Properties). They do not appear in the rendered page layout unless you also add a `cover` block or use them in header/footer text.

### `keywords`

Array of strings. Written to the PDF `Keywords` metadata field, space- or comma-separated when stored. Useful for document management systems and search.

```json
"keywords": ["risk management", "equity", "Q2 2026"]
```

### `page.size`

Supported values: `"A4"` (default), `"LETTER"`, `"LEGAL"`.

```json
"page": { "size": "LETTER" }
```

### `page.orientation`

`"portrait"` (default) or `"landscape"`.

```json
"page": { "size": "A4", "orientation": "landscape" }
```

Landscape simply rotates the page dimensions. All margins, headers, and footers work identically.

### `page.margins`

All four margins in **points** (1 point = 1/72 inch). The default is 72pt (1 inch) on all sides, which is a standard business document margin.

Common values:
- `72` — 1 inch, standard
- `54` — 0.75 inch, slightly compact
- `36` — 0.5 inch, tight; leaves little room for headers and footers

```json
"margins": { "top": 72, "bottom": 72, "left": 72, "right": 72 }
```

> **Note:** Margins are the gap between the physical page edge and the content frame. Header and footer text is drawn *within* the margin band above and below the content frame, so very small margins can cause overlap.

---

## `fonts`

An array of custom font families to register. Each entry specifies the family name and file paths to each variant. All paths are resolved **relative to the JSON file**, not the working directory.

```json
"fonts": [
  {
    "name":       "Calibri",
    "regular":    "fonts/Calibri.ttf",
    "bold":       "fonts/CalibriBold.ttf",
    "italic":     "fonts/CalibriItalic.ttf",
    "bold_italic": "fonts/CalibriBoldItalic.ttf"
  }
]
```

Once registered, the family name (`"Calibri"`) can be used anywhere a `"font"` property appears in `styles`.

Only `"name"` and `"regular"` are required. Missing variants fall back to `"regular"`.

Available built-in fonts (no registration required): `Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique`, `Helvetica-BoldOblique`, `Times-Roman`, `Times-Bold`, `Courier`, `Courier-Bold`.

---

## `styles`

Overrides for the named paragraph styles used throughout the document. See [Styles & Typography](02-styles-and-typography.md) for full details.

```json
"styles": {
  "h1": { "color": "#003366", "size": 22 },
  "h2": { "color": "#005599" }
}
```

---

## `table_style`

Global defaults for all tables. See [Tables](04-tables.md) for full details.

```json
"table_style": {
  "header_background": "#003366",
  "alternate_rows":    true
}
```

---

## `chart_style`

Global defaults for all charts. See [Charts](05-charts.md) for full details.

```json
"chart_style": {
  "colors": ["#003366", "#c69b3a", "#4a8b6e"]
}
```

---

## `pagination`

Boolean. Default `true`. Set to `false` to suppress the automatic "Page X of Y" footer stamp on every content page.

```json
"pagination": false
```

The cover page is never numbered regardless of this setting.

---

## `content`

An array of content elements. This is the only key that does **not** deep-merge — if you provide `"content"`, your array replaces the default entirely. The default is an empty array `[]`.

```json
"content": [
  { "type": "heading", "level": 1, "text": "Executive Summary" },
  { "type": "paragraph", "text": "Performance exceeded benchmarks by 2.4%." }
]
```

See [Content Types](03-content-types.md) for all available types.

---

## Minimal valid document

```json
{
  "content": [
    { "type": "paragraph", "text": "Hello." }
  ]
}
```

Produces: one A4 page, default typography, automatic page number in the bottom right.

---

## Full document skeleton

```json
{
  "document": {
    "title":    "Report Title",
    "author":   "Oxford Risk",
    "subject":  "Subject",
    "keywords": ["keyword1", "keyword2"],
    "page": {
      "size":        "A4",
      "orientation": "portrait",
      "margins":     { "top": 72, "bottom": 72, "left": 72, "right": 72 }
    }
  },

  "fonts": [],

  "styles": {
    "h1": { "color": "#003366" }
  },

  "cover": {
    "title":    "Report Title",
    "subtitle": "Subtitle",
    "author":   "Oxford Risk",
    "date":     "30 June 2026",
    "logo":     "assets/logo.png"
  },

  "header": {
    "logo":  "assets/logo.png",
    "right": "Confidential"
  },

  "footer": {
    "left": "© Oxford Risk 2026"
  },

  "table_style": {},
  "chart_style": {},
  "pagination": true,

  "content": [
    { "type": "heading",   "level": 1, "text": "Section One" },
    { "type": "paragraph", "text": "Body copy goes here." }
  ]
}
```
