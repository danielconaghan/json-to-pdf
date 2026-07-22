"""Optional element-to-page position map for the web UI's live preview.

The web UI wants a two-way link between the JSON editor and the rendered PDF:
click an element in the PDF and the editor jumps to the JSON that produced it;
move the caret in the JSON and the preview scrolls to the matching element.
That needs to know, for each top-level ``content`` element, which page it
landed on and the vertical band it occupies.

This module builds that map without touching the normal render path. A
``SourceMap`` is created only when a caller asks for one (the web UI's
``render_pdf_with_map``); the CLI and Lambda paths never construct one, so
their output is byte-for-byte unchanged.

Granularity is deliberately element-level, not line- or word-level. ReportLab
lays out one-or-more flowables per ``content[i]`` element but does not expose
sub-flowable line positions without significant effort, so a click anywhere in
a paragraph maps to that whole paragraph — which matches the JSON's own atoms.

Positions are captured by wrapping each flowable's ``drawOn`` (the public
"draw yourself at (x, y)" call). ReportLab's y origin is the page bottom, so a
flowable drawn at ``y`` with height ``h`` occupies the band ``[y, y + h]``; the
front end converts that to a top-based offset using the PDF.js viewport.

Known limitation: a flowable that splits across pages (a long table or
paragraph) is drawn as split fragments that do not carry the tag, so only the
part that fits without splitting is recorded. Most elements do not split.
"""


class SourceMap:
    """Records where each ``content`` element was drawn, keyed by flowable.

    ``instrument`` is called once per flowable while the story is assembled;
    ``reset`` is called at the start of every build pass (``multiBuild`` runs
    several) so only the final pass survives; ``bands`` returns the collapsed
    result once the build finishes.
    """

    def __init__(self):
        # id(flowable) -> {index, page, y0, y1}. Keyed by identity so a
        # multi-flowable element keeps a record per flowable, and a redraw of
        # the same flowable (a later build pass) overwrites in place.
        self._records = {}

    def reset(self):
        self._records.clear()

    def instrument(self, flowable, index):
        """Tag a flowable with its element index and capture its draw box."""
        flowable._content_index = index
        smap = self
        original_draw = flowable.drawOn

        def drawOn(canvas, x, y, *args, **kwargs):
            result = original_draw(canvas, x, y, *args, **kwargs)
            height = getattr(flowable, "height", 0) or 0
            smap._records[id(flowable)] = {
                "index": index,
                "page": canvas.getPageNumber(),
                "y0": y,
                "y1": y + height,
            }
            return result

        flowable.drawOn = drawOn

    def bands(self):
        """One vertical band per (element, page), sorted for stable output.

        Adjacent flowables of the same element on the same page are merged into
        a single band so the front end sees one target per element per page.
        """
        merged = {}  # (index, page) -> [y0, y1]
        for rec in self._records.values():
            key = (rec["index"], rec["page"])
            span = merged.get(key)
            if span is None:
                merged[key] = [rec["y0"], rec["y1"]]
            else:
                span[0] = min(span[0], rec["y0"])
                span[1] = max(span[1], rec["y1"])
        out = [
            {"index": index, "page": page, "y0": y0, "y1": y1}
            for (index, page), (y0, y1) in merged.items()
        ]
        out.sort(key=lambda b: (b["index"], b["page"]))
        return out
