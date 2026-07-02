# Limitations

This page documents the known constraints of pdfgen and, where possible, practical workarounds.

---

## Text and typography

### No RTL text support
Right-to-left scripts (Arabic, Hebrew, etc.) are not supported. ReportLab's core `Paragraph` class lays out text left-to-right. There is no configuration option or workaround within pdfgen.

### No variable substitution
JSON values are static strings. There is no template syntax like `{{ investor_name }}` or `$DATE`. If your documents need dynamic content, build the config programmatically and pass the dict straight to `pdfgen.engine.render_pdf()` (or write the JSON and use the CLI).

### Inline markup is limited
Paragraphs, list items, table cells, and headings support a small subset of HTML-like inline tags:

| Tag | Effect |
|---|---|
| `<b>text</b>` | Bold |
| `<i>text</i>` | Italic |
| `<u>text</u>` | Underline |
| `<br/>` | Line break |
| `<font color="#hex">text</font>` | Colour override |
| `<font size="N">text</font>` | Size override |

**Not supported:** `<span>`, `<a>`, `<sup>`, `<sub>`, `<code>`, `<strong>`, `<em>`, nested mixed markup (e.g. `<b><i>...</i></b>` — behavior is undefined in ReportLab's parser).

### No linked URLs
Inline hyperlinks are not supported. You can write a URL as plain text, but it will not be clickable. ReportLab supports link annotations at a lower level, but pdfgen does not currently expose this.

### Heading levels are fixed at 1–3
There is no `h4`, `h5`, or `h6`. If you need deeper hierarchy, use a bold paragraph or a named style to simulate a sub-heading without contributing to the TOC.

---

## Layout

### Uniform page size only
All pages in a document use the same size and orientation. You cannot mix portrait and landscape pages, or switch from A4 to LETTER mid-document.

### No multi-column layouts
Content always flows in a single column. Side-by-side columns, magazine-style layouts, and text that wraps around an image are not supported.

### Background images are cover-only
The `cover.background_image` field accepts a path to a PNG or JPEG and scales it to fill the cover page. Content pages (the pages after the cover) still have solid-white backgrounds only — a repeating or per-page background image is not supported.

### No absolute positioning
Every element is placed in document flow — height is determined by content. You cannot pin an element to a fixed position on the page (e.g. a watermark at a specific coordinate), except via the header/footer canvas areas, which are drawn at fixed positions but only support text and a single logo.

### Images have no explicit height
When you embed an `image`, height is always derived from the aspect ratio of the source file and the width you specify. You cannot override the height independently.

---

## Tables

### No cell merging (colspan / rowspan)
All cells in a table are uniform — you cannot merge cells horizontally or vertically. If you need a merged-cell layout, split the content across multiple tables or use manual spacing with `spacer` and `rule` elements.

### No per-cell styles
Style overrides (`header_background`, `body_color`, etc.) apply to entire rows or the whole table. You cannot target an individual cell with a different background, font, or alignment.

### No nested tables
A table cell cannot contain another table. For nested structures, compose the surrounding layout using multiple separate tables.

### Inline markup in cells is limited
The same inline markup constraints as paragraphs apply to cell content. Full HTML is not supported inside cells.

---

## Charts

### Pie and donut charts are single-series
Only the first series in `data.series` is used for `pie` and `donut` charts. Additional series are silently ignored.

### No stacked bars
Multiple series in a bar chart are always plotted as grouped (side-by-side) bars. Stacked bar charts are not supported.

### No horizontal bars
Bars are always vertical. Horizontal bar charts are not supported.

### No axis customisation
The y-axis label, axis limits, tick marks, tick formatting, and axis titles cannot be configured through JSON. They use matplotlib's automatic defaults. The x-axis tick rotation is automatically set to 45° when there are more than 6 labels or labels longer than 6 characters.

### No interactive elements
Charts are static PNG images embedded in the PDF. There are no tooltips, hover effects, or click interactions.

### Pie label overlap
When a pie chart has many segments, or several segments are small, the auto-placed labels on adjacent wedges can overlap. Workarounds:
- Reduce the number of segments (aggregate small values into an "Other" category).
- Increase `height_ratio` to give the wedges more area.
- Increase `width` to make the pie physically larger.
- Use a legend and leave `data.labels` empty — but note that this is not yet directly configurable through `chart_style.legend`; removing labels from the `data` block will suppress them.

### Chart height depends on title and legend
After rendering, the actual PNG height is read back from the image and used to set the element height in the PDF. This means a chart with a title and multi-row legend will be slightly taller than the same chart without them. This is correct behaviour, but it means you cannot predict the exact PDF height of a chart from `height_ratio` alone.

---

## Cover page

### Single background colour only
The cover uses one background colour for the dark area. Gradients, textures, and background images are not supported.

### White logo band is always 220pt
When a logo is set, the white band at the top is always 220 points tall. This is not configurable.

### No custom cover layout
The cover element positions (title, subtitle, author, date) are fixed. You cannot reorder them, add extra fields, or place custom content in specific positions on the cover.

---

## Fonts

### Custom fonts must be TTF files
Only TrueType (`.ttf`) font files are supported for custom font families. OpenType (`.otf`), WOFF, and WOFF2 are not supported by ReportLab.

### All four variants required for full use
Each custom font family ideally supplies four variants: `regular`, `bold`, `italic`, and `bold_italic`. You can omit variants — the font will register — but if you use bold or italic markup in text that references that font, ReportLab will fall back to a built-in font instead of the custom one.

### Default font is Vera, not a brand font
The built-in defaults use the Bitstream Vera Sans family (bundled with ReportLab). Vera is an open-source, fully embedded TrueType font chosen for PDF/UA compliance — it is not a brand typeface. Override `styles.body.font` and `styles.h1.font` in your JSON with a registered custom font to match your brand.

### No font subsetting
The entire TTF file is embedded in the PDF. For large CJK fonts this can increase file size significantly.

---

## Table of contents

### TOC must appear before headings it indexes
A `toc` element collects headings that appear **after** it in the `content` array. If the TOC is placed at the end of the document, it will be empty. Always place it before the first heading you want indexed.

### TOC requires a two-pass build
When a `toc` element is present, `multiBuild` is used — the document is built twice. For large documents with many charts, this roughly doubles build time. There is no way to skip the second pass while retaining accurate page numbers.

### TOC only indexes headings with levels 1–3
Only `heading` elements contribute to the TOC. Paragraphs formatted to look like headings (using a named style that mimics `h1`, for example) are not registered and will not appear in the TOC.

---

## PDF features

### No form fields
Interactive PDF form fields (text inputs, checkboxes, dropdowns) are not supported.

### No digital signatures
pdfgen does not produce digitally signed PDFs.

### No PDF/A compliance
The output is standard PDF 1.4. It is not certified PDF/A-1 or PDF/A-2.

### PDF/UA-1 is supported but requires embedded fonts
pdfgen produces PDF/UA-1-conformant output when all fonts used in the document are embedded TrueType fonts. The built-in Vera defaults satisfy this. If you configure custom fonts, all variants (regular, bold, italic) must be TTF files. Using non-embedded fonts such as Helvetica, Symbol, or ZapfDingbats (including via special characters that fall back to those fonts) will fail PDF/UA clause 7.21.4.1. See [Accessibility — PDF/UA-1](09-accessibility-pdf-ua.md) for full details and testing instructions.

### No encryption or password protection
Password-protected PDFs are not supported.

### No PDF layers (OCG)
Optional content groups (layers) are not supported.

### No SVG
SVG images cannot be embedded. Use PNG or JPEG. Render the SVG to PNG at the required resolution before referencing it in the JSON.

---

## General

### No streaming or chunked output
pdfgen builds the complete PDF in memory before writing to disk. Very large documents (hundreds of pages, many charts) may use significant RAM.

### Error messages are minimal
When an element fails to render (missing image, invalid chart data), it is silently skipped. No error is raised and no warning is written to the document. Check the terminal output for any Python tracebacks; missing elements mean there was likely a path or data issue.

### Content array is fully replaced, not merged
The `"content"` array in your JSON is **not** merged with the default `"content": []`. It replaces it entirely. This is expected — there are no sensible default content elements — but it is worth noting for consistency: every other top-level key is deep-merged.
