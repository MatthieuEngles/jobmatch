# =============================================================================
# JobMatch V0 - Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# VM Outputs
# -----------------------------------------------------------------------------

output "vm_name" {
  description = "Name of the VM instance"
  value       = google_compute_instance.main.name
}

output "vm_external_ip" {
  description = "External IP address of the VM"
  value       = google_compute_address.static.address
}

output "vm_internal_ip" {
  description = "Internal IP address of the VM"
  value       = google_compute_instance.main.network_interface[0].network_ip
}

output "vm_zone" {
  description = "Zone where the VM is deployed"
  value       = google_compute_instance.main.zone
}

output "ssh_command" {
  description = "Command to SSH into the VM"
  value       = "gcloud compute ssh ${google_compute_instance.main.name} --zone=${google_compute_instance.main.zone} --project=${var.project_id}"
}

# -----------------------------------------------------------------------------
# Network Outputs
# -----------------------------------------------------------------------------

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = google_compute_subnetwork.main.name
}

output "static_ip" {
  description = "Static external IP address"
  value       = google_compute_address.static.address
}

# -----------------------------------------------------------------------------
# Storage Outputs
# -----------------------------------------------------------------------------

output "bronze_bucket_name" {
  description = "Name of the bronze bucket"
  value       = google_storage_bucket.bronze.name
}

output "bronze_bucket_url" {
  description = "URL of the bronze bucket"
  value       = google_storage_bucket.bronze.url
}

output "backups_bucket_name" {
  description = "Name of the backups bucket"
  value       = google_storage_bucket.backups.name
}

# -----------------------------------------------------------------------------
# BigQuery Outputs
# -----------------------------------------------------------------------------

output "bigquery_silver_dataset" {
  description = "Silver dataset ID"
  value       = google_bigquery_dataset.silver.dataset_id
}

output "bigquery_gold_dataset" {
  description = "Gold dataset ID"
  value       = google_bigquery_dataset.gold.dataset_id
}

# -----------------------------------------------------------------------------
# IAM Outputs
# -----------------------------------------------------------------------------

output "vm_service_account_email" {
  description = "Email of the VM service account"
  value       = google_service_account.vm.email
}

output "terraform_service_account_email" {
  description = "Email of the Terraform service account"
  value       = google_service_account.terraform.email
}

output "deploy_service_account_email" {
  description = "Email of the Deploy service account"
  value       = google_service_account.deploy.email
}

# -----------------------------------------------------------------------------
# Workload Identity Federation Outputs
# -----------------------------------------------------------------------------

output "workload_identity_pool_name" {
  description = "Full name of the Workload Identity Pool"
  value       = google_iam_workload_identity_pool.github.name
}

output "workload_identity_provider" {
  description = "Workload Identity Provider for GitHub Actions (use in GitHub secrets)"
  value       = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}

# Data source to get project number
data "google_project" "current" {
  project_id = var.project_id
}

# -----------------------------------------------------------------------------
# Summary Output
# -----------------------------------------------------------------------------

output "summary" {
  description = "Deployment summary"
  value       = <<-EOT

    ============================================================
    JobMatch V0 - Deployment Summary
    ============================================================

    VM Instance:
      Name:        ${google_compute_instance.main.name}
      External IP: ${google_compute_address.static.address}
      Zone:        ${google_compute_instance.main.zone}

    SSH Command:
      gcloud compute ssh ${google_compute_instance.main.name} --zone=${google_compute_instance.main.zone} --project=${var.project_id}

    Storage:
      Bronze Bucket: ${google_storage_bucket.bronze.name}
      Backups Bucket: ${google_storage_bucket.backups.name}

    BigQuery:
      Silver Dataset: ${google_bigquery_dataset.silver.dataset_id}
      Gold Dataset:   ${google_bigquery_dataset.gold.dataset_id}

    GitHub Actions Secrets:
      GCP_PROJECT_ID:                  ${var.project_id}
      GCP_WORKLOAD_IDENTITY_PROVIDER:  projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}
      GCP_SERVICE_ACCOUNT:             ${google_service_account.terraform.email}

    Next Steps:
      1. Point your domain to ${google_compute_address.static.address}
      2. SSH into the VM and deploy your application
      3. Configure Caddyfile with your domain for HTTPS

    ============================================================
  EOT
}
