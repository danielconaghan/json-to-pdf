"""Lambda handler: pdfgen document config in, presigned S3 URL out.

POST a request body that is one of two shapes:

* a **render** request — a pdfgen document config JSON (``{document, content}``),
  rendered as-is; or
* a **compose** request — ``{template, values, translations}``, which is first
  resolved by :func:`pdfgen.compose.compose` into a document config and then
  rendered. The body is a compose request iff it carries a top-level
  ``template`` key.

Either way the rendered PDF is written to S3 (rendered PDFs routinely exceed
Lambda's 6MB response payload limit, so the body is never returned inline) and
the response carries a presigned GET URL. For a compose request the response
also carries the composed config under ``"config"`` — it is small, and keeping
it gives an audit trail and lets a caller tell a compose failure (400 before
any render) apart from a render failure. Compose and render stay distinct steps
sharing one service; the handler just chains them when handed template input.

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

from pdfgen.compose import compose
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
        body = _parse_body(event)
        config, composed = _resolve_config(body)
    except ValueError as e:
        # Covers a malformed body and any ComposeError (a ValueError): a bad
        # request, reported before a single byte is rendered or stored.
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
    payload = {
        "url": url,
        "key": key,
        "size_bytes": len(pdf),
        "expires_in": expiry,
    }
    if composed is not None:
        # Return (and above, log) the composed config so it is never discarded.
        logger.info("composed config for %s: %s", key, json.dumps(composed))
        payload["config"] = composed
    return _response(200, payload)


def _resolve_config(body):
    """Produce a render-ready config from a parsed request body.

    Returns ``(config, composed)``. For a compose request (``template`` present)
    the body is run through :func:`compose` and ``composed`` is that resolved
    config; for a plain render request the body is the config and ``composed``
    is ``None``. A :class:`~pdfgen.compose.ComposeError` (a ``ValueError``)
    propagates so the caller maps it to a 400. Aggregating several data sources
    into one ``values`` map is the caller's job upstream — compose, and this
    handler, take one already-assembled input.
    """
    if "template" in body:
        composed = compose(
            body["template"],
            body.get("values", {}),
            body.get("translations", {}),
        )
        return composed, composed
    return body, None


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
