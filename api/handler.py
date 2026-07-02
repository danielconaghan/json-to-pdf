"""Lambda handler: pdfgen document config in, presigned S3 URL out.

POST a pdfgen config JSON as the request body. The rendered PDF is written
to S3 (rendered PDFs routinely exceed Lambda's 6MB response payload limit,
so the body is never returned inline) and the response carries a presigned
GET URL.

Environment:
    OUTPUT_BUCKET        S3 bucket for rendered PDFs (required)
    URL_EXPIRY_SECONDS   presigned URL lifetime (default 3600)
"""
import base64
import json
import logging
import os
import uuid

import boto3

from pdfgen.engine import render_pdf

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3 = None


def _s3_client():
    # Created lazily, reused across warm invocations.
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def lambda_handler(event, context):
    try:
        config = _parse_body(event)
    except ValueError as e:
        return _response(400, {"error": str(e)})

    try:
        pdf = render_pdf(config)
    except ValueError as e:
        return _response(400, {"error": str(e)})
    except Exception:
        logger.exception("render failed")
        return _response(500, {"error": "internal error while rendering document"})

    bucket = os.environ["OUTPUT_BUCKET"]
    expiry = int(os.environ.get("URL_EXPIRY_SECONDS", "3600"))
    key = f"documents/{uuid.uuid4().hex}.pdf"

    _s3_client().put_object(
        Bucket=bucket, Key=key, Body=pdf, ContentType="application/pdf"
    )
    url = _s3_client().generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiry
    )

    logger.info("rendered %s (%d bytes)", key, len(pdf))
    return _response(200, {
        "url": url,
        "key": key,
        "size_bytes": len(pdf),
        "expires_in": expiry,
    })


def _parse_body(event):
    """Extract and validate the document config from an API Gateway event."""
    body = event.get("body")
    if not body:
        raise ValueError("request body is empty")
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            raise ValueError("request body is not valid base64-encoded UTF-8")
    try:
        config = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"request body is not valid JSON: {e}")
    if not isinstance(config, dict):
        raise ValueError("request body must be a JSON object")
    return config


def _response(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }
