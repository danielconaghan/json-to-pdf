# pdfgen infrastructure

Terraform for the pdfgen HTTP API: ECR repository, Lambda (container image),
HTTP API Gateway, and the S3 output bucket. See
[docs/10-lambda-api.md](../docs/10-lambda-api.md) for the API contract.

## Stack

| Resource | Purpose |
|---|---|
| ECR repository | Holds the Lambda container image (keeps 10 most recent) |
| Lambda function | Renders PDFs; container image, arm64, 2GB / 60s by default |
| HTTP API Gateway | `POST /render`, IAM-authenticated by default |
| S3 output bucket | Rendered PDFs, expired after `output_expiry_days` (default 1) |
| IAM role + policies | Basic execution logs + `Put/GetObject` on `documents/*` only |
| CloudWatch log group | 30-day retention by default |

## First deploy

There is a one-time ordering constraint: the Lambda can't be created until an
image exists in ECR.

```bash
# 0. (once) create the remote-state bucket, then fill in ../infra/backend.tf
cd infra/bootstrap
terraform init && terraform apply -var 'state_bucket_name=<unique name>'

# 1. create the ECR repo first
cd infra
terraform init
terraform apply -target=aws_ecr_repository.api

# 2. build and push the image (from the repo root)
make push REGION=<region>

# 3. create everything else
terraform apply
```

Subsequent deploys are just `make deploy` (or `make deploy TAG=v0.2.0`).
Note `image_tag` defaults to `latest`; pushing a new `latest` does **not**
redeploy the Lambda by itself — use immutable tags per release, or run
`aws lambda update-function-code --publish` after pushing.

## Architecture matters

`architecture` defaults to `arm64` and the Makefile builds `linux/arm64`.
These must agree — an amd64 image on an arm64 Lambda fails at invoke time
with an opaque `Runtime.InvalidEntrypoint`. If you build on CI x86 runners
without `--platform`, set `architecture = "x86_64"` or fix the platform flag.

## Calling the API

The render route requires SigV4-signed requests (`AWS_IAM`) by default —
callers need `execute-api:Invoke` on the API. Quick test with awscurl:

```bash
awscurl --service execute-api --region <region> \
  -X POST "$(terraform output -raw render_endpoint)" \
  -d @examples/minimal.json
```

Set `enable_iam_auth = false` only for local emulator testing.

## Local emulator (ministack)

One command runs the whole stack locally, end to end:

```bash
make local        # from the repo root
```

It starts the ministack emulator, builds and tags the image, applies this
Terraform against it, POSTs `examples/minimal.json` to the deployed API, and
downloads the resulting PDF to `local-test.pdf`. Tear down with
`make local-down`. Requirements: Docker, `make`, `nc`, and the
[terraform-ministack](../../terraform-ministack) repo checked out as a
sibling directory (override with `MINISTACK_DIR=...`). Terraform itself runs
in Docker — no local install needed.

The individual stages are also callable: `make local-up`, `make local-deploy`
(rerun after code changes), `make local-test`.

How it works, for when you need to poke at it by hand:

- The emulator starts with `infra/local/ministack-override.yml` applied,
  which sets `LAMBDA_DOCKER_PLATFORM=linux/arm64` to match our images
  (the ministack compose file defaults to amd64 for its PHP demo).
- No real image push happens: ministack resolves image URIs against the
  host docker daemon before pulling, so a `docker tag` to the fake ECR URI
  (`000000000000.dkr.ecr.us-east-1.amazonaws.com/pdfgen-api:<tag>`) is enough.
  Each deploy uses a fresh timestamp tag so rebuilt images actually load.
- Terraform runs on the `ministack-net` Docker network with
  `-var 'local_endpoint=http://ministack:4566' -var 'enable_iam_auth=false'`.
- The `render_endpoint` output uses a `*.execute-api.localhost` hostname,
  which macOS does not resolve — curl needs
  `--resolve <api-id>.execute-api.localhost:4566:127.0.0.1`.
- Presigned URLs in responses point at `host.docker.internal:4566` (the
  endpoint as seen from inside the Lambda container); swap the host for
  `localhost` when fetching from the host machine.
- Emulator state is in-memory: restarting ministack loses all deployed
  resources, and the next `terraform apply` recreates them (you'll see a
  harmless "resource not found during refresh" warning).
