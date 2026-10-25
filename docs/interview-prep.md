# Interview prep: explain every part of this project

For each area: the files to know, questions to answer out loud **before** opening the answers, and one thing to
break on purpose. Answers are folded; try first.

---

## 1. Docker and Linux (`backend/`, `frontend/`, `docker-compose.yml`, `scripts/bootstrap.sh`)

**Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `scripts/bootstrap.sh`, `.gitattributes`

1. Why is the backend Dockerfile multi-stage but the frontend one single-stage?
2. What does `HEALTHCHECK --start-period` actually do? What happens when it expires?
3. Why is the data mount `:ro` for the A\* container but read-write for Valhalla?
4. What does each flag in `set -euo pipefail` protect against?
5. What does `docker compose down` remove, and what does it leave behind (bind mount vs named volume)?
6. Why numeric `USER 10001` and not a name?

<details><summary>Answers</summary>

1. The backend has a (small) real build-time check, `py_compile`, so the second stage ships only the source; the
   frontend is one static file with nothing to build, so a second stage would be decoration.
2. Failures during the start period are not counted toward `retries`, so the container shows `starting`, not
   `unhealthy`. After it expires, `retries` consecutive failures flip it to `unhealthy`. The missing-data crash loop showed this.
3. The A\* service only reads the OSM file, so read-only limits damage if it is compromised. Valhalla builds and rewrites
   tiles and files in that folder, so read-only would break it.
4. `-e` stops at the first failing command, `-u` makes an unset variable an error (a typo like `$DIRR` otherwise expands
   to nothing), `pipefail` makes a pipeline fail if any stage fails, not only the last.
5. It removes containers and the network, not images. A bind-mounted host folder is never deleted; named volumes survive
   `down` too and are removed only by `down -v`.
6. Kubernetes' `runAsNonRoot` can verify a numeric UID; it cannot verify a name.

**Break it:** rename `data/tokyo_center.osm` and recreate the A\* container. The logs show the real cause first
(`Local OSM cache not found`); the final traceback line is a misleading network error from the last of five mirrors,
and `restart: unless-stopped` crash-loops it.
</details>

---

## 2. CI and supply-chain security (`.github/workflows/ci.yml`)

1. Why can a docs-only pull request fail the Trivy gate?
2. Why does `publish` get `packages: write` but `build` does not?
3. Why pin actions by commit SHA instead of tag? What is the cost?
4. Why does the pipeline publish the *saved* scanned image rather than rebuilding it?
5. What does `needs:` do, and what does `publish` wait for?
6. The first Trivy failure was OpenSSL in the frontend image, which only serves static files. Why did it still matter?

<details><summary>Answers</summary>

1. Scan results depend on the vulnerability database at scan time, not just on your code. A CVE published after the last
   green run fails the same image. (It happened: a new `brotli-libs` HIGH.)
2. Least privilege. Pull requests, including from forks, never get write access; only the job that pushes images does,
   and only on `main`.
3. A tag can be moved by its maintainer (the Trivy action was hit by a supply-chain attack where this mattered); a
   SHA cannot. The cost is staleness, which Dependabot addresses by proposing updates through the same CI.
4. A rebuild probably yields the same layers; shipping the exact file that was scanned guarantees it.
5. `needs:` orders jobs and skips a job if a dependency fails. `publish` needs build/scan, manifest validation, the
   end-to-end deploy and the Terraform/secret checks.
6. Vulnerabilities in the base image are reachable through anything that image runs or links; "it only serves HTML"
   is an assumption about what an attacker can reach, not a guarantee. The fix was cheap (a base-image bump).

**Break it:** on a throwaway branch change the backend base to `python:3.8-slim` and read the Trivy table that fails
the build. Do not merge.
</details>

---

## 3. Kubernetes and Helm (`charts/routing/`, `k8s/`)

1. Why does the chart not contain the namespace?
2. Why do selector labels differ from the general labels?
3. What is the checksum annotation for, and why did it cause an unwanted Valhalla restart once?
4. Why `required` in templates?
5. `startupProbe` versus `livenessProbe` and `readinessProbe`: why all three for the A\* backend?
6. Requests versus limits. Why a memory limit but no CPU limit?
7. Why does Valhalla use `strategy: Recreate`, and why is it excluded from autoscaling?
8. Why host-based Ingress (`valhalla.localhost`) instead of path prefixes?
9. Why `runtime config.js` instead of building the image per environment?
10. Why was `ingress-nginx` not used?

<details><summary>Answers</summary>

1. `helm install -n NAME --create-namespace` chooses it; hard-coding it makes a chart impossible to install twice.
2. A Deployment's selector is immutable. It must contain only labels that never change; general labels include the
   chart version, which changes every release.
3. Config changes do not restart pods by themselves; hashing the config into the pod template makes any change roll
   the pods. The first version hashed the *rendered* ConfigMap, whose labels include the chart version and, on
   Windows, CRLF line endings. A different byte string gave a different hash, so a version bump or a different OS
   restarted Valhalla (downtime, because of `Recreate`). It now hashes only the config data.
4. A missing value fails loudly at render time with a clear message instead of silently producing an empty field.
5. The A\* backend builds its road graph before it listens. `startupProbe` holds off the other two until it
   succeeds; otherwise liveness could kill the pod mid-start.
6. A memory limit protects the node from a leak (exceeding it gets the pod killed). A CPU limit mostly just throttles
   the process while the node is idle.
7. One pod owns a `ReadWriteOnce` volume that its entrypoint modifies: two pods would be two writers, so the old pod
   must stop first. For the same reason a second replica is not safe.
8. Path prefixes need the controller to strip the prefix, which with standard Ingress objects requires a controller-specific
   CRD (a Traefik `Middleware`). Host-based routing needs nothing extra and mirrors production.
9. One image means the image CI scanned and published is exactly the one that runs everywhere; the environment-specific
   URLs live in a ConfigMap-mounted file.
10. It is archived (maintenance ended March 2026), so it would receive no security fixes on the cluster's edge.

**Break it:** set the A\* memory limit to `128Mi` and watch `OOMKilled` in `kubectl describe pod`; or point the
readiness probe at a wrong port and watch the pod never become Ready.
</details>

---

## 4. Infrastructure as code (`terraform/`)

1. What does `terraform plan` show, and what does exit code 2 from `-detailed-exitcode` mean?
2. Why commit `.terraform.lock.hcl` but never `terraform.tfstate`?
3. Why is local state acceptable for `terraform/local` but not for a team on a cloud?
4. What did Trivy find in the AWS reference code, and how was each finding handled?
5. How is the AWS reference code different from evidence of an AWS deployment?
6. What nearly leaked, and how was it caught?

<details><summary>Answers</summary>

1. The changes Terraform would make without making them. Exit code 2 means changes are pending (0 means none).
   After a clean `apply`, `plan` showed no changes, proving no drift.
2. The lock file pins exact provider builds so every machine uses the same ones. State can contain secrets and
   describes live infrastructure, so it is git-ignored.
3. Local state is a file on one machine: fine for one person and a disposable local cluster. A team needs a shared,
   locked remote backend (S3 with locking) so two applies cannot collide.
4. A public Kubernetes API endpoint (CRITICAL) and a bucket without a customer-managed KMS key (HIGH): both fixed in
   the code. Worker-node egress (CRITICAL) was accepted, with a written reason in `.trivyignore`.
5. It was only formatted, validated and scanned. Nothing was ever created on AWS, so it says nothing about whether it
   would work there. The README says so on purpose.
6. The kind provider writes a kubeconfig (with client keys) beside the Terraform code and `git add terraform`
   staged it. `git ls-files` showed it before any push; the local commit was rewritten, the pattern ignored, and a
   repository-wide secret scan was added to CI.

**Break it:** on a throwaway branch change `replicas:` to `replica:` in the A\* template and open a pull request.
`kubeconform -strict` is documented to reject unknown fields, so the manifests job should fail on it. Check what CI
actually reports (this one was not tried). Then delete `data/` and watch the A\* pod fail on a missing file.
</details>

---

## 5. Monitoring (`docs/monitoring.md`, `charts/routing/files/dashboard.json`)

1. Where do request rate, latency and error rate come from when the apps expose no metrics?
2. What was the `service` / `exported_service` problem?
3. Why did the first error-rate alert stay silent during a total outage, and what fixed it?
4. Why must a `rate()` window be at least two scrape intervals?
5. Why was Valhalla, and not A\*, used for the outage test?

<details><summary>Answers</summary>

1. From Traefik's own metrics at the ingress (the RED signals), plus cAdvisor and kube-state-metrics for pod CPU,
   memory and replica counts.
2. Traefik labels its metrics `service` and a ServiceMonitor also stamps `service` on every target. On a clash
   Prometheus keeps its own and renames Traefik's, so every query on `service` returned nothing, with no error.
   `honorLabels: true` fixes it.
3. When a Service has no endpoints, Traefik answers `503` itself at the entrypoint and attributes nothing to the
   service, so a per-service 5xx alert never saw it. An entrypoint-level alert (`RoutingIngress5xx`) covers it.
4. A rate needs at least two samples inside the window. With a 30-second scrape, `rate(...[30s])` returned nothing.
5. Valhalla has no autoscaler to quietly undo the outage; an HPA would have restored A\* within seconds.
</details>

---

## 6. Load testing and capacity (`docs/capacity-report.md`, `loadtest/`)

1. Why `constant-arrival-rate` instead of a fixed number of virtual users?
2. What is the "knee", and where is it for each service?
3. Why does the A\* backend use exactly one CPU core at saturation?
4. How were the CPU request and HPA target derived, and why was 100m wrong?
5. After the HPA added replicas, why did latency recover *later* than the replicas became Ready?
6. List three limits of this test.

<details><summary>Answers</summary>

1. A fixed number of users slows down together with the server and hides overload; a fixed arrival rate keeps
   pushing and exposes where the server falls behind.
2. The load where latency stops being flat and errors begin: about 3 requests/s per A\* replica and about 30 per
   Valhalla replica.
3. It is single-threaded, CPU-bound Python: one request at a time, so it can use only one core (the GIL stops threads
   from helping).
4. Measured 0.23 to 0.27 CPU cores per request/s and a knee near 3 req/s. At a 70% target, 100m scaled out around
   0.3 req/s (almost any traffic); 600m scales out at roughly 1.6 to 1.9 req/s, about half the knee.
5. The saturated first replica still had a backlog of queued requests to drain.
6. One laptop runs the load generator, cluster and monitoring; only central-Tokyo trips of 2 to 6 km; 45-second steps;
   one run per step; latency percentiles above 10 s are capped by the histogram's top bucket.

**Break it:** run `python loadtest/run.py astar 4` and watch p95 jump from 0.4 s to many seconds.
</details>

---

## 7. Git and workflow habits

1. Why were pull requests squash-merged?
2. Why do shell scripts need `eol=lf` in `.gitattributes`?
3. Why does `git update-index --chmod=+x` exist, and when did it matter?
4. What is the difference between a merge and a rebase, and when was each used here?

<details><summary>Answers</summary>

1. One commit per change keeps `main` readable at the cost of losing the intermediate commits.
2. A script with CRLF endings fails on Linux with `bad interpreter: /bin/bash^M`; it also changed Helm hashes.
3. Git on Windows records new files as non-executable (0644); CI got `Permission denied` on `smoke-test.sh`.
4. A merge keeps both histories and adds a merge commit; a rebase replays your commits on top of another base for a
   straight line. Unpushed local commits were rebased onto `main` after each squash merge.
</details>
