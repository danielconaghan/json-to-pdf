# Cover Page, Headers & Footers

---

## Cover page

A full-page cover is added automatically when the `cover` block contains a `title`. The cover uses a separate page template — it has no header, no footer, and no page number.

```json
"cover": {
  "title":    "Q2 2026 Investment Report",
  "subtitle": "Quarterly Performance Review",
  "author":   "Oxford Risk",
  "date":     "30 June 2026",
  "logo":     "assets/DefaultLogo.png"
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `title` | yes* | `""` | Main cover title. The cover page is only generated when this is non-empty. |
| `subtitle` | no | `""` | Smaller line below the title. |
| `author` | no | `""` | Shown at the bottom-left of the cover. |
| `date` | no | `""` | Shown at the bottom-right of the cover. |
| `logo` | no | `null` | Path to a logo image. Triggers the split cover design (see below). Resolved relative to the JSON file. |
| `background_color` | no | `"#1a1a2e"` | Background colour of the dark portion. |
| `title_color` | no | `"#ffffff"` | Title text colour. |
| `subtitle_color` | no | `"#cccccc"` | Subtitle, author, and date text colour. |

\* The cover page is only rendered when `cover.title` is a non-empty string. If you omit `title` or set it to `""`, no cover page is added.

---

## Cover design: with logo (split layout)

When `cover.logo` is set, the cover uses a **split design**:

- **Top band (220pt):** White background. The logo is centred horizontally and vertically within this band, scaled as large as possible while leaving padding on all sides.
- **Body:** Dark background (default: `#1a1a2e`). Title, subtitle, author, and date are drawn here.

```
┌─────────────────────────────────┐
│         [white band]            │
│       [OXFORD RISK LOGO]        │
│                                 │
├─────────────────────────────────┤
│                                 │
│   Q2 2026 Investment Report     │  ← title_color
│   Quarterly Performance Review  │  ← subtitle_color
│                                 │
│                                 │
│   Oxford Risk     30 June 2026  │  ← subtitle_color
└─────────────────────────────────┘
```

The white band is intentional — it gives the logo (which is typically black on white) a clean background without requiring a colour-inverted version for dark covers.

---

## Cover design: without logo (full dark)

When `cover.logo` is omitted or the file is not found, the entire page uses the background colour:

```
┌─────────────────────────────────┐
│                                 │
│                                 │
│   Q2 2026 Investment Report     │
│   Quarterly Performance Review  │
│                                 │
│                                 │
│   Oxford Risk     30 June 2026  │
└─────────────────────────────────┘
```

---

## Header

The header appears at the top of every **content page** (not the cover). It has three text zones (left, center, right) plus an optional logo and separator line.

```json
"header": {
  "logo":      "assets/DefaultLogo.png",
  "left":      "Oxford Risk",
  "center":    "Q2 2026",
  "right":     "Confidential",
  "separator": true
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `logo` | no | `null` | Path to a logo image. When set, **replaces** the `left` text. The logo is rendered at 20pt height, aligned to the text baseline. |
| `left` | no | `""` | Text in the left zone. Ignored if `logo` is set. |
| `center` | no | `""` | Text in the center zone. |
| `right` | no | `""` | Text in the right zone. |
| `separator` | no | `true` | Draw a thin horizontal line below the header. |

**Logo vs text:** `logo` and `left` are mutually exclusive — the logo takes priority. If you want both a logo and a left text label, the current design does not support this. Use `center` or `right` for any supplemental text.

**`right` is free to use** — it does not conflict with page numbers. Page numbers are stamped by the canvas in the **footer** area (bottom-right), not the header.

---

## Footer

The footer appears at the bottom of every content page. It has three text zones and an optional separator line. The page number is always drawn independently in the bottom-right, outside these zones.

```json
"footer": {
  "left":      "© Oxford Risk 2026",
  "center":    "Strictly Confidential",
  "separator": true
}
```

| Property | Required | Default | Description |
|---|---|---|---|
| `left` | no | `""` | Text in the left zone. |
| `center` | no | `""` | Text in the center zone. |
| `right` | no | `""` | Text in the right zone. **Do not use** — this position is reserved for the automatic page number. |
| `separator` | no | `true` | Draw a thin horizontal line above the footer. |

> **Do not set `footer.right`.** The automatic page number ("Page X of Y") is always stamped at the right side of the footer area. If you set `footer.right` to a text string, it will be drawn on top of the page number.

---

## Page numbers

Page numbers are automatic and always on. They are rendered in the bottom-right corner of the footer area as **"Page X of Y"** where X is the current page and Y is the total number of content pages.

- The **cover page is never numbered**, even if it is page 1 of the physical document.
- Page numbering starts at 1 on the first content page after the cover.
- "Page X of Y" is always accurate — it is computed in a two-pass build when needed.

To disable page numbers entirely:

```json
"pagination": false
```

---

## Combining cover, header, and footer

A complete page identity block:

```json
"cover": {
  "title":            "Oxford Risk — Annual Report 2026",
  "subtitle":         "Investment Performance Summary",
  "author":           "Oxford Risk Investment Management",
  "date":             "31 December 2026",
  "logo":             "assets/DefaultLogo.png",
  "background_color": "#003366",
  "title_color":      "#ffffff",
  "subtitle_color":   "#aaccff"
},

"header": {
  "logo":      "assets/DefaultLogo.png",
  "right":     "Annual Report 2026",
  "separator": true
},

"footer": {
  "left":      "© Oxford Risk Investment Management 2026",
  "center":    "Strictly Confidential — Not for Distribution",
  "separator": true
}
```

---

## Path resolution for logos

Logo paths in both `cover.logo` and `header.logo` are resolved **relative to the JSON file's directory**, not the working directory.

If your JSON file is at `reports/q2.json` and your logo is at `assets/DefaultLogo.png` (a sibling of `reports/`), reference it as:

```json
"logo": "../assets/DefaultLogo.png"
```

If the logo file is not found at the resolved path, it is silently omitted — the cover/header renders without a logo rather than crashing. Check the path if the logo is missing.

`cover.logo`, `cover.background_image`, and `header.logo` also accept inline base64 data URIs (`"data:image/png;base64,..."`) in place of a path — see [Content Types — inline base64 images](03-content-types.md#image). This is the usual form when the JSON is sent to the [HTTP API](10-lambda-api.md).
