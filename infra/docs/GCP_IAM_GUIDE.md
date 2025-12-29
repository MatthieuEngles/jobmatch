# Guide IAM Google Cloud Platform - JobMatch

## Introduction

Ce guide explique comment configurer Google Cloud Platform pour le projet JobMatch.
Il couvre deux scenarios :

1. **Bootstrap initial** : Configuration depuis ton poste local (une seule fois)
2. **CI/CD** : Configuration pour GitHub Actions (deploiements automatiques)

---

## PARTIE 1 : Bootstrap Initial (Depuis ton poste)

Cette partie est a executer **une seule fois** pour creer l'infrastructure initiale.

### Prerequis

1. **Un compte Google** (personnel ou Workspace)
2. **gcloud CLI installe** : https://cloud.google.com/sdk/docs/install
3. **Terraform installe** : `sudo snap install terraform --classic`

---

### Etape 1 : Installer et configurer gcloud CLI

#### 1.1 Installation (Ubuntu/WSL)

```bash
# Methode recommandee : via apt
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates gnupg curl

# Ajouter le repo Google Cloud
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Installer
sudo apt-get update && sudo apt-get install google-cloud-cli

# Verifier l'installation
gcloud version
```

#### 1.2 Authentification initiale

```bash
# Connexion a ton compte Google
# Cela ouvre un navigateur pour te connecter
gcloud auth login
```

**Ce qui se passe** :
1. Un navigateur s'ouvre
2. Tu te connectes avec ton compte Google
3. Tu autorises "Google Cloud SDK"
4. Un message "You are now authenticated" confirme le succes

---

### Etape 2 : Creer le projet GCP

```bash
# Definir l'ID du projet (doit etre unique globalement)
export PROJECT_ID=job-match-v0

# Creer le projet
gcloud projects create $PROJECT_ID --name="JobMatch V0"

# Definir comme projet par defaut
gcloud config set project $PROJECT_ID

# Verifier
gcloud config get-value project
# Doit afficher: job-match-v0
```

**En cas d'erreur "project already exists"** : Le nom est pris, choisis un autre ID.

---

### Etape 3 : Activer la facturation (OBLIGATOIRE)

**CRITIQUE** : Sans facturation, AUCUNE API ne peut etre activee.

#### 3.1 Via la Console Web (recommande)

1. Ouvre : https://console.cloud.google.com/billing/linkedaccount?project=job-match-v0

2. Clique sur **"Link a billing account"**

3. Deux options :
   - **Compte existant** : Selectionne-le
   - **Nouveau compte** : Clique "Create billing account"

4. **Premiere fois sur GCP** : Tu beneficies de **300$ de credits gratuits pendant 90 jours**

#### 3.2 Verification

```bash
# Verifier que la facturation est liee
gcloud billing projects describe $PROJECT_ID

# Tu dois voir quelque chose comme :
# billingAccountName: billingAccounts/XXXXXX-XXXXXX-XXXXXX
# billingEnabled: true
```

**Si `billingEnabled: false`** : Retourne a l'etape 3.1

---

### Etape 4 : Configurer l'authentification locale pour Terraform

Il y a deux types d'authentification avec gcloud :

| Commande | Usage | Stockage |
|----------|-------|----------|
| `gcloud auth login` | CLI gcloud | ~/.config/gcloud/ |
| `gcloud auth application-default login` | **Applications** (Terraform, SDK) | ~/.config/gcloud/application_default_credentials.json |

**Terraform utilise Application Default Credentials (ADC)**, pas les credentials de `gcloud auth login`.

#### 4.1 Creer les Application Default Credentials

```bash
gcloud auth application-default login
```

**Ce qui se passe** :
1. Un navigateur s'ouvre (a nouveau)
2. Tu te connectes avec ton compte Google
3. Tu autorises "Google Auth Library"
4. Un fichier est cree : `~/.config/gcloud/application_default_credentials.json`

#### 4.2 Verification

```bash
# Verifier que le fichier existe
cat ~/.config/gcloud/application_default_credentials.json

# Tu dois voir un JSON avec "client_id", "client_secret", "refresh_token"
```

#### 4.3 Definir le projet par defaut pour ADC

```bash
gcloud auth application-default set-quota-project $PROJECT_ID
```

---

### Etape 5 : Activer les APIs necessaires

```bash
# Activer toutes les APIs requises
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com

# Verifier
gcloud services list --enabled
```

**Erreur "Billing account not found"** ? Retourne a l'etape 3.

---

### Etape 6 : Creer le bucket pour Terraform state

Le state Terraform doit etre stocke dans un bucket Cloud Storage (partage, versionne, securise).

```bash
# Creer le bucket dans la region EU
gsutil mb -l EU gs://jobmatch-terraform-state-$PROJECT_ID

# Activer le versioning (permet de recuperer un ancien state)
gsutil versioning set on gs://jobmatch-terraform-state-$PROJECT_ID

# Verifier
gsutil ls
# Doit afficher: gs://jobmatch-terraform-state-job-match-v0/
```

---

### Etape 7 : Initialiser et appliquer Terraform

```bash
# Aller dans le dossier Terraform
cd infra/terraform

# Creer le fichier de variables
cp terraform.tfvars.example terraform.tfvars

# Editer si necessaire (le fichier example est deja configure pour job-match-v0)
# nano terraform.tfvars

# Initialiser Terraform (telecharge les providers, connecte au backend)
terraform init

# Voir ce qui va etre cree
terraform plan

# Appliquer (cree l'infrastructure)
terraform apply
# Tape "yes" pour confirmer
```

**Duree** : ~5-10 minutes pour creer la VM, le reseau, les buckets, BigQuery, etc.

---

### Etape 8 : Noter les outputs

Apres `terraform apply`, note ces valeurs importantes :

```bash
terraform output

# Outputs importants :
# - vm_external_ip : IP publique de la VM
# - workload_identity_provider : Pour GitHub Actions
# - deploy_service_account : Pour GitHub Actions
```

---

## PARTIE 2 : Configuration CI/CD avec GitHub Actions

Une fois l'infrastructure creee, configure GitHub Actions pour les deploiements automatiques.

### Methode A : Workload Identity Federation (Recommandee)

**Avantages** :
- Pas de cle JSON a gerer
- Pas de secret qui peut fuiter
- Rotation automatique des credentials

#### A.1 L'infrastructure est deja creee par Terraform

Le fichier `iam.tf` a deja cree :
- Le Workload Identity Pool
- Le Provider OIDC pour GitHub
- Les bindings IAM

#### A.2 Recuperer les valeurs pour GitHub Secrets

```bash
cd infra/terraform

# Recuperer le provider complet
terraform output workload_identity_provider

# Recuperer le service account de deploiement
terraform output deploy_service_account

# Recuperer le service account Terraform
terraform output terraform_service_account
```

#### A.3 Configurer les GitHub Secrets

Va dans ton repo GitHub : **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Valeur | Description |
|-------------|--------|-------------|
| `GCP_PROJECT_ID` | `job-match-v0` | ID du projet |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | (output terraform) | Format: `projects/123.../providers/github-provider` |
| `GCP_TERRAFORM_SERVICE_ACCOUNT` | `terraform-sa@job-match-v0.iam.gserviceaccount.com` | Pour workflow Terraform |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `deploy-sa@job-match-v0.iam.gserviceaccount.com` | Pour workflow Deploy |

**Secrets applicatifs** (pour le .env sur la VM) :

| Secret Name | Valeur |
|-------------|--------|
| `POSTGRES_USER` | `jobmatch` |
| `POSTGRES_PASSWORD` | (genere un mot de passe fort) |
| `POSTGRES_DB` | `jobmatch` |
| `DJANGO_SECRET_KEY` | (genere avec `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `LLM_API_KEY` | (ta cle API LLM) |
| `LLM_ENDPOINT` | `https://llm.molp.fr/v1` |

#### A.4 Creer un Environment "production" (optionnel mais recommande)

1. **Settings → Environments → New environment**
2. Nom : `production`
3. Ajouter des "Required reviewers" si tu veux une approbation avant deploiement

---

### Methode B : Cle JSON Service Account (Alternative)

**A utiliser seulement si** :
- Workload Identity Federation ne fonctionne pas
- Tu as besoin de credentials hors GitHub Actions
- Tu fais du debug local

#### B.1 Creer une cle JSON

```bash
# Se placer dans un dossier securise (pas dans le repo!)
cd ~

# Creer la cle pour le SA Terraform
gcloud iam service-accounts keys create terraform-sa-key.json \
    --iam-account=terraform-sa@job-match-v0.iam.gserviceaccount.com

# Creer la cle pour le SA Deploy
gcloud iam service-accounts keys create deploy-sa-key.json \
    --iam-account=deploy-sa@job-match-v0.iam.gserviceaccount.com

# IMPORTANT: Ces fichiers contiennent des secrets!
# Ne JAMAIS les commiter dans git
```

#### B.2 Utiliser la cle localement

```bash
# Option 1: Variable d'environnement
export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-sa-key.json

# Option 2: Dans Terraform provider
# (Deconseille - hardcode le chemin)
```

#### B.3 Stocker dans GitHub Secrets

1. Ouvre le fichier JSON :
   ```bash
   cat ~/terraform-sa-key.json
   ```

2. Copie TOUT le contenu (y compris les accolades)

3. Dans GitHub : **Settings → Secrets → New secret**
   - Name: `GCP_SA_KEY`
   - Value: (colle le JSON complet)

#### B.4 Workflow avec cle JSON

```yaml
# .github/workflows/terraform.yml (version JSON key)
name: Terraform

on:
  push:
    branches: [main]
    paths: ['infra/terraform/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra/terraform

    steps:
      - uses: actions/checkout@v4

      # Authentification avec cle JSON
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
```

#### B.5 Securite des cles JSON

**CRITIQUE** : Les cles JSON sont des secrets permanents.

```bash
# Lister les cles existantes
gcloud iam service-accounts keys list \
    --iam-account=terraform-sa@job-match-v0.iam.gserviceaccount.com

# Supprimer une cle (rotation)
gcloud iam service-accounts keys delete KEY_ID \
    --iam-account=terraform-sa@job-match-v0.iam.gserviceaccount.com
```

**Bonnes pratiques** :
- Rotation tous les 90 jours
- Une cle par usage (pas de partage)
- Supprimer immediatement si fuite suspectee

---

## PARTIE 3 : Gestion des droits IAM

### Hierarchie GCP

```
Organisation (optionnel pour compte perso)
    │
    └── Projet: job-match-v0
            │
            ├── Ressources
            │   ├── Compute Engine (VM)
            │   ├── Cloud Storage (Buckets)
            │   └── BigQuery (Datasets)
            │
            └── IAM
                ├── Membres (users, groups, service accounts)
                └── Roles (permissions)
```

### Concepts cles

#### Membres (Principals)

| Type | Format | Exemple |
|------|--------|---------|
| Utilisateur | `user:email` | `user:matthieu@gmail.com` |
| Groupe | `group:email` | `group:dev-team@googlegroups.com` |
| Service Account | `serviceAccount:email` | `serviceAccount:terraform-sa@project.iam.gserviceaccount.com` |

#### Roles principaux

| Role | Description | Qui |
|------|-------------|-----|
| `roles/owner` | Controle total | Toi uniquement |
| `roles/editor` | Lecture + ecriture | Dangereux, eviter |
| `roles/viewer` | Lecture seule | Observateurs |

#### Roles par service

**Compute Engine** :
| Role | Description |
|------|-------------|
| `roles/compute.viewer` | Voir les VM |
| `roles/compute.instanceAdmin.v1` | Gerer les VM (start/stop/SSH) |
| `roles/compute.osLogin` | SSH via OS Login |

**Cloud Storage** :
| Role | Description |
|------|-------------|
| `roles/storage.objectViewer` | Lire les objets |
| `roles/storage.objectCreator` | Creer des objets |
| `roles/storage.objectAdmin` | CRUD sur objets |

**BigQuery** :
| Role | Description |
|------|-------------|
| `roles/bigquery.dataViewer` | Lire les donnees |
| `roles/bigquery.dataEditor` | Modifier les donnees |
| `roles/bigquery.jobUser` | Executer des requetes |

### Service Accounts du projet

| Service Account | Usage | Roles |
|-----------------|-------|-------|
| `terraform-sa` | Terraform (infra) | Editor, Storage Admin, IAM Admin |
| `deploy-sa` | GitHub Deploy | Compute Instance Admin, Storage Object Viewer |
| `vm-sa` | Runtime VM | Storage Object Admin, BigQuery Data Editor |

### Ajouter un collegue

#### Option A : Acces complet developpeur

```bash
PROJECT_ID=job-match-v0
EMAIL=collegue@gmail.com

# VM access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/compute.instanceAdmin.v1"

# Storage access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/storage.objectAdmin"

# BigQuery access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/bigquery.jobUser"
```

#### Option B : Lecture seule (Data Analyst)

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$EMAIL" \
    --role="roles/bigquery.jobUser"
```

#### Option C : Utiliser un groupe Google

1. Creer un groupe sur https://groups.google.com
2. Ajouter les membres
3. Donner les droits au groupe :

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="group:jobmatch-dev@googlegroups.com" \
    --role="roles/compute.instanceAdmin.v1"
```

---

## PARTIE 4 : Commandes utiles

### Authentification

```bash
# Verifier qui est connecte
gcloud auth list

# Verifier le projet actif
gcloud config get-value project

# Verifier les ADC
gcloud auth application-default print-access-token

# Re-authentifier
gcloud auth login
gcloud auth application-default login
```

### IAM

```bash
# Lister tous les membres du projet
gcloud projects get-iam-policy $PROJECT_ID

# Lister les roles d'un utilisateur
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:EMAIL" \
    --format="table(bindings.role)"

# Supprimer un role
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="user:EMAIL" \
    --role="ROLE"
```

### Service Accounts

```bash
# Lister les SA
gcloud iam service-accounts list

# Lister les cles d'un SA
gcloud iam service-accounts keys list \
    --iam-account=SA_EMAIL

# Creer une cle
gcloud iam service-accounts keys create key.json \
    --iam-account=SA_EMAIL

# Supprimer une cle
gcloud iam service-accounts keys delete KEY_ID \
    --iam-account=SA_EMAIL
```

### VM

```bash
# SSH sur la VM
gcloud compute ssh jobmatch-vm --zone=europe-west9-a

# Voir les logs de la VM
gcloud compute instances get-serial-port-output jobmatch-vm \
    --zone=europe-west9-a
```

---

## PARTIE 5 : Troubleshooting

### "Permission denied" ou "403 Forbidden"

1. **Verifier l'authentification** :
   ```bash
   gcloud auth list
   # L'etoile (*) doit etre sur ton compte
   ```

2. **Verifier les ADC** :
   ```bash
   gcloud auth application-default print-access-token
   # Doit afficher un token, pas une erreur
   ```

3. **Verifier le projet** :
   ```bash
   gcloud config get-value project
   # Doit afficher job-match-v0
   ```

4. **Verifier les APIs** :
   ```bash
   gcloud services list --enabled | grep -E "(compute|storage|bigquery)"
   ```

### "Billing account not found"

La facturation n'est pas liee. Voir Etape 3.

### "storage.NewClient() failed: dialing: google: could not find default credentials"

Les Application Default Credentials ne sont pas configurees :

```bash
gcloud auth application-default login
```

### "The project is not found"

```bash
# Verifier que le projet existe
gcloud projects list

# Verifier le projet actif
gcloud config get-value project

# Changer de projet
gcloud config set project job-match-v0
```

### Terraform "Error acquiring the state lock"

Quelqu'un d'autre utilise Terraform, ou un precedent run a crash :

```bash
# Forcer le deverrouillage (ATTENTION: s'assurer que personne d'autre ne l'utilise)
terraform force-unlock LOCK_ID
```

### GitHub Actions "Unable to detect credentials"

1. Verifier que `id-token: write` est dans les permissions du workflow
2. Verifier les secrets GitHub
3. Verifier que le Workload Identity Pool est correctement configure

---

## Resume : Checklist de configuration

### Bootstrap initial (une fois)

- [ ] gcloud CLI installe
- [ ] `gcloud auth login` execute
- [ ] Projet cree (`gcloud projects create`)
- [ ] Facturation activee (Console GCP)
- [ ] `gcloud auth application-default login` execute
- [ ] APIs activees (`gcloud services enable`)
- [ ] Bucket Terraform state cree (`gsutil mb`)
- [ ] `terraform init` reussi
- [ ] `terraform apply` reussi

### GitHub Actions

- [ ] Secrets configures dans GitHub
- [ ] Environment "production" cree (optionnel)
- [ ] Premier workflow execute avec succes

---

*Document cree le 2025-12-29 - JobMatch V0*
