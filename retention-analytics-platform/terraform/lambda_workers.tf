# Lambda Worker Migration - Phase 2 Serverless
# Replaces 80% of spot workers with Lambda functions
# Triggered by SQS, processes workflow steps

resource "aws_iam_role" "lambda_worker" {
  name = "${var.cluster_name}-lambda-worker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_worker" {
  name = "${var.cluster_name}-lambda-worker-policy"
  role = aws_iam_role.lambda_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.cluster_name}-worker-*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.worker_jobs.arn,
          aws_sqs_queue.worker_jobs_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.workflow_events.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-data:BeginTransaction",
          "rds-data:CommitTransaction",
          "rds-data:RollbackTransaction"
        ]
        Resource = [
          aws_db_instance.primary.arn,
          aws_db_instance.replica.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:Connect"
        ]
        Resource = aws_elasticache_replication_group.redis.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.data.arn}/*",
          "${aws_s3_bucket.backups.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.cluster_name}-*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda Function for Workflow Step Execution
resource "aws_lambda_function" "worker_step" {
  function_name = "${var.cluster_name}-worker-step"
  description  = "Execute workflow steps from SQS queue"
  runtime      = "python3.11"
  handler      = "worker_step.lambda_handler"
  timeout      = 300  # 5 minutes max
  memory_size  = 1024  # 1GB

  role    = aws_iam_role.lambda_worker.arn
  filename = "lambda_worker_step.zip"
  source_code_hash = filebase64sha256("lambda_worker_step.zip")

  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV                     = var.environment
      DATABASE_HOST           = aws_db_instance.primary.endpoint
      DATABASE_NAME           = "retention"
      REDIS_HOST              = aws_elasticache_replication_group.redis.primary_endpoint_address
      REDIS_PORT              = "6379"
      SQS_QUEUE_URL           = aws_sqs_queue.worker_jobs.url
      SNS_TOPIC_ARN           = aws_sns_topic.workflow_events.arn
      AWS_REGION              = var.aws_region
      PII_ENCRYPTION_KEY      = var.pii_encryption_key
    }
  }

  # Reserve concurrency to prevent runaway
  reserved_concurrent_executions = 500
}

# Lambda Event Source Mapping (SQS -> Lambda)
resource "aws_lambda_event_source_mapping" "worker_step" {
  event_source_arn = aws_sqs_queue.worker_jobs.arn
  function_name    = aws_lambda_function.worker_step.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 30
  enabled          = true

  # Retry policy
  maximum_retry_attempts = 2
  bisect_batch_on_function_error = true

  # Destination for failed records
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.worker_jobs_dlq.arn
    }
  }
}

# Lambda Function for Email Sending
resource "aws_lambda_function" "email_sender" {
  function_name = "${var.cluster_name}-email-sender"
  description  = "Send emails via SES"
  runtime      = "python3.11"
  handler      = "email_sender.lambda_handler"
  timeout      = 60
  memory_size  = 512

  role    = aws_iam_role.lambda_worker.arn
  filename = "lambda_email_sender.zip"
  source_code_hash = filebase64sha256("lambda_email_sender.zip")

  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV              = var.environment
      AWS_REGION       = var.aws_region
      SES_FROM_EMAIL   = var.ses_from_email
    }
  }

  reserved_concurrent_executions = 200
}

# Lambda Event Source for Email Queue
resource "aws_sqs_queue" "email_queue" {
  name                      = "${var.cluster_name}-email-queue"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 86400
  sqs_managed_sse_enabled    = true
}

resource "aws_lambda_event_source_mapping" "email_sender" {
  event_source_arn = aws_sqs_queue.email_queue.arn
  function_name    = aws_lambda_function.email_sender.arn
  batch_size       = 5
  maximum_batching_window_in_seconds = 10
  enabled          = true
}

# Lambda Function for SMS Sending
resource "aws_lambda_function" "sms_sender" {
  function_name = "${var.cluster_name}-sms-sender"
  description  = "Send SMS via SNS"
  runtime      = "python3.11"
  handler      = "sms_sender.lambda_handler"
  timeout      = 30
  memory_size  = 512

  role    = aws_iam_role.lambda_worker.arn
  filename = "lambda_sms_sender.zip"
  source_code_hash = filebase64sha256("lambda_sms_sender.zip")

  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV          = var.environment
      AWS_REGION   = var.aws_region
    }
  }

  reserved_concurrent_executions = 100
}

# Lambda Function for Push Notifications
resource "aws_lambda_function" "push_sender" {
  function_name = "${var.cluster_name}-push-sender"
  description  = "Send push notifications via FCM/APNs"
  runtime      = "python3.11"
  handler      = "push_sender.lambda_handler"
  timeout      = 30
  memory_size  = 512

  role    = aws_iam_role.lambda_worker.arn
  filename = "lambda_push_sender.zip"
  source_code_hash = filebase64sha256("lambda_push_sender.zip")

  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV              = var.environment
      AWS_REGION       = var.aws_region
      FCM_SERVER_KEY   = var.fcm_server_key
      APNS_KEY_ID      = var.apns_key_id
      APNS_TEAM_ID     = var.apns_team_id
      APNS_BUNDLE_ID   = var.apns_bundle_id
    }
  }

  reserved_concurrent_executions = 100
}

# Lambda Security Group
resource "aws_security_group" "lambda" {
  name        = "${var.cluster_name}-lambda"
  description = "Lambda worker security group"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-lambda"
  }
}

# CloudWatch Log Groups for Lambda
resource "aws_cloudwatch_log_group" "lambda_worker" {
  name              = "/aws/lambda/${var.cluster_name}-worker-step"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_email" {
  name              = "/aws/lambda/${var.cluster_name}-email-sender"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "lambda_sms" {
  name              = "/aws/lambda/${var.cluster_name}-sms-sender"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "lambda_push" {
  name              = "/aws/lambda/${var.cluster_name}-push-sender"
  retention_in_days = 30
}

# CloudWatch Alarms for Lambda
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.cluster_name}-lambda-worker-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Lambda worker step errors > 10 in 10 minutes"
  alarm_actions       = [aws_sns_topic.workflow_events.arn]

  dimensions = {
    FunctionName = aws_lambda_function.worker_step.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.cluster_name}-lambda-worker-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda worker step throttles > 5 in 5 minutes"
  alarm_actions       = [aws_sns_topic.workflow_events.arn]

  dimensions = {
    FunctionName = aws_lambda_function.worker_step.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.cluster_name}-lambda-worker-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 240000  # 4 minutes (close to 5 min timeout)
  alarm_description   = "Lambda worker step avg duration > 4 minutes"
  alarm_actions       = [aws_sns_topic.workflow_events.arn]

  dimensions = {
    FunctionName = aws_lambda_function.worker_step.function_name
  }
}

# Step Functions for Complex Workflows (Optional - for future)
resource "aws_sfn_state_machine" "workflow_orchestrator" {
  name     = "${var.cluster_name}-workflow-orchestrator"
  role_arn = aws_iam_role.lambda_worker.arn

  definition = jsonencode({
    Comment = "Workflow orchestrator for multi-step campaigns"
    StartAt = "ExecuteStep"
    States = {
      ExecuteStep = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.worker_step.arn
          Payload = {
            "task_token.$" = "$$.Task.Token"
            "step.$" = "$"
          }
        }
        Next = "CheckResult"
      }
      CheckResult = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.status"
            StringEquals = "SUCCESS"
            Next = "NextStep"
          },
          {
            Variable = "$.status"
            StringEquals = "FAILURE"
            Next = "HandleFailure"
          }
        ]
        Default = "HandleFailure"
      }
      NextStep = {
        Type = "Pass"
        Result = "Step completed successfully"
        End = true
      }
      HandleFailure = {
        Type = "Pass"
        Result = "Step failed, sending to DLQ"
        End = true
      }
    }
  })

  logging_configuration {
    level = "ALL"
    include_execution_data = true
    destinations {
      cloudwatch_logs_log_group {
        log_group_arn = aws_cloudwatch_log_group.lambda_worker.arn
      }
    }
  }
}

# API Gateway for Step Functions (Optional)
resource "aws_apigatewayv2_api" "stepfunctions" {
  name          = "${var.cluster_name}-stepfunctions-api"
  protocol_type = "HTTP"
  target        = "arn:aws:apigateway:${var.aws_region}:states:path/2015-08-01/stateMachines/${aws_sfn_state_machine.workflow_orchestrator.name}/executions"
}

resource "aws_apigatewayv2_stage" "stepfunctions" {
  api_id      = aws_apigatewayv2_api.stepfunctions.id
  name        = "$default"
  auto_deploy = true
}