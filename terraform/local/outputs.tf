output "app_url" {
  description = "Open this in a browser (browsers resolve *.localhost to loopback)."
  value       = "http://app.localhost:${var.ingress_host_port}"
}

output "kubectl_context" {
  description = "kubectl context of the new cluster."
  value       = "kind-${kind_cluster.this.name}"
}
