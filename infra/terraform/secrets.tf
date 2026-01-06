# =============================================================================
# JobMatch V0 - GCP Secret Manager Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Enable Secret Manager API
# -----------------------------------------------------------------------------

resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# Secrets
# -----------------------------------------------------------------------------

# Django Secret Key
resource "google_secret_manager_secret" "django_secret_key" {
  project   = var.project_id
  secret_id = "django-secret-key"

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.secretmanager]
}

# PostgreSQL Password
resource "google_secret_manager_secret" "postgres_password" {
  project   = var.project_id
  secret_id = "postgres-password"

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.secretmanager]
}

# BigQuery Gold Service Account Key (for cross-project access)
resource "google_secret_manager_secret" "bigquery_gold_sa_key" {
  project   = var.project_id
  secret_id = "bigquery-gold-sa-key"

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.secretmanager]
}

# -----------------------------------------------------------------------------
# IAM - Allow VM Service Account to access secrets
# -----------------------------------------------------------------------------

resource "google_secret_manager_secret_iam_member" "vm_django_secret" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.django_secret_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_secret_manager_secret_iam_member" "vm_postgres_password" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.postgres_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_secret_manager_secret_iam_member" "vm_bigquery_gold_sa_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.bigquery_gold_sa_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.vm.email}"
}
