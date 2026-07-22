"""Tests for the Lambda handler. Uses a stub S3 client — no AWS calls."""
import base64
import json

import pytest

boto3 = pytest.importorskip("boto3")

from api import handler


class StubS3:
    def __init__(self):
        self.put_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def generate_presigned_url(self, operation, Params=None, ExpiresIn=None):
        return f"https://example.com/{Params['Key']}?sig=stub"


@pytest.fixture
def stub_s3(monkeypatch):
    stub = StubS3()
    monkeypatch.setattr(handler, "_s3", stub)
    monkeypatch.setenv("OUTPUT_BUCKET", "test-bucket")
    return stub


MINIMAL_BODY = json.dumps({
    "document": {"title": "Handler Test"},
    "content": [{"type": "paragraph", "text": "Hello from the API."}],
})


def test_renders_and_returns_presigned_url(stub_s3):
    result = handler.lambda_handler({"body": MINIMAL_BODY}, None)

    assert result["statusCode"] == 200
    payload = json.loads(result["body"])
    assert payload["url"].startswith("https://example.com/documents/")
    assert payload["size_bytes"] > 1000
    assert payload["expires_in"] == 3600

    [put] = stub_s3.put_calls
    assert put["Bucket"] == "test-bucket"
    assert put["ContentType"] == "application/pdf"
    assert put["Body"].startswith(b"%PDF-")


def test_accepts_base64_encoded_body(stub_s3):
    event = {
        "body": base64.b64encode(MINIMAL_BODY.encode()).decode(),
        "isBase64Encoded": True,
    }
    result = handler.lambda_handler(event, None)
    assert result["statusCode"] == 200


def test_empty_body_is_400(stub_s3):
    result = handler.lambda_handler({"body": ""}, None)
    assert result["statusCode"] == 400
    assert "empty" in json.loads(result["body"])["error"]


def test_invalid_json_is_400(stub_s3):
    result = handler.lambda_handler({"body": "{not json"}, None)
    assert result["statusCode"] == 400
    assert "JSON" in json.loads(result["body"])["error"]


def test_non_object_json_is_400(stub_s3):
    result = handler.lambda_handler({"body": "[1, 2]"}, None)
    assert result["statusCode"] == 400


COMPOSE_BODY = json.dumps({
    "template": {
        "document": {"title": "Composed"},
        "content": [{"type": "heading", "level": 1, "key": "title"}],
    },
    "values": {"name": "Dana"},
    "translations": {"title": "Results for {{name}}"},
})


def test_compose_request_renders_and_returns_composed_config(stub_s3):
    result = handler.lambda_handler({"body": COMPOSE_BODY}, None)

    assert result["statusCode"] == 200
    payload = json.loads(result["body"])
    assert payload["url"].startswith("https://example.com/documents/")
    # The composed config is returned alongside the URL, never discarded, and
    # carries no template vocabulary — the key resolved to interpolated text.
    assert payload["config"]["content"] == [
        {"type": "heading", "level": 1, "text": "Results for Dana"}
    ]

    [put] = stub_s3.put_calls
    assert put["Body"].startswith(b"%PDF-")


def test_render_request_omits_config_from_response(stub_s3):
    # A plain render request (no `template`) behaves exactly as before.
    result = handler.lambda_handler({"body": MINIMAL_BODY}, None)
    assert result["statusCode"] == 200
    assert "config" not in json.loads(result["body"])


def test_compose_failure_is_400_before_any_render(stub_s3):
    # No variant matches -> ComposeError -> 400, and nothing is stored.
    body = json.dumps({
        "template": {
            "content": [{"variants": [{"when": {"b": "low"}, "content": []}]}]
        },
        "values": {"b": "high"},
        "translations": {},
    })
    result = handler.lambda_handler({"body": body}, None)
    assert result["statusCode"] == 400
    assert "no variant matched" in json.loads(result["body"])["error"]
    assert stub_s3.put_calls == []


def test_bad_inline_image_is_400(stub_s3):
    body = json.dumps({
        "content": [{"type": "image", "src": "data:image/png;base64,!!!", "alt": "x"}],
    })
    result = handler.lambda_handler({"body": body}, None)
    assert result["statusCode"] == 400
    assert "base64" in json.loads(result["body"])["error"]
    assert stub_s3.put_calls == []
