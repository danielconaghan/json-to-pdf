# HTTP API — AWS Lambda

pdfgen ships a service layer for running as an HTTP API on AWS Lambda: a handler package (`api/`) and a container image (`Dockerfile`). The library itself stays AWS-free — the handler is a thin wrapper over the programmatic entry point.

---

## Programmatic entry point

Any embedder (the Lambda handler, a script, another service) renders through `pdfgen.engine.render_pdf`:

```python
from pdfgen.engine import render_pdf

config = {
    "document": {"title": "My Report"},
    "content": [{"type": "paragraph", "text": "Hello."}],
}
pdf_bytes = render_pdf(config)
```

It takes a config dict (same shape as the JSON files), applies defaults, and returns the finished PDF as bytes. The caller's dict is not mutated.

`render_pdf(config, base_path=...)` resolves relative asset paths against `base_path` — the CLI passes the input file's directory. When there is no filesystem to reference (an API caller), embed images as base64 data URIs instead; see below.

---

## Request

`POST` the document config JSON as the request body — the same JSON you would pass to the CLI.

Because API callers have no shared filesystem:

- **Brand assets are bundled in the container image.** Anything under `assets/` in the repo is available at that same relative path, e.g. `"logo": "assets/DefaultLogo.png"`.
- **Per-document images travel inline as base64 data URIs** in any image field (`src`, `cover.logo`, `cover.background_image`, `header.logo`):

```json
{
  "document": { "title": "Client Report" },
  "cover":    { "title": "Client Report", "logo": "assets/DefaultLogo.png" },
  "content": [
    { "type": "image", "src": "data:image/png;base64,iVBORw0KG...", "alt": "Allocation chart" }
  ]
}
```

Supported inline types: `image/png`, `image/jpeg`, `image/gif`. API Gateway caps request bodies at 10MB, which allows roughly 7MB of embedded images per document.

---

## Response

The rendered PDF is written to S3 and the response returns a presigned URL (PDFs routinely exceed Lambda's 6MB response payload limit, so the document is never returned inline):

```json
{
  "url": "https://<bucket>.s3.amazonaws.com/documents/9f2c...pdf?X-Amz-...",
  "key": "documents/9f2c07e1b64d4d0a8a3f.pdf",
  "size_bytes": 48213,
  "expires_in": 3600
}
```

| Status | Meaning |
|---|---|
| `200` | Rendered; body contains the presigned URL. |
| `400` | Empty body, invalid JSON, non-object JSON, or a malformed base64 image / unloadable font. Body contains `{"error": "..."}`. |
| `500` | Unexpected render failure. Details are in CloudWatch, not the response. |

---

## Configuration

| Environment variable | Required | Default | Purpose |
|---|---|---|---|
| `OUTPUT_BUCKET` | yes | — | S3 bucket rendered PDFs are written to. Give it a lifecycle rule expiring `documents/` after a day or so. |
| `URL_EXPIRY_SECONDS` | no | `3600` | Presigned URL lifetime. |

The Lambda execution role needs `s3:PutObject` and `s3:GetObject` on the output bucket prefix.

---

## Container image

```bash
make build    # docker build --platform linux/arm64 -t pdfgen-api .
```

The platform pin matters: the image architecture must match the Lambda's `architectures` setting (`arm64` by default in `infra/`), or invocations fail with `Runtime.InvalidEntrypoint`.

The image is based on `public.ecr.aws/lambda/python:3.12` and:

- installs pdfgen plus the `api` extra (boto3) into site-packages,
- copies `assets/` and `api/` into the task root,
- sets `MPLCONFIGDIR=/tmp/mpl` (matplotlib writes a font cache on first import, and `/tmp` is the only writable path at Lambda runtime),
- uses `api.handler.lambda_handler` as the entry point.

Updating a bundled brand asset means rebuilding and redeploying the image — that is deliberate: assets version with the code.

---

## Deployment

The full stack — ECR repository, Lambda, HTTP API Gateway (`POST /render`, IAM-authenticated), and the output bucket with its lifecycle rule — is defined in [`infra/`](../infra/README.md). Day-to-day deploys are `make deploy` from the repo root; the infra README covers the one-time bootstrap (remote state, first image push) and how to call the IAM-authenticated endpoint.

---

## Running the handler locally

### Step-by-step: render an example through the local API

Copy-paste from the repo root. Requires Docker running and the
[terraform-ministack](../../terraform-ministack) repo checked out as a
sibling directory.

```bash
# 1. Start the emulator, deploy the stack, and run a smoke test.
#    First run takes a few minutes (image builds). Re-run after code changes.
make local

# 2. Capture the API endpoint into a variable.
#    (It contains a random id that changes every emulator restart —
#    never hardcode it.)
ENDPOINT=$(make -s local-endpoint)
echo "$ENDPOINT"
#   → http://30655bb2.execute-api.localhost:4566/render

# 3. Extract the hostname for curl.
#    (macOS can't resolve *.execute-api.localhost on its own, so we tell
#    curl explicitly that it lives at 127.0.0.1.)
HOST=$(echo "$ENDPOINT" | sed -E 's|https?://([^:/]+).*|\1|')

# 4. POST your JSON. The response is NOT the PDF — it's JSON containing
#    a presigned URL where the PDF is waiting.
RESPONSE=$(curl -sS --resolve "$HOST:4566:127.0.0.1" \
  -X POST "$ENDPOINT" -d @examples/charts.json)
echo "$RESPONSE"
#   → {"url": "http://host.docker.internal:4566/...", "key": "documents/...", ...}

# 5. Pull the URL out of the response and fix the hostname.
#    (host.docker.internal is the emulator's address as seen from inside
#    the Lambda container — from your machine it's just localhost.)
URL=$(echo "$RESPONSE" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' \
  | sed 's|host.docker.internal|localhost|')

# 6. Download the PDF.
curl -sS "$URL" -o report.pdf
open report.pdf

# 7. When you're done, tear everything down.
make local-down
```

To render a different document, change the file in step 4 (`-d @examples/tables.json`, `-d @my-report.json`, …) and repeat steps 4–6.

**Shortcut:** steps 2–6 are exactly what `make local-test` does — one command, any file:

```bash
make local-test FILE=examples/charts.json OUT=report.pdf
```

### Handler-only, without the emulator

The handler is plain Python — point it at a bucket and invoke it directly, or use the Lambda runtime interface emulator baked into the base image:

```bash
docker run -p 9000:8080 -e OUTPUT_BUCKET=my-test-bucket \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... pdfgen-api

curl -s "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"body": "{\"content\": [{\"type\": \"paragraph\", \"text\": \"Hello\"}]}"}'
```

The test suite covers the handler with a stubbed S3 client — no AWS credentials needed:

```bash
pip install -e '.[dev]'
pytest tests/test_api_handler.py
```
