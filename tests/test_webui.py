"""Tests for the web UI server. Uses FastAPI's TestClient — no live server."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from webui.server import app

client = TestClient(app)

MINIMAL_CONFIG = {
    "document": {"title": "Web UI Test"},
    "content": [{"type": "paragraph", "text": "Hello from the web UI."}],
}


def test_preview_returns_pdf():
    resp = client.post("/api/preview", json={"config": MINIMAL_CONFIG})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_preview_mapped_returns_pdf_and_map():
    import base64

    two = {
        "document": {"title": "Web UI Test"},
        "content": [
            {"type": "paragraph", "text": "First paragraph."},
            {"type": "paragraph", "text": "Second paragraph."},
        ],
    }
    resp = client.post("/api/preview-mapped", json={"config": two})
    assert resp.status_code == 200
    body = resp.json()
    assert base64.b64decode(body["pdf"]).startswith(b"%PDF")
    assert isinstance(body["map"], list) and body["map"]
    band = body["map"][0]
    assert {"index", "page", "y0", "y1"} <= band.keys()
    # Both top-level content elements should appear in the map.
    assert {b["index"] for b in body["map"]} == {0, 1}


def test_render_returns_pdf_as_attachment():
    resp = client.post(
        "/api/render", json={"config": MINIMAL_CONFIG, "filename": "report"}
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    assert resp.headers["content-disposition"] == 'attachment; filename="report.pdf"'


def test_render_defaults_filename_when_omitted():
    resp = client.post("/api/render", json={"config": MINIMAL_CONFIG})
    assert resp.status_code == 200
    assert 'filename="document.pdf"' in resp.headers["content-disposition"]


def test_render_strips_path_from_filename():
    resp = client.post(
        "/api/render", json={"config": MINIMAL_CONFIG, "filename": "../../etc/passwd"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="passwd.pdf"'


def test_invalid_config_is_400_with_error_body():
    # A malformed base64 image is a ValueError inside render_pdf.
    bad = {
        "content": [{"type": "image", "src": "data:image/png;base64,not-valid!!"}]
    }
    resp = client.post("/api/preview", json={"config": bad})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_compose_returns_resolved_config():
    resp = client.post(
        "/api/compose",
        json={
            "template": {
                "document": {"title": "T"},
                "content": [{"type": "paragraph", "key": "body"}],
            },
            "values": {"name": "Dana"},
            "translations": {"body": "Hello {{name}}."},
        },
    )
    assert resp.status_code == 200
    config = resp.json()
    assert config["content"] == [{"type": "paragraph", "text": "Hello Dana."}]


def test_compose_bad_input_is_400_with_error_body():
    # No matching variant -> ComposeError (a ValueError) -> 400.
    resp = client.post(
        "/api/compose",
        json={
            "template": {
                "content": [
                    {"variants": [{"when": {"b": "low"}, "content": []}]}
                ]
            },
            "values": {"b": "high"},
            "translations": {},
        },
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_compose_render_returns_config_and_pdf():
    import base64

    resp = client.post(
        "/api/compose/render",
        json={
            "template": {
                "document": {"title": "T"},
                "content": [{"type": "heading", "level": 1, "key": "title"}],
            },
            "values": {},
            "translations": {"title": "Results"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["config"]["content"] == [
        {"type": "heading", "level": 1, "text": "Results"}
    ]
    assert base64.b64decode(body["pdf"]).startswith(b"%PDF")


def test_compose_example_returns_the_bundled_triple():
    resp = client.get("/api/compose/example")
    assert resp.status_code == 200
    example = resp.json()
    # The three inputs the compose UI seeds itself from.
    assert set(example) >= {"template", "values", "translations"}
    assert isinstance(example["template"], dict)
    assert "content" in example["template"]


def test_bundled_compose_example_resolves_to_medium_variant():
    # Guards the shipped example from rotting: composing it must select the
    # variant matching values.composure ("medium") and interpolate {{client_name}}.
    example = client.get("/api/compose/example").json()
    resp = client.post("/api/compose", json=example)
    assert resp.status_code == 200
    content = resp.json()["content"]

    # Interpolated title heading, then the medium composure heading — the low
    # and high variants must have been dropped, and no key/placeholder survives.
    assert content[0] == {"type": "heading", "level": 1, "text": "Results for Dana Okoro"}
    headings = [c["text"] for c in content if c.get("type") == "heading"]
    assert "Composure: Medium" in headings
    assert "Composure: Low" not in headings
    assert "Composure: High" not in headings
    assert all("key" not in c and "{{" not in c.get("text", "") for c in content)


def test_examples_list_includes_known_examples():
    resp = client.get("/api/examples")
    assert resp.status_code == 200
    names = resp.json()
    assert "minimal" in names
    assert "charts" in names


def test_get_example_returns_config():
    resp = client.get("/api/examples/minimal")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_get_missing_example_is_404():
    resp = client.get("/api/examples/does-not-exist")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_get_example_rejects_path_traversal():
    resp = client.get("/api/examples/..%2f..%2fpyproject")
    assert resp.status_code in (400, 404)


def test_index_is_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "pdfgen" in resp.text


def test_openapi_schema_carries_tags_and_examples():
    schema = client.get("/openapi.json").json()
    # The three capability tags are described for the docs page.
    tag_names = {t["name"] for t in schema.get("tags", [])}
    assert {"render", "compose", "examples"} <= tag_names
    # Every route is grouped under a tag (drives the /docs sidebar sections).
    assert schema["paths"]["/api/compose/render"]["post"]["tags"] == ["compose"]


def test_docs_page_uses_vendored_swagger_not_a_cdn():
    resp = client.get("/docs")
    assert resp.status_code == 200
    body = resp.text
    # Assets must come from the vendored copy, never a CDN.
    assert "/vendor/swagger/swagger-ui-bundle.js" in body
    assert "/vendor/swagger/swagger-ui.css" in body
    assert "cdn" not in body.lower()
