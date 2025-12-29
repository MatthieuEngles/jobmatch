# =============================================================================
# JobMatch V0 - Compute Engine VM
# =============================================================================

# -----------------------------------------------------------------------------
# Get available zones in the region
# -----------------------------------------------------------------------------

data "google_compute_zones" "available" {
  project = var.project_id
  region  = var.region
  status  = "UP"
}

# -----------------------------------------------------------------------------
# VM Instance
# -----------------------------------------------------------------------------

resource "google_compute_instance" "main" {
  name         = var.vm_name
  machine_type = var.vm_machine_type
  zone         = data.google_compute_zones.available.names[0]  # First available zone
  project      = var.project_id

  tags = ["ssh", "http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = var.vm_image
      size  = var.vm_disk_size
      type  = var.vm_disk_type
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.id

    access_config {
      nat_ip       = google_compute_address.static.address
      network_tier = "PREMIUM"
    }
  }

  service_account {
    email  = google_service_account.vm.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e

    # Log startup script output
    exec > >(tee /var/log/startup-script.log) 2>&1
    echo "Starting startup script at $(date)"

    # Update system
    apt-get update
    apt-get upgrade -y

    # Install Docker
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start Docker
    systemctl enable docker
    systemctl start docker

    # Install Caddy
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
    apt-get install -y caddy

    # Install Git
    apt-get install -y git

    # Create app directory
    mkdir -p /opt/jobmatch
    chown -R 1000:1000 /opt/jobmatch

    # Create Caddy config placeholder
    cat > /etc/caddy/Caddyfile <<'CADDYFILE'
    # JobMatch Caddyfile
    # Replace :80 with your domain for automatic HTTPS

    :80 {
        reverse_proxy localhost:8085
    }
    CADDYFILE

    # Reload Caddy
    systemctl reload caddy

    echo "Startup script completed at $(date)"
  EOF

  labels = var.labels

  # Allow stopping for updates
  allow_stopping_for_update = true

  depends_on = [
    google_project_service.apis,
    google_service_account.vm
  ]
}
