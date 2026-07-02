# Remote state. Create the state bucket first with the bootstrap stack
# (see bootstrap/), then uncomment and `terraform init -migrate-state`.
#
# terraform {
#   backend "s3" {
#     bucket       = "<state bucket from bootstrap output>"
#     key          = "pdfgen-api/terraform.tfstate"
#     region       = "us-east-1"
#     use_lockfile = true
#   }
# }
