# =============================================================================
# JobMatch V0 - Cloud Storage
# =============================================================================

# -----------------------------------------------------------------------------
# Bronze Bucket (Raw offers data)
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "bronze" {
  name          = "jobmatch-bronze-${var.project_id}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  # Prevent accidental deletion
  force_destroy = false

  # Uniform bucket-level access
  uniform_bucket_level_access = true

  # Versioning for data recovery
  versioning {
    enabled = true
  }

  # Lifecycle rules for cost optimization
  lifecycle_rule {
    condition {
      age = 90 # days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365 # days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Delete old versions after 30 days
  lifecycle_rule {
    condition {
      num_newer_versions = 3
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Backup Bucket (PostgreSQL dumps, etc.)
# -----------------------------------------------------------------------------

resource "google_storage_bucket" "backups" {
  name          = "jobmatch-backups-${var.project_id}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Move to nearline after 7 days
  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  # Move to coldline after 30 days
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Delete after 90 days
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# IAM - VM Service Account access to buckets
# -----------------------------------------------------------------------------

# Bronze bucket - read/write for offre-ingestion
resource "google_storage_bucket_iam_member" "vm_bronze_admin" {
  bucket = google_storage_bucket.bronze.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm.email}"
}

# Backups bucket - write for pg_dump
resource "google_storage_bucket_iam_member" "vm_backups_admin" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm.email}"
}
