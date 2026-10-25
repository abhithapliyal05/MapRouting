# AWS reference design (never applied)

> **Status: written and statically validated only. No AWS account was used and none of this was ever applied.**
> CI checks it with `terraform fmt`, `terraform validate` and a Trivy misconfiguration scan. That proves the
> code is well-formed and passes a security linter. It does not prove it works on AWS.

This is what the project would run on if it were deployed to EKS, written so the design decisions can be
reviewed and discussed.

| File | What it defines |
|---|---|
| `main.tf` | VPC (2 AZs, private and public subnets, one NAT) and an EKS cluster with a managed node group and the core add-ons, built from the community `terraform-aws-modules` |
| `ecr.tf` | Two ECR repositories with **immutable tags**, scan-on-push and a retention policy |
| `github-oidc.tf` | GitHub Actions OIDC provider and a role that only runs on `main` of this repository and can only push to those two ECR repositories. **No stored AWS keys** |
| `data-bucket.tf` | Private, versioned, KMS-encrypted S3 bucket for map data, and a read-only role for the pods through EKS Pod Identity |
| `.trivyignore` | The one accepted scanner finding, with its reason |

## Decisions worth discussing

- **Private API endpoint only.** Trivy rates a public Kubernetes API (even CIDR-restricted) as CRITICAL. The cost
  is that `kubectl` and any deploy pipeline must reach the VPC through a VPN, bastion or self-hosted runner,
  so GitHub-hosted runners could not deploy to this cluster as written.
- **Data from S3 with Pod Identity, instead of EFS.** A shared network disk across nodes would need EFS
  (ReadWriteMany). Copying data from S3 into each pod's local volume avoids that, at the price of a download at
  pod start. The Helm chart does not have the init container or ServiceAccounts for this yet, so the
  chart and this code are not yet consistent. That gap is real.
- **One NAT gateway, not one per AZ.** Roughly halves NAT cost; losing that AZ loses egress for the whole cluster.
- **Customer-managed KMS key** for the bucket (Trivy AWS-0132), at about $1/month.
- **Accepted finding AWS-0104** (node security group allows all egress): workers need outbound access to pull
  images. The hardening path is VPC endpoints for ECR, S3 and STS plus a restrictive egress rule.
- **State:** a commented-out S3 backend with native locking in `versions.tf`. CI runs with `-backend=false`.

## Rough cost, if it were ever applied

These are order-of-magnitude figures from memory, **not verified against current AWS pricing**; check the AWS
pricing pages before relying on any of them.

| Item | Approximate |
|---|---|
| EKS control plane | ~$0.10 per hour |
| 2 x `t3.large` workers | ~$0.17 per hour together |
| NAT gateway | ~$0.045 per hour plus data |
| KMS key, S3, ECR | cents to a few dollars per month |

Roughly **$0.35 per hour** while running, so about $8 for a day left on. That is why the project's rule is that
nothing billable is ever created, and why this directory stays a reference.
