# =============================================================================
# JobMatch V0 - IAM Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Service Account for VM
# -----------------------------------------------------------------------------

resource "google_service_account" "vm" {
  account_id   = "jobmatch-vm-sa"
  display_name = "JobMatch VM Service Account"
  description  = "Service account for the JobMatch VM instance"
  project      = var.project_id
}

# VM SA - BigQuery Job User (to run queries)
resource "google_project_iam_member" "vm_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# VM SA - Logging Writer (for VM logs)
resource "google_project_iam_member" "vm_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# VM SA - Monitoring Metric Writer (for VM metrics)
resource "google_project_iam_member" "vm_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# VM SA - Vertex AI User (for Gemini via Vertex AI)
resource "google_project_iam_member" "vm_vertexai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# -----------------------------------------------------------------------------
# Service Account for Terraform (GitHub Actions)
# -----------------------------------------------------------------------------

resource "google_service_account" "terraform" {
  account_id   = "terraform-sa"
  display_name = "Terraform Service Account"
  description  = "Service account for Terraform deployments via GitHub Actions"
  project      = var.project_id
}

# Terraform SA - Editor role
resource "google_project_iam_member" "terraform_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.terraform.email}"
}

# Terraform SA - Storage Admin (for bucket management)
resource "google_project_iam_member" "terraform_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.terraform.email}"
}

# Terraform SA - Service Account User (to attach SA to VM)
resource "google_project_iam_member" "terraform_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.terraform.email}"
}

# -----------------------------------------------------------------------------
# Workload Identity Federation for GitHub Actions
# -----------------------------------------------------------------------------

# Workload Identity Pool
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  project                   = var.project_id
  display_name              = "GitHub Actions Pool"
  description               = "Workload Identity Pool for GitHub Actions"

  depends_on = [google_project_service.apis]
}

# Workload Identity Provider (OIDC)
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  project                            = var.project_id
  display_name                       = "GitHub Provider"
  description                        = "OIDC provider for GitHub Actions"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  attribute_condition = "assertion.repository_owner == '${var.github_org}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub repo to impersonate Terraform SA
resource "google_service_account_iam_member" "terraform_workload_identity" {
  service_account_id = google_service_account.terraform.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"
}

# -----------------------------------------------------------------------------
# Deploy Service Account (for GitHub Actions to SSH into VM)
# -----------------------------------------------------------------------------

resource "google_service_account" "deploy" {
  account_id   = "deploy-sa"
  display_name = "Deploy Service Account"
  description  = "Service account for deploying applications to VM"
  project      = var.project_id
}

# Deploy SA - Compute Instance Admin (to manage VM)
resource "google_project_iam_member" "deploy_compute_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# Deploy SA - OS Login (to SSH into VM)
resource "google_project_iam_member" "deploy_os_login" {
  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# Allow GitHub repo to impersonate Deploy SA
resource "google_service_account_iam_member" "deploy_workload_identity" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"
}
