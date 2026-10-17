// Default runtime config, used by Docker Compose (backends published on localhost).
// Kubernetes overrides this file with a ConfigMap (see charts/routing).
window.APP_CONFIG = {
  valhallaUrl: "http://localhost:8002",
  astarUrl: "http://localhost:8003",
};
