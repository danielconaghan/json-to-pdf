# pdfgen

Render professional PDFs from a JSON file.

```bash
pdfgen report.json output.pdf
```

No layout code. No coordinate arithmetic. Describe what you want — pdfgen handles the rest.

---

## Installation

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Quickstart

```json
{
  "document": { "title": "My Report" },
  "cover": {
    "title":    "My Report",
    "subtitle": "Q2 2026",
    "author":   "Oxford Risk",
    "date":     "1 July 2026"
  },
  "content": [
    { "type": "heading",   "level": 1, "text": "Executive Summary" },
    { "type": "paragraph", "text": "Performance exceeded benchmarks by 2.4%." },
    {
      "type": "table",
      "headers": ["Fund", "Return YTD", "Sharpe"],
      "rows": [
        ["Oxford Risk Growth",   "+8.4%", "1.42"],
        ["Oxford Risk Balanced", "+5.2%", "1.18"]
      ]
    }
  ]
}
```

```bash
pdfgen report.json output.pdf
```

This produces a cover page, a headed table, and automatic "Page X of Y" numbering — with no further configuration.

Prefer to stay in Python? The same pipeline is available as a function:

```python
from pdfgen.engine import render_pdf

pdf_bytes = render_pdf(config)   # config: same shape as the JSON files
```

---

## What you get by default

- Cover page with logo, title, subtitle, author, and date
- Page headers and footers with separator lines
- Automatic page numbers (cover excluded)
- Headings at three levels
- Tables with alternating rows and header repeat on page breaks
- Bar, line, pie, and donut charts
- Bullet and numbered lists
- Table of contents (accurate page numbers, multi-pass build)
- PDF bookmarks and document metadata
- PDF/UA-1 accessibility — passes veraPDF validation out of the box
- Images by file path or inline base64 data URI — no filesystem needed

Everything has a sensible default. Your JSON only needs to include the things you want to change.

---

## Customising

Override any default by including the key in your JSON. Everything else is inherited.

```json
{
  "styles": {
    "h1": { "color": "#003366", "size": 22 }
  },
  "header": {
    "logo":  "assets/logo.png",
    "right": "Confidential"
  },
  "footer": {
    "left": "© Oxford Risk 2026"
  }
}
```

To use your own fonts, register them as TTF files:

```json
{
  "fonts": [
    {
      "name":       "BrandSans",
      "regular":    "fonts/BrandSans-Regular.ttf",
      "bold":       "fonts/BrandSans-Bold.ttf",
      "italic":     "fonts/BrandSans-Italic.ttf",
      "bold_italic":"fonts/BrandSans-BoldItalic.ttf"
    }
  ],
  "styles": {
    "body": { "font": "BrandSans" },
    "h1":   { "font": "BrandSans-Bold" }
  }
}
```

---

## Running as an API (AWS Lambda)

The repo includes a service layer for deploying pdfgen as an HTTP API on AWS Lambda:

- `api/` — the Lambda handler: POST a document config JSON, receive a presigned S3 URL for the rendered PDF
- `Dockerfile` — a Lambda container image bundling the library, brand assets, and handler
- `infra/` — Terraform for the full stack: ECR, Lambda, HTTP API Gateway, output bucket ([deploy guide](infra/README.md))

```bash
make local            # run the whole stack locally (ministack emulator) + smoke test
make build            # container image
make deploy           # push to ECR + terraform apply
```

Per-document images travel inline as base64 data URIs; brand assets (fonts, logos) are bundled in the image. See [HTTP API — AWS Lambda](docs/10-lambda-api.md) for the request/response contract, configuration, and local testing.

---

## Example files

| File | Demonstrates |
|---|---|
| `examples/phase2_report.json` | Paragraphs, headings, lists, page structure |
| `examples/phase3_tables.json` | All table variants, large wrapping table |
| `examples/phase4_toc.json` | Table of contents, PDF keywords, multi-section report |
| `examples/phase5_charts.json` | Bar, line, and pie charts in a full report |

---

## Documentation

| Page | Contents |
|---|---|
| [Document Structure](docs/01-document-structure.md) | JSON envelope, page size, margins, metadata, merge rules |
| [Styles & Typography](docs/02-styles-and-typography.md) | Built-in styles, overriding, custom fonts, inline markup |
| [Content Types](docs/03-content-types.md) | All element types with full examples |
| [Tables](docs/04-tables.md) | Column widths, alignment, styling, large tables |
| [Charts](docs/05-charts.md) | Bar, line, pie; data format, multi-series, style overrides |
| [Cover, Headers & Footers](docs/06-cover-headers-footers.md) | Cover page design, header/footer zones, page numbering |
| [Defaults Reference](docs/07-defaults-reference.md) | Complete annotated defaults.json |
| [Limitations](docs/08-limitations.md) | Known constraints and workarounds |
| [Accessibility — PDF/UA-1](docs/09-accessibility-pdf-ua.md) | Compliance details, font requirements, testing with veraPDF |
| [HTTP API — AWS Lambda](docs/10-lambda-api.md) | `render_pdf()` entry point, request/response contract, container image, deployment configuration |
