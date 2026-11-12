module "platform" {
  source = "../../"

  aws_region          = "us-east-1"
  environment         = "production"
  app_name            = "retention-analytics"
  tf_state_bucket     = var.tf_state_bucket
  github_repository   = var.github_repository
  jwt_secret_arn      = var.jwt_secret_arn
  database_url_arn    = var.database_url_arn
}

variable "tf_state_bucket" {
  type = string
}

variable "github_repository" {
  type = string
}

variable "jwt_secret_arn" {
  type = string
}

variable "database_url_arn" {
  type = string
}
