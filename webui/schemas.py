"""Request/response models and OpenAPI metadata for the web UI API.

Kept apart from ``server.py`` so the route handlers stay about behaviour while
the schema — the shape the ``/docs`` page documents — lives in one place.
FastAPI turns these models, their examples, and the tag descriptions into the
OpenAPI document served at ``/openapi.json`` and rendered at ``/docs``.
"""
from pydantic import BaseModel, Field

API_TITLE = "pdfgen"

API_DESCRIPTION = """\
Generate PDFs from JSON.

Two capabilities, one service:

* **render** — POST a fully-resolved pdfgen document config and get a PDF back.
* **compose** — POST a `template` + `values` + `translations` and get the
  resolved config (and, optionally, the rendered PDF). This is the upstream
  authoring step: it collapses `variants` groups by matching each `when` against
  `values`, and fills `{{placeholder}}` tokens from `values`. It knows nothing
  about layout — its output is a render config.

**Error contract** (mirrors the AWS Lambda handler): a malformed body or an
unresolvable template/config is `400 {"error": "..."}`; anything unexpected is
`500`. Compose failures name the offending node or key.

The web UI at `/` (Render and Compose tabs) is a thin demo over these endpoints.
"""

TAGS_METADATA = [
    {"name": "render", "description": "Turn a resolved document config into a PDF."},
    {"name": "compose", "description": "Resolve a template + values + translations into a config, and optionally render it."},
    {"name": "examples", "description": "Bundled example configs and the compose demo that seed the UI."},
]

# ---- example payloads (surfaced in the /docs "Try it out" panels) ----------

MINIMAL_CONFIG = {
    "document": {"title": "My Report"},
    "content": [
        {"type": "heading", "level": 1, "text": "Introduction"},
        {"type": "paragraph", "text": "Hello from pdfgen."},
    ],
}

# A compact compose example: one variant group (selected by ``composure``) plus
# a ``{{client_name}}`` placeholder. The fuller version is GET /api/compose/example.
COMPOSE_EXAMPLE = {
    "template": {
        "document": {"title": "Risk Profile"},
        "content": [
            {"type": "heading", "level": 1, "key": "title"},
            {
                "type": "group",
                "variants": [
                    {"when": {"composure": "low"}, "content": [{"type": "paragraph", "key": "composure.low"}]},
                    {"when": {"composure": "high"}, "content": [{"type": "paragraph", "key": "composure.high"}]},
                ],
            },
        ],
    },
    "values": {"client_name": "Dana", "composure": "high"},
    "translations": {
        "title": "Results for {{client_name}}",
        "composure.low": "{{client_name}} may feel uneasy when markets fall.",
        "composure.high": "{{client_name}} stays composed through market swings.",
    },
}

# What composing the example above yields — shown as the /api/compose response.
COMPOSE_RESULT_EXAMPLE = {
    "document": {"title": "Risk Profile"},
    "content": [
        {"type": "heading", "level": 1, "text": "Results for Dana"},
        {"type": "paragraph", "text": "Dana stays composed through market swings."},
    ],
}

# ---- request models --------------------------------------------------------


class RenderRequest(BaseModel):
    config: dict = Field(
        ..., description="A fully-resolved pdfgen document config: `{document, content, ...}`."
    )
    filename: str | None = Field(
        None,
        description="Download name for `/api/render` only; sanitised to a `.pdf` basename.",
    )
    model_config = {
        "json_schema_extra": {"examples": [{"config": MINIMAL_CONFIG, "filename": "report"}]}
    }


class ComposeRequest(BaseModel):
    template: dict = Field(
        ..., description="A template tree with a top-level `content` array; leaves carry a `key`, conditional groups carry `variants`."
    )
    values: dict = Field(
        default_factory=dict,
        description="The client's resolved data: banded fields for `when` matching plus raw fields for `{{placeholder}}` interpolation.",
    )
    translations: dict = Field(
        default_factory=dict,
        description="A flat `key -> string` map, locale-resolved. Strings may contain `{{placeholder}}` tokens.",
    )
    filename: str | None = Field(
        None, description="Download name for the rendered PDF (compose/render only)."
    )
    model_config = {"json_schema_extra": {"examples": [COMPOSE_EXAMPLE]}}


# ---- response models -------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Human-readable reason the request was rejected.")


class Band(BaseModel):
    index: int = Field(..., description="Index of the top-level `content` element this band belongs to.")
    page: int = Field(..., description="1-based page the element landed on.")
    y0: float = Field(..., description="Bottom edge of the element, in bottom-origin PDF points.")
    y1: float = Field(..., description="Top edge of the element, in bottom-origin PDF points.")


class PreviewMappedResponse(BaseModel):
    pdf: str = Field(..., description="Base64-encoded PDF bytes.")
    map: list[Band] = Field(
        ..., description="One band per top-level `content` element: where it landed in the PDF, for editor↔preview sync."
    )


class ComposeRenderResponse(BaseModel):
    config: dict = Field(..., description="The composed, fully-resolved document config (kept as an audit trail).")
    pdf: str = Field(..., description="Base64-encoded PDF bytes of the rendered composed config.")


# Reusable OpenAPI ``responses`` fragments.
ERROR_400 = {400: {"model": ErrorResponse, "description": "Bad request: invalid body, config, or template."}}
ERROR_404 = {404: {"model": ErrorResponse, "description": "Not found."}}
PDF_200 = {
    200: {
        "content": {"application/pdf": {}},
        "description": "The rendered PDF.",
    }
}
