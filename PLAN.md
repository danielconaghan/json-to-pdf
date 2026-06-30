# pdfgen — Project Plan

A CLI tool that renders beautifully structured PDFs from a JSON configuration.
The middle ground between htmltopdf (too unpredictable) and TCPDF (too low-level).

---

## Core Philosophy

- **JSON is the contract.** Variable substitution happens upstream — the CLI receives
  fully-resolved JSON and outputs a PDF. No templating logic inside the renderer.
- **Sensible defaults mean you only configure what you're changing.** A minimal document
  needs only `document.title` and `content`. Everything else is inherited.
- **The defaults file is also the documentation.** Users who want to know what's
  configurable just read `defaults.json`.

---

## Stack

| Layer      | Choice                  | Reason                                              |
|------------|-------------------------|-----------------------------------------------------|
| Language   | Python 3.11+            | ReportLab is the best PDF library in existence      |
| PDF engine | ReportLab (Platypus)    | Flowable layout, pagination, TOC — all built in     |
| CLI        | Click                   | Clean, composable                                   |
| Validation | jsonschema              | Validate config before rendering, clear errors      |
| Charts     | matplotlib              | Renders to image, embedded — simple and powerful    |

---

## CLI Invocation

```bash
pdfgen document.json output.pdf
```

---

## Architecture: Defaults + Deep Merge

```
defaults.json          (ships with the tool — full, complex, never edited by users)
      +
user_document.json     (as minimal or as detailed as the user needs)
      ↓
deep_merge()
      ↓
resolved_config  →  renderer  →  output.pdf
```

### Merge Rules

| Type       | Behaviour                                                          |
|------------|--------------------------------------------------------------------|
| Objects    | Deep merge — user wins on conflicts                                |
| Arrays     | User replaces entirely (`content` has no sensible default)         |
| Primitives | User wins                                                          |
| Styles     | Style *properties* deep merge into the default style (rule a)      |

**Style merge example:** `"h1": { "color": "#ff0000" }` overrides only colour;
font, size, spacing are all inherited from the default `h1`.

---

## Configuration Schema

### Minimal valid document

```json
{
  "document": { "title": "My Report" },
  "content": [
    { "type": "heading", "level": 1, "text": "Hello" },
    { "type": "paragraph", "text": "World" }
  ]
}
```

Produces: valid paginated A4 PDF, default typography, automatic page numbers.

### Full schema (all keys — this mirrors defaults.json)

```json
{
  "document": {
    "title": "Q2 Report",
    "author": "Oxford Risk",
    "subject": "Quarterly Performance",
    "keywords": ["risk", "performance"],
    "page": {
      "size": "A4",
      "orientation": "portrait",
      "margins": { "top": 72, "bottom": 72, "left": 72, "right": 72 }
    }
  },

  "fonts": [
    {
      "name": "Inter",
      "regular": "./fonts/Inter-Regular.ttf",
      "bold": "./fonts/Inter-Bold.ttf",
      "italic": "./fonts/Inter-Italic.ttf",
      "bold_italic": "./fonts/Inter-BoldItalic.ttf"
    }
  ],

  "styles": {
    "h1":      { "font": "Helvetica-Bold", "size": 24, "color": "#1a1a2e", "space_before": 24, "space_after": 8 },
    "h2":      { "extends": "h1", "size": 18, "space_before": 18 },
    "h3":      { "extends": "h1", "size": 14, "space_before": 14 },
    "body":    { "font": "Helvetica",      "size": 11, "leading": 16, "color": "#333333" },
    "caption": { "extends": "body",        "size": 9,  "color": "#888888" }
  },

  "cover": {
    "title":            "Document Title",
    "subtitle":         "",
    "author":           "",
    "date":             "",
    "logo":             null,
    "logo_align":       "left",
    "background_color": "#1a1a2e",
    "title_color":      "#ffffff",
    "subtitle_color":   "#cccccc"
  },

  "header": {
    "left":      "",
    "center":    "",
    "right":     "",
    "separator": true
  },

  "footer": {
    "left":      "",
    "center":    "",
    "right":     "",
    "separator": true
  },

  "content": []
}
```

### Notes on header/footer

- **Page numbers are automatic** — always rendered bottom-right, no configuration needed.
  Add `"pagination": false` later to disable (not in scope for Phase 1).
- **Cover page is always excluded** from headers, footers, and page numbering — it is a
  separate page template.
- The `separator` line defaults to `true` — most professional documents have it.

### Inline markup in text fields

ReportLab paragraph markup is supported in any `text` value:

```
<b>bold</b>   <i>italic</i>   <u>underline</u>
```

### Content types

| Type         | Key fields                                              |
|--------------|---------------------------------------------------------|
| `heading`    | `level` (1–3), `text`                                   |
| `paragraph`  | `text`, optional `style`                               |
| `list`       | `style` (bullet/numbered), `items: []`                 |
| `table`      | `headers`, `rows`, `column_widths`, `column_align`, `style` |
| `image`      | `src`, `width`, `align`, optional `caption`            |
| `chart`      | `chart_type`, `title`, `data`, `width`                 |
| `toc`        | `title`, `depth` (default 2)                           |
| `spacer`     | `height` (points)                                      |
| `rule`       | `color`, `thickness`                                   |
| `page_break` | (no fields)                                            |

### Table style block

Global defaults live in `table_style` (in defaults.json). Per-table `style` shallowly overrides them.

```json
{
  "type": "table",
  "headers": ["Fund", "Return", "Risk"],
  "column_widths": ["50%", "25%", "25%"],
  "column_align":  ["left", "right", "right"],
  "style": {
    "header_background": "#1a1a2e",
    "header_color":      "#ffffff",
    "alternate_rows":    true,
    "cell_padding":      8
  },
  "rows": [
    ["Alpha Fund", "12.4%", "Low"]
  ]
}
```

All `table_style` keys (global default):

| Key | Default | Notes |
|---|---|---|
| `header_background` | `#1a1a2e` | |
| `header_color` | `#ffffff` | |
| `header_font` | `Helvetica-Bold` | |
| `header_align` | `left` | |
| `body_font` | `Helvetica` | |
| `body_color` | `#333333` | |
| `font_size` | `10` | |
| `cell_padding` | `8` | applied to all four sides |
| `alternate_rows` | `true` | |
| `alternate_color` | `#f5f7fa` | |
| `grid_color` | `#dddddd` | |
| `grid_thickness` | `0.5` | |
| `align` | `left` | body cell default; overridden per-column by `column_align` |
| `space_before` | `12` | |
| `space_after` | `12` | |

### Chart data block

```json
{
  "type": "chart",
  "chart_type": "bar",
  "title": "Quarterly Performance",
  "width": "100%",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "series": [
      { "name": "Return", "values": [8, 12, 7, 15] }
    ]
  }
}
```

---

## Build Phases

### Phase 1 — Core ✓
- [x] Project scaffold (`pyproject.toml`, package structure)
- [x] `defaults.json` (full defaults file)
- [ ] JSON Schema validation _(deferred — errors surface clearly via Python for now)_
- [x] Deep merge engine (defaults + user input)
- [x] Font registration (built-ins + custom TTF)
- [x] Style resolution (including `extends` inheritance)
- [x] Page setup (size, orientation, margins)
- [x] Paragraph rendering
- [x] Heading rendering (levels 1–3)
- [x] CLI entry point (`pdfgen in.json out.pdf`)

### Phase 2 — Structure ✓
- [x] Page template (header, footer, automatic page numbers)
- [x] Cover page (separate first-page template)
- [x] `spacer`, `rule`, `page_break` content types
- [x] `list` (bullet + numbered)
- [x] `image` content type

### Phase 3 — Tables ✓
- [x] Basic table rendering
- [x] Column widths (% or pt)
- [x] Per-column alignment (`column_align` list)
- [x] Header row styling (background, colour, font)
- [x] Header repeats on page breaks (`repeatRows=1`)
- [x] Alternating row colours (`ROWBACKGROUNDS`)
- [x] Cell padding (all four sides)
- [x] Global `table_style` defaults + per-table `style` override

### Phase 4 — Document-level ✓
- [x] Table of contents (auto-generated from headings)
- [x] PDF metadata (title, author, subject, keywords)

### Phase 5 — Charts
- [ ] Bar chart
- [ ] Line chart
- [ ] Pie chart

---

## Project Structure

```
pdfgen/
├── pdfgen/
│   ├── __init__.py
│   ├── cli.py              # Click entry point
│   ├── merger.py           # Deep merge: defaults + user config
│   ├── renderer.py         # Orchestrator + paragraph/heading inline; RenderContext dataclass
│   ├── styles.py           # Style resolution + extends inheritance
│   ├── fonts.py            # TTF font family registration
│   ├── elements/
│   │   ├── __init__.py
│   │   ├── table.py        # Tables with Paragraph cells, col widths/align, style merge
│   │   ├── image.py        # Image + optional caption
│   │   ├── list_element.py # Bullet + numbered lists (NOTE: not list.py)
│   │   └── primitives.py   # spacer, rule, page_break
│   ├── templates/
│   │   ├── __init__.py
│   │   └── page.py         # NumberedCanvas, cover template, standard template,
│   │                       # all draw helpers (_draw_cover_split, _draw_header, etc.)
│   └── defaults.json       # Full default config — the hidden complex document
├── assets/
│   └── DefaultLogo.png     # Oxford Risk wordmark (2952×422, 7:1 ratio)
├── examples/
│   ├── minimal.json
│   ├── styled_report.json
│   ├── phase2_report.json
│   └── phase3_tables.json  # Full tables showcase incl. 30-row wrapping table
├── tests/
│   └── __init__.py
├── .venv/                  # Python 3.14 venv — activate before running
├── pyproject.toml
└── PLAN.md
```

**Run any example:**
```bash
.venv/bin/pdfgen examples/phase3_tables.json out.pdf
```

---

## Decisions Log

| Decision | Choice | Reason |
|---|---|---|
| Language | Python | ReportLab ecosystem |
| Variable substitution | Upstream, not in renderer | Keeps renderer pure and simple |
| Pagination | Always on by default | Universal requirement; `pagination: false` added later |
| Cover page numbering | Always excluded | Cover is a separate page template; `_is_cover` flag on canvas |
| Header separator | Default `true` | Standard in professional documents |
| Style conflict | Deep merge (rule a) | Override only what you specify, inherit the rest |
| Array conflict | User replaces | No sensible default for `content` |
| Font variants | Registered as family | Allows bold/italic to resolve automatically |
| `footer.right` | Reserved for page number | Page number always bottom-right via `NumberedCanvas`; don't set `footer.right` |
| Page template engine | `BaseDocTemplate` | Required for multiple templates (cover + standard); `SimpleDocTemplate` was Phase 1 only |
| `RenderContext` dataclass | Passed to all element builders | Avoids long argument lists; carries `doc`, `rl_styles`, `base_path` |
| Image paths | Resolved relative to JSON file | `base_path` passed from CLI via config; keeps JSON portable |
| TOC mechanism | `PDFDocTemplate` + `multiBuild` | Subclass overrides `afterFlowable` to emit `TOCEntry` notifications; `multiBuild` runs two passes so page numbers are accurate |
| TOC title heading | Not marked with `_toc_entry` | Prevents "Contents" from appearing as an entry inside the TOC it labels |
| PDF keywords | Set via `doc.keywords` (not canvas `__init__`) | `BaseDocTemplate._makeCanvas` calls `canv.setKeywords(self.keywords)` after canvas creation, overwriting anything set earlier; must set on the doc instance |
