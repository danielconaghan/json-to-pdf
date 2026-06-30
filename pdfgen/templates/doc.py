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
