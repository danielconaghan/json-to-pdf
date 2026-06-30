from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, PageTemplate

_HEADER_FONT = "Helvetica"
_HEADER_SIZE = 9
_HEADER_COLOR = "#666666"
_SEP_COLOR = "#cccccc"
_SEP_THICKNESS = 0.5

# Cover layout constants (points)
_COVER_BAND_HEIGHT = 220    # white top band containing the logo
_COVER_LOGO_PAD = 40        # vertical padding inside the band (top + bottom each)
_COVER_TITLE_SIZE = 32
_COVER_SUBTITLE_SIZE = 16
_COVER_META_SIZE = 10
_HEADER_LOGO_HEIGHT = 20    # logo height on content-page headers


def _resolve_path(path, base_path):
    """Return an absolute file path, or None if the file cannot be found."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return str(p) if p.exists() else None
    if base_path:
        resolved = Path(base_path) / p
        return str(resolved) if resolved.exists() else None
    return str(p) if p.exists() else None


def _image_ratio(path):
    """Return (width_px, height_px) for an image, or None on failure."""
    try:
        r = ImageReader(path)
        return r.getSize()
    except Exception:
        return None


# ── Canvas subclass ──────────────────────────────────────────────────────────


def make_numbered_canvas_class(config):
    """Return a Canvas subclass that stamps 'Page X of Y' on every content page."""
    pagination = config.get("pagination", True)
    margins = config["document"]["page"]["margins"]

    class _NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_states = []
            self._page_meta = []

        def showPage(self):
            self._page_states.append(dict(self.__dict__))
            self._page_meta.append({"is_cover": getattr(self, "_is_cover", False)})
            self._startPage()

        def save(self):
            meta = list(self._page_meta)   # snapshot before __dict__ updates overwrite it
            total = sum(1 for m in meta if not m["is_cover"])
            content_page = 0
            for state, m in zip(self._page_states, meta):
                self.__dict__.update(state)
                if not m["is_cover"]:
                    content_page += 1
                    if pagination:
                        self._stamp_page_number(content_page, total)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def _stamp_page_number(self, num, total):
            page_w, _ = self._pagesize
            self.saveState()
            self.setFont(_HEADER_FONT, _HEADER_SIZE)
            self.setFillColor(HexColor(_HEADER_COLOR))
            self.drawRightString(
                page_w - margins["right"],
                margins["bottom"] * 0.45,
                f"Page {num} of {total}",
            )
            self.restoreState()

    return _NumberedCanvas


# ── Page templates ───────────────────────────────────────────────────────────


def make_standard_template(doc, config):
    """Content-page template: header (with optional logo) + footer + page number."""
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="standard_frame",
    )

    def on_page(canv, doc):
        canv._is_cover = False
        _draw_header(canv, doc, config)
        _draw_footer(canv, doc, config)

    return PageTemplate(id="standard", frames=[frame], onPage=on_page)


def make_cover_template(doc, config):
    """Full-page cover template: no header, footer, or page number."""
    page_w, page_h = doc.pagesize
    frame = Frame(
        0, 0, page_w, page_h,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="cover_frame",
    )

    def on_page(canv, doc):
        canv._is_cover = True
        _draw_cover(canv, doc, config)

    return PageTemplate(id="cover", frames=[frame], onPage=on_page)


# ── Drawing helpers ──────────────────────────────────────────────────────────


def _draw_header(canv, doc, config):
    header = config.get("header", {})
    base_path = config.get("_base_path")
    page_w, page_h = doc.pagesize
    left = doc.leftMargin
    right = page_w - doc.rightMargin

    y_text = page_h - doc.topMargin * 0.55
    y_sep = page_h - doc.topMargin + 4

    canv.saveState()

    # Left position: logo takes priority over text when both are set
    logo_path = _resolve_path(header.get("logo"), base_path)
    if logo_path:
        dims = _image_ratio(logo_path)
        if dims:
            iw, ih = dims
            logo_h = _HEADER_LOGO_HEIGHT
            logo_w = logo_h * iw / ih
            # Align the logo's bottom edge with the text baseline
            canv.drawImage(logo_path, left, y_text - 2, width=logo_w, height=logo_h,
                           preserveAspectRatio=True, mask="auto")
    elif header.get("left"):
        canv.setFont(_HEADER_FONT, _HEADER_SIZE)
        canv.setFillColor(HexColor(_HEADER_COLOR))
        canv.drawString(left, y_text, header["left"])

    canv.setFont(_HEADER_FONT, _HEADER_SIZE)
    canv.setFillColor(HexColor(_HEADER_COLOR))

    if header.get("center"):
        canv.drawCentredString(page_w / 2, y_text, header["center"])
    if header.get("right"):
        canv.drawRightString(right, y_text, header["right"])

    if header.get("separator", True):
        canv.setStrokeColor(HexColor(_SEP_COLOR))
        canv.setLineWidth(_SEP_THICKNESS)
        canv.line(left, y_sep, right, y_sep)

    canv.restoreState()


def _draw_footer(canv, doc, config):
    footer = config.get("footer", {})
    page_w, _ = doc.pagesize
    left = doc.leftMargin
    right = page_w - doc.rightMargin

    y_text = doc.bottomMargin * 0.45
    y_sep = doc.bottomMargin - 4

    canv.saveState()
    canv.setFont(_HEADER_FONT, _HEADER_SIZE)
    canv.setFillColor(HexColor(_HEADER_COLOR))

    if footer.get("left"):
        canv.drawString(left, y_text, footer["left"])
    if footer.get("center"):
        canv.drawCentredString(page_w / 2, y_text, footer["center"])

    if footer.get("separator", True):
        canv.setStrokeColor(HexColor(_SEP_COLOR))
        canv.setLineWidth(_SEP_THICKNESS)
        canv.line(left, y_sep, right, y_sep)

    canv.restoreState()


def _draw_cover(canv, doc, config):
    cover = config.get("cover", {})
    base_path = config.get("_base_path")
    page_w, page_h = doc.pagesize
    left = doc.leftMargin
    right = page_w - doc.rightMargin
    bg = cover.get("background_color", "#1a1a2e")

    logo_path = _resolve_path(cover.get("logo"), base_path)

    canv.saveState()

    if logo_path and _image_ratio(logo_path):
        _draw_cover_split(canv, doc, cover, logo_path, page_w, page_h, left, right, bg)
    else:
        _draw_cover_full(canv, doc, cover, page_w, page_h, left, right, bg)

    canv.restoreState()


def _draw_cover_split(canv, doc, cover, logo_path, page_w, page_h, left, right, bg):
    """White top band (logo) over dark body (title/content). Used when a logo is set."""
    band_h = _COVER_BAND_HEIGHT
    band_y = page_h - band_h   # y coordinate of band bottom edge

    # Dark background — full page, then white band painted on top
    canv.setFillColor(HexColor(bg))
    canv.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # White top band
    canv.setFillColor(HexColor("#ffffff"))
    canv.rect(0, band_y, page_w, band_h, fill=1, stroke=0)

    # Logo, scaled to fill the band with padding on all sides
    iw, ih = _image_ratio(logo_path)
    ratio = iw / ih
    max_w = page_w - 2 * left
    max_h = band_h - 2 * _COVER_LOGO_PAD
    logo_w = min(max_w, max_h * ratio)
    logo_h = logo_w / ratio

    logo_x = (page_w - logo_w) / 2               # horizontally centred
    logo_y = band_y + (band_h - logo_h) / 2      # vertically centred in band

    canv.drawImage(logo_path, logo_x, logo_y, width=logo_w, height=logo_h,
                   preserveAspectRatio=True, mask="auto")

    # Title and subtitle — anchored in the upper portion of the dark body
    blue_h = band_y                               # height of the dark body section
    title_y = blue_h * 0.56

    title = cover.get("title", "")
    if title:
        canv.setFillColor(HexColor(cover.get("title_color", "#ffffff")))
        canv.setFont("Helvetica-Bold", _COVER_TITLE_SIZE)
        canv.drawString(left, title_y, title)

    subtitle = cover.get("subtitle", "")
    if subtitle:
        canv.setFillColor(HexColor(cover.get("subtitle_color", "#cccccc")))
        canv.setFont("Helvetica", _COVER_SUBTITLE_SIZE)
        canv.drawString(left, title_y - _COVER_TITLE_SIZE - 10, subtitle)

    # Author (left) and date (right) near the bottom of the dark body
    meta_y = doc.bottomMargin + 20
    canv.setFillColor(HexColor(cover.get("subtitle_color", "#cccccc")))
    canv.setFont("Helvetica", _COVER_META_SIZE)
    if cover.get("author"):
        canv.drawString(left, meta_y, cover["author"])
    if cover.get("date"):
        canv.drawRightString(right, meta_y, cover["date"])


def _draw_cover_full(canv, doc, cover, page_w, page_h, left, right, bg):
    """Fallback: full dark cover used when no logo is provided."""
    canv.setFillColor(HexColor(bg))
    canv.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    title = cover.get("title", "")
    if title:
        canv.setFillColor(HexColor(cover.get("title_color", "#ffffff")))
        canv.setFont("Helvetica-Bold", 36)
        canv.drawString(left, page_h * 0.42, title)

    subtitle = cover.get("subtitle", "")
    if subtitle:
        canv.setFillColor(HexColor(cover.get("subtitle_color", "#cccccc")))
        canv.setFont("Helvetica", 18)
        canv.drawString(left, page_h * 0.42 - 44, subtitle)

    meta_y = doc.bottomMargin + 20
    canv.setFillColor(HexColor(cover.get("subtitle_color", "#cccccc")))
    canv.setFont("Helvetica", 11)
    if cover.get("author"):
        canv.drawString(left, meta_y, cover["author"])
    if cover.get("date"):
        canv.drawRightString(right, meta_y, cover["date"])
