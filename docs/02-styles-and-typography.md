# Styles & Typography

pdfgen uses **named paragraph styles**. Every piece of text — headings, body copy, captions, table cells — is rendered using one of these styles. You configure the styles once, and every element that references them picks up the change automatically.

---

## Built-in styles

These styles exist in `defaults.json` and are always available.

| Name | Used by | Default appearance |
|---|---|---|
| `body` | `paragraph` elements (default) | Vera 11pt, #333333, 16pt leading |
| `h1` | `heading level: 1` | Vera-Bold 24pt, #1a1a2e, 28pt leading |
| `h2` | `heading level: 2` | Vera-Bold 18pt, #1a1a2e (extends h1) |
| `h3` | `heading level: 3` | Vera-Bold 14pt, #1a1a2e (extends h1) |
| `caption` | `paragraph style: "caption"`, image captions | Vera 9pt, #888888 (extends body) |
| `toc_h1` | TOC entries at level 1 | body, bold |
| `toc_h2` | TOC entries at level 2 | body, 16pt left indent |
| `toc_h3` | TOC entries at level 3 | body, 10pt, 32pt left indent |

---

## Overriding styles

Include a `"styles"` block in your document. Only the properties you specify are changed — all others are inherited from the default.

```json
"styles": {
  "h1": { "color": "#003366" },
  "h2": { "color": "#005599" },
  "body": { "size": 10, "leading": 15 }
}
```

This changes h1 to Oxford Navy and adjusts body to 10pt — font, spacing, and every other property remain at their default values.

---

## Style properties

| Property | Type | Description |
|---|---|---|
| `font` | string | Font name. The built-in default is `Vera` (embedded, PDF/UA-safe). Standard PDF fonts (`Helvetica`, `Times-Roman`, etc.) are available but not embedded. Custom TTFs must be registered in `fonts`. |
| `size` | number | Font size in points. |
| `leading` | number | Line height in points. Rule of thumb: `size × 1.4` for body, `size × 1.15` for headings. |
| `color` | hex string | Text colour as `"#rrggbb"`. |
| `space_before` | number | Whitespace in points before the paragraph. |
| `space_after` | number | Whitespace in points after the paragraph. |
| `left_indent` | number | Left indent in points. |
| `right_indent` | number | Right indent in points. |
| `alignment` | string | `"left"` (default), `"center"`, `"right"`, `"justify"`. |

---

## The `extends` chain

Styles can inherit from other styles using `"extends"`. The child style starts with all properties of the parent, then applies its own overrides.

```json
"styles": {
  "callout": {
    "extends":    "body",
    "color":      "#003366",
    "left_indent": 24,
    "size":       10
  }
}
```

`callout` inherits font, leading, spacing, and alignment from `body`, then overrides colour, indent, and size.

Chains can be as deep as you like (`callout_bold` extends `callout` extends `body`), but circular chains (`a` extends `b`, `b` extends `a`) will raise an error at render time.

The built-in styles already use `extends` internally:

```
h1 ← h2 ← (body of h2 definition)
h1 ← h3
body ← caption
body ← toc_h1
body ← toc_h2
body ← toc_h3
```

---

## Defining custom styles

Add any new name to the `styles` block. Reference it in content elements via `"style": "your_name"`.

```json
"styles": {
  "disclaimer": {
    "extends":   "caption",
    "alignment": "justify",
    "size":      8
  },
  "pullquote": {
    "extends":     "body",
    "size":        14,
    "color":       "#003366",
    "left_indent":  24,
    "right_indent": 24,
    "space_before": 16,
    "space_after":  16
  }
}
```

Use in content:

```json
{ "type": "paragraph", "text": "Important note.", "style": "disclaimer" }
{ "type": "paragraph", "text": "Markets moved sharply.", "style": "pullquote" }
```

---

## Inline markup

ReportLab's paragraph markup is supported inside any `"text"` value. Mix it freely.

| Tag | Effect | Example |
|---|---|---|
| `<b>text</b>` | Bold | `<b>important</b>` |
| `<i>text</i>` | Italic | `<i>see note below</i>` |
| `<u>text</u>` | Underline | `<u>§ 4.2</u>` |
| `<br/>` | Line break within paragraph | `Line one<br/>Line two` |
| `<font color="#cc0000">text</font>` | Inline colour | `<font color="#cc0000">alert</font>` |
| `<font size="9">text</font>` | Inline size override | `<font size="9">footnote</font>` |
| `<super>text</super>` | Superscript | `10<super>th</super>` |
| `<sub>text</sub>` | Subscript | `H<sub>2</sub>O` |

Tags can be nested:

```json
{
  "type": "paragraph",
  "text": "Returns of <b><font color=\"#003366\">+12.4%</font></b> exceeded the benchmark."
}
```

> **Note:** JSON requires double quotes inside strings to be escaped as `\"`. All HTML attribute values above use `\"` when embedded in JSON.

---

## Custom fonts (TTF)

Register a font family in the `fonts` array. Paths are resolved relative to the JSON file location.

```json
"fonts": [
  {
    "name":       "Lato",
    "regular":    "fonts/Lato-Regular.ttf",
    "bold":       "fonts/Lato-Bold.ttf",
    "italic":     "fonts/Lato-Italic.ttf",
    "bold_italic": "fonts/Lato-BoldItalic.ttf"
  }
],
"styles": {
  "body":    { "font": "Lato" },
  "h1":      { "font": "Lato", "color": "#003366" },
  "caption": { "font": "Lato" }
}
```

Once registered, use the `"name"` value wherever a `"font"` property appears.

**Variant fallback:** If you only register `"regular"`, the renderer uses it for bold, italic, and bold-italic too (no fake-bold/fake-italic from ReportLab — just no style change). Register all four variants for full inline markup support.

---

## Typography tips

**Leading (line height):**
- Body text: `size × 1.4` to `size × 1.5` (e.g. 11pt → 16pt leading)
- Headings: `size × 1.15` to `size × 1.2` (e.g. 24pt → 28pt leading)
- Too-tight leading makes dense body copy hard to read; too-loose heading leading looks amateurish.

**Space before/after:**
- `space_before` on headings creates visual separation between sections
- `space_after` on body controls paragraph rhythm
- Don't use spacer elements to fake spacing between paragraphs — use `space_after` on the style instead

**Justified text:**
- `"alignment": "justify"` can look clean in wide columns but create ugly rivers of whitespace in narrow columns (e.g. inside table cells). Use `"left"` for cell content.

**Colour conventions used in defaults:**
- `#1a1a2e` — deep navy (headings)
- `#333333` — near-black (body)
- `#888888` — mid-grey (captions, metadata)
