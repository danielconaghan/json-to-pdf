terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # When local_endpoint is set, all requests go to a local emulator (e.g.
  # ministack) instead of AWS. Setting access_key to a 12-digit number makes
  # the emulator use it as the account ID.
  access_key                  = var.local_endpoint != null ? "000000000000" : null
  secret_key                  = var.local_endpoint != null ? "test" : null
  skip_credentials_validation = var.local_endpoint != null
  skip_metadata_api_check     = var.local_endpoint != null
  skip_requesting_account_id  = var.local_endpoint != null
  s3_use_path_style           = var.local_endpoint != null

  dynamic "endpoints" {
    for_each = var.local_endpoint != null ? [1] : []
    content {
      lambda       = var.local_endpoint
      apigateway   = var.local_endpoint
      apigatewayv2 = var.local_endpoint
      iam          = var.local_endpoint
      sts          = var.local_endpoint
      ecr          = var.local_endpoint
      s3           = var.local_endpoint
      logs         = var.local_endpoint
    }
  }
}
