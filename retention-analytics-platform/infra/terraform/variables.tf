variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tf_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "retention-analytics"
}

variable "github_repository" {
  description = "GitHub repository (owner/repo) for GHCR images"
  type        = string
}

variable "jwt_secret_arn" {
  description = "Secrets Manager ARN for JWT_SECRET"
  type        = string
}

variable "database_url_arn" {
  description = "Secrets Manager ARN for DATABASE_URL"
  type        = string
}
