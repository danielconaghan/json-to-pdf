output "render_endpoint" {
  description = "Full URL of the render route"
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/render"
}

output "ecr_repository_url" {
  description = "ECR repository the container image is pushed to"
  value       = aws_ecr_repository.api.repository_url
}

output "output_bucket" {
  description = "S3 bucket rendered PDFs are written to"
  value       = aws_s3_bucket.output.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}
