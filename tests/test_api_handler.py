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


def test_bad_inline_image_is_400(stub_s3):
    body = json.dumps({
        "content": [{"type": "image", "src": "data:image/png;base64,!!!", "alt": "x"}],
    })
    result = handler.lambda_handler({"body": body}, None)
    assert result["statusCode"] == 400
    assert "base64" in json.loads(result["body"])["error"]
    assert stub_s3.put_calls == []
