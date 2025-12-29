# JobMatch V0 - Architecture GCP

## Vue d'ensemble

Cette documentation decrit l'infrastructure Google Cloud Platform pour le deploiement de JobMatch V0.

```
                              Internet
                                  │
                             [Domain]
                           jobmatch.xxx
                                  │
                         ┌────────┴────────┐
                         │   IP Statique   │
                         │  (europe-west9) │
                         └────────┬────────┘
                                  │
                         ┌────────┴────────┐
                         │    Firewall     │
                         │ (22, 80, 443)   │
                         └────────┬────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │           VM e2-medium                │
              │           (4GB RAM, 2 vCPU)           │
              │                                       │
              │  ┌─────────────────────────────────┐  │
              │  │            Caddy                │  │ ──► SSL/HTTPS auto
              │  │        (reverse proxy)          │  │
              │  └───────────────┬─────────────────┘  │
              │                  │                    │
              │  ┌───────────────┴─────────────────┐  │
              │  │        docker-compose           │  │
              │  │                                 │  │
              │  │  ┌───────────┐  ┌────────────┐  │  │
              │  │  │    gui    │  │ai-assistant│  │  │
              │  │  │   :8085   │  │   :8084    │  │  │
              │  │  │  Django   │  │  FastAPI   │  │  │
              │  │  └───────────┘  └────────────┘  │  │
              │  │                                 │  │
              │  │  ┌───────────┐  ┌────────────┐  │  │
              │  │  │cv-ingest. │  │offre-ingest│  │  │
              │  │  │   :8081   │  │   :8082    │  │  │
              │  │  │  FastAPI  │  │  FastAPI   │  │  │
              │  │  └───────────┘  └────────────┘  │  │
              │  │                                 │  │
              │  │  ┌───────────┐  ┌────────────┐  │  │
              │  │  │ matching  │  │local-ollama│  │  │
              │  │  │   :8083   │  │  :11434    │  │  │
              │  │  │  FastAPI  │  │   Ollama   │  │  │
              │  │  └───────────┘  └────────────┘  │  │
              │  │                                 │  │
              │  │  ┌───────────┐  ┌────────────┐  │  │
              │  │  │ PostgreSQL│  │   Redis    │  │  │
              │  │  │   :5433   │  │   :6379    │  │  │
              │  │  │ Database  │  │   Cache    │  │  │
              │  │  └───────────┘  └────────────┘  │  │
              │  │                                 │  │
              │  └─────────────────────────────────┘  │
              └───────────────────┬───────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │  Cloud Storage  │ │  Cloud Storage  │ │    BigQuery     │
     │(terraform-state)│ │    (bronze)     │ │  (silver/gold)  │
     │                 │ │                 │ │                 │
     │terraform.tfstate│ │  offres JSON    │ │ offers dataset  │
     └─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Composants

### 1. Compute Engine (VM)

| Parametre | Valeur |
|-----------|--------|
| **Type** | e2-medium |
| **vCPU** | 2 |
| **RAM** | 4 GB |
| **Disque** | 50 GB SSD (pd-balanced) |
| **OS** | Ubuntu 22.04 LTS |
| **Region** | europe-west9 (Paris) |
| **Zone** | europe-west9-a |
| **Cout estime** | ~25 EUR/mois |

**Logiciels installes via startup script** :
- Docker + Docker Compose
- Caddy (reverse proxy HTTPS)
- Git

### 2. Reseau

#### VPC (Virtual Private Cloud)
- Nom : `jobmatch-vpc`
- Mode : Custom (pas de sous-reseau auto)
- Sous-reseau : `jobmatch-subnet` (10.0.0.0/24)

#### IP Statique
- Type : EXTERNAL (Regional)
- Region : europe-west9
- Cout : ~7 EUR/mois (gratuit si attache a une VM)

#### Firewall Rules

| Regle | Ports | Source | Description |
|-------|-------|--------|-------------|
| `allow-ssh` | 22 | 0.0.0.0/0 | Acces SSH (a restreindre plus tard) |
| `allow-http` | 80 | 0.0.0.0/0 | HTTP (redirect vers HTTPS) |
| `allow-https` | 443 | 0.0.0.0/0 | HTTPS (Caddy) |
| `allow-icmp` | ICMP | 0.0.0.0/0 | Ping (debug) |

### 3. Cloud Storage

#### Bucket Terraform State
- Nom : `jobmatch-terraform-state-{project_id}`
- Location : EU (multi-regional)
- Classe : STANDARD
- Versioning : Active
- Acces : Private

#### Bucket Bronze (Offres brutes)
- Nom : `jobmatch-bronze-{project_id}`
- Location : europe-west9
- Classe : STANDARD
- Lifecycle : 90 jours vers NEARLINE, 365 jours vers COLDLINE
- Acces : Private

### 4. BigQuery

#### Dataset Silver
- Nom : `jobmatch_silver`
- Location : europe-west9
- Description : Donnees offres transformees

**Tables** :
| Table | Description |
|-------|-------------|
| `offers` | Table principale (27 colonnes) |
| `offer_locations` | Lieux de travail |
| `offer_companies` | Informations entreprise |
| `offer_salaries` | Grilles salariales |
| `offer_skills` | Competences requises |
| `offer_formations` | Formations demandees |
| `offer_languages` | Langues requises |
| `offer_permits` | Permis requis |

#### Dataset Gold
- Nom : `jobmatch_gold`
- Location : europe-west9
- Description : Donnees agregees et KPIs

**Tables** :
| Table | Description |
|-------|-------------|
| `offers_daily_stats` | Statistiques journalieres |
| `skills_ranking` | Classement des competences |
| `companies_ranking` | Classement des entreprises |

### 5. Service Accounts

| Compte | Roles | Usage |
|--------|-------|-------|
| `terraform-sa` | Editor, Storage Admin | Deploiement Terraform |
| `vm-sa` | Storage Object Viewer, BigQuery Data Editor | VM runtime |

### 6. Caddy (Reverse Proxy)

Configuration HTTPS automatique avec Let's Encrypt.

```
jobmatch.xxx {
    reverse_proxy localhost:8085
}

api.jobmatch.xxx {
    reverse_proxy /ai/* localhost:8084
    reverse_proxy /cv/* localhost:8081
    reverse_proxy /* localhost:8085
}
```

## Estimation des couts

| Service | Cout mensuel estime |
|---------|---------------------|
| VM e2-medium | 25 EUR |
| Disque 50GB SSD | 5 EUR |
| IP Statique | 0 EUR (attache) |
| Cloud Storage (10 GB) | 0.5 EUR |
| BigQuery (10 GB) | 0.2 EUR |
| Egress (10 GB) | 1 EUR |
| **Total** | **~32 EUR/mois** |

## Flux de donnees

### 1. Ingestion d'offres
```
France Travail API
       │
       ▼
[offre-ingestion service]
       │
       ├──► Cloud Storage (bronze/)
       │    └── offer_2025-01-15.json
       │
       └──► BigQuery (silver)
            └── offers, skills, etc.
```

### 2. Import CV
```
User upload PDF
       │
       ▼
[cv-ingestion service]
       │
       ├──► llm.molp.fr (LLM analysis)
       │
       └──► PostgreSQL
            └── candidate_profiles
```

### 3. Generation CV/LM
```
User request
       │
       ▼
[ai-assistant service]
       │
       ├──► llm.molp.fr (LLM generation)
       │
       └──► Response (CV/LM content)
```

## Deploiement

Le deploiement est entierement automatise via **GitHub Actions** avec **Workload Identity Federation**.

### Architecture CI/CD

```
Developer                   GitHub                        GCP
    │                          │                           │
    │  git push main           │                           │
    ├─────────────────────────►│                           │
    │                          │                           │
    │                   ┌──────┴──────┐                    │
    │                   │   Actions   │                    │
    │                   │  Workflow   │                    │
    │                   └──────┬──────┘                    │
    │                          │                           │
    │                          │ OIDC Token                │
    │                          ├──────────────────────────►│
    │                          │                           │
    │                          │◄──────────────────────────┤
    │                          │ Access Token              │
    │                          │                           │
    │                   ┌──────┴──────┐                    │
    │                   │  Terraform  │                    │
    │                   │ plan/apply  │                    │
    │                   └──────┬──────┘                    │
    │                          │                           │
    │                          │ Create/Update resources   │
    │                          ├──────────────────────────►│
    │                          │                           │
    │                   ┌──────┴──────┐            ┌───────┴───────┐
    │                   │   Docker    │            │   VM + GCS    │
    │                   │ Build/Push  │────────────│   + BigQuery  │
    │                   └─────────────┘            └───────────────┘
```

### Workflows GitHub Actions

| Workflow | Declencheur | Actions |
|----------|-------------|---------|
| `terraform.yml` | Push sur `main` (infra/) | Plan + Apply Terraform |
| `deploy.yml` | Push sur `main` (app/) | Build Docker + Deploy sur VM |
| `terraform-pr.yml` | PR vers `main` | Terraform Plan (preview) |

### Etapes de configuration initiale (une seule fois)

#### 1. Prerequis
- Compte GCP avec facturation active
- gcloud CLI installe et configure
- Repo GitHub configure

#### 2. Creation du projet GCP
```bash
gcloud projects create jobmatch-prod --name="JobMatch Production"
gcloud config set project jobmatch-prod

# Activer la facturation via Console GCP
# https://console.cloud.google.com/billing/linkedaccount?project=jobmatch-prod

# Activer les APIs
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

#### 3. Creation du bucket Terraform state (manuel)
```bash
PROJECT_ID=$(gcloud config get-value project)
gsutil mb -l EU gs://jobmatch-terraform-state-${PROJECT_ID}
gsutil versioning set on gs://jobmatch-terraform-state-${PROJECT_ID}
```

#### 4. Configurer Workload Identity Federation

Voir le guide complet dans [GCP_IAM_GUIDE.md](GCP_IAM_GUIDE.md#etape-6--configurer-workload-identity-federation-pour-github-actions)

```bash
PROJECT_ID=jobmatch-prod
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
GITHUB_ORG=MatthieuEngles
GITHUB_REPO=jobmatch

# Creer le pool et provider
gcloud iam workload-identity-pools create github-pool \
    --project=$PROJECT_ID \
    --location=global \
    --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
    --project=$PROJECT_ID \
    --location=global \
    --workload-identity-pool=github-pool \
    --display-name="GitHub Provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'"
```

#### 5. Configurer les secrets GitHub

Dans **Settings → Secrets and variables → Actions** :

##### Secrets pour l'authentification GCP

| Secret | Description | Exemple |
|--------|-------------|---------|
| `GCP_PROJECT_ID` | ID du projet GCP | `jobmatch-prod` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Provider Workload Identity | `projects/123456/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | Email du Service Account | `terraform-sa@jobmatch-prod.iam.gserviceaccount.com` |

##### Secrets pour l'application

| Secret | Description | Exemple |
|--------|-------------|---------|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `super_secret_pwd` |
| `DJANGO_SECRET_KEY` | Cle secrete Django | `django-insecure-xxx...` |
| `LLM_API_KEY` | Cle API pour le LLM | `sk-...` |
| `LLM_ENDPOINT` | Endpoint du LLM | `http://llm.molp.fr/v1` |

##### Variables d'environnement (non secretes)

Dans **Settings → Secrets and variables → Actions → Variables** :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `GCP_REGION` | Region GCP | `europe-west9` |
| `GCP_ZONE` | Zone GCP | `europe-west9-a` |
| `DOMAIN` | Domaine de l'application | `jobmatch.example.com` |

### Alternative : Credentials JSON

Si Workload Identity Federation n'est pas possible (certains environnements restreints), utiliser une cle JSON :

```bash
# Generer la cle
gcloud iam service-accounts keys create terraform-sa-key.json \
    --iam-account=terraform-sa@jobmatch-prod.iam.gserviceaccount.com

# Encoder en base64
cat terraform-sa-key.json | base64 -w 0
```

Stocker dans GitHub Secret `GCP_SA_KEY` et utiliser dans le workflow :

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

**Inconvenients** :
- Risque de fuite si le secret est expose
- Rotation manuelle tous les 90 jours recommandee
- Pas de revocation automatique

#### 6. Premier deploiement
```bash
git push origin main
# Le workflow GitHub Actions se declenche automatiquement
```

### Configuration post-deploiement

1. **DNS** : Pointer le domaine vers l'IP statique
2. **Caddy** : Configurer le Caddyfile avec le domaine
3. **Variables d'environnement** : Configurer les secrets sur la VM

### Terraform vs Deploiement de code

**IMPORTANT** : Terraform gere l'**infrastructure**, pas le **code applicatif**.

| Changement | Terraform detecte ? | Action requise |
|------------|---------------------|----------------|
| VM, reseau, buckets, BigQuery | Oui | `terraform apply` |
| Code Python/Django | Non | Workflow `deploy.yml` |
| docker-compose.yml | Non | Workflow `deploy.yml` |
| Dockerfile | Non | Workflow `deploy.yml` |

**Pourquoi ?** Terraform compare la configuration declaree (ex: `machine_type = "e2-medium"`), pas le contenu des fichiers sur la VM.

**Solution implementee** : Le workflow `deploy.yml` :
1. Force `docker compose build --no-cache --pull` pour rebuilder les images
2. Execute `docker compose down` puis `up -d` pour forcer le redemarrage
3. S'execute sur tout push dans `app/` ou `docker-compose.yml`

Voir : [POSTMORTEM_miniterraform.md](../../doc_support_contexte/POSTMORTEM_miniterraform.md) pour plus de details.

## Securite

### Mesures implementees

- [x] Firewall restrictif (ports 22, 80, 443 uniquement)
- [x] HTTPS force via Caddy
- [x] Service accounts avec privileges minimaux
- [x] Buckets prives par defaut
- [x] Versioning sur bucket Terraform state

### Ameliorations futures (V1)

- [ ] Restreindre SSH a des IPs specifiques
- [ ] Cloud Armor (WAF)
- [ ] Secret Manager pour les credentials
- [ ] VPC Service Controls
- [ ] Cloud NAT pour la VM
- [ ] Identity-Aware Proxy (IAP)

## Monitoring (V1)

### A implementer

- Cloud Monitoring dashboards
- Alertes CPU/Memory/Disk
- Uptime checks
- Log-based metrics
- Error reporting

## Backup (V1)

### Strategie

| Composant | Strategie |
|-----------|-----------|
| PostgreSQL | pg_dump quotidien vers Cloud Storage |
| Cloud Storage | Versioning + Lifecycle |
| BigQuery | Snapshots automatiques |
| VM | Snapshots disque hebdomadaires |

## Evolution vers V1

### Ameliorations prevues

1. **Cloud SQL** : Migration PostgreSQL vers service manage
2. **Cloud Run** : Migration des services FastAPI
3. **Vertex AI** : Remplacement de llm.molp.fr
4. **Load Balancer** : Haute disponibilite
5. **Cloud CDN** : Performance assets statiques
6. **Artifact Registry** : Stockage images Docker

---

*Document cree le 2025-12-29 - JobMatch V0*
