# Build, push, and deploy the pdfgen Lambda image.
#
#   make build                  build the container image (arm64)
#   make push                   build, then push to the ECR repo Terraform created
#   make deploy                 push, then terraform apply
#   make plan                   terraform plan
#
# Override defaults per-invocation, e.g.: make push TAG=v0.2.0 REGION=eu-west-2

REGION   ?= us-east-1
TAG      ?= latest
PLATFORM ?= linux/arm64
IMAGE    ?= pdfgen-api

ACCOUNT   = $(shell aws sts get-caller-identity --query Account --output text)
ECR_REPO  = $(ACCOUNT).dkr.ecr.$(REGION).amazonaws.com/$(IMAGE)

.PHONY: build push deploy plan test

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
