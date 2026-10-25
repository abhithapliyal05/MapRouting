# Resume bullets (draft)

Pick three. Every figure below is something that actually happened in this repo; adjust the wording to your voice and be ready to explain each one.

**Containers and CI/CD**
- Built a GitHub Actions pipeline (hadolint, multi-service image builds, Trivy vulnerability gating, SHA/hash-pinned third-party tooling) that publishes only scanned images to GHCR with commit-SHA tags, using least-privilege tokens with write access confined to the publish job.
- Caught 41 fixable vulnerabilities (2 critical, OpenSSL) in a container base image through automated scanning, and traced them to a frozen upstream release line; resolved by upgrading the base.

**Kubernetes and Helm**
- Packaged a three-service routing platform as a Helm chart with dev and prod values, host-based Traefik Ingress, ConfigMap/Secret-driven config with checksum-triggered rollouts, and HPAs, validated in CI with `helm lint --strict` and `kubeconform` against rendered output.
- Load-tested the routing services with k6 (constant-arrival-rate steps, 300 verified trips) and found the saturation points: ~3 req/s per replica for a single-threaded Python backend versus ~30 req/s for Valhalla. Re-derived CPU requests and HPA thresholds from the data (the old 100m request would have scaled out at ~0.3 req/s), then validated that the autoscaler added replicas within seconds and restored p95 latency to 0.49 s after about 80 s of overload.

**Debugging and judgement**
- Diagnosed spurious pod restarts to a CRLF/LF difference in Helm template text hashed into pod annotations, and fixed it repo-wide with `.gitattributes`, verified by a no-op second `helm upgrade`.
- Replaced an archived ingress controller (ingress-nginx) with an actively maintained one after checking upstream project status before installing.

**Do not claim:** any cloud deployment (AWS or GCP). Nothing in this project was ever deployed to a cloud. "Wrote and validated" is true only for code that exists in the repo.

**More from later days** (each is real; pick what fits the role)
- Built a no-cloud CD pipeline in GitHub Actions: an ephemeral kind cluster deploys the exact scanned images, smoke-tests real routes through the Ingress, deliberately breaks a release, verifies the service stays up, and recovers with `helm rollback`.
- Added Prometheus/Grafana monitoring with ingress-level RED metrics and alert rules; a deliberate outage showed the first error-rate alert was blind to Traefik-generated 503s, so an ingress-level alert was added and both alerts were observed firing.
- Managed the local environment as code with Terraform (kind, Traefik, metrics-server, Helm releases; `plan` shows no drift, `destroy` and re-`apply` verified), and wrote and security-scanned an EKS/VPC/ECR/OIDC reference design that was **never applied**.
- Caught a kubeconfig with client credentials about to be committed before it was pushed, rewrote the local commit, and added a repository-wide secret scan to CI.
