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

The provider supports pointing every AWS call at a local emulator:

```bash
terraform apply -var 'local_endpoint=http://localhost:4566' -var 'enable_iam_auth=false'
```
