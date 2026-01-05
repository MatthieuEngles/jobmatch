# JobMatch - Guide de Deploiement Production

## Pre-requis

- [x] Compte GCP avec facturation activee
- [x] `gcloud` CLI installe et authentifie
- [x] `terraform` installe (>= 1.0)
- [x] Acces au repo GitHub

## Etape 1 : Terraform (une seule fois)

```bash
cd infra/terraform

# Creer le bucket pour le state Terraform (une seule fois)
gsutil mb -l EU gs://jobmatch-terraform-state-job-match-v0
gsutil versioning set on gs://jobmatch-terraform-state-job-match-v0

# Initialiser Terraform
terraform init

# Creer le fichier de variables
cat > terraform.tfvars << EOF
project_id = "job-match-v0"
github_org = "MatthieuEngles"
github_repo = "jobmatch"
bigquery_gold_project_id = "jobmatch-482415"
bigquery_gold_dataset = "jobmatch_gold"
EOF

# Verifier le plan
terraform plan

# Appliquer (cree VM, service accounts, secrets vides, etc.)
terraform apply
```

**Outputs importants** (noter ces valeurs) :
- `vm_external_ip`
- `workload_identity_provider`
- `deploy_service_account_email`
- `vm_name`

## Etape 2 : Secrets GCP (une seule fois)

```bash
# Definir le projet
export PROJECT_ID="job-match-v0"
gcloud config set project $PROJECT_ID

# 1. Mot de passe PostgreSQL
echo -n "MotDePasseSecurise123!" | gcloud secrets versions add postgres-password --data-file=-

# 2. Django Secret Key (genere automatiquement)
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | gcloud secrets versions add django-secret-key --data-file=-

# 3. BigQuery Gold SA Key (fichier JSON de Mohamed)
gcloud secrets versions add bigquery-gold-sa-key --data-file=/chemin/vers/bigquery-gold-key.json
```

## Etape 3 : GitHub Variables (une seule fois)

Aller sur : `https://github.com/MatthieuEngles/jobmatch/settings/variables/actions`

Ajouter ces **Repository Variables** :

| Variable | Valeur |
|----------|--------|
| `GCP_PROJECT_ID` | `job-match-v0` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | (output terraform `workload_identity_provider`) |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `deploy-sa@TON_PROJECT_ID.iam.gserviceaccount.com` |
| `VM_NAME` | `jobmatch-vm` |

## Etape 4 : GitHub Environment (une seule fois)

Aller sur : `https://github.com/MatthieuEngles/jobmatch/settings/environments`

1. Cliquer "New environment"
2. Nom : `production`
3. (Optionnel) Ajouter des reviewers pour les deployements manuels

## Etape 5 : Premier Deploiement

Option A - **Automatique** (push sur main) :
```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

Option B - **Manuel** (GitHub Actions) :
1. Aller sur `https://github.com/MatthieuEngles/jobmatch/actions`
2. Selectionner "Deploy Production"
3. Cliquer "Run workflow"

## Verification

```bash
# IP de la VM (depuis terraform output ou GCP Console)
VM_IP="XX.XX.XX.XX"

# Tester les services
curl http://$VM_IP/health/          # GUI
curl http://$VM_IP:8081/health      # CV Ingestion
curl http://$VM_IP:8084/health      # AI Assistant
curl http://$VM_IP:8086/health      # Matching

# Acceder a l'application
open http://$VM_IP
```

## Connexion SSH a la VM (debug)

```bash
gcloud compute ssh jobmatch-vm --zone=europe-west9-a --project=TON_PROJECT_ID

# Une fois connecte :
cd /opt/jobmatch
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs -f gui
```

## Architecture

```
GitHub (push main)
       |
       v
GitHub Actions (deploy-prod.yml)
       |
       | Workload Identity Federation
       v
GCP VM (jobmatch-vm)
       |
       +-- fetch-secrets.sh (lit GCP Secret Manager)
       +-- docker-compose.prod.yml
           +-- gui (port 8085 -> Caddy -> :80)
           +-- cv-ingestion (port 8081)
           +-- ai-assistant (port 8084)
           +-- matching (port 8086)
           +-- db (PostgreSQL)
           +-- redis
```

## Services et Ports

| Service | Port Interne | Port Externe | Description |
|---------|--------------|--------------|-------------|
| GUI | 8080 | 80 (via Caddy) | Interface web Django |
| CV Ingestion | 8081 | 8081 | Extraction de CV |
| AI Assistant | 8084 | 8084 | Chat assistant |
| Matching | 8086 | 8086 | Matching CV/Offres |
| PostgreSQL | 5432 | - | Base de donnees |
| Redis | 6379 | - | Cache |

## Credentials Admin

Apres le premier deploiement, un superuser est cree automatiquement :
- **Email** : `admin@jobmatch.fr`
- **Password** : `admin123jobmatch`

**IMPORTANT** : Changer ce mot de passe en production !

## Troubleshooting

### Les secrets ne sont pas lus
```bash
# Sur la VM
sudo /opt/jobmatch/fetch-secrets.sh
cat /opt/jobmatch/.env
```

### Les containers ne demarrent pas
```bash
sudo docker compose -f docker-compose.prod.yml logs
```

### Vertex AI ne fonctionne pas
```bash
# Verifier que l'API est activee
gcloud services list --enabled | grep aiplatform

# Verifier les permissions du service account
gcloud projects get-iam-policy TON_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:jobmatch-vm-sa"
```

### Redemarrer tous les services
```bash
sudo docker compose -f docker-compose.prod.yml down
sudo docker compose -f docker-compose.prod.yml up -d
```
