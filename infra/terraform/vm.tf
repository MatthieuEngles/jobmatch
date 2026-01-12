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
    apt-get install -y ca-certificates curl gnupg jq
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

    # Create app directories
    mkdir -p /opt/jobmatch
    mkdir -p /opt/jobmatch/secrets
    chown -R 1000:1000 /opt/jobmatch

    # Create Caddy config with domain support
    DOMAIN="${var.domain}"

    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "" ]; then
      # Domain configured - enable HTTPS with automatic certificate
      cat > /etc/caddy/Caddyfile <<CADDYFILE
# JobMatch Caddyfile with HTTPS

# Main domain with automatic HTTPS
$DOMAIN {
    reverse_proxy localhost:8085
    encode gzip

    header {
        # Security headers
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}

# Also allow access via IP on port 80 (no HTTPS)
:80 {
    reverse_proxy localhost:8085
}
CADDYFILE
    else
      # No domain - HTTP only
      cat > /etc/caddy/Caddyfile <<'CADDYFILE'
# JobMatch Caddyfile (HTTP only - no domain configured)

:80 {
    reverse_proxy localhost:8085
}
CADDYFILE
    fi

    # Reload Caddy
    systemctl reload caddy

    # Clone the repository (public repo, no auth needed)
    echo "Cloning repository..."
    cd /opt/jobmatch
    if [ ! -d ".git" ]; then
      git clone https://github.com/${var.github_org}/${var.github_repo}.git .
    fi
    chown -R 1000:1000 /opt/jobmatch

    # Create script to fetch secrets from Secret Manager
    cat > /opt/jobmatch/fetch-secrets.sh <<'FETCHSCRIPT'
    #!/bin/bash
    set -e

    PROJECT_ID="${var.project_id}"
    SECRETS_DIR="/opt/jobmatch/secrets"
    ENV_FILE="/opt/jobmatch/.env"

    echo "Fetching secrets from GCP Secret Manager..."

    # Fetch secrets using gcloud (VM has access via service account)
    POSTGRES_PASSWORD=$(gcloud secrets versions access latest --secret="postgres-password" --project="$PROJECT_ID" 2>/dev/null || echo "")
    DJANGO_SECRET_KEY=$(gcloud secrets versions access latest --secret="django-secret-key" --project="$PROJECT_ID" 2>/dev/null || echo "")

    # Fetch BigQuery Gold SA key and save to file
    gcloud secrets versions access latest --secret="bigquery-gold-sa-key" --project="$PROJECT_ID" > "$SECRETS_DIR/bigquery-gold-key.json" 2>/dev/null || echo "{}" > "$SECRETS_DIR/bigquery-gold-key.json"
    chmod 600 "$SECRETS_DIR/bigquery-gold-key.json"

    # Create .env file for docker-compose
    cat > "$ENV_FILE" <<ENVFILE
    # Auto-generated from GCP Secret Manager
    POSTGRES_PASSWORD=$POSTGRES_PASSWORD
    DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY

    # GCP Configuration (for Vertex AI - no API key needed, uses ADC)
    GCP_PROJECT_ID=${var.project_id}
    GCP_LOCATION=europe-west1

    # BigQuery Gold cross-project access
    BIGQUERY_GOLD_PROJECT_ID=${var.bigquery_gold_project_id}
    BIGQUERY_GOLD_CROSS_PROJECT_DATASET=${var.bigquery_gold_dataset}

    # LLM Configuration (Vertex AI Gemini)
    LLM_MODEL=gemini-1.5-flash-002
    LLM_MAX_TOKENS=4096

    # Embeddings
    EMBEDDINGS_PROVIDER=sentence-transformers
    EMBEDDINGS_MODEL=paraphrase-multilingual-MiniLM-L12-v2

    # Domain configuration (for CSRF/CORS)
    DOMAIN=${var.domain}
    ENVFILE

    chmod 600 "$ENV_FILE"
    echo "Secrets fetched successfully."
    FETCHSCRIPT
    chmod +x /opt/jobmatch/fetch-secrets.sh

    # Create deploy script
    cat > /opt/jobmatch/deploy.sh <<'DEPLOYSCRIPT'
    #!/bin/bash
    set -e

    cd /opt/jobmatch

    # Fetch latest secrets
    ./fetch-secrets.sh

    # Pull latest code (if git repo exists)
    if [ -d ".git" ]; then
        git pull origin main
    fi

    # Build and start services
    docker compose -f docker-compose.prod.yml build
    docker compose -f docker-compose.prod.yml up -d

    echo "Deployment completed at $(date)"
    DEPLOYSCRIPT
    chmod +x /opt/jobmatch/deploy.sh

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
