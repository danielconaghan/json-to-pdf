# Build, push, and deploy the pdfgen Lambda image.
#
#   make build                  build the container image (arm64)
#   make push                   build, then push to the ECR repo Terraform created
#   make deploy                 push, then terraform apply
#   make plan                   terraform plan
#
#   make local                  one command: start ministack emulator, deploy, smoke test
#   make local-down             destroy local stack and stop the emulator
#
# Override defaults per-invocation, e.g.: make push TAG=v0.2.0 REGION=eu-west-2

REGION   ?= us-east-1
TAG      ?= latest
PLATFORM ?= linux/arm64
IMAGE    ?= pdfgen-api

ACCOUNT   = $(shell aws sts get-caller-identity --query Account --output text)
ECR_REPO  = $(ACCOUNT).dkr.ecr.$(REGION).amazonaws.com/$(IMAGE)

.PHONY: build push deploy plan test local local-up local-deploy local-test local-down

build:
	docker build --platform $(PLATFORM) -t $(IMAGE):$(TAG) .

push: build
	aws ecr get-login-password --region $(REGION) | \
		docker login --username AWS --password-stdin $(ACCOUNT).dkr.ecr.$(REGION).amazonaws.com
	docker tag $(IMAGE):$(TAG) $(ECR_REPO):$(TAG)
	docker push $(ECR_REPO):$(TAG)

deploy: push
	terraform -chdir=infra apply -var "image_tag=$(TAG)" -var "aws_region=$(REGION)"

plan:
	terraform -chdir=infra plan -var "image_tag=$(TAG)" -var "aws_region=$(REGION)"

test:
	python -m pytest

# ── Local development against the ministack emulator ────────────────────────
# Requires the terraform-ministack repo checked out as a sibling directory
# (override with MINISTACK_DIR=...). Terraform runs in Docker, so no local
# terraform install is needed.

MINISTACK_DIR ?= ../terraform-ministack
LOCAL_COMPOSE  = docker compose -f $(MINISTACK_DIR)/docker-compose.yml -f infra/local/ministack-override.yml
LOCAL_ECR      = 000000000000.dkr.ecr.us-east-1.amazonaws.com/$(IMAGE)
# Fresh tag per invocation so the emulator picks up rebuilt images instead of
# reusing the warm container for an unchanged URI.
LOCAL_TAG     := local-$(shell date +%Y%m%d%H%M%S)
LOCAL_TF       = docker run --rm -v $(CURDIR)/infra:/wd -w /wd --network ministack-net hashicorp/terraform:latest
LOCAL_TF_VARS  = -var 'local_endpoint=http://ministack:4566' -var 'enable_iam_auth=false'

local: local-up local-deploy local-test

local-up:
	$(LOCAL_COMPOSE) up -d --build
	@for i in $$(seq 1 30); do nc -z localhost 4566 2>/dev/null && break; sleep 1; done
	@nc -z localhost 4566 2>/dev/null || { echo "ministack did not become ready on :4566"; exit 1; }
	@echo "ministack ready on http://localhost:4566"

local-deploy:
	docker build --platform $(PLATFORM) -t $(IMAGE):$(LOCAL_TAG) .
	docker tag $(IMAGE):$(LOCAL_TAG) $(LOCAL_ECR):$(LOCAL_TAG)
	$(LOCAL_TF) init -input=false > /dev/null
	$(LOCAL_TF) apply -auto-approve $(LOCAL_TF_VARS) -var 'image_tag=$(LOCAL_TAG)'

local-test:
	@ENDPOINT=$$($(LOCAL_TF) output -raw render_endpoint); \
	HOST=$$(echo $$ENDPOINT | sed -E 's|https?://([^:/]+).*|\1|'); \
	echo "POST $$ENDPOINT"; \
	RESP=$$(curl -sS --max-time 120 --resolve $$HOST:4566:127.0.0.1 -X POST "$$ENDPOINT" -d @examples/minimal.json); \
	echo "$$RESP"; \
	URL=$$(echo "$$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' | sed 's|host.docker.internal|localhost|'); \
	curl -sS "$$URL" -o local-test.pdf; \
	file local-test.pdf

local-down:
	-$(LOCAL_TF) destroy -auto-approve $(LOCAL_TF_VARS)
	$(LOCAL_COMPOSE) down
