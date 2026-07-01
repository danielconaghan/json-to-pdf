from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, PageTemplate

from ..accessibility import begin_artifact, end_artifact
from ..utils import resolve_path

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


def _image_ratio(path):
    """Return (width_px, height_px) for an image, or None if the file is unreadable."""
    try:
        r = ImageReader(path)
        return r.getSize()
    except (OSError, IOError):
        return None


# ── Canvas subclass ──────────────────────────────────────────────────────────


def make_numbered_canvas_class(config):
    """Return a Canvas subclass that stamps 'Page X of Y' on every content page."""
    from ..accessibility import _StructTracker, setup_document

    pagination = config.get("pagination", True)
    margins = config["document"]["page"]["margins"]

    # One tracker shared across all canvas instances; reset on each new canvas
    # so only the final multiBuild pass contributes to the structure tree.
    tracker = _StructTracker()
    config["_struct_tracker"] = tracker

    class _NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_states = []
            self._page_meta = []
            self._mcid_counter = 0
            tracker.reset()
            self._tracker = tracker
            setup_document(self, config)

        def showPage(self):
            self._page_states.append(dict(self.__dict__))
            self._page_meta.append({"is_cover": getattr(self, "_is_cover", False)})
            self._mcid_counter = 0
            tracker.new_page()
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
            begin_artifact(self, "Pagination")
            self.saveState()
            self.setFont(_HEADER_FONT, _HEADER_SIZE)
            self.setFillColor(HexColor(_HEADER_COLOR))
            self.drawRightString(
                page_w - margins["right"],
                margins["bottom"] * 0.45,
                f"Page {num} of {total}",
            )
            self.restoreState()
            end_artifact(self)

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

    begin_artifact(canv, "Pagination")
    canv.saveState()

    # Left position: logo takes priority over text when both are set
    logo_path = resolve_path(header.get("logo"), base_path)
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
    end_artifact(canv)


def _draw_footer(canv, doc, config):
    footer = config.get("footer", {})
    page_w, _ = doc.pagesize
    left = doc.leftMargin
    right = page_w - doc.rightMargin

    y_text = doc.bottomMargin * 0.45
    y_sep = doc.bottomMargin - 4

    begin_artifact(canv, "Pagination")
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
    end_artifact(canv)


def _draw_cover_background(canv, bg_image_path, page_w, page_h, bg):
    """Fill the cover page: background image (scale-to-fill) or solid colour."""
    if bg_image_path:
        dims = _image_ratio(bg_image_path)
        if dims:
            iw, ih = dims
            img_ratio = iw / ih
            page_ratio = page_w / page_h
            if img_ratio > page_ratio:
                draw_h = page_h
                draw_w = page_h * img_ratio
            else:
                draw_w = page_w
                draw_h = page_w / img_ratio
            draw_x = (page_w - draw_w) / 2
            draw_y = (page_h - draw_h) / 2
            canv.drawImage(bg_image_path, draw_x, draw_y,
                           width=draw_w, height=draw_h, mask="auto")
            return
    canv.setFillColor(HexColor(bg))
    canv.rect(0, 0, page_w, page_h, fill=1, stroke=0)


def _draw_cover(canv, doc, config):
    cover = config.get("cover", {})
    base_path = config.get("_base_path")
    page_w, page_h = doc.pagesize
    left = doc.leftMargin
    right = page_w - doc.rightMargin
    bg = cover.get("background_color", "#1a1a2e")

    logo_path = resolve_path(cover.get("logo"), base_path)
    bg_image_path = resolve_path(cover.get("background_image"), base_path)

    begin_artifact(canv, "Layout")
    canv.saveState()

    if logo_path and _image_ratio(logo_path):
        _draw_cover_split(canv, doc, cover, logo_path, bg_image_path, page_w, page_h, left, right, bg)
    else:
        _draw_cover_full(canv, doc, cover, bg_image_path, page_w, page_h, left, right, bg)

    canv.restoreState()
    end_artifact(canv)


def _draw_cover_split(canv, doc, cover, logo_path, bg_image_path, page_w, page_h, left, right, bg):
    """White top band (logo) over dark body (title/content). Used when a logo is set."""
    band_h = _COVER_BAND_HEIGHT
    band_y = page_h - band_h   # y coordinate of band bottom edge

    # Background — image or solid colour, then white band painted on top
    _draw_cover_background(canv, bg_image_path, page_w, page_h, bg)

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

    _draw_cover_meta(canv, cover, doc, left, right)


def _draw_cover_full(canv, doc, cover, bg_image_path, page_w, page_h, left, right, bg):
    """Full cover — image or solid colour background with title/subtitle/meta."""
    _draw_cover_background(canv, bg_image_path, page_w, page_h, bg)

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

    _draw_cover_meta(canv, cover, doc, left, right)


def _draw_cover_meta(canv, cover, doc, left, right):
    """Draw author (left) and date (right) near the bottom of the cover."""
    meta_y = doc.bottomMargin + 20
    canv.setFillColor(HexColor(cover.get("subtitle_color", "#cccccc")))
    canv.setFont("Helvetica", _COVER_META_SIZE)
    if cover.get("author"):
        canv.drawString(left, meta_y, cover["author"])
    if cover.get("date"):
        canv.drawRightString(right, meta_y, cover["date"])
