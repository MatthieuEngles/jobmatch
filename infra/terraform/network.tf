# =============================================================================
# JobMatch V0 - Network Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# VPC Network
# -----------------------------------------------------------------------------

resource "google_compute_network" "main" {
  name                    = var.network_name
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Subnet
# -----------------------------------------------------------------------------

resource "google_compute_subnetwork" "main" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.main.id
  project       = var.project_id
}

# -----------------------------------------------------------------------------
# Static External IP
# -----------------------------------------------------------------------------

resource "google_compute_address" "static" {
  name         = "jobmatch-static-ip"
  region       = var.region
  project      = var.project_id
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Firewall Rules
# -----------------------------------------------------------------------------

# Allow SSH
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.network_name}-allow-ssh"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.ssh_allowed_ips
  target_tags   = ["ssh"]

  description = "Allow SSH access"
}

# Allow HTTP
resource "google_compute_firewall" "allow_http" {
  name    = "${var.network_name}-allow-http"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]

  description = "Allow HTTP traffic"
}

# Allow HTTPS
resource "google_compute_firewall" "allow_https" {
  name    = "${var.network_name}-allow-https"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]

  description = "Allow HTTPS traffic"
}

# Allow ICMP (ping)
resource "google_compute_firewall" "allow_icmp" {
  name    = "${var.network_name}-allow-icmp"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "icmp"
  }

  source_ranges = ["0.0.0.0/0"]

  description = "Allow ICMP (ping) for debugging"
}

# Allow internal communication
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.network_name}-allow-internal"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]

  description = "Allow internal traffic within the VPC"
}
