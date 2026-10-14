# CLAUDE.md

## Goal
Turn this routing platform (Valhalla + MapLibre GL JS + Photon + OSM data) into a production-style DevOps project for the Acumen Advisory Consulting DevOps Engineer internship (remote, 3 months). Application deadline is about Oct 26, 2026, so the build must be finished and public by Oct 24.

The internship asks for: CI/CD, AWS and GCP, Docker, Kubernetes, Infrastructure as Code, Linux administration, monitoring, networking, shell scripting, version control, and quantitative analysis. Every piece of work here should map to one of these.

## Owner context
Abhi is a CS student. He will be asked about every file in this repo in an interview, so he must understand all of it. Optimize for his understanding, not just working output.

## Working rules
1. **One plan day per session.** Do only the current day's scope. Do not start later days.
2. **One step at a time.** Give or do one step, then wait for Abhi's result before the next. Do not chain ahead.
3. **Explain as you go.** After each meaningful change, state in 2-3 sentences what it does and why that choice was made over the alternative. Name the trade-off.
4. **Be opinionated.** Pick one approach and justify it. Don't list five options.
5. **Small commits.** Commit at the end of each logical step with a clear message. Never commit secrets, state files, or `.tfvars` with real values.
6. **Verify, don't assume.** After each change, run the relevant check (`docker compose up`, `kubectl get pods`, `terraform plan`, `helm lint`) and show the result.
7. **Cost control.** Use kind (local) for Days 1-4. Only create EKS/GKE on Days 5-9. Always tell Abhi what costs money before creating it, and finish each cloud session with `terraform destroy` unless told otherwise.
8. **Security defaults.** Non-root containers, no static cloud keys in CI (use GitHub OIDC), least-privilege IAM, secrets via Kubernetes Secrets or a secret manager, never in the repo.
9. **Flag risky actions.** Ask before anything destructive or billable.

## Learning checkpoint (end of every day)
Before closing the day, ask Abhi to explain that day's changes without looking. Then give him one thing to break on purpose (kill a pod, misconfigure a port, remove a security group rule) and have him diagnose it from logs and events, not from memory.

## Plan

| Day | Focus | Done when |
|---|---|---|
| 1 | Docker + Linux: multi-stage builds per service, non-root users, healthchecks, Compose for local dev, bash bootstrap script (`set -euo pipefail`) | `docker compose up` brings up the full stack from a clean clone |
| 2 | CI: GitHub Actions with hadolint, image build, Trivy scan, push to registry on merge to `main` | Green pipeline publishing tagged images |
| 3 | Kubernetes on kind: Deployments, Services, PVC for tile data, liveness/readiness probes, resource requests/limits | App runs in local cluster and serves a route request |
| 4 | Helm chart: package manifests, add Ingress, ConfigMaps/Secrets, HPA | `helm install` works with dev and prod values files |
| 5 | Terraform on AWS: VPC, ECR, IAM, EKS, remote state in S3; deploy the chart | `terraform apply` yields a reachable app |
| 6 | CD: pipeline deploys to EKS via GitHub OIDC; practice a bad deploy and `helm rollback` | Merge to `main` auto-deploys; rollback demonstrated |
| 7 | Monitoring: kube-prometheus-stack, Grafana dashboards (request rate, p95/p99 latency, pod CPU/memory, error rate), one alert rule | Dashboard screenshots and a firing alert |
| 8 | Load test + analysis: k6 against the routing endpoint, find the saturation point, set HPA thresholds from data, write capacity report | One-page writeup with graphs |
| 9 | GCP: Terraform for GKE, same Helm chart, compare cost, setup friction and latency with AWS | Same chart running on both clouds |
| 10 | Polish: README with architecture diagram, destroy all cloud resources, 3 resume bullets, submit application | Public repo, application sent |

**If time slips:** cut Day 9 (GCP) first, then keep a documented GCP path in the README instead. Days 1-8 are the core.

## Definition of done (whole project)
- Fresh clone to running stack with one command locally
- CI builds, scans and publishes images; CD deploys to a cloud cluster
- All infrastructure reproducible from Terraform, with remote state
- Dashboards and an alert exist, plus a load-test report with real numbers
- README includes an architecture diagram, setup steps, and cost notes
- No secrets in git history
