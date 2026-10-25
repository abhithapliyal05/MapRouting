locals {
  repo_root = abspath("${path.module}/../..")
  # kind passes this path to Docker; forward slashes work on every OS, backslashes break on Windows.
  data_dir = replace(coalesce(var.data_dir, "${local.repo_root}/data"), "\\", "/")
}

# --- Cluster ---------------------------------------------------------------------------------
resource "kind_cluster" "this" {
  name           = var.cluster_name
  node_image     = var.node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      # Host 127.0.0.1:<port> -> node :30080 (Traefik's NodePort). Localhost only: not exposed to the LAN.
      extra_port_mappings {
        container_port = 30080
        host_port      = var.ingress_host_port
        listen_address = "127.0.0.1"
        protocol       = "TCP"
      }

      # Local-only shortcut: the host's map data becomes visible in the node, and a PV points at it.
      extra_mounts {
        host_path      = local.data_dir
        container_path = "/data-host"
      }
    }
  }
}

# The helm provider is configured from the cluster the kind provider just created.
provider "helm" {
  kubernetes = {
    host                   = kind_cluster.this.endpoint
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
  }
}

# --- Cluster add-ons ---------------------------------------------------------------------------
# Prometheus, Alertmanager and Grafana. Installed first because Traefik and the app ship
# ServiceMonitor / PrometheusRule objects that need its CRDs.
resource "random_password" "grafana" {
  length  = 20
  special = false
}

resource "helm_release" "monitoring" {
  name             = "monitoring"
  namespace        = "monitoring"
  create_namespace = true
  repository       = "oci://ghcr.io/prometheus-community/charts"
  chart            = "kube-prometheus-stack"
  version          = "92.13.1"
  values = [
    file("${local.repo_root}/k8s/monitoring-values.yaml"),
    # LOCAL ONLY: anonymous read-only access, so the dashboard can be opened (and screenshotted) without
    # typing a password. Viewers cannot change anything, and Grafana is reachable only through a
    # localhost port-forward. Never enable this on a shared or cloud cluster.
    yamlencode({
      grafana = {
        "grafana.ini" = {
          "auth.anonymous" = { enabled = true, org_role = "Viewer" }
        }
      }
    }),
  ]

  # Generated per apply and kept in (git-ignored) state; never written into a file in the repo.
  set_sensitive = [{
    name  = "grafana.adminPassword"
    value = random_password.grafana.result
  }]

  wait    = true
  timeout = 900
}

resource "helm_release" "traefik" {
  name             = "traefik"
  namespace        = "traefik"
  create_namespace = true
  repository       = "oci://ghcr.io/traefik/helm"
  chart            = "traefik"
  version          = "42.0.0"

  values = [
    file("${local.repo_root}/k8s/traefik-values.yaml"),
    # Request rate, latency and error rate on the dashboard come from Traefik's own metrics. The
    # default latency buckets (0.1/0.3/1.2/5 s) are too coarse for meaningful p95/p99.
    yamlencode({
      metrics = {
        prometheus = {
          buckets = "0.05,0.1,0.25,0.5,1,2.5,5,10"
          service = { enabled = true }
          # honorLabels: Traefik labels its metrics with `service`, and so does every ServiceMonitor
          # target. Without this Prometheus renames Traefik's label to `exported_service`, and every
          # dashboard and alert query on `service` silently matches nothing.
          serviceMonitor = { enabled = true, honorLabels = true }
        }
      }
    }),
  ]

  wait    = true
  timeout = 300

  depends_on = [helm_release.monitoring]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  namespace  = "kube-system"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = "3.14.0" # app v0.9.0, same as k8s/metrics-server.yaml

  # DEV ONLY: kind's kubelets use self-signed certificates. Never set this on a real cluster.
  set = [{
    name  = "args[0]"
    value = "--kubelet-insecure-tls"
  }]

  wait    = true
  timeout = 300
}

# --- The application ---------------------------------------------------------------------------
resource "helm_release" "routing" {
  name             = "routing"
  namespace        = "routing"
  create_namespace = true
  chart            = "${local.repo_root}/charts/routing"
  values           = [file("${local.repo_root}/charts/routing/${var.chart_values_file}")]

  # Dashboard and alert rules need the Prometheus CRDs, which the monitoring release provides.
  set = [{
    name  = "monitoring.enabled"
    value = "true"
  }]

  wait    = true
  timeout = 900 # Valhalla loads existing tiles quickly; a first-ever tile build would not

  depends_on = [helm_release.traefik, helm_release.metrics_server, helm_release.monitoring]
}
