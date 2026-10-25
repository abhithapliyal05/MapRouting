# Map data and Valhalla tiles live in a private bucket. Pods copy them into a local volume at start
# (an init container, not yet in the chart), so no shared writable volume is needed across nodes.
resource "aws_s3_bucket" "map_data" {
  bucket_prefix = "${var.name}-map-data-"
}

resource "aws_s3_bucket_public_access_block" "map_data" {
  bucket                  = aws_s3_bucket.map_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "map_data" {
  bucket = aws_s3_bucket.map_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Customer-managed key (Trivy AWS-0132): lets the key policy and rotation be controlled, and every use of
# the key shows up in CloudTrail. Costs about $1/month per key.
resource "aws_kms_key" "map_data" {
  description             = "${var.name} map data bucket"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_s3_bucket_server_side_encryption_configuration" "map_data" {
  bucket = aws_s3_bucket.map_data.id
  rule {
    bucket_key_enabled = true # cuts KMS request volume (and cost) for many small reads
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.map_data.arn
    }
  }
}

# Read-only access for the application pods through EKS Pod Identity (no keys in the cluster).
data "aws_iam_policy_document" "pods_trust" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "pods_map_data" {
  name               = "${var.name}-pods-map-data"
  assume_role_policy = data.aws_iam_policy_document.pods_trust.json
}

data "aws_iam_policy_document" "pods_map_data" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.map_data.arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.map_data.arn}/*"]
  }
  # Objects are encrypted with the customer-managed key, so reading them needs Decrypt on it.
  statement {
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.map_data.arn]
  }
}

resource "aws_iam_role_policy" "pods_map_data" {
  name   = "map-data-read"
  role   = aws_iam_role.pods_map_data.id
  policy = data.aws_iam_policy_document.pods_map_data.json
}

# The chart does not define these ServiceAccounts yet; this documents the intended binding.
resource "aws_eks_pod_identity_association" "map_data" {
  for_each = toset(["routing-valhalla", "routing-astar"])

  cluster_name    = module.eks.cluster_name
  namespace       = "routing"
  service_account = each.key
  role_arn        = aws_iam_role.pods_map_data.arn
}
