# Defaults Reference

This is the complete `defaults.json` with every key annotated. Your document is deep-merged on top of this — you only need to include the keys you want to change.

---

```jsonc
{
  // ── Document metadata & page layout ──────────────────────────────────────
  "document": {
    "title":   "",           // Written to PDF metadata (not rendered in layout)
    "author":  "",           // Written to PDF metadata
    "subject": "",           // Written to PDF metadata
    "keywords": [],          // Array of strings → written to PDF keywords field

    "page": {
      "size":        "A4",   // "A4" | "LETTER" | "LEGAL"
      "orientation": "portrait", // "portrait" | "landscape"
      "margins": {
        "top":    72,        // Points (1pt = 1/72 inch). 72 = 1 inch.
        "bottom": 72,
        "left":   72,
        "right":  72
      }
    }
  },

  // ── Custom font families ──────────────────────────────────────────────────
  // Each entry registers a TTF font family. Paths relative to the JSON file.
  "fonts": [],
  // Example entry:
  // { "name": "Calibri", "regular": "fonts/Calibri.ttf", "bold": "...", ... }

  // ── Named paragraph styles ────────────────────────────────────────────────
  "styles": {
    // Base heading style. h2 and h3 extend this.
    "h1": {
      "font":         "Helvetica-Bold",
      "size":         24,
      "color":        "#1a1a2e",
      "leading":      28,
      "space_before": 24,
      "space_after":  8,
      "left_indent":  0,
      "right_indent": 0,
      "alignment":    "left"
    },
    "h2": {
      "extends":      "h1",  // Inherits font, color, alignment from h1
      "size":         18,
      "leading":      22,
      "space_before": 18,
      "space_after":  8,
      "left_indent":  0,
      "right_indent": 0
    },
    "h3": {
      "extends":      "h1",
      "size":         14,
      "leading":      18,
      "space_before": 14,
      "space_after":  8,
      "left_indent":  0,
      "right_indent": 0
    },
    // Base body style. caption, table_header, and toc_h* extend this.
    "body": {
      "font":         "Helvetica",
      "size":         11,
      "color":        "#333333",
      "leading":      16,
      "space_before": 0,
      "space_after":  8,
      "left_indent":  0,
      "right_indent": 0,
      "alignment":    "left"
    },
    "caption": {
      "extends":      "body",
      "size":         9,
      "color":        "#888888",
      "space_before": 0,
      "space_after":  4,
      "left_indent":  0,
      "right_indent": 0
    },
    "table_header": {
      "extends":      "body",
      "font":         "Helvetica-Bold",
      "color":        "#ffffff",
      "space_before": 0,
      "space_after":  0,
      "left_indent":  0,
      "right_indent": 0
    },
    // TOC entry styles — one per depth level
    "toc_h1": {
      "extends":      "body",
      "font":         "Helvetica-Bold",
      "space_before": 4,
      "space_after":  2,
      "left_indent":  0,
      "right_indent": 0
    },
    "toc_h2": {
      "extends":      "body",
      "space_before": 0,
      "space_after":  2,
      "left_indent":  16,
      "right_indent": 0
    },
    "toc_h3": {
      "extends":      "body",
      "size":         10,
      "space_before": 0,
      "space_after":  1,
      "left_indent":  32,
      "right_indent": 0
    }
  },

  // ── Cover page ────────────────────────────────────────────────────────────
  // Cover is only rendered when cover.title is non-empty.
  "cover": {
    "title":            "",       // Main cover title
    "subtitle":         "",       // Smaller line below title
    "author":           "",       // Bottom-left
    "date":             "",       // Bottom-right
    "logo":             null,     // Path to logo. Triggers split design when set.
    "logo_align":       "left",   // Currently unused — logo is always centred in band
    "background_color": "#1a1a2e",// Solid background (used when background_image is null)
    "background_image": null,     // Path to image. Scales to fill the page. Replaces background_color.
    "title_color":      "#ffffff",
    "subtitle_color":   "#cccccc" // Also used for author and date text
  },

  // ── Header (content pages only, not cover) ────────────────────────────────
  "header": {
    "logo":      null,  // Path to logo. Replaces 'left' text when set.
    "left":      "",    // Left zone text
    "center":    "",    // Center zone text
    "right":     "",    // Right zone text
    "separator": true   // Thin horizontal line below header
  },

  // ── Footer (content pages only) ───────────────────────────────────────────
  "footer": {
    "left":      "",    // Left zone text
    "center":    "",    // Center zone text
    "right":     "",    // ⚠ Reserved for automatic page number — do not set
    "separator": true   // Thin horizontal line above footer
  },

  // ── Global table defaults ─────────────────────────────────────────────────
  // Per-table 'style' overrides these shallowly (element wins).
  "table_style": {
    "header_background": "#1a1a2e", // Header row background
    "header_color":      "#ffffff", // Header row text colour
    "header_font":       "Helvetica-Bold",
    "header_align":      "left",    // Header text alignment
    "body_font":         "Helvetica",
    "body_color":        "#333333",
    "font_size":         10,        // Points, applies to all cells
    "cell_padding":      8,         // Points, all four sides
    "alternate_rows":    true,      // Alternate row background colours
    "alternate_color":   "#f5f7fa", // Colour of alternate rows (white is the other)
    "grid_color":        "#dddddd", // Horizontal rules + outer border
    "grid_thickness":    0.5,       // Points
    "align":             "left",    // Default body cell alignment
    "full_width":        true,      // Scale columns to fill content width
    "space_before":      12,        // Points
    "space_after":       12
  },

  // ── Global chart defaults ─────────────────────────────────────────────────
  // Per-chart 'style' overrides these shallowly.
  "chart_style": {
    "colors": [
      "#1a1a2e",  // deep navy (series 1)
      "#2e6da4",  // steel blue (series 2)
      "#c69b3a",  // amber (series 3)
      "#4a8b6e",  // sage green (series 4)
      "#8b5a6e",  // mauve (series 5)
      "#4b8fcf"   // sky blue (series 6)
    ],
    "background":   "#ffffff",  // Chart and axes background
    "grid":         true,       // Horizontal grid lines (bar and line only)
    "grid_color":   "#eeeeee",
    "grid_style":   "solid",    // solid | dashed | dotted | dashdot
    "axis_color":   "#cccccc",  // Bottom/left axis line colour
    "tick_size":    9,          // Tick label font size (legend matches)
    "tick_color":   "#555555",  // Tick label colour
    "title_size":   12,         // Chart title font size (left-aligned on bar/line)
    "title_color":  "#1a1a2e",  // Chart title colour
    "legend":       true,       // Show legend when series have names
    "legend_position": "best",  // best | top | bottom | right
    "bar_width":    0.7,        // 0–1; total group width as fraction of slot
    "line_width":   2.0,        // Points
    "show_points":  false,      // Show circle markers at each data point (line only)
    "show_area":    false,      // Fill area below each line with a tint (line only)
    "area_alpha":   0.07,       // Opacity of the area fill (0–1)
    "marker_size":  4,          // Marker size when show_points is on
    "show_values":  false,      // Print each bar's value above it (bar only)
    "value_format": "{:g}",     // Format string for show_values, e.g. "{:.1f}%"
    "y_prefix":     "",         // Text before y-axis tick labels, e.g. "£"
    "y_suffix":     "",         // Text after y-axis tick labels, e.g. "%"
    "dpi":          300,        // Render resolution (print quality)
    "height_ratio": 0.55,       // Chart height = width × height_ratio
    "donut_ratio":  0.5,        // Inner hole radius as fraction of outer (donut only)
    "space_before": 12,
    "space_after":  12
  },

  // ── Pagination ────────────────────────────────────────────────────────────
  "pagination": true,  // false suppresses "Page X of Y" stamp

  // ── Content ───────────────────────────────────────────────────────────────
  // Array of content elements. User array replaces this entirely (no merge).
  "content": []
}
```

---

## Style property reference

Available in any entry under `"styles"`:

| Property | Type | Description |
|---|---|---|
| `font` | string | Font family name |
| `size` | number | Font size in pt |
| `leading` | number | Line height in pt |
| `color` | hex string | Text colour |
| `space_before` | number | Space above paragraph in pt |
| `space_after` | number | Space below paragraph in pt |
| `left_indent` | number | Left indent in pt |
| `right_indent` | number | Right indent in pt |
| `alignment` | string | `"left"` / `"center"` / `"right"` / `"justify"` |
| `extends` | string | Name of another style to inherit from |
