"""FastAPI app backing the pdfgen web UI.

A lightweight, self-hostable render path: the browser posts a pdfgen config
JSON, the server calls ``render_pdf`` directly and streams the PDF back. No
Docker, no S3, no AWS — the document never leaves the machine.

Interactive API docs (Swagger UI, served from vendored assets — no CDN) live at
``/docs``; the machine-readable schema is at ``/openapi.json``.

Endpoints
---------
GET  /                       the single-page UI (static/index.html)
GET  /docs                   Swagger UI over the endpoints below
POST /api/preview            {config} -> application/pdf (inline) or 400 {"error"}
POST /api/preview-mapped     {config} -> {"pdf": base64, "map": [bands]} (preview + sync)
POST /api/render             {config, filename?} -> application/pdf (attachment)
POST /api/compose            {template, values, translations} -> composed config JSON
POST /api/compose/render     {template, values, translations, filename?}
                             -> {"config": composed, "pdf": base64} (audit trail + PDF)
GET  /api/compose/example    -> a bundled {template, values, translations} triple
GET  /api/examples           -> ["basic_report", "charts", ...]
GET  /api/examples/{name}    -> the example's config JSON

Compose and render are two distinct capabilities of this one service. Compose
(pdfgen/compose.py) turns a template + values + translations into a resolved
config; render turns a resolved config into a PDF. They are kept separate on
purpose — /api/render still takes an already-composed config, and /api/compose
is usable on its own. The engine is agnostic to whether a report is one data
source or an aggregate: post one template or a pre-merged one, it neither knows
nor cares.

The 400/500 error contract mirrors the Lambda handler (api/handler.py):
a bad config (ValueError) is a 400 with {"error": ...}; anything else is a 500.
"""
import base64
import json
import mimetypes
from pathlib import Path

# The preview pane loads PDF.js as an ES module (static/vendor/pdfjs/*.mjs).
# .mjs is missing from some platforms' mimetype tables; without a JavaScript
# content-type the browser refuses to execute the module. Register it up front.
mimetypes.add_type("text/javascript", ".mjs")

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from pdfgen.compose import compose
from pdfgen.engine import render_pdf, render_pdf_with_map

from .schemas import (
    API_DESCRIPTION,
    API_TITLE,
    COMPOSE_RESULT_EXAMPLE,
    ERROR_400,
    ERROR_404,
    PDF_200,
    TAGS_METADATA,
    ComposeRenderResponse,
    ComposeRequest,
    PreviewMappedResponse,
    RenderRequest,
)

try:
    API_VERSION = _pkg_version("pdfgen")
except PackageNotFoundError:  # running from source without an install
    API_VERSION = "0.1.0"

# webui/server.py -> repo root is the parent of the webui package. Relative
# asset paths in a config ("assets/DefaultLogo.png") resolve against it.
REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
EXAMPLES_DIR = REPO_ROOT / "examples"
# The compose UI seeds its three inputs from one bundled worked example. Kept in
# a subdirectory so it never leaks into /api/examples (which globs *.json at the
# examples/ top level, non-recursively).
COMPOSE_EXAMPLE = EXAMPLES_DIR / "compose" / "composure_demo.json"

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    # Swagger UI and ReDoc default to CDN-hosted assets; a self-hosted tool must
    # work offline, so disable the built-ins and serve Swagger UI from vendored
    # files (see /docs below), mirroring how PDF.js is vendored.
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
def swagger_ui_html() -> Response:
    """Swagger UI rendered from vendored assets under /vendor/swagger (no CDN)."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{API_TITLE} API — docs",
        swagger_js_url="/vendor/swagger/swagger-ui-bundle.js",
        swagger_css_url="/vendor/swagger/swagger-ui.css",
        swagger_favicon_url="",  # no external favicon fetch
    )


@app.middleware("http")
async def _revalidate_static(request, call_next):
    """Make browsers revalidate the UI's static assets on every load.

    The single-page UI ships as static HTML/JS/CSS baked into the image, and it
    changes with each build. Starlette's StaticFiles sends no Cache-Control, so
    browsers heuristically cache these files and a rebuilt asset can be masked by
    a stale copy (a changed stylesheet silently ignored). ``no-cache`` keeps the
    cached copy but forces an ETag revalidation first, so an unchanged asset is a
    cheap 304 and a changed one is refetched. API responses are dynamic and left
    untouched.
    """
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".mjs", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    return response


def _guard(fn):
    """Run a render callable, translating failures to HTTP errors.

    A bad config (ValueError) becomes a 400 with the message; an HTTPException
    passes through unchanged; anything else is an opaque 500. Shared by every
    render endpoint so they report failures identically.
    """
    try:
        return fn()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="internal error while rendering document"
        )


def _render(config: dict) -> bytes:
    """Render a config to PDF bytes, translating failures to HTTP errors."""
    return _guard(lambda: render_pdf(config, base_path=str(REPO_ROOT)))


@app.post(
    "/api/preview",
    tags=["render"],
    summary="Render a config to an inline PDF",
    response_class=Response,
    responses={**PDF_200, **ERROR_400},
)
def preview(req: RenderRequest) -> Response:
    """Render and return the PDF inline, for display in the preview pane."""
    pdf = _render(req.config)
    return Response(content=pdf, media_type="application/pdf")


@app.post(
    "/api/preview-mapped",
    tags=["render"],
    summary="Render a config plus an element→page map",
    response_model=PreviewMappedResponse,
    responses={**ERROR_400},
)
def preview_mapped(req: RenderRequest) -> JSONResponse:
    """Render the PDF plus an element-to-page map for editor↔preview sync.

    Returns ``{"pdf": <base64>, "map": [{index, page, y0, y1}, ...]}``. The map
    links each top-level ``content`` element to where it landed (page and
    bottom-origin vertical band) so the front end can jump between the JSON and
    the preview. ``/api/preview`` stays a plain PDF for callers that don't sync.
    """
    pdf, bands = _guard(
        lambda: render_pdf_with_map(req.config, base_path=str(REPO_ROOT))
    )
    return JSONResponse(
        {"pdf": base64.b64encode(pdf).decode("ascii"), "map": bands}
    )


@app.post(
    "/api/render",
    tags=["render"],
    summary="Render a config to a downloadable PDF",
    response_class=Response,
    responses={**PDF_200, **ERROR_400},
)
def render(req: RenderRequest) -> Response:
    """Render and return the PDF as a download."""
    pdf = _render(req.config)
    name = _safe_filename(req.filename) or "document.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.post(
    "/api/compose",
    tags=["compose"],
    summary="Resolve a template into a config",
    responses={
        200: {
            "description": "The composed, fully-resolved document config.",
            "content": {"application/json": {"example": COMPOSE_RESULT_EXAMPLE}},
        },
        **ERROR_400,
    },
)
def compose_config(req: ComposeRequest) -> JSONResponse:
    """Resolve a template + values + translations into a render-ready config.

    Returns the composed JSON only — no PDF. A ComposeError (bad template,
    unmatched variant, missing key/value) is a ValueError, so _guard maps it to
    a 400, matching the render error contract.
    """
    composed = _guard(lambda: compose(req.template, req.values, req.translations))
    return JSONResponse(composed)


@app.post(
    "/api/compose/render",
    tags=["compose"],
    summary="Compose then render (config + PDF)",
    response_model=ComposeRenderResponse,
    responses={**ERROR_400},
)
def compose_and_render(req: ComposeRequest) -> JSONResponse:
    """Compose then render, returning both the composed config and the PDF.

    The composed config is always returned alongside the PDF (never discarded)
    so it can be logged as an audit trail and used to tell a compose failure
    apart from a render failure. PDF is base64 in JSON so both travel together.
    """
    composed = _guard(lambda: compose(req.template, req.values, req.translations))
    pdf = _render(composed)
    return JSONResponse(
        {"config": composed, "pdf": base64.b64encode(pdf).decode("ascii")}
    )


@app.get(
    "/api/compose/example",
    tags=["examples", "compose"],
    summary="The bundled compose demo inputs",
    responses={**ERROR_404},
)
def compose_example() -> JSONResponse:
    """The bundled {template, values, translations} triple that seeds the UI.

    One worked example demonstrating a ``variants`` group and ``{{placeholder}}``
    interpolation, so the compose tab shows what it does the moment it opens.
    """
    if not COMPOSE_EXAMPLE.is_file():
        raise HTTPException(status_code=404, detail="no bundled compose example")
    try:
        return JSONResponse(json.loads(COMPOSE_EXAMPLE.read_text()))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"compose example is not valid JSON: {e}")


@app.get(
    "/api/examples",
    tags=["examples"],
    summary="List bundled example configs",
    response_model=list[str],
)
def list_examples() -> list[str]:
    """Names (without extension) of the bundled example configs."""
    if not EXAMPLES_DIR.is_dir():
        return []
    return sorted(p.stem for p in EXAMPLES_DIR.glob("*.json"))


@app.get(
    "/api/examples/{name}",
    tags=["examples"],
    summary="Fetch one example config",
    responses={**ERROR_400, **ERROR_404},
)
def get_example(name: str) -> JSONResponse:
    """The config JSON for a single named example."""
    # Guard against path traversal: accept a bare stem only.
    if "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(status_code=400, detail="invalid example name")
    path = EXAMPLES_DIR / f"{name}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no such example: {name}")
    try:
        return JSONResponse(json.loads(path.read_text()))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"example is not valid JSON: {e}")


@app.exception_handler(HTTPException)
def _http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    # Uniform {"error": ...} body, matching the Lambda handler's shape.
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def _safe_filename(name: str | None) -> str | None:
    """Reduce a user-supplied filename to a safe basename ending in .pdf."""
    if not name:
        return None
    stem = Path(name).name  # strip any directory components
    if not stem:
        return None
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    return stem


# Serve the front-end assets. Mounted last so it never shadows /api routes.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
