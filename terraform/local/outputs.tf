output "app_url" {
  description = "Open this in a browser (browsers resolve *.localhost to loopback)."
  value       = "http://app.localhost:${var.ingress_host_port}"
}

output "grafana_admin_password" {
  description = "Grafana login (user: admin). Show with: terraform output -raw grafana_admin_password"
  value       = random_password.grafana.result
  sensitive   = true
}

output "grafana_port_forward" {
  description = "Command to reach Grafana at http://localhost:3000"
  value       = "kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80"
}

output "kubectl_context" {
  description = "kubectl context of the new cluster."
  value       = "kind-${kind_cluster.this.name}"
}
