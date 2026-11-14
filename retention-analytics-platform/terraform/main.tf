# Terraform Configuration for Retention Analytics Platform
# Optimized for: Spot workers, Reserved API/DB, Right-sized resources, SQS/SNS

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }
  backend "s3" {
    bucket = "retention-analytics-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project        = "retention-analytics"
      Environment    = var.environment
      ManagedBy      = "terraform"
      CostCenter     = "engineering"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

# ============================================================
# Variables
# ============================================================
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "retention-analytics-prod"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

# ============================================================
# Data Sources
# ============================================================
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# ============================================================
# VPC & Networking
# ============================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr_block = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway     = true
  single_nat_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # VPC Endpoints for cost optimization (no NAT for AWS services)
  vpc_endpoints = {
    s3 = {
      service             = "s3"
      vpc_endpoint_type   = "Gateway"
      policy              = jsonencode({
        Version = "2012-10-17"
        Statement = [{
          Effect = "Allow"
          Principal = "*"
          Action = "s3:*"
          Resource = "*"
        }]
      })
    }
    dynamodb = {
      service             = "dynamodb"
      vpc_endpoint_type   = "Gateway"
    }
    sqs = {
      service             = "sqs"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    sns = {
      service             = "sns"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    secretsmanager = {
      service             = "secretsmanager"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    logs = {
      service             = "logs"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    monitoring = {
      service             = "monitoring"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    ecr = {
      service             = "ecr.api"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
    ecr_dkr = {
      service             = "ecr.dkr"
      vpc_endpoint_type   = "Interface"
      private_dns_enabled = true
    }
  }

  tags = {
    Name = "${var.cluster_name}-vpc"
  }
}

# ============================================================
# EKS Cluster
# ============================================================
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.28"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true
  cluster_endpoint_private_access = true

  eks_managed_node_group_defaults = {
    ami_type       = "AL2_x86_64"
    root_volume_type = "gp3"
    root_volume_size = 100
  }

  # Node groups defined in node_groups.tf
  node_groups = {}

  # Add-ons
  enable_irsa = true

  cluster_addons = {
    vpc-cni = {
      most_recent = true
    }
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  tags = {
    Environment = var.environment
  }
}

# ============================================================
# RDS Database (Right-Sized: db.r6g.xlarge)
# ============================================================
resource "aws_db_instance" "primary" {
  identifier             = "${var.cluster_name}-db-primary"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = "db.r6g.xlarge"
  allocated_storage      = 500
  max_allocated_storage  = 1000
  storage_type           = "gp3"
  storage_encrypted      = true
  iops                   = 10000
  storage_throughput     = 500

  db_name  = "retention"
  username = "retention"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.cluster_name}-db-final-${formatdate("YYYY-MM-DD", timestamp())}"

  deletion_protection = true
  copy_tags_to_snapshot = true

  performance_insights_enabled = true
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  parameter_group_name = aws_db_parameter_group.postgres16.name

  tags = {
    Name        = "${var.cluster_name}-db-primary"
    Role        = "primary"
    Environment = var.environment
  }
}

resource "aws_db_instance" "replica" {
  identifier             = "${var.cluster_name}-db-replica"
  replicate_source_db    = aws_db_instance.primary.identifier
  instance_class         = "db.r6g.large"
  allocated_storage      = 500
  storage_type           = "gp3"
  storage_encrypted      = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  tags = {
    Name        = "${var.cluster_name}-db-replica"
    Role        = "replica"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.cluster_name}-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
  tags = {
    Name = "${var.cluster_name}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "postgres16" {
  family = "postgres16"
  name   = "${var.cluster_name}-postgres16"

  parameter {
    name  = "max_connections"
    value = "200"
  }
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }
  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4}"
  }
  parameter {
    name  = "work_mem"
    value = "64MB"
  }
  parameter {
    name  = "maintenance_work_mem"
    value = "2GB"
  }
  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }
  parameter {
    name  = "wal_buffers"
    value = "64MB"
  }
  parameter {
    name  = "default_statistics_target"
    value = "100"
  }
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }
  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }
  parameter {
    name  = "synchronous_commit"
    value = "on"
  }
  parameter {
    name  = "wal_level"
    value = "replica"
  }
  parameter {
    name  = "max_wal_senders"
    value = "3"
  }
  parameter {
    name  = "wal_keep_size"
    value = "1GB"
  }
}

# ============================================================
# ElastiCache Redis Cluster (r6g.large, 3 nodes)
# ============================================================
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.cluster_name}-redis"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.r6g.large"
  number_cache_clusters      = 3
  automatic_failover_enabled = true
  multi_az_enabled           = true

  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.redis7.name

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_password

  snapshot_retention_limit = 7
  snapshot_window          = "03:00-04:00"
  maintenance_window       = "sun:04:00-sun:05:00"

  tags = {
    Name        = "${var.cluster_name}-redis"
    Environment = var.environment
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cluster_name}-elasticache-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_parameter_group" "redis7" {
  name   = "${var.cluster_name}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  parameter {
    name  = "appendonly"
    value = "yes"
  }
  parameter {
    name  = "appendfsync"
    value = "everysec"
  }
  parameter {
    name  = "maxmemory"
    value = "10737418240"  # 10GB
  }
  parameter {
    name  = "timeout"
    value = "0"
  }
  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }
}

# ============================================================
# SQS/SNS for Messaging (Replaces RabbitMQ)
# ============================================================
resource "aws_sqs_queue" "worker_jobs" {
  name                      = "${var.cluster_name}-worker-jobs"
  fifo_queue                = false
  content_based_deduplication = false
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue" "worker_jobs_dlq" {
  name                      = "${var.cluster_name}-worker-jobs-dlq"
  fifo_queue                = false
  message_retention_seconds  = 1209600
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue_redrive_policy" "worker_jobs" {
  queue_url = aws_sqs_queue.worker_jobs.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.worker_jobs_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sns_topic" "workflow_events" {
  name = "${var.cluster_name}-workflow-events"
  fifo_topic = false
}

resource "aws_sns_topic_subscription" "worker_jobs" {
  topic_arn = aws_sns_topic.workflow_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.worker_jobs.arn
  filter_policy = jsonencode({
    event_type = [{
      "anything-but": ["internal"]
    }]
  })
}

# ============================================================
# S3 Buckets with Intelligent Tiering
# ============================================================
resource "aws_s3_bucket" "data" {
  bucket = "${var.cluster_name}-data-${data.aws_caller_identity.current.account_id}"
  force_destroy = false

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "intelligent-tiering"
    enabled = true

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 2555  # 7 years
    }
  }

  lifecycle_rule {
    id      = "incomplete-multipart-upload"
    enabled = true
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  tags = {
    Name        = "${var.cluster_name}-data"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "backups" {
  bucket = "${var.cluster_name}-backups-${data.aws_caller_identity.current.account_id}"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "backup-retention"
    enabled = true
    expiration {
      days = 90
    }
  }

  tags = {
    Name        = "${var.cluster_name}-backups"
    Environment = var.environment
  }
}

# ============================================================
# IAM Roles & Policies
# ============================================================
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.cluster_name}-rds-monitoring"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ============================================================
# Security Groups
# ============================================================
resource "aws_security_group" "eks" {
  name        = "${var.cluster_name}-eks"
  description = "EKS cluster security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-eks"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.cluster_name}-rds"
  description = "RDS security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-rds"
  }
}

resource "aws_security_group" "elasticache" {
  name        = "${var.cluster_name}-elasticache"
  description = "ElastiCache security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-elasticache"
  }
}

# ============================================================
# CloudWatch Log Groups
# ============================================================
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/ecs/${var.cluster_name}/api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/ecs/${var.cluster_name}/worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 30
}

# ============================================================
# Outputs
# ============================================================
output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "db_primary_endpoint" {
  value = aws_db_instance.primary.endpoint
  sensitive = true
}

output "db_replica_endpoint" {
  value = aws_db_instance.replica.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive = true
}

output "sqs_worker_jobs_url" {
  value = aws_sqs_queue.worker_jobs.url
}

output "sns_workflow_events_arn" {
  value = aws_sns_topic.workflow_events.arn
}

output "s3_data_bucket" {
  value = aws_s3_bucket.data.bucket
}