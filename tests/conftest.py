"""Shared fixtures for the pdfgen test suite."""
import base64
import io

import pytest
from reportlab.lib.styles import ParagraphStyle


# ── Canvas / doc stubs ────────────────────────────────────────────────────────

class _MockCatalog:
    pass


class _MockPDFDoc:
    def __init__(self):
        self.Catalog = _MockCatalog()


class MockCanvas:
    """Minimal canvas stub that captures addLiteral calls."""
    def __init__(self):
        self._doc = _MockPDFDoc()
        self._mcid_counter = 0
        self._tracker = None
        self._literals = []

    def addLiteral(self, s):
        self._literals.append(s)


class MockDoc:
    """Minimal doc stub with a fixed text-width (A4 minus 72pt margins)."""
    width = 452.0


class MockCtx:
    def __init__(self, rl_styles=None, config=None):
        self.rl_styles = rl_styles or {}
        self.doc = MockDoc()
        self.config = config or {}
        self.base_path = None


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_canvas():
    return MockCanvas()


@pytest.fixture
def body_style():
    return ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=16)


@pytest.fixture
def h1_style():
    return ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=24, leading=28)


@pytest.fixture
def minimal_styles(body_style, h1_style):
    return {"body": body_style, "h1": h1_style}


@pytest.fixture
def mock_ctx(minimal_styles):
    return MockCtx(rl_styles=minimal_styles)


@pytest.fixture
def png_data_uri():
    """A valid base64 PNG data URI (4x4 solid red)."""
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (4, 4), "red").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
