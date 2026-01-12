# =============================================================================
# JobMatch V0 - Main Terraform Configuration
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Remote backend - Cloud Storage
  # The bucket must be created manually before running terraform init:
  #   gsutil mb -l EU gs://jobmatch-terraform-state-job-match-v0
  #   gsutil versioning set on gs://jobmatch-terraform-state-job-match-v0
  backend "gcs" {
    bucket = "jobmatch-terraform-state-job-match-v0"
    prefix = "terraform/state"
  }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "aiplatform.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
