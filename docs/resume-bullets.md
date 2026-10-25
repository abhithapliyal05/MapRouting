# Resume bullets (draft)

Pick three. Every figure below is something that actually happened in this repo; adjust the wording to your voice and be ready to explain each one.

**Containers and CI/CD**
- Built a GitHub Actions pipeline (hadolint, multi-service image builds, Trivy vulnerability gating, SHA/hash-pinned third-party tooling) that publishes only scanned images to GHCR with commit-SHA tags, using least-privilege tokens with write access confined to the publish job.
- Caught 41 fixable vulnerabilities (2 critical, OpenSSL) in a container base image through automated scanning, and traced them to a frozen upstream release line; resolved by upgrading the base.

**Kubernetes and Helm**
- Packaged a three-service routing platform as a Helm chart with dev and prod values, host-based Traefik Ingress, ConfigMap/Secret-driven config with checksum-triggered rollouts, and HPAs, validated in CI with `helm lint --strict` and `kubeconform` against rendered output.
- Verified autoscaling with a short load smoke test on a kind cluster (the A* service scaled from 1 to 3 replicas in about 30 seconds); the measurements showed each replica saturating about one CPU core against a 100m request, flagging the request as far too low. (Replace with real load-test numbers after Day 9.)

**Debugging and judgement**
- Diagnosed spurious pod restarts to a CRLF/LF difference in Helm template text hashed into pod annotations, and fixed it repo-wide with `.gitattributes`, verified by a no-op second `helm upgrade`.
- Replaced an archived ingress controller (ingress-nginx) with an actively maintained one after checking upstream project status before installing.

**Do not claim:** any cloud deployment (AWS or GCP). Nothing in this project was ever deployed to a cloud. "Wrote and validated" is true only for code that exists in the repo.
