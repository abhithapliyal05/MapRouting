output "cluster_name" {
  value = module.eks.cluster_name
}

output "ecr_repository_urls" {
  value = { for k, r in aws_ecr_repository.service : k => r.repository_url }
}

output "ci_publish_role_arn" {
  description = "Role GitHub Actions would assume through OIDC."
  value       = aws_iam_role.ci_publish.arn
}

output "map_data_bucket" {
  value = aws_s3_bucket.map_data.bucket
}
