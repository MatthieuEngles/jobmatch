# =============================================================================
# JobMatch V0 - Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Project Configuration
# -----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west9"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "europe-west9-a"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# -----------------------------------------------------------------------------
# VM Configuration
# -----------------------------------------------------------------------------

variable "vm_name" {
  description = "Name of the VM instance"
  type        = string
  default     = "jobmatch-vm"
}

variable "vm_machine_type" {
  description = "Machine type for the VM"
  type        = string
  default     = "e2-medium"
}

variable "vm_disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "vm_disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "pd-balanced"
}

variable "vm_image" {
  description = "Boot disk image"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

# -----------------------------------------------------------------------------
# Network Configuration
# -----------------------------------------------------------------------------

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "jobmatch-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "jobmatch-subnet"
}

variable "subnet_cidr" {
  description = "CIDR range for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

# -----------------------------------------------------------------------------
# Application Configuration
# -----------------------------------------------------------------------------

variable "domain" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "ssh_allowed_ips" {
  description = "List of IP ranges allowed to SSH (CIDR format)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Warning: Open to all - restrict in production
}

# -----------------------------------------------------------------------------
# GitHub Configuration (for Workload Identity Federation)
# -----------------------------------------------------------------------------

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
  default     = "MatthieuEngles"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "jobmatch"
}

# -----------------------------------------------------------------------------
# Labels
# -----------------------------------------------------------------------------

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "jobmatch"
    environment = "prod"
    managed_by  = "terraform"
  }
}
