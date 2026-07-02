variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "local_endpoint" {
  description = "Override all AWS service endpoints to point at a local emulator (e.g. ministack). Leave null for real AWS."
  type        = string
  default     = null
}

variable "function_name" {
  description = "Name of the Lambda function; also prefixes the ECR repo, API, and output bucket"
  type        = string
  default     = "pdfgen-api"
}

variable "image_tag" {
  description = "Tag of the container image in ECR to deploy"
  type        = string
  default     = "latest"
}

variable "architecture" {
  description = "Lambda architecture. Must match the platform the image was built for (docker build --platform)."
  type        = string
  default     = "arm64"

  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture must be arm64 or x86_64."
  }
}

variable "memory_size" {
  description = "Lambda memory in MB. Rendering with matplotlib charts needs headroom; CPU scales with memory."
  type        = number
  default     = 2048
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "url_expiry_seconds" {
  description = "Lifetime of presigned URLs returned by the API"
  type        = number
  default     = 3600
}

variable "output_expiry_days" {
  description = "Days before rendered PDFs are deleted from the output bucket"
  type        = number
  default     = 1
}

variable "enable_iam_auth" {
  description = "Require SigV4-signed (AWS_IAM) requests on the render route. Disable only for local emulator testing."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the Lambda"
  type        = number
  default     = 30
}
