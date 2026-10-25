# Local stack as code

Provisions the same environment as the manual quick start, with one command: a `kind` cluster, Traefik,
metrics-server and the `routing` Helm chart. Nothing here touches a cloud and nothing costs money.

```bash
cd terraform/local
terraform init
terraform plan
terraform apply          # ~6-7 min; most of it is pulling images and loading Valhalla
# open http://app.localhost:8088
terraform destroy        # ~1 min; the host's data/ folder is never touched
```

- **Providers:** `tehcyx/kind` (the cluster) and `hashicorp/helm` (add-ons and the app), versions pinned in
  `versions.tf`; `.terraform.lock.hcl` pins the exact builds and is committed.
- **State is local** (`terraform.tfstate`, git-ignored). A shared, locked remote backend would only matter with
  several people or a cloud account; see `../aws-reference/` for what that would look like.
- **Requirements:** Docker running, `data/` already holding the map data and Valhalla tiles (see the root
  README). The host port defaults to 8088 and can be changed with `-var ingress_host_port=...`.
- **`--kubelet-insecure-tls` on metrics-server is dev-only** (kind's self-signed kubelet certificates).
- **Windows note:** the data path is normalised to forward slashes, because backslashes break Docker mounts.
