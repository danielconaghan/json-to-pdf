from unittest.mock import MagicMock, patch

from pdfgen.templates.doc import PDFDocTemplate


def _make_doc():
    return PDFDocTemplate.__new__(PDFDocTemplate)


class TestPDFDocTemplate:
    def test_toc_entry_triggers_notify(self):
        doc = _make_doc()
        doc.page = 3
        doc.notify = MagicMock()

        flowable = MagicMock()
        flowable._toc_entry = (0, "Introduction")

        doc.afterFlowable(flowable)
        doc.notify.assert_called_once_with("TOCEntry", (0, "Introduction", 3))

    def test_flowable_without_toc_entry_does_not_notify(self):
        doc = _make_doc()
        doc.page = 1
        doc.notify = MagicMock()

        flowable = MagicMock(spec=[])  # no _toc_entry attribute
        doc.afterFlowable(flowable)
        doc.notify.assert_not_called()

    def test_toc_entry_none_does_not_notify(self):
        doc = _make_doc()
        doc.page = 1
        doc.notify = MagicMock()

        flowable = MagicMock()
        flowable._toc_entry = None
        doc.afterFlowable(flowable)
        doc.notify.assert_not_called()

    def test_level_and_text_forwarded_correctly(self):
        doc = _make_doc()
        doc.page = 7
        doc.notify = MagicMock()

        flowable = MagicMock()
        flowable._toc_entry = (2, "Sub-section")
        doc.afterFlowable(flowable)

        args = doc.notify.call_args[0]
        level, text, page = args[1]
        assert level == 2
        assert text == "Sub-section"
        assert page == 7
