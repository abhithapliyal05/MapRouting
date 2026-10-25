# CLAUDE.md

## Goal
Turn this routing platform (Valhalla + MapLibre GL JS + Photon + OSM data) into a resume-quality DevOps project. It is a student project: it does not need to be public or meet an external deadline, it needs to work, be reproducible, and be fully understood by its owner.

**No cloud spend.** Everything runs locally (Docker, kind) or on free GitHub Actions runners. Cloud infrastructure code (AWS/EKS) may be written and statically validated in CI but is never applied. The README must state plainly what ran where. Never describe unapplied code as deployed.

Skills to demonstrate: CI/CD, Docker, Kubernetes, Helm, Infrastructure as Code, Linux administration, monitoring, networking, shell scripting, version control, and quantitative analysis. Every piece of work should map to one of these.

## Owner context
Abhi is a CS student. He will be asked about every file in this repo in an interview, so he must understand all of it. Optimize for his understanding, not just working output.

## Working rules
1. **One plan day per session.** Do only the current day's scope. Do not start later days.
2. **One step at a time.** Give or do one step, then wait for Abhi's result before the next. Do not chain ahead.
3. **Explain as you go.** After each meaningful change, state in 2-3 sentences what it does and why that choice was made over the alternative. Name the trade-off.
4. **Be opinionated.** Pick one approach and justify it. Don't list five options.
5. **Small commits.** Commit at the end of each logical step with a clear message. Never commit secrets, state files, or `.tfvars` with real values.
6. **Verify, don't assume.** After each change, run the relevant check (`docker compose up`, `kubectl get pods`, `terraform validate`, `helm lint`) and show the result. Say plainly what was not verified.
7. **Cost control.** Nothing billable is ever created. If a step would cost money, stop and say so instead of proposing it.
8. **Security defaults.** Non-root containers, least-privilege permissions in CI, no static cloud keys, secrets via Kubernetes Secrets or a secret manager, never in the repo. Pin third-party actions and downloads by SHA/hash.
9. **Flag risky actions.** Ask before anything destructive, before every push, and before every merge. Approval applies to one action only.

## Learning checkpoint
Per-day checkpoints are deferred by the owner's decision: questions are appended to the memory file `deferred-learning-checkpoints.md` as each day goes, and run together as one full project breakdown and Q&A after the final build.

## Plan

| Day | Focus | Done when | Status |
|---|---|---|---|
| 1 | Docker + Linux: multi-stage builds per service, non-root users, healthchecks, Compose for local dev, bash bootstrap script (`set -euo pipefail`) | `docker compose up` brings up the full stack from a clean clone | done |
| 2 | CI: GitHub Actions with hadolint, image build, Trivy scan, push to GHCR on merge to `main` | Green pipeline publishing tagged images | done |
| 3 | Kubernetes on kind: Deployments, Services, PVC for tile data, probes, resource requests/limits | App runs in local cluster and serves a route request | done |
| 4 | Helm chart: Ingress (Traefik), ConfigMaps/Secrets, HPA, dev and prod values | `helm install` works with dev values; prod renders and validates | done |
| 5 | README: architecture diagram, run instructions, honest "what ran where" table, cost notes, 3 resume bullets (draft) | A reader can understand and run the project from the README alone | next |
| 6 | CD without a cloud: GitHub Actions deploys the chart to an ephemeral kind cluster with a tiny OSM extract, smoke-tests a real route, deliberately breaks a deploy and rolls back with `helm rollback` | Pipeline proves deploy + rollback end to end | |
| 7 | Terraform: provision the kind cluster, Traefik, metrics-server and the Helm release locally; plus unapplied AWS/EKS reference code validated in CI (`terraform validate`, `tflint`, Trivy config scan) | `terraform apply/destroy` works locally; reference code validates in CI | |
| 8 | Monitoring: kube-prometheus-stack on kind, Grafana dashboards (request rate, p95/p99 latency, pod CPU/memory, error rate), one alert rule | Dashboard screenshots and a firing alert | |
| 9 | Load test + analysis: k6 against the routing endpoints, find the saturation point, set HPA thresholds and CPU requests from data, write a capacity report | One-page writeup with graphs | |
| 10 | Final polish, update the README with real results, then the full project breakdown and Q&A (deferred checkpoints) | Owner can explain every file | |

GCP/GKE is dropped (no spend). **If time slips:** cut Day 8 (monitoring) before touching Days 5-7 and 9.

## Definition of done (whole project)
- Fresh clone to running stack with one command locally
- CI builds, scans and publishes images; a pipeline deploys the chart to an ephemeral cluster and proves rollback
- Infrastructure provisioned from Terraform locally; cloud reference code validated but clearly marked as not applied
- Dashboards and an alert exist, plus a load-test report with real numbers
- README includes an architecture diagram, setup steps, cost notes, and an honest "what ran where" table
- No secrets in git history
