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

### Phase 5 — Charts ✓
- [x] Bar chart
- [x] Line chart
- [x] Pie chart

### Phase 6 — PDF/UA Accessibility ✓ (6A + 6B complete)

PDF/UA (ISO 14289) compliance in four sub-phases, all implemented within ReportLab.
No library swap. No layout changes. The existing flow control, pagination, table splitting,
and two-pass TOC are completely untouched.

**How it works at the PDF level:**

ReportLab's `canvas._code` is a plain Python list of PDF operator strings. We can append
raw marked-content operators (`BDC`/`EMC`) around any drawing call. The `PDFCatalog` class
already has `MarkInfo` and `StructTreeRoot` as declared optional slots — setting them as
attributes is enough to include them in the output. The override point for flowables is
`drawOn(canvas, x, y)`, called by `Frame._add()` with the canvas already resolved.

---

#### Phase 6A — Document-level metadata
_Effort: 1 evening. Zero layout impact._

**What PDF/UA requires at the document level:**
- `MarkInfo` dictionary in the catalog with `Marked: true`
- `Lang` string on the catalog (e.g. `"en-GB"`)
- `DisplayDocTitle` in `ViewerPreferences` (reader shows document title, not filename)
- All existing metadata fields populated (title, author, subject — already wired)

**Files changed:**
- `renderer.py` — pass `lang` through to `PDFDocTemplate`; after `doc.build()` / `doc.multiBuild()`, set `doc._doc.Catalog.MarkInfo` and `doc._doc.Catalog.ViewerPreferences`
- `templates/doc.py` — forward `lang` kwarg to `BaseDocTemplate`

**JSON schema addition:**
```json
"document": {
  "lang": "en-GB"
}
```

**Deliverable:** PDF passes the "document metadata" checks in PAC 2024 / Adobe Acrobat checker.

---

#### Phase 6B — Tagged flowables + Artifact marking
_Effort: 1 weekend. Zero layout impact._

**What PDF/UA requires:**
- Every piece of content is either tagged with a semantic role or marked as `Artifact`
- Tagged content: paragraphs (`/P`), headings (`/H1`–`/H6`), images (`/Figure`), lists (`/L`, `/LI`, `/LBody`), captions (`/Caption`), page numbers (these become Artifact)
- Artifact content: headers, footers, decorative rules, cover background, page numbers — these are explicitly outside the reading order and require no structure entry

**New file: `pdfgen/accessibility.py`**
```
MCIDTracker         — thread-safe counter; call .next() to get a new MCID int
ElementRecord       — datatype: (mcid, role, page_number, alt_text)
AccessibilityContext — holds MCIDTracker + list[ElementRecord]; passed via RenderContext
```

**`RenderContext` change (`renderer.py`):**
Add `accessibility: AccessibilityContext` field. Instantiated at render time, passed to all element builders.

**Tagged subclasses — one per element type:**

| Class | File | Role | Notes |
|---|---|---|---|
| `TaggedParagraph` | `elements/primitives.py` | `/P` | Override `drawOn()` — prepend BDC, call super, append EMC |
| `TaggedHeading` | `elements/primitives.py` | `/H1`–`/H6` | Same; role derived from heading level |
| `TaggedImage` | `elements/image.py` | `/Figure` | BDC/EMC around image draw; `Alt` added to XObject dict |
| `TaggedCaption` | `elements/image.py` | `/Caption` | Wraps the caption paragraph beneath an image |
| `TaggedListContainer` | `elements/list_element.py` | `/L` | Wraps the whole list |
| `TaggedListItem` | `elements/list_element.py` | `/LI` + `/LBody` | One per item |
| `TaggedChart` | `elements/chart.py` | `/Figure` | BDC/EMC around chart image; `Alt` from JSON `alt` field |

**Artifact marking in `templates/page.py`:**
- `_draw_header()` — wrap entire draw block in `/Artifact <</Type /Pagination>> BDC` … `EMC`
- `_draw_footer()` — same
- `_draw_page_number()` — same
- Cover page background / logo band — mark as `/Artifact <</Type /Layout>>`

**JSON schema additions:**
```json
{ "type": "image", "src": "...", "alt": "Bar chart showing Q1–Q4 returns" }
{ "type": "chart", "alt": "Pie chart: 60% equities, 40% bonds" }
```
`alt` is required for images and charts (enforced at render time with a warning if absent).

**Deliverable:** Every content element has a role or Artifact marker. Basic screen readers
(NVDA, VoiceOver) navigate the document in reading order. PAC 2024 passes "tagged content" checks.

---

#### Phase 6C — Structure Tree (StructTreeRoot)
_Effort: 2–3 weekends. The core of PDF/UA._

**What PDF/UA requires:**
- A `StructTreeRoot` object in the catalog containing the full logical tree
- Tree shape: `Document > Section* > (H1, P, Figure, L, Table, ...)`
- A `ParentTree` (PDF number tree) mapping every MCID integer to the indirect reference of
  its parent structure element — this is how a reader resolves "MCID 7 on page 3" → "this is
  inside the second paragraph of section 1"
- `StructParents` integer on each page's dictionary — its index into the ParentTree
- A `RoleMap` if any non-standard role names are used (we use standard names so this is minimal)

**New module additions to `pdfgen/accessibility.py`:**

```
StructElement       — wraps a PDFDictionary; has role, kids list, page ref, mcid ref
StructTreeBuilder   — called after build(); walks ElementRecord list, assembles the tree

build_struct_tree(ctx, doc) → PDFDictionary
    1. Group ElementRecords by section (detected from H1/H2 level changes)
    2. Create StructElement objects for each record
    3. Build Document > Section > element hierarchy
    4. Build ParentTree: number tree where key=mcid, value=indirect ref to parent StructElement
    5. Set StructParents on each page object
    6. Return root PDFDictionary; caller sets doc._doc.Catalog.StructTreeRoot = root
```

**ReportLab PDF primitives used (all already in `pdfdoc.py`):**
- `PDFDictionary` — each struct element is one of these
- `PDFArray` — kids list
- `PDFString` — text values
- `PDFName` — role names (`/P`, `/H1`, etc.)
- `document.Reference(obj)` — registers an object, returns an indirect reference
- `PDFNumberTree` (or hand-built dict) — ParentTree

**Page-level wiring:**
After build, iterate `doc._doc.pages` and set `StructParents` integer on each page dict.
This is a single integer (the page's index into the ParentTree array of arrays).

**Deliverable:** PAC 2024 passes all structural checks. Acrobat accessibility checker passes.
NVDA and VoiceOver announce headings, navigate by landmark, read alt text on images.

---

#### Phase 6D — Table accessibility
_Effort: 1 weekend. Builds on Phase 6C._

Tables require per-cell tagging — each header cell is `/TH` with a `Scope` attribute,
each data cell is `/TD`. The containing table is `/Table`, rows are `/TR`.

**The challenge:** ReportLab's `Table.draw()` iterates cells and calls canvas drawing
methods directly — there is no single `drawOn()` we can wrap for individual cells.
The solution is to subclass `Table` and override `_drawLines()` and the cell-drawing
loop to inject BDC/EMC around each cell's content draw.

**New class: `TaggedTable` in `elements/table.py`:**

```
TaggedTable(Table)
    _draw_cell_content(canvas, cell, row, col)
        role = 'TH' if row == 0 else 'TD'
        attrs = '/Scope /Column' if row == 0 else ''
        mcid = ctx.accessibility.next()
        canvas._code.append(f'/{role} <<MCID {mcid}{attrs}>> BDC')
        super()._draw_cell_content(canvas, cell, row, col)
        canvas._code.append('EMC')
        ctx.accessibility.record(mcid, role, ...)
```

**Structure tree additions (in `accessibility.py`):**
- `StructElement` for `/Table` containing `/TR` children
- Each `/TR` contains `/TH` or `/TD` children
- Header `/TH` elements carry a `Scope` attribute dict (`/Column` for column headers)

**JSON schema:** No changes needed — the `headers` list already signals which row is the header.

**Deliverable:** Tables are fully navigable by screen readers. Column headers are announced
when a user moves to each cell. PAC 2024 table checks pass.

---

#### Phase 6 — Summary

| Sub-phase | Key output | PAC 2024 checks unlocked |
|---|---|---|
| 6A — Metadata | `MarkInfo`, `Lang`, `DisplayDocTitle` | Document info, language |
| 6B — Tagged flowables | BDC/EMC on every element, Artifacts on decorative content | Tagged content, role mapping |
| 6C — Structure tree | `StructTreeRoot`, `ParentTree`, `StructParents` | Logical structure, reading order |
| 6D — Table tags | `TH`/`TD`/`TR` per cell with `Scope` | Table headers, cell association |

**New files:**
- `pdfgen/accessibility.py` — `MCIDTracker`, `ElementRecord`, `AccessibilityContext`, `StructTreeBuilder`

**Files modified:**
- `renderer.py` — instantiate `AccessibilityContext`, pass in `RenderContext`, call `build_struct_tree()` post-render, set catalog entries
- `templates/doc.py` — forward `lang`
- `templates/page.py` — Artifact markers on header/footer/cover drawing methods
- `elements/primitives.py` — `TaggedParagraph`, `TaggedHeading`
- `elements/image.py` — `TaggedImage`, `TaggedCaption`
- `elements/chart.py` — `TaggedChart`
- `elements/list_element.py` — `TaggedListContainer`, `TaggedListItem`
- `elements/table.py` — `TaggedTable`
- `pdfgen/defaults.json` — add `document.lang` default (`"en-GB"`)

**No changes to:** `merger.py`, `styles.py`, `fonts.py`, `utils.py`, `cli.py`

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
| Accessibility library | No swap — ReportLab extended | `canvas._code` is a plain list; `addLiteral()` injects raw operators; `PDFCatalog` already has `MarkInfo`/`StructTreeRoot` slots. Zero layout risk. |
| Tagged flowable hook | `drawOn()` not `draw()` | `Frame._add()` calls `drawOn(canvas, x, y)` — canvas is already resolved and coordinates are translated. `draw()` is called internally with no canvas arg. |
| Header/footer tagging | Mark as Artifact, not tagged | PDF/UA explicitly allows decorative/pagination content to be Artifact — simpler than OBJR wiring for Form XObjects |
| StructTreeRoot | Built post-render, set on catalog | All MCIDs are known only after layout (flowables can split across pages); build the tree after `build()`/`multiBuild()` using collected `ElementRecord` list |
| Table cell tagging | Subclass `Table`, override cell draw loop | ReportLab `Table.draw()` iterates cells directly; no single `drawOn()` to wrap — must hook at cell-draw level inside the subclass |
| `alt` text | Required field on image/chart with warning | PDF/UA requires `Alt` on all Figure elements; enforced at render time with a logged warning (not a hard error) if absent |
