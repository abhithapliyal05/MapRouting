variable "cluster_name" {
  description = "Name of the kind cluster."
  type        = string
  default     = "routing"
}

variable "node_image" {
  description = "kind node image, pinned by digest. Pulled via mirror.gcr.io because Docker Hub's CDN is unreachable from the author's network."
  type        = string
  default     = "mirror.gcr.io/kindest/node:v1.34.11@sha256:44e222ee2132dab25ff87301682f89eb82c7880ea3a1bf543bfe9708fd08d67d"
}

variable "data_dir" {
  description = "Absolute path of the folder holding the map data and Valhalla tiles. It is mounted into the node at /data-host."
  type        = string
  default     = null # resolved to <repo>/data in locals
}

variable "ingress_host_port" {
  description = "Host port (bound to 127.0.0.1) that reaches the Traefik NodePort."
  type        = number
  default     = 8088
}

variable "chart_values_file" {
  description = "Values file for the routing chart."
  type        = string
  default     = "values-dev.yaml"
}
