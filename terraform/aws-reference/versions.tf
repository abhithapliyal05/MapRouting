terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.70"
    }
  }

  # REFERENCE ONLY, never applied. A real deployment would keep state in S3 with native locking:
  #
  #   backend "s3" {
  #     bucket       = "<state-bucket>"
  #     key          = "routing/terraform.tfstate"
  #     region       = "<region>"
  #     use_lockfile = true
  #     encrypt      = true
  #   }
  #
  # CI runs `terraform init -backend=false`, so no account or credentials are needed to validate.
}
