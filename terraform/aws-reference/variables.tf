variable "region" {
  description = "AWS region."
  type        = string
  default     = "ap-northeast-1"
}

variable "name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "routing"
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
  default     = "1.34"
}

variable "node_instance_types" {
  description = "Worker node instance types. The A* backend holds ~470 MiB per replica, so 8 GiB nodes leave headroom."
  type        = list(string)
  default     = ["t3.large"]
}

variable "github_repository" {
  description = "owner/repo allowed to assume the CI role through GitHub OIDC (no static keys)."
  type        = string
  default     = "abhithapliyal05/MapRouting"
}
