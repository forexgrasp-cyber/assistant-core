terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = var.tf_state_bucket
    key    = "retention-analytics/terraform.tfstate"
    region = var.aws_region
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name = "${var.app_name}-${var.environment}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = local.name
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

module "api_service" {
  source = "./modules/ecs-service"

  name            = "${local.name}-api"
  cluster_id      = aws_ecs_cluster.main.id
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  desired_count   = 2
  cpu             = "1024"
  memory          = "2048"
  container_image = "ghcr.io/${var.github_repository}/api:latest"
  container_port  = 47319

  environment = [
    { name = "ENVIRONMENT", value = var.environment },
  ]

  secrets = [
    { name = "JWT_SECRET", valueFrom = var.jwt_secret_arn },
    { name = "DATABASE_URL", valueFrom = var.database_url_arn },
  ]
}
