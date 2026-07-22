from reportlab.platypus import BaseDocTemplate


class PDFDocTemplate(BaseDocTemplate):
    """BaseDocTemplate with automatic TOC notification.

    Headings that carry a ``_toc_entry = (level, text)`` attribute emit a
    ``TOCEntry`` notification after they are rendered, which any
    ``TableOfContents`` flowable in the story will pick up.
    """

    def afterFlowable(self, flowable):
        entry = getattr(flowable, "_toc_entry", None)
        if entry is not None:
            level, text = entry
            self.notify("TOCEntry", (level, text, self.page))

    def handle_documentBegin(self, *args, **kwargs):
        # multiBuild lays the story out several times to resolve the TOC; clear
        # any optional source map at the start of each pass so only the final
        # pass's element positions survive. No-op on the normal render path.
        super().handle_documentBegin(*args, **kwargs)
        source_map = getattr(self, "source_map", None)
        if source_map is not None:
            source_map.reset()
