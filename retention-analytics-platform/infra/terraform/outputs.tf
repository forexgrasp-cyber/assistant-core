output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "api_service_name" {
  value = module.api_service.service_name
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
