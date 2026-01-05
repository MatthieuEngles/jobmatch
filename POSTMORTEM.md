# Postmortem - JobMatch

## 📅 Sessions

### 2026-01-05 (36) - Implémentation Workflows CI/CD Multi-Environnement

**Contexte:** Suite de la session 35. Implémentation concrète des workflows GitHub Actions pour une architecture multi-environnement (staging/prod) avec gestion sécurisée des secrets via GCP Secret Manager.

**Réalisations:**

- **Refonte terraform.yml** : Workflow multi-environnement automatisé
  - Détection automatique d'environnement : `main` → prod, `staging` → staging
  - Plan + Apply automatique sur push vers main/staging
  - Plan only sur PR (commentaire dans la PR)
  - Déclenchement manuel avec choix environnement/action
  - **Mise à jour GitHub Variables** après apply : `GCS_BUCKET_PROD`, `VM_NAME_STAGING`, etc.
  - Changement `secrets.GCP_*` → `vars.GCP_*` (identifiants, pas sensibles)

- **Refonte deploy.yml** : Déploiement sécurisé sans secrets
  - Support branches main et staging
  - Plus d'écriture de secrets dans .env
  - Seules variables dans .env : `ENVIRONMENT=prod` et `GCP_PROJECT_ID`
  - Applications lisent secrets directement depuis Secret Manager à runtime
  - VM_NAME dynamique depuis GitHub Variables (set par Terraform)
  - Branch checkout adapté à l'environnement

- **Documentation mise à jour** : `docs/multi_environnement_gestion.md`
  - Architecture Secret Manager avec lecture directe (jamais sur disque)
  - Code module `app/shared/secrets.py` pour lecture secrets
  - Workflows détaillés avec Option B (Terraform séparé)
  - Checklist 7 phases pour implémentation

**Décisions techniques clés:**

| Décision | Justification |
|----------|---------------|
| Secrets JAMAIS sur disque | Principe "gros projet à risque" - secrets lus at runtime |
| GitHub Variables vs Secrets | Terraform outputs (buckets, VM names) = non-sensibles → Variables |
| Workflows séparés | terraform.yml pour infra, deploy.yml pour apps |
| Auto-apply on push | Simplifie le flow - "si c'est à jour, au moins c'est automatique" |
| Workload Identity | Pas de credentials dans CI/CD |

**Architecture finale workflows:**

```
push to main/staging (infra changes)
       ↓
  terraform.yml
       ↓
  plan → apply → update GitHub Variables
                        ↓
              GCS_BUCKET_PROD, VM_NAME_PROD, etc.

push to main/staging (app changes)
       ↓
   deploy.yml
       ↓
  reads GitHub Variables ← set by terraform.yml
       ↓
  SSH to VM → git pull → docker compose up
       ↓
  Apps read secrets from Secret Manager at runtime
```

**Fichiers modifiés:**
- `.github/workflows/terraform.yml` : Refonte complète multi-env
- `.github/workflows/deploy.yml` : Refonte sans secrets, multi-env
- `docs/multi_environnement_gestion.md` : Architecture Secret Manager

**GitHub Variables à créer (via Settings > Variables):**
- `GCP_WORKLOAD_IDENTITY_PROVIDER` : projects/xxx/locations/global/...
- `GCP_SERVICE_ACCOUNT` : terraform@project.iam.gserviceaccount.com
- `GCP_PROJECT_ID` : job-match-v0
- Les autres (GCS_BUCKET_*, VM_NAME_*, etc.) seront créées par Terraform

**Prochaines étapes:**
1. Créer les GitHub Variables dans le repo
2. Créer les secrets dans GCP Secret Manager (`jobmatch-{env}-{secret}`)
3. Implémenter `app/shared/secrets.py`
4. Ajouter Terraform outputs (gcs_bucket, vm_name, etc.)
5. Créer branche staging et tester le flow complet

---

### 2026-01-05 (35) - Design Multi-Environnement Staging + Documentation Gestion Secrets

**Contexte:** Conception d'une architecture multi-environnement (local/dev/staging/prod) pour JobMatch avec focus sur la gestion des secrets et la détection d'environnement par les services.

**Réalisations:**

- **Documentation Multi-Environnement** : Création de `docs/multi_environnement_gestion.md`
  - 3 approches pour la détection d'environnement (ENV_MODE global, variables explicites, hybride)
  - Analyse d'impact par service (GUI, offre-ingestion, cv-ingestion, ai-assistant, matching)
  - Panorama complet de 9 techniques de gestion de secrets
  - Recommandations basées sur les principes 12-Factor App
  - Workflows CI/CD avec GitHub Environments et GCP Secret Manager

- **Documentation Docker Compose** : Création de `docs/docker_compose_guide.md`
  - Guide d'utilisation en français
  - Section V1 vs V2 avec bug connu (panic slice bounds)

- **Audit Dockerfile Matching** : Créé `matthieu_perso/audit_matching_dockerfile.md`
  - 3 problèmes identifiés : contexte de build, incohérence ports, chemins modules

- **Documentation Sécurité** : Création de `docs/SECURITY_NOTES.md`
  - Faux positifs Bandit B608 (SQL injection) documentés

- **Fixes mineurs** :
  - `app/gui/services/offers_db.py` ligne 240 : Ajout `from e` (ruff B904)
  - Script accès GCP : `infra/scripts/add_gcp_access.sh` + `emails.txt`

**Problèmes identifiés (non résolus - discussion only):**

- **ENV_MODE seulement dans GUI** : Les autres services n'ont pas de notion d'environnement
- **Datasets hardcodés** : `offre-ingestion/transform_offers_to_bigquery_silver.py` ligne 91
  ```python
  DATASET_ID = "jobmatch_silver"  # HARDCODED - doit être variable d'environnement
  ```
- **deploy.yml incomplet** : Génère .env sans variables GCP (buckets, datasets)

**Décisions techniques prises:**

- **Approche Hybride (Option C)** : ENV_MODE pour comportement + variables explicites pour ressources
- **GCP Secret Manager** : Recommandé pour secrets (audit, rotation, versioning)
- **Terraform outputs** : Pour noms de ressources non-sensibles (buckets, datasets)
- **Workload Identity Federation** : Déjà en place, pas de secrets GCP à gérer
- **États Terraform séparés** : Un state par environnement (staging/prod)
- **VM staging séparée** : Option A retenue
- **Branche staging** : Depuis dev, pas depuis main

**Fichiers créés:**
- `docs/multi_environnement_gestion.md` : Documentation principale (~800 lignes)
- `docs/docker_compose_guide.md` : Guide Docker Compose en français
- `docs/SECURITY_NOTES.md` : Faux positifs Bandit
- `matthieu_perso/audit_matching_dockerfile.md` : Audit Dockerfile
- `infra/scripts/add_gcp_access.sh` : Script accès GCP équipe
- `infra/scripts/emails.txt` : Template emails

**Prochaines étapes (à implémenter plus tard):**
1. Ajouter ENV_MODE à tous les services
2. Paramétrer datasets/buckets via variables d'environnement dans offre-ingestion
3. Configurer GitHub Environments (staging/production)
4. Créer infrastructure staging avec Terraform
5. Mettre à jour deploy.yml pour multi-environnement

---

### 2025-12-30 (34) - Top Offres : Correction Ajout Candidatures + Documentation Architecture

**Contexte:** Correction des bugs dans le flux d'ajout d'offres aux candidatures et création de la documentation technique d'architecture du système Top Offres.

**Réalisations:**

- **Fix ImportError** : Ajout de `ImportedOffer` aux imports dans `accounts/views.py` (ligne 36)
  - Erreur : `name 'ImportedOffer' is not defined`

- **Fix création Application manquante** : Modification de `add_offer_to_applications_view`
  - Bug : L'offre était importée (`ImportedOffer.objects.create()`) mais aucune `Application` n'était créée
  - Fix : Ajout de `Application.objects.create()` après la création de l'ImportedOffer
  - L'utilisateur peut maintenant voir l'offre dans "Suivi des candidatures"

- **Fix rechargement sidebar** : Ajout de `window.location.reload()` dans le handler JS
  - Bug : Après ajout d'une offre, la carte "Suivi des candidatures" ne se mettait pas à jour
  - Fix : Rechargement complet de la page après 1s (solution simple et efficace)

- **Documentation Architecture** : Création de `docs/top_offers_architecture.md`
  - Schéma flux utilisateur complet
  - Architecture mode mock (USE_MOCK_MATCHING=true) avec SQLite Silver DB
  - Architecture mode production avec BigQuery et matching API
  - Modèles de données (CandidateProfile, MatchResult, TopOfferResult, ImportedOffer, Application)
  - Endpoints API documentés
  - Structure table BigQuery `gold.offers` avec colonnes embeddings

- **Export PDF** : Génération de `docs/top_offers_architecture.pdf` via pandoc

**Problèmes rencontrés:**

- **Docker ContainerConfig KeyError** : Erreur récurrente au rebuild
  - Solution : `docker rm -f <container_id>` puis `docker-compose up -d`

- **Offres non ajoutées aux candidatures** :
  - Diagnostic : Query SQL confirmant ImportedOffer créé (id=13) mais Application manquante
  - Cause : `add_offer_to_applications_view` créait seulement ImportedOffer
  - Solution : Ajout de la création d'Application dans la même vue

**Décisions techniques:**

- **Deux embeddings séparés** : `title_embedding` (384 dims) + `cv_embedding` (384 dims)
  - title_embedding : généré depuis profile.description ou profile.title
  - cv_embedding : généré depuis les lignes CV sélectionnées du profil

- **Embeddings dans BigQuery** : Colonnes `ARRAY<FLOAT64>` dans `gold.offers` (pas de vector DB séparée)

- **Rechargement page** : Choisi plutôt qu'AJAX partiel pour simplicité et fiabilité

**Fichiers modifiés:**
- `app/gui/accounts/views.py` : Import ImportedOffer + création Application
- `app/gui/templates/home.html` : Reload page après ajout offre
- `docs/top_offers_architecture.md` : Nouvelle documentation (créé)
- `docs/top_offers_architecture.pdf` : Export PDF (créé)

---

### 2025-12-29 (33) - Feature Top Offres Pour Vous (Design + Documentation)

**Contexte:** Ajout d'une nouvelle fonctionnalite permettant aux utilisateurs de rafraichir leurs recommandations d'offres d'emploi personnalisees.

**Realisations:**

- **Bouton Rafraichir** : Ajout du bouton dans la carte "Top offres pour vous" sur la homepage
  - CSS avec animation de rotation au survol
  - Structure HTML modifiee (`<a>` → `<div>` + bouton separe)
  - ID `refresh-offers-btn` pour la future implementation JS

- **Documentation technique** : Creation de `doc_support_contexte/FEATURE_TOP_OFFERS.md`
  - Architecture complete du flux (GUI → Shared → Matching → Gold DB)
  - Contrat API matching defini (POST `/api/match` avec embeddings + top_k)
  - Schemas de base de donnees Gold (embeddings + details)
  - Responsabilites par composant (Matthieu: GUI/Shared, Maxime: Matching)

**Decisions techniques:**

- **Gold DB unifie** : Les details des offres (intitule, description, entreprise) seront dans Gold DB (pas Silver)
- **Embeddings calcules cote GUI** : La GUI utilise `app/shared/` pour generer les embeddings avant d'appeler matching
- **API Matching simple** : Entree = 2 embeddings + top_k, Sortie = liste (offer_id, score)
- **Fusion multi-profils** : GUI fusionne les resultats de tous les profils, dedup par meilleur score

**Fichiers modifies:**
- `app/gui/templates/home.html` : Bouton rafraichir + CSS
- `doc_support_contexte/FEATURE_TOP_OFFERS.md` : Documentation complete (nouveau fichier)

**Prochaines etapes:**
1. Implementation du backend Django (endpoint AJAX)
2. Implementation du frontend JS (appel AJAX, loading state, affichage resultats)
3. Coordination avec Maxime pour l'API matching
4. Tests d'integration

---

### 2025-12-29 (32) - Exécution Terraform + Configuration GitHub Secrets

**Contexte:** Suite de la session 31, exécution du Terraform et résolution des problèmes de déploiement.

**Réalisations:**

- **Terraform apply réussi** : Infrastructure GCP créée (VM europe-west1, VPC, Storage, BigQuery, IAM)
- **Zone dynamique** : Ajout de `data.google_compute_zones.available` pour sélectionner automatiquement une zone disponible
- **Documentation enrichie** : Section détaillée configuration GitHub Secrets dans GCP_IAM_GUIDE.md avec erreur exacte et étapes pas à pas
- **Workflow deploy.yml corrigé** : Récupération dynamique de la zone VM via `gcloud compute instances list`

**Problèmes rencontrés:**

- **VM unavailable europe-west9** :
  - Symptôme : `e2-standard-2 is currently unavailable in europe-west9-b zone`
  - Solution : Changement région vers `europe-west1` (Belgique) + zone dynamique

- **BigQuery dataset "already exists"** :
  - Symptôme : `Error 409: Already Exists: Dataset job-match-v0:jobmatch_gold`
  - Cause : Bug provider Google, dataset créé mais pas dans le state
  - Solution : `terraform import google_bigquery_dataset.gold job-match-v0/jobmatch_gold`

- **GitHub Actions "workload_identity_provider" error** :
  - Symptôme : `google-github-actions/auth failed with: must specify exactly one of "workload_identity_provider" or "credentials_json"`
  - Cause : Secrets GitHub non configurés
  - Solution : Documenter la configuration complète des secrets dans GCP_IAM_GUIDE.md

- **Terraform --classic snap** :
  - Symptôme : `error: This revision of snap "terraform" was published using classic confinement`
  - Solution : `sudo snap install terraform --classic`

- **Application Default Credentials manquantes** :
  - Symptôme : `storage.NewClient() failed: could not find default credentials`
  - Cause : `gcloud auth login` ≠ `gcloud auth application-default login`
  - Solution : Exécuter les deux commandes, documenter la différence

**Décisions techniques:**

- **europe-west1** au lieu de europe-west9 : Plus de disponibilité VM
- **Zone dynamique** : `data.google_compute_zones.available.names[0]` évite les erreurs de capacité
- **Deux types d'auth gcloud** : Documenter `auth login` (CLI) vs `auth application-default login` (SDK/Terraform)

**Fichiers modifiés:**
- `infra/terraform/vm.tf` : Ajout data source zones dynamique
- `infra/terraform/outputs.tf` : Références zone dynamique
- `infra/terraform/terraform.tfvars.example` : Région europe-west1, suppression variable zone
- `.github/workflows/deploy.yml` : GCP_REGION + récupération zone dynamique
- `infra/docs/GCP_IAM_GUIDE.md` : Section détaillée GitHub Secrets

**Prochaines étapes:**
1. Configurer les secrets GitHub (voir GCP_IAM_GUIDE.md section A.3)
2. Donner accès GCP à Mohamed (Storage + BigQuery)
3. Intégration BigQuery dans offre-ingestion
4. Déploiement initial sur la VM

---

### 2025-12-29 (31) - Infrastructure Terraform GCP + CI/CD GitHub Actions

**Contexte:** Création de l'infrastructure de déploiement V0 sur Google Cloud Platform avec Terraform et CI/CD via GitHub Actions.

**Réalisations:**

- **Documentation architecture** (`infra/docs/`) :
  - `ARCHITECTURE_V0.md` : Schéma complet de l'infra (VM, VPC, Storage, BigQuery), estimation coûts (~32€/mois), flux de données, CI/CD
  - `GCP_IAM_GUIDE.md` : Guide complet gestion des droits IAM, Workload Identity Federation, ajout collègues

- **Terraform complet** (`infra/terraform/`) :
  - `main.tf` : Provider GCP, backend GCS, activation APIs
  - `variables.tf` : Toutes les variables configurables
  - `network.tf` : VPC custom, subnet, IP statique, firewall (22, 80, 443)
  - `vm.tf` : VM e2-medium Ubuntu 22.04 avec startup script (Docker, Caddy, Git)
  - `storage.tf` : Buckets bronze (offres JSON) + backups avec lifecycle policies
  - `bigquery.tf` : Datasets silver/gold avec tables offers, skills, formations, etc.
  - `iam.tf` : 3 Service Accounts (vm, terraform, deploy) + Workload Identity Federation
  - `outputs.tf` : Outputs utiles (IP, SSH command, secrets GitHub)

- **GitHub Actions CI/CD** (`.github/workflows/`) :
  - `terraform.yml` : Plan sur PR, Apply sur push main
  - `deploy.yml` : Build Docker + deploy sur VM via SSH

**Problèmes rencontrés:**

- **Variable `$PROJECT_ID` non définie** :
  - Symptôme : `gsutil mb` échoue avec "Invalid bucket name"
  - Solution : Utiliser `$(gcloud config get-value project)` ou hardcoder `job-match-v0`

- **Billing account not linked** :
  - Symptôme : `gcloud services enable` échoue avec FAILED_PRECONDITION
  - Solution : Activer la facturation via Console GCP avant d'activer les APIs
  - Documenté dans GCP_IAM_GUIDE.md comme étape obligatoire

- **Terraform ne déploie pas les changements de code** (cf. POSTMORTEM_miniterraform) :
  - Cause : Terraform compare la configuration, pas le contenu des images Docker
  - Solution : `docker compose build --no-cache --pull` + `down` + `up -d` dans deploy.yml

**Décisions techniques:**

- **Workload Identity Federation** (pas de clé JSON) : Méthode recommandée par Google, pas de secret à gérer
- **VM unique avec docker-compose** : Simple pour V0, migration vers Cloud Run possible en V1
- **Caddy sur VM** : SSL automatique avec Let's Encrypt, gratuit
- **IP statique** : Stabilité DNS, gratuit si attachée à une VM
- **BigQuery pour Silver/Gold** : Analytics, pas de serveur à gérer
- **Backend GCS pour Terraform** : State partagé entre CI/CD et local

**Fichiers créés:**
```
infra/
├── docs/
│   ├── ARCHITECTURE_V0.md
│   └── GCP_IAM_GUIDE.md
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── network.tf
    ├── vm.tf
    ├── storage.tf
    ├── bigquery.tf
    ├── iam.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    └── .gitignore
.github/workflows/
├── terraform.yml
└── deploy.yml
```

**Prochaines étapes:**
1. Créer le bucket Terraform state : `gsutil mb -l EU gs://jobmatch-terraform-state-job-match-v0`
2. Configurer les secrets GitHub
3. Premier `terraform init` + `terraform apply`
4. Configurer DNS vers IP statique

---

### 2025-12-29 (30) - Local Ollama Docker + README + Debug cv-ingestion LLM

**Contexte:** Ajouter un serveur Ollama local en Docker avec modèles Mistral pré-téléchargés, créer le README global du projet, et débugger les problèmes de connexion LLM pour cv-ingestion.

**Réalisations:**

- **Service local-ollama Docker** :
  - Nouveau dossier `app/local_ollama/` avec Dockerfile et entrypoint
  - Modèles `mistral:latest` et `mistral:7b` téléchargés au build
  - Service ajouté dans docker-compose.yml (port 11434)
  - Volume `ollama_data` pour persister les modèles

- **README.md global** :
  - Architecture du projet avec arborescence
  - Table des services avec ports et status (OK/WIP)
  - Instructions de démarrage (docker-compose + dev.sh)
  - Documentation de tous les services : gui, ai-assistant, cv-ingestion, offre-ingestion, matching, local-ollama
  - Configuration et variables d'environnement
  - Stack technique et conventions

- **Documentation schémas Django** :
  - Explication du modèle User (AbstractUser avec préférences)
  - Explication du modèle CandidateProfile
  - Relation CandidateProfile ↔ ExtractedLine via ProfileItemSelection (N:N)

**Problèmes rencontrés:**

- **cv-ingestion : "model 'ministral-3:14b' not found"** :
  - Symptôme : Erreur 404 sur l'endpoint `/v1/chat/completions`
  - Cause : Le serveur distant `llm.molp.fr` expose l'API Ollama native (`/api/tags`, `/api/generate`) mais l'API OpenAI-compatible (`/v1/models`, `/v1/chat/completions`) ne liste aucun modèle
  - Le SDK OpenAI utilisé par cv-ingestion appelle `/v1/chat/completions` qui retourne "model not found"
  - `/api/tags` montre les modèles mais `/v1/models` retourne une liste vide
  - Status : Non résolu - problème côté serveur `llm.molp.fr`

**Décisions techniques:**

- **Modèles téléchargés au build** : Plutôt qu'au runtime (entrypoint), pour un démarrage plus rapide des containers
- **Volume Docker pour Ollama** : Les modèles sont volumineux (~4GB), évite de re-télécharger à chaque rebuild
- **README structuré par service** : Chaque microservice a sa section avec exemples curl

**Fichiers créés/modifiés:**
- `app/local_ollama/Dockerfile` : Image Ollama avec pull des modèles
- `app/local_ollama/entrypoint.sh` : Script de démarrage simplifié
- `docker-compose.yml` : Service local-ollama + volume ollama_data
- `README.md` : Documentation complète du projet (nouveau fichier)

---

### 2025-12-24 (29) - Boutons Voir/Télécharger DOCX pour CV et Lettre

**Contexte:** Améliorer l'UX de la page candidature en ajoutant des boutons d'action (voir/télécharger) pour les documents générés, avec export DOCX.

**Réalisations:**

- **Nouveau layout document-item** :
  - Remplacé les simples boutons texte par des cartes `.document-item` avec icônes d'action
  - Deux boutons par document : œil (voir) et flèche (télécharger DOCX)
  - Design cohérent avec hover effet violet

- **Export DOCX avec docx.js** :
  - Chargement dynamique de la librairie docx.js depuis unpkg CDN
  - Parsing intelligent du contenu : détection des headers `--- TITLE ---`, bullet points, paragraphes
  - Formatage DOCX avec titres colorés (#667eea), bullet points natifs
  - Nommage fichier avec nom entreprise slugifié

- **Amélioration modal preview** :
  - Ajout bouton "Télécharger DOCX" dans le footer de la modal
  - Variable `currentPreviewType` pour savoir quel document est affiché

**Fonctions JavaScript ajoutées:**
- `downloadDocx(type)` : télécharge CV ou lettre selon le type
- `downloadCurrentDocx()` : télécharge le document actuellement prévisualisé
- `generateDocx(content, title, fileName)` : génère et télécharge le DOCX

**Fichiers modifiés:**
- `app/gui/templates/accounts/application_detail.html` : CSS + JS + HTML pour boutons action

---

### 2025-12-24 (28) - Génération CV/Lettre de motivation + Fix async pattern

**Contexte:** Implémentation de la génération IA de CV et lettres de motivation personnalisés pour les candidatures, avec correction du pattern async pour éviter les timeouts.

**Réalisations:**

- **Génération de CV personnalisé** :
  - Nouveau prompt `cv_generation.txt` avec optimisation ATS (intitulé proche de l'offre, mots-clés exacts)
  - Ajout des liens sociaux (LinkedIn, Portfolio, GitHub) dans le CV
  - Endpoint FastAPI `/generate/cv` avec task_id + polling

- **Génération de lettre de motivation** :
  - Nouveau prompt `cover_letter_generation.txt`
  - Utilise le CV généré comme référence pour cohérence
  - Endpoint FastAPI `/generate/cover-letter`

- **Schémas Pydantic** (schemas.py) :
  - `CandidateContext` : profil complet avec social_links
  - `JobOfferContext` : offre cible
  - `GenerateCVRequest/Response`, `GenerateCoverLetterRequest/Response`
  - `GenerationTaskStatusResponse` pour le polling

- **UI génération** (application_detail.html) :
  - Boutons "Générer CV" et "Générer la lettre"
  - Animation loading pendant la génération
  - Polling status toutes les 2 secondes
  - Modal de preview pour visualiser les documents générés
  - Sauvegarde automatique en base après génération

- **Documentation pattern async** (docs/ASYNC_PATTERNS.md) :
  - Explication complète du problème de timeout
  - Diagramme du flow task_id + polling
  - Exemples code FastAPI, Django, JavaScript
  - Pièges à éviter (BackgroundTasks vs create_task, to_thread)

**Problèmes rencontrés:**

- **"Service IA indisponible" (timeout 10s)** :
  - Symptôme : Django timeout après 10s, mais ai-assistant génère bien le CV (30s)
  - Cause : `BackgroundTasks.add_task()` n'est pas vraiment async - attend la fin de la fonction
  - Cause 2 : `provider.chat()` est synchrone, bloque l'event loop même dans une fonction `async`

- **Solution double** :
  1. Remplacer `background_tasks.add_task(fn)` par `asyncio.create_task(fn())` pour retourner immédiatement
  2. Utiliser `asyncio.to_thread(provider.chat, ...)` pour exécuter l'appel LLM synchrone dans un thread séparé

- **docker-compose KeyError 'ContainerConfig'** :
  - Bug de docker-compose avec des containers stale
  - Solution : `docker-compose stop svc && docker-compose rm -f svc && docker-compose up -d svc`

**Décisions techniques:**

- **Task-based polling plutôt que streaming** : Pour génération one-shot (CV, lettre), le polling est plus simple et robuste que SSE
- **asyncio.create_task() plutôt que BackgroundTasks** : Seule façon d'avoir une vraie exécution non-bloquante avec FastAPI
- **asyncio.to_thread() pour LLM calls** : Les SDKs OpenAI/Anthropic sont synchrones, nécessitent un thread pool
- **Documentation dédiée** : Pattern async suffisamment complexe pour mériter un fichier docs/ASYNC_PATTERNS.md

**Fichiers créés/modifiés:**
- `app/ai-assistant/src/main.py` : asyncio.create_task() pour génération
- `app/ai-assistant/src/llm/chat_handler.py` : asyncio.to_thread() pour LLM calls + social_links
- `app/ai-assistant/src/prompts/cv_generation.txt` : prompt CV avec ATS
- `app/ai-assistant/src/schemas.py` : CandidateContext.social_links
- `app/gui/accounts/views.py` : endpoints génération + status polling + save
- `app/gui/templates/accounts/application_detail.html` : UI génération complète
- `docs/ASYNC_PATTERNS.md` : documentation pattern pending/done

---

### 2025-12-24 (27) - Candidatures sur Home + Fix ENV_MODE Docker + Migrations
**Contexte:** Afficher les candidatures récentes sur la page d'accueil et résoudre les problèmes de configuration Docker (ENV_MODE, base de données).

**Réalisations:**

- **Affichage candidatures sur page d'accueil** :
  - Nouvelle vue `HomeView` dans `config/views.py` (remplace `TemplateView` générique)
  - Passe `recent_applications` (3 dernières) et `applications_count` au template
  - Mini-cartes dans la section "Suivi des candidatures" avec : entreprise, status coloré, titre
  - Badge compteur dans le header de la carte
  - Lien "Voir toutes mes candidatures (N)"

- **Styles CSS pour mini-cartes** :
  - `.application-mini-card` avec bordure gauche colorée
  - Badges status colorés : `.app-status-added` (gris), `.app-status-in_progress` (bleu), `.app-status-applied` (orange), `.app-status-interview` (violet), `.app-status-accepted` (vert), `.app-status-rejected` (rouge)

- **Fix ENV_MODE dans docker-compose.yml** :
  - Ajout `ENV_MODE=dev` pour le service gui
  - Ajout variables PostgreSQL : `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`, etc.
  - Suppression dépendances vers services non implémentés (cv-ingestion, ai-assistant)

- **Commande `full-restart` dans dev.sh** :
  - `./dev.sh full-restart [svc]` : stop + rm + build + up
  - Message d'aide amélioré avec liste formatée

- **Fix IntegrityError sur import d'offre** :
  - Remplacé `Application.objects.create()` par `get_or_create()` dans `ImportOfferView`
  - Évite erreur si l'Application existe déjà pour ce user+offre

**Problèmes rencontrés:**
- **`no such table: accounts_application`** (SQLite erreur) :
  - Cause : `ENV_MODE` non défini → Django utilisait mode "local" mais psycopg2 absent → fallback SQLite
  - Solution : ajouter `ENV_MODE=dev` dans docker-compose.yml pour forcer PostgreSQL

- **`relation "accounts_application" does not exist`** (PostgreSQL erreur) :
  - Cause : migration créée dans le container mais pas persistée dans le code source
  - Solution : `docker cp` pour récupérer la migration, puis `makemigrations && migrate`

- **Base de données vide après full-restart** :
  - Cause : nouveau container avec PostgreSQL vide (pas de user)
  - Solution : créer superuser via `manage.py shell`

**Décisions techniques:**
- **Vue HomeView plutôt que TemplateView** : nécessaire pour passer le contexte dynamique (candidatures)
- **get_or_create pour Application** : idempotent, évite les erreurs de doublon
- **docker cp pour migrations** : récupérer les fichiers générés dans le container vers le code source

**Fichiers créés/modifiés:**
- `app/gui/config/views.py` : nouvelle HomeView
- `app/gui/config/urls.py` : utilise HomeView au lieu de TemplateView
- `app/gui/templates/home.html` : mini-cartes candidatures + CSS
- `docker-compose.yml` : ENV_MODE=dev + variables PostgreSQL
- `dev.sh` : commande full-restart + aide améliorée
- `app/gui/api/views.py` : get_or_create pour Application
- `app/gui/accounts/migrations/0016_add_application_model.py` : migration Application

---

### 2025-12-24 (26) - Dev Workflow + Base de données partagée + Script dev.sh
**Contexte:** Résoudre le problème de perte de données entre les rebuilds Docker et améliorer le workflow de développement.

**Réalisations:**

- **Base de données partagée Local/Docker** :
  - Avant : Local utilisait SQLite, Docker utilisait PostgreSQL → données séparées
  - Après : Les deux modes utilisent le même PostgreSQL Docker
  - Local se connecte via `localhost:5433` (port exposé)
  - Docker se connecte via `db:5432` (réseau interne)
  - Modification dans `settings.py` : config DB unifiée

- **Script interactif `dev.sh`** :
  - Menu interactif avec emojis et couleurs
  - Affichage du status des containers au démarrage
  - Sous-menus : Start, Stop, Rebuild, Logs, Shell, Migrations, Reset DB
  - Mode rapide en ligne de commande : `./dev.sh start`, `./dev.sh rebuild gui`, etc.
  - Gestion gracieuse des services non implémentés (skip avec warning)
  - Option "Start core services only" pour ne démarrer que db + gui

- **Commandes rapides disponibles** :
  ```bash
  ./dev.sh start              # Démarre db + gui
  ./dev.sh stop               # Arrête tout (données préservées)
  ./dev.sh rebuild gui        # Rebuild + restart gui
  ./dev.sh logs gui           # Voir les logs
  ./dev.sh migrate            # Appliquer migrations
  ./dev.sh shell              # Django shell
  ```

**Problèmes rencontrés:**
- **Perte de données après rebuild** : causée par l'utilisation de bases différentes (SQLite local vs PostgreSQL Docker)
  - Solution : unifier sur PostgreSQL, accessible via port exposé en local
- **Migration manquante** : `no such table: accounts_application` après création du modèle
  - Solution : `docker-compose exec -T gui python manage.py makemigrations && migrate`

**Décisions techniques:**
- **PostgreSQL partout** : cohérence des données entre modes de développement
- **Volume Docker persistant** : `postgres_data` survit aux `docker-compose down` (sans `-v`)
- **Script interactif** : plus user-friendly que des commandes manuelles
- **Mode rapide CLI** : pour les actions fréquentes sans passer par le menu

**Fichiers créés/modifiés:**
- `dev.sh` : script de développement interactif
- `app/gui/config/settings.py` : config DB unifiée pour local/Docker

---

### 2025-12-24 (25) - Swagger Docs + Application Model + Candidatures UI
**Contexte:** Documenter l'API REST avec Swagger/OpenAPI, créer le modèle Application (candidature) et afficher les candidatures en cards.

**Réalisations:**

- **Documentation Swagger (drf-spectacular)** :
  - Ajout `drf-spectacular>=0.27` dans requirements.txt
  - Configuration dans settings.py : `SPECTACULAR_SETTINGS` avec titre, description, version
  - Routes ajoutées : `/api/schema/` (JSON), `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc)
  - Décorateurs `@extend_schema` sur toutes les vues API (tags, summary, request/response schemas)
  - Auth JWT intégrée avec `persistAuthorization: True` dans Swagger UI

- **Modèle Application (Candidature)** (migration 0016) :
  - Workflow status : added → in_progress → applied → interview → accepted/rejected
  - Liens : `imported_offer` (FK), `candidate_profile` (FK nullable)
  - Documents : `custom_cv` (TextField), `custom_cv_file` (FileField), `cover_letter`, `cover_letter_file`
  - Métadonnées : `interview_date`, `notes`, `history` (JSONField pour event tracking)
  - Helper methods : `add_history_event()`, `has_cv()`, `has_cover_letter()`, `get_completion_status()`
  - Dynamic upload paths : `applications/{user_id}/{app_id}/cv/` et `.../cover_letter/`

- **Auto-création Application sur import** :
  - Dans `ImportOfferView.post()` (api/views.py) : création automatique d'une Application après chaque ImportedOffer
  - Associe le `candidate_profile` si fourni lors de l'import

- **Page liste candidatures** (`/accounts/applications/`) :
  - Vue `applications_list_view` avec filtrage par status (query param `?status=`)
  - Compteurs par status : all, added, in_progress, applied, interview, accepted, rejected
  - Template cards avec : header (entreprise, titre), meta (lieu, contrat, remote), badge status, progress (CV, Lettre)
  - Grid responsive `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))`
  - Status badges colorés (vert=accepted, bleu=applied, orange=in_progress, rouge=rejected)

- **Intégration home page** :
  - Lien "Suivi des candidatures" → `/accounts/applications/`
  - Suppression du badge "coming soon"

**Problèmes rencontrés:**
- **Données perdues après rebuild** : l'offre test importée via l'extension a disparu après `docker-compose down/up`
  - Cause : volumes Docker recréés en dev
  - Note : comportement attendu, pas un bug

**Décisions techniques:**
- **drf-spectacular plutôt que drf-yasg** : plus moderne, meilleur support OpenAPI 3, maintenu activement
- **History en JSONField** : simplicité, pas besoin d'une table séparée pour le POC
- **Application auto-créée** : chaque offre importée démarre automatiquement le workflow de candidature
- **Status workflow linéaire** : added → in_progress → applied → interview → {accepted, rejected}

**Fichiers créés/modifiés:**
- `app/gui/requirements.txt` : ajout drf-spectacular
- `app/gui/config/settings.py` : config SPECTACULAR_SETTINGS
- `app/gui/api/urls.py` : routes schema/docs/redoc
- `app/gui/api/views.py` : extend_schema decorators + Application auto-create
- `app/gui/accounts/models.py` : Application model
- `app/gui/accounts/views.py` : applications_list_view
- `app/gui/accounts/urls.py` : route applications
- `app/gui/templates/accounts/applications_list.html` : nouveau template
- `app/gui/templates/home.html` : lien candidatures

---

### 2025-12-24 (24) - API REST Extension Navigateur (DRF + JWT)
**Contexte:** Créer une API REST pour l'extension navigateur JobMatch qui capture des offres d'emploi depuis n'importe quel site web.

**Réalisations:**

- **Nouvelle app Django `api/`** :
  - Structure complète : `urls.py`, `views.py`, `serializers.py`, `apps.py`
  - Séparation claire entre pages web (accounts) et API REST (api)
  - Prêt pour versioning futur (`/api/v1/`, `/api/v2/`)

- **Authentification JWT (SimpleJWT)** :
  - `POST /api/auth/token/` - Login → access + refresh tokens
  - `POST /api/auth/token/refresh/` - Rafraîchir le token
  - `GET /api/auth/user/` - Infos utilisateur courant
  - `POST /api/auth/logout/` - Blacklist refresh token
  - Config : access 15min, refresh 7 jours, rotation automatique

- **Endpoints offres importées** :
  - `POST /api/offers/import/` - Importer une offre capturée
  - `GET /api/offers/` - Lister les offres de l'utilisateur
  - `GET/PATCH/DELETE /api/offers/<id>/` - Détail, mise à jour status, suppression
  - `GET /api/health/` - Health check

- **Modèle `ImportedOffer`** (migration 0015) :
  - Champs source : `source_url`, `source_domain`, `captured_at`
  - Champs offre : `title`, `company`, `location`, `description`, `contract_type`, `remote_type`, `salary` (JSON), `skills` (JSON)
  - Matching : `match_score`, `matched_at` (TODO: intégration service matching)
  - Status : new, viewed, saved, applied, rejected
  - Contrainte unicité : `(user, source_url)` évite les doublons

- **Configuration CORS** :
  - Dev : `CORS_ALLOW_ALL_ORIGINS = True`
  - Prod : regex pour `chrome-extension://` et `moz-extension://`
  - Headers autorisés : authorization, content-type, etc.

- **Dépendances ajoutées** :
  - `djangorestframework>=3.14`
  - `djangorestframework-simplejwt>=5.3`
  - `django-cors-headers>=4.3`

**Problèmes rencontrés:**
- **ModuleNotFoundError rest_framework** : dépendances non installées en local
  - Solution : `pip install djangorestframework djangorestframework-simplejwt django-cors-headers`
- **Port 8085 déjà utilisé** : serveur Django déjà lancé
  - Solution : `docker-compose down && build && up`

**Décisions techniques:**
- **App séparée `api/`** : meilleure séparation des responsabilités que tout mettre dans `accounts`
- **JWT plutôt que sessions** : les sessions Django ne fonctionnent pas cross-origin pour les extensions
- **Rotation des refresh tokens** : sécurité renforcée, ancien token blacklisté après refresh
- **camelCase dans API** : convention frontend, snake_case dans les modèles Django
- **Contrainte unicité sur URL** : un utilisateur ne peut pas importer deux fois la même offre

**TODOs documentés:**
1. **Matching service integration** : appeler POST /match lors de l'import d'une offre
2. **CORS security** : restreindre aux IDs d'extensions spécifiques en production

**Fichiers créés:**
- `app/gui/api/__init__.py`, `apps.py`, `urls.py`, `views.py`, `serializers.py`
- `app/gui/accounts/migrations/0015_add_imported_offer.py`
- `docs/api_extension.md` - Documentation complète de l'API

---

### 2025-12-24 (23) - Architecture Offres/Matching + Infrastructure Cloud + Stratégie ML
**Contexte:** Concevoir l'architecture d'intégration entre le GUI, le service offres (Mohamed) et le service matching (Maxime), avec une vision cloud et stratégie ML long terme.

**Réalisations:**

- **Analyse base offers.db (Silver)** :
  - 13 tables SQLite : offers (principale), offers_lieu_travail, offers_entreprise, offers_salaire, offers_competences, etc.
  - 150 offres sample avec format France Travail (codes ROME, NAF)
  - Champs clés identifiés pour l'UI : intitule, typeContratLibelle, libelle (salaire), competences, formations

- **Architecture offres documentée** (`docs/interface_gui_offers.md`) :
  - Option 1 (recommandée) : API REST exposée par `offre-ingestion` → GUI consomme
  - Option 2 (pragmatique court terme) : Base partagée avec modèle Django `managed=False`
  - Mapping champs UI ↔ tables SQLite

- **Architecture matching documentée** (`docs/interface_gui_offers_match.md`) :
  - Flux complet : GUI → cv_embedding → Matcher → (id, score) top 20 → GUI → offre-ingestion → détails
  - Modèle cache `MatchResult` avec TTL 24h et invalidation sur changement profil
  - Modèles Django : `JobOffer`, `JobOfferSkill`, `MatchResult`
  - API specs : POST /match (CV embedding → scores), GET /offers/{id} (détail offre)

- **Analyse critique architecture actuelle** :
  - Points forts : microservices Docker, shared/ package, Factory pattern LLM, Medallion (Bronze→Silver→Gold)
  - Améliorations suggérées : pgvector, message queue, monitoring/alerting, CI/CD complet

- **Recommandation infrastructure GCP** :
  - Services : Cloud Run (serverless), Cloud SQL + pgvector, Vertex AI (embeddings), BigQuery, Memorystore
  - Coûts estimés : MVP ~50-60$/mois, Growth ~300-400$/mois
  - Migration en 4 phases : Local → GCP MVP → GCP Growth → GCP Scale

- **Stratégie ML & Embeddings** :
  - MVP : sentence-transformers pre-trained (all-MiniLM-L6-v2), pas de MLflow
  - V1 : collecte données via `OfferInteraction` model (vues, applications, embauches)
  - V2 : fine-tuning avec MLflow (contrastive learning, cross-encoder, learning to rank)
  - Dataset potentiel : profils + offres + candidatures = supervision implicite

- **Modèle OfferInteraction conçu** :
  ```python
  class OfferInteraction(models.Model):
      user = models.ForeignKey(User)
      offer_external_id = models.CharField(max_length=50)
      match_score = models.FloatField()  # Score initial du matcher
      viewed = models.BooleanField()
      time_spent_seconds = models.IntegerField()
      saved = models.BooleanField()
      applied = models.BooleanField()
      got_interview = models.BooleanField(null=True)
      got_hired = models.BooleanField(null=True)
  ```

**Problèmes rencontrés:**
- **Pandoc LaTeX unicode** : caractères ↔, ✅ non supportés par pdflatex
  - Solution 1 : xelatex engine
  - Solution 2 : Python markdown + wkhtmltopdf (sans LaTeX)

**Décisions techniques:**
- **API REST (Option 1)** : découplage propre GUI/offres, Mohamed contrôle son API
- **Cache lazy refresh** : TTL 24h avec invalidation explicite (pas de refresh proactif)
- **pgvector recommandé** : PostgreSQL extension pour recherche vectorielle avec index HNSW
- **GCP plutôt qu'AWS** : meilleur rapport coût/features pour ML (Vertex AI, BigQuery)
- **MLflow différé** : overkill pour MVP avec modèles pre-trained, utile uniquement pour fine-tuning
- **Collecte données implicite** : tracker les interactions dès le MVP pour préparer le fine-tuning futur

**Documents créés:**
- `docs/interface_gui_offers.md` - Interface GUI ↔ Offres
- `docs/interface_gui_offers_match.md` - Architecture complète avec matching, cache, cloud, ML
- `docs/interface_gui_offers_match.pdf` - Export PDF pour l'équipe

---

### 2025-12-24 (22) - UI Success Cards + Export DOCX + Ruff fixes
**Contexte:** Enrichir les cartes de succès professionnels avec toggle, visualisation et export, et corriger les erreurs Ruff pour le pre-commit hook.

**Réalisations:**

- **Cartes succès enrichies** :
  - Toggle "Profil candidat" (comme expériences, éducation) pour inclure/exclure du profil
  - Bouton "voir" (icône œil) → modal de visualisation avec détails STAR
  - Bouton "supprimer" (icône corbeille) → modal de confirmation
  - Nouveau champ `is_active` sur `ProfessionalSuccess` (migration 0014)
  - Endpoint `success_update_view` mis à jour pour gérer `is_active`

- **Modal de visualisation** :
  - Affichage complet : Titre, Situation, Tâche, Actions, Résultats, Compétences
  - Largeur 900px (50% plus large que le défaut 600px)
  - Bouton "Export DOCX" pour téléchargement Word

- **Export DOCX** :
  - Bibliothèque `docx.js` v8.5.0 chargée dynamiquement depuis CDN (unpkg)
  - Build UMD (`index.umd.js`) pour compatibilité browser
  - Génération document Word avec sections STAR formatées (titres en couleur #667eea)
  - Téléchargement automatique avec nom fichier basé sur le titre
  - Feedback visuel : "Chargement..." puis "Téléchargé !" avec gestion erreurs

- **Règle #6 généralisée** :
  - Règle "questions NON AMBIGUËS" appliquée à toutes les phases du coaching STAR
  - Exemples MAUVAIS/BON génériques (pas seulement Phase 6)

- **Corrections Ruff pre-commit** :
  - `SIM105` : `contextlib.suppress()` au lieu de `try/except/pass` (2 occurrences dans views.py)
  - `F841` : variable `initial_message` inutilisée supprimée
  - `UP028` : `yield from` au lieu de `for/yield` où applicable (providers.py)
  - `noqa: UP028` ajouté où `yield from` incompatible avec `try/except` fallback (chat_handler.py)

- **Corrections Bandit pre-commit** :
  - `B104` : `# noqa: S104` ne fonctionne pas pour Bandit → utiliser `# nosec B104`
  - `B110` : `try/except/pass` supprimé - le `.filter().first()` Django retourne `None` sans exception

**Problèmes rencontrés:**
- **Export DOCX sans action** :
  - Cause 1 : mauvais CDN (`jsdelivr` avec path incorrect)
  - Cause 2 : Build `index.min.js` au lieu de `index.umd.js` (non compatible browser)
  - Solution : utiliser `unpkg.com/docx@8.5.0/build/index.umd.js`
- **Ruff SIM105 faux positif** : `try/except/pass` flaggé mais `contextlib.suppress` est plus idiomatique
- **Ruff UP028 incompatible avec try/except** : `yield from` ne permet pas de catch les exceptions du générateur
  - Solution : ajouter `# noqa: UP028` avec explication
- **Bandit B104 non ignoré** : `# noqa: S104` (syntaxe Ruff/flake8) ne fonctionne pas pour Bandit
  - Solution : utiliser `# nosec B104` (syntaxe Bandit)
- **Bandit B110 try/except/pass** : code inutile car `.filter().first()` retourne `None` au lieu de lever une exception
  - Solution : supprimer le try/except

**Décisions techniques:**
- **CDN unpkg plutôt que jsdelivr** : URLs plus simples et prévisibles pour les libs npm
- **Build UMD** : nécessaire pour usage browser sans bundler (ESM ne fonctionne pas avec script tag)
- **Chargement dynamique** : évite d'inclure 500KB de lib si l'utilisateur n'exporte jamais
- **contextlib.suppress** : plus pythonique que `try/except/pass` pour ignorer une exception spécifique
- **noqa avec explication** : documenter pourquoi la règle est ignorée pour la maintenance future

---

### 2025-12-24 (21) - Refonte Prompt STAR + Auto-création Succès
**Contexte:** Le chatbot STAR était trop verbeux (400+ mots par message) et ne permettait pas la création automatique des succès en fin de conversation.

**Réalisations:**

- **Refonte complète `star_coaching.txt`** :
  - Messages courts : 2-4 phrases max par réponse (vs 400+ mots avant)
  - 6 phases strictes : Choix expérience → S → T → A → R → Création
  - Règle "une seule phase à la fois" : le LLM n'évoque jamais la phase suivante
  - Exemples MAUVAIS/BON dans le prompt pour guider le modèle
  - Marqueur `[STAR_COMPLETE]` avec JSON structuré à la fin

- **Détection automatique `[STAR_COMPLETE]`** dans `profile.html` :
  - Nouvelle méthode `handleStarComplete(rawText, contentDiv)` dans `StarChatbot`
  - Extraction du JSON après le marqueur via regex
  - Appel API `/accounts/api/successes/create/` avec les données STAR
  - Message de confirmation "✅ Succès ajouté à ton profil !"
  - Fermeture automatique du chat après 2 secondes

- **Chat expandable amélioré** :
  - CSS `position: fixed` avec overlay backdrop (modal-like)
  - Couvre tout l'écran y compris le titre de section
  - Centré avec `top/left: 50%` + `transform: translate(-50%, -50%)`
  - z-index 1000 pour le chat, 999 pour le backdrop

**Problèmes rencontrés:**
- **Expand ne couvrait pas le titre** : CSS `position: absolute` sur `.achievements-layout` ne remontait pas assez
  - Solution : passer à `position: fixed` avec comportement modal

**Décisions techniques:**
- **Marqueur `[STAR_COMPLETE]` plutôt que extraction séparée** : le LLM génère le JSON directement, pas besoin d'un second appel LLM
- **is_draft: false** envoyé à l'API : le succès est complet quand auto-créé (toutes les infos STAR collectées)
- **Fermeture après 2s** : donne le temps à l'utilisateur de lire la confirmation avant reset

**Patterns appliqués:**
- **Marqueur de fin dans le stream** : `[MARKER]` + JSON permet d'extraire des données structurées du stream SSE
- **Prompt engineering strict** : exemples MAUVAIS/BON explicites pour contraindre le comportement du modèle
- **Phases séquentielles** : empêcher le LLM de "sauter" des étapes en interdisant de mentionner les phases suivantes

---

### 2025-12-24 (20) - Markdown + Chat Expandable
**Contexte:** Améliorer l'affichage des réponses du chatbot (rendu markdown) et permettre d'agrandir la fenêtre de chat pour couvrir la sidebar pendant une conversation.

**Réalisations:**

- **Rendu Markdown dans le chat** :
  - Ajout de `marked.js` (v11.1.1) via CDN pour parser le markdown des réponses LLM
  - Nouvelle méthode `renderMarkdown(text)` dans StarChatbot et PitchChatbot
  - Modification de `addMessage()` : markdown pour assistant, `escapeHtml()` pour user
  - Modification de `appendToStreamingMessage()` : utilise `textContent` pendant le streaming
  - Modification de `finishStreamingMessage()` : applique `marked.parse()` à la fin du stream
  - CSS ajouté pour les éléments markdown (p, strong, em, ul, ol, li, blockquote, code, pre, h1-h3)

- **Chat extensible (expand/collapse)** :
  - CSS `.achievements-layout.chat-expanded` : position absolute pour couvrir la sidebar
  - Bouton expand dans les headers des deux chats (STAR et Pitch) avec icônes SVG
  - Méthodes `expandChat()`, `collapseChat()`, `toggleExpand()` dans les deux classes
  - Auto-expand dans `startConversation()` : le chat s'agrandit automatiquement
  - Auto-collapse dans `resetChat()` : le chat se réduit quand on clique "Nouvelle conversation"
  - Toggle manuel via bouton dans le header

**Décisions techniques:**
- **marked.js** : bibliothèque standard légère (CDN) plutôt que solution custom
- **textContent pendant streaming** : évite les problèmes d'injection HTML pendant l'accumulation des tokens, markdown appliqué une seule fois à la fin
- **CSS position absolute** : permet de superposer le chat sur la sidebar sans modifier le layout de base

**Patterns appliqués:**
- Streaming + markdown : accumuler en texte brut, parser à la fin pour éviter les états intermédiaires cassés
- UI responsive : un bouton toggle avec deux icônes (expand/collapse) selon l'état CSS

---

### 2025-12-24 (19) - SSE Streaming pour Chat IA + Fix 404 polling
**Contexte:** Implémenter le streaming SSE (Server-Sent Events) pour afficher les réponses du chatbot token par token, et corriger un bug 404 sur le polling du status.

**Réalisations:**

- **Fix 404 sur chat status polling** :
  - Bug : `/accounts/api/chat/status/{task_id}/` retournait 404
  - Cause : `chat_start_view` recevait le `task_id` de ai-assistant mais ne créait pas de `ChatMessage` avec ce task_id
  - Solution : ajout de `ChatMessage.objects.create(conversation=conversation, role="assistant", content="", status="pending", task_id=task_id)` après réception du task_id

- **Configuration LLM_MAX_TOKENS** :
  - Ajout dans `app/ai-assistant/.env` : `LLM_MAX_TOKENS=4096`
  - Valeur récupérée par `config.py` avec fallback à 4096

- **Streaming SSE complet** (architecture 3 couches) :
  1. **LLM Providers** (`providers.py`) :
     - Nouvelle méthode abstraite `chat_stream()` sur `LLMProvider`
     - Implémentation pour OpenAI : `stream=True` + iteration sur `chunk.choices[0].delta.content`
     - Implémentation pour Anthropic : `messages.stream()` context manager + `stream.text_stream`
     - Implémentation pour Ollama : même pattern qu'OpenAI (API compatible)

  2. **FastAPI Endpoints** (`main.py`) :
     - Nouvelle fonction `_sse_generator()` : formate les tokens en SSE (`data: {"token": "..."}`)
     - Endpoint `/chat/start/stream` : démarre une conversation avec réponse streaming
     - Endpoint `/chat/message/stream` : envoie un message avec réponse streaming
     - Headers SSE : `Cache-Control: no-cache`, `X-Accel-Buffering: no` (nginx)

  3. **Django Proxy** (`views.py`) :
     - `chat_start_stream_view` : crée ChatConversation + ChatMessage, proxy le stream SSE
     - `chat_message_stream_view` : crée ChatMessage user + assistant, proxy le stream
     - Accumulation du contenu pendant le stream pour sauvegarder la réponse complète
     - `StreamingHttpResponse` avec `content_type="text/event-stream"`

- **Frontend JavaScript** (`profile.html`) :
  - Propriétés ajoutées aux chatbots : `useStreaming = true`, `currentStreamingMessage`
  - `startConversationStreaming()` : utilise `fetch()` + `response.body.getReader()` pour lire le stream
  - `sendMessageStreaming()` : même pattern pour les messages suivants
  - `createStreamingMessage()` : crée une bulle vide avec classe `.streaming`
  - `appendToStreamingMessage()` : ajoute le token à la bulle courante
  - `finishStreamingMessage()` : retire la classe `.streaming` et finalise
  - Pattern `ReadableStream` avec `TextDecoder` pour parser les chunks SSE
  - Fallback automatique si `useStreaming = false`

**Problèmes rencontrés:**
- **404 sur /api/chat/status/{task_id}/** :
  - Cause : ChatMessage avec task_id manquant dans la base
  - Diagnostic : les logs montraient que le LLM répondait correctement mais la GUI ne recevait rien
  - Solution : créer le ChatMessage "pending" immédiatement après avoir reçu le task_id

**Décisions techniques:**
- **Option 1 choisie : Proxy Django** plutôt que WebSocket direct ou connexion directe client→ai-assistant
  - Avantages : architecture cohérente, auth centralisée, CORS simplifié
  - Inconvénient : latence légèrement supérieure (hop supplémentaire)
  - Impact scaling : le serveur Django doit maintenir les connexions ouvertes pendant le streaming

**Impact Scaling** :
- **Django** : chaque requête streaming bloque un worker pendant toute la durée de génération (10-60s selon le LLM)
  - Mitigation : utiliser Gunicorn avec workers async (gevent/eventlet) ou passer à ASGI (Daphne/Uvicorn)
  - Alternative : augmenter le nombre de workers proportionnellement aux users concurrents
- **ai-assistant FastAPI** : déjà async natif, scale bien avec uvicorn
- **LLM** : le bottleneck principal reste le temps de génération du LLM
- **Recommandation prod** : si >100 users concurrents, envisager une connexion WebSocket directe client→ai-assistant avec auth par token JWT

---

### 2025-12-24 (18) - Prompts proactifs + Transmission LLM Config + Logs debug
**Contexte:** Améliorer les prompts des assistants IA pour qu'ils soient proactifs (proposent au lieu de poser des questions), transmettre la config LLM utilisateur aux assistants, et ajouter des logs de debug pour les appels LLM.

**Réalisations:**

- **Prompts proactifs** (`star_coaching.txt`, `pitch_coaching.txt`) :
  - Ajout Règle 0 : "Présente-toi et explique le processus" dès le premier message
  - STAR : se présente comme coach STAR, explique les étapes (choix expérience → S→T→A→R → validation)
  - Pitch : se présente comme coach pitch, annonce la génération directe des pitchs
  - Remplacement de `{existing_successes}` par `{professional_successes}` dans le prompt STAR

- **Transmission LLM Config utilisateur** :
  - Nouveau schema `LLMConfigRequest` avec `llm_endpoint`, `llm_model`, `llm_api_key`
  - Ajout `llm_config` optionnel dans `ChatStartRequest` et `ChatMessageRequest`
  - Helper `_build_llm_config()` dans main.py pour convertir en `LLMConfig`
  - Helper `_get_user_llm_config()` dans views.py pour récupérer la config Premium+
  - Transmission de la config aux endpoints `/chat/start` et `/chat/message/async`
  - Les utilisateurs Premium+ peuvent utiliser leur propre LLM dans le chat

- **Logs debug LLM** (`providers.py`) :
  - Chaque provider (OpenAI, Anthropic, Ollama) loggue maintenant :
    - `=== LLM CALL (Provider) ===`
    - Endpoint utilisé
    - Modèle utilisé
    - System prompt (500 premiers chars)
    - Messages utilisateur (300 premiers chars chacun)
  - Permet de diagnostiquer les problèmes de connexion/configuration

- **Unification des données envoyées aux assistants** :
  - `build_system_prompt()` passe maintenant les mêmes champs aux deux types de coaching
  - `professional_successes` (détaillé) envoyé aux deux pour éviter les doublons

**Problèmes rencontrés:**
- **KeyError 'existing_successes'** : le prompt STAR référençait `{existing_successes}` mais le code ne passait que `{professional_successes}`
  - Solution : remplacer les références dans le prompt par des textes statiques ("ci-dessus", "déjà formalisés")
- **GPU non triggered** : les logs n'apparaissaient pas car aucun appel LLM ne se faisait (erreur silencieuse)
  - Solution : ajout des logs explicites dans chaque provider avant l'appel LLM

**Décisions techniques:**
- **LLM config optionnel** : si non fourni ou endpoint vide, utilise les env vars du service
- **Logs avant l'appel** : permet de voir ce qui est envoyé même si l'appel échoue
- **500/300 chars max** : évite de polluer les logs avec des prompts complets

---

### 2025-12-24 (17) - Interface Chat Pitch + Modèle Pitch Django
**Contexte:** Créer l'interface utilisateur pour le coaching pitch et le modèle Django pour stocker les pitchs générés.

**Réalisations:**

- **Modèle Pitch Django** (`accounts/models.py`) :
  - Champs : `title`, `pitch_30s`, `pitch_3min`, `key_strengths` (JSONField), `target_context`
  - Métadonnées : `source_conversation`, `is_draft`, `is_default`, `created_at`, `updated_at`
  - Méthodes : `is_complete()`, `get_word_count_30s()`, `get_word_count_3min()`, `get_completion_percentage()`
  - Un seul pitch par défaut par utilisateur (save() override)

- **Migration 0012_add_pitch_model** : création de la table Pitch

- **5 nouvelles vues API Pitch** (`views.py`) :
  - `pitch_list_view` - GET `/api/pitches/`
  - `pitch_create_view` - POST `/api/pitches/create/`
  - `pitch_detail_view` - GET `/api/pitches/<id>/`
  - `pitch_update_view` - POST `/api/pitches/<id>/update/`
  - `pitch_delete_view` - DELETE `/api/pitches/<id>/delete/`

- **Interface Chat Pitch** (`profile.html`) :
  - Section "Mon pitch" transformée : placeholder → chat IA complet
  - Classe JavaScript `PitchChatbot` (~350 lignes) basée sur `StarChatbot`
  - Envoi `coaching_type: 'pitch'` au démarrage de conversation
  - Couleur violet (#8b5cf6) pour différencier du coaching STAR (bleu)
  - Sidebar "Mes pitchs" avec compteur de mots 30s/3min
  - Lazy init avec MutationObserver quand la section devient visible

- **CSS spécifique pitch** :
  - `.chat-welcome-note` : note italique pour le contexte
  - `.pitch-list strong` : couleur violette pour les libellés
  - `.pitch-card-info` : affichage compteurs de mots
  - `.pitches-sidebar .successes-count` : badge violet

**Problèmes rencontrés:**
- **docker-compose KeyError 'ContainerConfig'** : erreur récurrente au rebuild
  - Solution : `docker-compose rm -sf <service> && docker-compose up -d <service>`
- **Migrations non détectées dans container** : fichiers locaux non visibles
  - Solution : rebuild complet du container GUI après ajout des migrations

**Décisions techniques:**
- **Réutilisation pattern StarChatbot** : même architecture JS, seul `coaching_type` change
- **Couleur différente (violet)** : distinction visuelle claire entre STAR (bleu) et Pitch (violet)
- **Word count display** : aide l'utilisateur à respecter les durées cibles (75-80 mots pour 30s, 400-450 mots pour 3min)
- **Lazy initialization** : les chatbots ne sont instanciés que quand leur section est visible (performance)

---

### 2025-12-24 (16) - Extension ai-assistant pour Pitch Coaching
**Contexte:** Étendre le module ai-assistant pour supporter également le coaching de création de pitch (30s et 3min), en réutilisant l'infrastructure existante du STAR coaching.

**Réalisations:**

- **Extension schemas.py** :
  - Ajout de `CoachingType` enum (STAR, PITCH)
  - Ajout du champ `coaching_type` dans `ChatStartRequest` et `ChatMessageRequest`
  - Nouveaux champs dans `UserContext` : `skills`, `education`
  - Nouveaux schémas `ExtractPitchRequest` et `ExtractPitchResponse`

- **Nouveau prompt pitch_coaching.txt** :
  - Structure pitch 30s : accroche, qui je suis, valeur ajoutée, objectif
  - Structure pitch 3min : accroche, parcours, réalisations STAR, compétences, vision, conclusion
  - Intègre les succès STAR du candidat comme base pour les exemples concrets
  - Placeholders : {education}, {skills}, {professional_successes} (données STAR complètes)

- **Mise à jour chat_handler.py** :
  - `load_system_prompt(coaching_type)` : charge le prompt approprié
  - `format_education()`, `format_skills()` : nouvelles fonctions de formatage
  - `format_existing_successes(detailed=True)` : inclut données STAR complètes pour pitch
  - `extract_pitch_data()` : extraction des pitchs 30s/3min depuis la conversation

- **Mise à jour main.py** :
  - Endpoints `/chat/start` et `/chat/message/async` acceptent `coaching_type`
  - Nouvel endpoint `/chat/extract-pitch`

- **Côté Django** :
  - Ajout de `COACHING_TYPE_CHOICES` dans models.py
  - Nouveau champ `coaching_type` sur `ChatConversation`
  - Migration `0011_add_coaching_type_to_conversation`
  - `_build_user_context(coaching_type)` : pour pitch, inclut education, skills, et données STAR complètes des succès
  - Vues mises à jour pour passer et utiliser le coaching_type

**Problèmes rencontrés:**
- **Aucun problème majeur** : l'architecture générique du module a permis une extension facile

**Décisions techniques:**
- **Enum CoachingType** : permet d'ajouter facilement d'autres types de coaching à l'avenir
- **Données STAR complètes pour pitch** : le LLM peut citer les résultats chiffrés des succès dans le pitch
- **Réutilisation des endpoints** : même API, juste un paramètre `coaching_type` différent
- **Priorité aux succès finalisés** : pour le pitch, on prend d'abord les succès non-draft

---

### 2025-12-24 (15) - AI Assistant STAR Coaching Chatbot
**Contexte:** Implémenter un chatbot IA pour accompagner les candidats dans la formalisation de leurs succès professionnels avec la méthode STAR (Situation, Task, Action, Result)

**Réalisations:**

- **Nouveau microservice ai-assistant (FastAPI)** :
  - Structure complète : `app/ai-assistant/src/{main.py, config.py, schemas.py, task_store.py, llm/, prompts/}`
  - Endpoints : `/health`, `/chat/start`, `/chat/message/async`, `/chat/message/status/{task_id}`, `/chat/extract-success`
  - Pattern async polling identique à cv-ingestion (task_id + status polling)
  - Support multi-LLM : OpenAI, Anthropic, Ollama via Factory Pattern
  - Dockerfile Python 3.12-slim, port 8084

- **LLM Chat Handler pour coaching STAR** :
  - `build_system_prompt()` : injecte le contexte utilisateur dans le prompt
  - `get_initial_message()` : message d'accueil personnalisé
  - `process_chat_message()` : traitement des messages avec historique
  - `extract_star_data()` : extraction structurée des composants STAR

- **Prompt STAR coaching** (`prompts/star_coaching.txt`) :
  - Consultant expert en méthode STAR
  - Guide progressif S → T → A → R
  - Encourage quantification et utilisation du "je" (pas "nous")
  - Placeholders pour contexte : {first_name}, {experiences}, {interests}, {existing_successes}

- **3 nouveaux modèles Django** :
  - `ChatConversation` : user, title, status (active/completed/abandoned), context_snapshot
  - `ChatMessage` : conversation, role (user/assistant/system), content, status, task_id, extracted_data
  - `ProfessionalSuccess` : user, title, situation, task, action, result, skills_demonstrated, is_draft
  - Migration `0010_add_chat_and_professional_success`

- **9 nouvelles vues Django** :
  - Chat : `chat_start_view`, `chat_message_view`, `chat_status_view`, `chat_history_view`
  - Succès : `success_list_view`, `success_create_view`, `success_update_view`, `success_delete_view`
  - Helper `_build_user_context()` pour récupérer les données utilisateur

- **Interface Chat UI** :
  - Layout deux colonnes : chat à gauche, liste des succès à droite
  - Classe JavaScript `StarChatbot` (~400 lignes)
  - Polling status toutes les 2s avec typing indicator
  - Messages avec bulles stylisées (user bleu, assistant gris)
  - Lazy initialization avec MutationObserver

- **Intégration Docker** :
  - Service `ai-assistant` ajouté à docker-compose.yml
  - Variable `AI_ASSISTANT_URL` dans settings.py GUI
  - Réseaux partagés jobmatch-network

**Problèmes rencontrés:**
- **docker-compose exec -T** : flag nécessaire pour commandes non-interactives (migrations)
- **Contexte compacté** : session continuée après compactage, contexte récupéré du summary

**Décisions techniques:**
- **Chat intégré** (pas modal) : meilleure UX pour conversations longues
- **Microservice dédié** : séparation des responsabilités, scalabilité indépendante
- **Persistance conversations** : historique en base pour reprendre les échanges
- **Modèle ProfessionalSuccess dédié** : pas d'utilisation d'ExtractedLine pour éviter confusion
- **Context injection** : le LLM reçoit automatiquement profil, expériences, intérêts, succès existants

---

### 2025-12-23 (14) - Fix extraction personal_info/social_link + CSS/Text tweaks
**Contexte:** Bug où les données personnelles et liens sociaux extraits du CV n'étaient pas sauvegardés correctement

**Réalisations:**
- **Fix analyzer.py pour personal_info et social_link** :
  - Bug identifié : `parse_llm_response()` n'extrayait les champs structurés que pour `experience` et `education`
  - Les types `personal_info` et `social_link` avaient leurs ExtractedLine créées mais avec tous les champs structurés à `None`
  - Ajout des elif blocks pour extraire : first_name, last_name, email, phone, location (personal_info) et link_type, url (social_link)

- **Fix CSS checkboxes type de contrat** :
  - Les checkboxes s'affichaient verticalement au lieu d'horizontalement
  - Le CSS sur `.contract-checkboxes ul` ne fonctionnait pas car Django `CheckboxSelectMultiple` génère un `<ul>` avec styles inline
  - Solution : rendu manuel des checkboxes avec `{% for choice in form.contract_types %}` au lieu de `{{ form.contract_types }}`
  - Nouveau CSS ciblant `.contract-checkbox-label` directement

- **Mise à jour textes sections profil** :
  - "Mon pitch" subtitle : "Preparez votre presentation..." → "Boostez votre presentation avec notre IA"
  - "Succes professionnels" subtitle : "Listez vos accomplissements..." → "Laissez-vous guider par notre consultant IA pour formaliser vos succes"

**Problèmes rencontrés:**
- **ExtractedLine structured fields all None** :
  - Diagnostic via Django shell : `ExtractedLine.objects.filter(content_type="personal_info")` retournait des objets avec first_name=None
  - Cause : le code dans parse_llm_response() avait des elif pour experience/education mais pas pour les autres types structurés
  - Solution : ajout des branches elif pour personal_info et social_link

**Décisions techniques:**
- **Extraction conditionnelle par content_type** : chaque type avec des champs structurés a sa propre branche de parsing
- **Validation None-safe** : `item.get("field", "").strip() if item.get("field") else None` pour éviter les strings vides

---

### 2025-12-23 (13) - Photo Upload avec Cropper.js + django-extensions local
**Contexte:** Ajouter l'upload de photo de profil avec recadrage style LinkedIn et outils de visualisation des modèles Django

**Réalisations:**
- **django-extensions pour visualisation modèles** (local uniquement) :
  - `requirements-dev.txt` créé pour dépendances locales seulement
  - `django_extensions` ajouté conditionnellement dans settings.py (`if ENV_MODE == "local"`)
  - Import try/except pour éviter crash si non installé
  - `graph_models accounts -o models.png` pour générer diagramme des relations

- **Photo de profil avec Cropper.js** :
  - Field `photo` (ImageField) ajouté au modèle User
  - Migration 0007_add_photo_to_user créée et appliquée
  - Pillow ajouté à requirements.txt pour traitement images
  - `photo_upload_view` et `photo_delete_view` créées
  - Routes `/photo/upload/` et `/photo/delete/` configurées
  - Media files servis en développement (config/urls.py avec `static(MEDIA_URL)`)

- **Interface recadrage style LinkedIn** :
  - Cropper.js intégré via CDN (CSS + JS)
  - Modal en deux étapes : 1) Sélection photo, 2) Recadrage
  - Vue circulaire pour le crop (style LinkedIn)
  - Zoom avec molette, drag pour repositionner
  - Sortie 400x400px JPEG qualité 90%
  - Boutons Annuler/Appliquer pour le crop

- **Configuration Docker** :
  - django_extensions conditionnel : chargé uniquement si `ENV_MODE == "local"` ET module disponible
  - Évite `ModuleNotFoundError` en Docker où le module n'est pas installé

**Problèmes rencontrés:**
- **graphviz not found** : pydotplus nécessite le package système graphviz
  - Solution : `sudo apt install graphviz` (manuel car besoin de sudo)
- **ModuleNotFoundError: django_extensions** en Docker
  - Cause : django_extensions installé en local mais pas dans requirements.txt Docker
  - Solution : ajout conditionnel avec try/except + vérification ENV_MODE == "local"
- **offre-ingestion sans Dockerfile** : `docker-compose build` échoue
  - Solution : builder explicitement `docker-compose build gui cv-ingestion`

**Décisions techniques:**
- **Cropper.js** : bibliothèque la plus populaire et mature pour le recadrage d'images
- **Two-step modal** : sépare la sélection du recadrage pour une UX plus claire
- **Crop circulaire** : correspond au style moderne des profils (LinkedIn, etc.)
- **Canvas toBlob** : conversion côté client avant upload pour réduire la bande passante
- **requirements-dev.txt** : sépare les dépendances dev (graph_models) des dépendances prod
- **ENV_MODE check** : double protection (env var + try/except) pour éviter crashes

---

### 2025-12-23 (12) - LLM Config Fallback + Sélecteur d'abonnement + Modal Pricing
**Contexte:** Améliorer la gestion de la config LLM et ajouter un sélecteur d'abonnement avec comparaison des plans

**Réalisations:**
- **LLM Config Fallback environnement** :
  - Si l'utilisateur n'a pas configuré son LLM, le système utilise les variables d'environnement
  - Classe `LLMConfig` dans `analyzer.py` pour passer une config optionnelle
  - `get_llm_provider(config: LLMConfig | None)` : utilise config custom si fournie, sinon env vars
  - `analyze_cv_text()` et `analyze_cv_images()` acceptent un paramètre `llm_config` optionnel
  - Endpoint `/extract/async` accepte des Form fields : `llm_endpoint`, `llm_model`, `llm_api_key`

- **Transmission config LLM GUI → cv-ingestion** :
  - `cv_upload_view` envoie la config LLM de l'utilisateur si activée ET si abonnement Premium+
  - Vérification `user.subscription_tier not in ("free", "basic")` avant envoi
  - Données transmises via multipart form data

- **Sélecteur d'abonnement** dans Account Settings :
  - 5 plans : Free (0€), Basic (9€), Premium (29€), Head Hunter (49€), Enterprise (99€)
  - Radio buttons stylisés avec prix et descriptions
  - Handler `form_type == "subscription"` pour mise à jour du tier

- **Modal Pricing "Voir les offres"** :
  - Bouton gradient "Voir les offres" sur la carte abonnement
  - Modal plein écran avec comparaison des 5 plans
  - Tableau des fonctionnalités : CVs, Offres, Analyses LLM, Support, etc.
  - Checkmarks verts / croix rouges pour chaque fonctionnalité
  - Prix affichés pour chaque plan

- **Restriction LLM Config par abonnement** :
  - Section LLM Config visible uniquement pour Premium, Head Hunter, Enterprise
  - Message explicatif pour Free/Basic : "disponible à partir du plan Premium"
  - Section grisée (opacity: 0.6) pour plans non éligibles

**Problèmes rencontrés:**
- **File not read error** : tentative d'édition sans lecture préalable
  - Solution : toujours lire le fichier avant de l'éditer

**Décisions techniques:**
- **Form fields plutôt que JSON body** : compatible avec multipart/form-data pour upload fichier
- **Config optionnelle avec fallback** : pattern robuste, pas de breaking change
- **Restriction par tier** : vérification côté serveur ET côté template
- **Modal CSS natif** : pas de dépendance JS externe, animation simple

---

### 2025-12-23 (11) - Page Gestion Compte + LLM Config + Export RGPD
**Contexte:** Remplacer "Supprimer mon compte" par une page complète de gestion du compte utilisateur

**Réalisations:**
- **Page Account Settings** (`/accounts/settings/`) :
  - Sections : Identité, Email, Mot de passe, Abonnement, Config LLM, Export données, Suppression compte
  - Multi-formulaires sur une page (pattern `form_type` hidden field)
  - Messages de succès/erreur par section
  - Danger zone en rouge pour suppression compte

- **Modèles ajoutés** :
  - `SUBSCRIPTION_TIER_CHOICES` : Free, Basic, Premium, Head Hunter, Enterprise
  - `subscription_tier` field sur User (default="free")
  - `UserLLMConfig` model (OneToOne avec User) :
    - `is_enabled`, `llm_endpoint`, `llm_model`, `llm_api_key`
    - Permet aux utilisateurs d'utiliser leur propre LLM

- **Formulaires créés** :
  - `AccountIdentityForm` : prénom, nom
  - `AccountEmailForm` : changement email avec vérification unicité
  - `AccountPasswordForm` : mot de passe actuel + nouveau + confirmation
  - `UserLLMConfigForm` : activation + endpoint + modèle + API key

- **Export RGPD** (`/accounts/export/`) :
  - Endpoint `export_data_view`
  - Export JSON complet : profil, CVs, lignes extraites, lettres motivation, config LLM
  - Clé API exclue de l'export pour sécurité
  - Téléchargement fichier `jobmatch_data_{user_id}.json`

- **UI/UX** :
  - Sidebar profil : "Supprimer mon compte" → "Gérer mon compte" avec icône engrenage
  - Template `settings.html` avec design cohérent (cards, gradients)
  - Formulaires stylisés Bootstrap 5

- **Migration 0004** : `add_subscription_and_llm_config`

**Problèmes rencontrés:**
- **File not read error** : outil Edit échoue si fichier non lu préalablement
  - Solution : toujours lire le fichier avant de l'éditer
- **docker-compose KeyError 'ContainerConfig'** (récurrent)
  - Solution : `docker-compose down` complet avant `up`

**Décisions techniques:**
- **Multi-form pattern** : un seul template, plusieurs formulaires indépendants via `form_type`
- **Re-login après password change** : `login(request, user)` après `form.save()` pour éviter déconnexion
- **get_or_create pour LLM config** : crée automatiquement la config si inexistante
- **OneToOneField avec related_name** : `user.llm_config` pour accès direct
- **API key non exportée** : sécurité RGPD (données sensibles exclues)

---

### 2025-12-23 (10) - Vision LLM + Prompts externalisés + Toggle/Edit UI
**Contexte:** Améliorer cv-ingestion pour supporter les PDF image (scannés) via Vision LLM, externaliser les prompts, et ajouter des contrôles UI sur les lignes extraites

**Réalisations:**
- **Support Vision LLM** dans cv-ingestion :
  - Méthode `supports_vision()` sur `LLMProvider` base class
  - Méthode `analyze_images()` pour traiter les images avec Vision LLM
  - Support OpenAI (GPT-4V, GPT-4o), Anthropic (Claude 3/4), Ollama (LLaVA)
  - Nouvelle fonction `analyze_cv_images()` exportée

- **Extraction PDF intelligente** :
  - `is_text_based_pdf()` : détection auto texte vs image (heuristique: min 100 chars total, 50 chars/page)
  - `extract_pdf_content()` : retourne `PDFContent(is_text_based, text, images)`
  - `convert_pdf_to_images()` : PDF → PNG via pdf2image/poppler
  - `ocr_images()` : fallback OCR via Tesseract si Vision LLM non disponible
  - Logique dans main.py : texte → LLM texte, image → Vision LLM ou OCR fallback

- **Prompts externalisés** :
  - Dossier `src/prompts/` avec fichiers .txt séparés
  - `cv_extraction_text.txt` : prompt pour extraction texte
  - `cv_extraction_vision.txt` : prompt pour extraction images
  - `__init__.py` avec `load_prompt()`, `get_cv_text_prompt()`, `get_cv_vision_prompt()`
  - Prompts traduits en français
  - Règle expériences : 1 mission = 1 entrée (découpage si trop long)

- **UI Toggle/Edit sur ExtractedLines** :
  - Toggle switch actif/inactif (vert/rouge) sur chaque ligne extraite
  - Bouton édition (pictogramme crayon)
  - Endpoint `line/toggle/<int:line_id>/` avec `extracted_line_toggle_view`
  - JavaScript pour appels API et mise à jour visuelle
  - `resumeProcessingCVs()` pour reprendre le polling des CVs "En cours" au chargement

- **Dépendances ajoutées** :
  - requirements.txt : `pdf2image`, `pytesseract`, `Pillow`
  - Dockerfile : `poppler-utils`, `tesseract-ocr`, `tesseract-ocr-fra`, `tesseract-ocr-eng`

**Problèmes rencontrés:**
- **CV stuck "En cours..."** après page reload
  - Cause : polling interrompu par le reload avant réception du status "completed"
  - Solution : `resumeProcessingCVs()` qui reprend le polling pour les CVs avec `data-status="processing"`
- **docker-compose KeyError 'ContainerConfig'**
  - Cause : bug docker-compose avec rebuild
  - Solution : `docker-compose stop && rm -f && up` au lieu de `up -d` direct

**Décisions techniques:**
- **Vision LLM natif plutôt qu'OCR seul** : meilleure qualité d'extraction, compréhension du layout
- **OCR en fallback** : Tesseract si le provider LLM ne supporte pas la vision
- **Prompts en fichiers .txt** : facilite l'itération et le versioning des prompts
- **Découpage expériences** : 1 mission = 1 entrée pour granularité fine dans le matching
- **Prompt en français** : le LLM comprend mieux le contexte des CVs français

---

### 2025-12-22 (9) - Intégration GUI ↔ cv-ingestion + Polling asynchrone + Suppression CV
**Contexte:** Connecter la GUI Django au microservice cv-ingestion en mode Docker, implémenter le polling asynchrone pour les traitements longs, et ajouter la suppression des CVs

**Réalisations:**
- **Configuration Docker multi-service** :
  - docker-compose.yml : context root pour accès au package shared
  - app/cv-ingestion/Dockerfile : copie shared/ et install pip
  - app/gui/Dockerfile : adapté pour context root
  - env_file dans docker-compose pour charger app/cv-ingestion/.env
  - Ports exposés via variables : GUI_PORT=8085, DB_PORT=5433

- **Configuration environnement** :
  - `.env` root avec config commune (DATABASE_URL, ports, URLs inter-services)
  - `.envrc` pour direnv (charge tous les .env du projet)
  - `app/cv-ingestion/.env` : LLM_TYPE=ollama, LLM_ENDPOINT=http://ollama.molp.fr/v1

- **Polling asynchrone cv-ingestion** (pattern async/polling) :
  - `task_store.py` : store en mémoire thread-safe (TaskStatus enum, Task dataclass)
  - `POST /extract/async` : retourne immédiatement un task_id
  - `GET /extract/status/{task_id}` : retourne pending/processing/completed/failed
  - BackgroundTasks FastAPI pour traitement asynchrone
  - Ancien endpoint synchrone `/extract` conservé pour rétrocompatibilité

- **Intégration GUI polling** :
  - `cv_upload_view` : appelle `/extract/async`, retourne task_id au frontend
  - `cv_status_view` : nouvelle vue pour polling depuis le frontend
  - Modèle CV : ajout champ `task_id` (migration 0003)
  - JavaScript : polling toutes les 2s avec messages de progression dynamiques
  - Timeout max 4 minutes (MAX_POLL_ATTEMPTS=120)

- **Suppression CV** :
  - `cv_delete_view` : endpoint DELETE/POST pour supprimer un CV
  - Supprime le fichier du storage + cascade sur ExtractedLines
  - Modal de confirmation avec nom du CV
  - Bouton corbeille sur chaque document dans la liste

- **Navigation par hash URL** :
  - `showSection()` met à jour `window.location.hash` avec `history.replaceState()`
  - Au chargement de la page, lecture du hash pour restaurer la section active
  - Après upload/suppression CV : `window.location.hash = 'documents'` avant reload
  - Permet de rester sur la bonne section après n'importe quelle action

**Problèmes rencontrés:**
- **`shared` package not found** en Docker build
  - Cause : context `./app/cv-ingestion` n'inclut pas `../../shared`
  - Solution : context `.` (root) + `COPY shared/` dans Dockerfile
- **Port 5432 already allocated**
  - Cause : PostgreSQL local déjà sur le port
  - Solution : DB_PORT=5433 dans .env
- **Port 8080 already allocated**
  - Cause : autre service sur le port
  - Solution : GUI_PORT=8085 dans .env
- **`LLM_API_KEY is required for OpenAI`** en Docker
  - Cause : Docker ne chargeait pas le .env du service
  - Solution : ajouter `env_file: app/cv-ingestion/.env` dans docker-compose.yml
- **404 Not Found `/chat/completions`** sur Ollama
  - Cause : LLM_ENDPOINT sans `/v1` suffix
  - Solution : `http://ollama.molp.fr/v1` (pas `http://ollama.molp.fr`)
- **Container ne pick up pas les changements .env**
  - Solution : `docker-compose down && docker-compose up -d` (pas juste restart)
- **docker-compose `KeyError: 'ContainerConfig'`**
  - Cause : bug docker-compose avec rebuild
  - Solution : `docker-compose down` puis `up` au lieu de juste `up -d`

**Décisions techniques:**
- **Polling plutôt que WebSockets** : plus simple, suffisant pour le POC
- **Store en mémoire** plutôt que Redis : simplicité, pas de dépendance externe
- **BackgroundTasks FastAPI** plutôt que Celery : léger, pas de broker à gérer
- **task_id UUID** : unique, non prédictible, pas besoin de séquence DB
- **Cascade delete** : supprimer un CV supprime automatiquement ses ExtractedLines

---

### 2025-12-22 (8) - Tests intégration cv-ingestion + Package shared installable
**Contexte:** Tester cv-ingestion avec serveur Ollama distant et rendre le package shared installable

**Réalisations:**
- **Script de test d'intégration** (`scripts/test_integration.py`) :
  - Test extraction PDF (pdfplumber)
  - Test analyse LLM avec Ollama distant (`llm.molp.fr`)
  - Testé avec plusieurs modèles : llama3.1:8b, gpt-oss:20b, gemma3:4b
  - Sortie vers `data_test/output.txt` avec résultats complets
  - Extraction réussie : 22-45 lignes selon le modèle

- **Package shared installable** (`shared/`) :
  - Structure `shared/src/shared/` pour package pip standard
  - `pyproject.toml` avec setuptools
  - Installation via `pip install -e ../../shared` dans requirements.txt
  - Plus besoin de PYTHONPATH pour les imports
  - Microservices vraiment indépendants

- **Fix CI check-branch** :
  - Job ne se déclenchait pas correctement (github.head_ref vide sur push)
  - Ajout condition `if: github.event_name == 'pull_request' && github.base_ref == 'main'`
  - Maintenant le check ne tourne que pour les PRs vers main

- **Interfaces partagées créées** :
  - `shared.constants.ContentType` : enum pour CV et offres
  - `shared.interfaces.ExtractedLine` : ligne extraite avec type et ordre
  - `shared.interfaces.CVData` : données CV avec helpers (skills_hard, experiences, etc.)
  - `shared.interfaces.ServiceHealth` : health check standard

**Problèmes rencontrés:**
- **ModuleNotFoundError: No module named 'shared'** lors du lancement serveur
  - Cause : PYTHONPATH non configuré
  - Solution : transformer shared en package pip installable
- **Structure package incorrecte** : hatchling vs setuptools
  - Solution : utiliser setuptools avec structure `src/shared/`
- **CI check-branch exécuté sur push** : `github.head_ref` vide sur event push
  - Solution : ajouter condition `if: github.event_name == 'pull_request' && github.base_ref == 'main'`

**Commandes utiles:**
- Supprimer branche locale : `git branch -d feature/matthieu-cv-ingestion`
- Supprimer branche distante : `git push origin --delete feature/matthieu-cv-ingestion`

**Workflow Ruff + Git (commandes essentielles):**
```bash
# 1. Checker les erreurs (sans modifier)
ruff check .

# 2. Auto-fix ce qui peut l'être + formatter
ruff check --fix . && ruff format .

# 3. Stage + commit + push (one-liner)
ruff check --fix . && ruff format . && git add -A && git commit -m "message" && git push

# Si le commit échoue à cause du pre-commit hook (trailing whitespace, etc.) :
# → Les fichiers modifiés par le hook sont "unstaged"
# → Solution : re-stage et re-commit
git add -A && git commit -m "message"
```

**Décisions techniques:**
- **Package pip installable** plutôt que PYTHONPATH : vraie indépendance des microservices
- **Mode éditable** (`-e`) : modifications shared reflétées sans réinstallation
- **Helpers dans CVData** : `skills_hard`, `experiences`, `get_by_type()` pour faciliter l'usage

---

### 2025-12-22 (7) - Microservice cv-ingestion + Migration Ruff
**Contexte:** Implémenter le microservice cv-ingestion et migrer les outils de linting vers Ruff

**Réalisations:**
- **Microservice cv-ingestion complet** :
  - FastAPI sur port 8081 (standalone, pas Django)
  - Extraction PDF (pdfplumber + PyMuPDF)
  - Extraction DOCX (python-docx)
  - LLM provider-agnostic avec Factory Pattern :
    - `OpenAIProvider` (OpenAI + OpenAI-compatible APIs)
    - `AnthropicProvider` (Claude)
    - `OllamaProvider` (local, utilise API compatible OpenAI)
  - Configuration via env vars : LLM_TYPE, LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL
  - Endpoint POST /extract avec validation fichier
  - Dockerfile et .env.example

- **Migration pre-commit vers Ruff** :
  - Remplacement de black, isort, flake8, mypy par Ruff
  - Configuration dans pyproject.toml (line-length=120, Python 3.12)
  - Règles activées : E, W, F, I, B, C4, UP, SIM
  - CI mis à jour avec job lint Ruff dédié
  - Documentation pre_commit_101.md mise à jour

**Problèmes rencontrés:**
- **Bandit B104** : "Possible binding to all interfaces" sur `0.0.0.0`
  - Solution : `# nosec B104 - Docker container` (faux positif pour conteneur)
- **Ruff B904** : "raise ... from err" dans except clause
  - Solution : `raise HTTPException(...) from e`
- **mypy bloquait le CI** pour membres sans assistant de code
  - Solution : migration complète vers Ruff (plus simple, plus rapide)

**Décisions techniques:**
- **cv-ingestion isolé** : microservice indépendant, ne partage pas la DB Django
- **Factory Pattern LLM** : permet de changer de provider sans modifier le code métier
- **Ruff plutôt que black+isort+flake8+mypy** : 1 outil au lieu de 4, 10-100x plus rapide
- **bandit conservé** : Ruff ne fait pas l'analyse sécurité
- **gitleaks conservé** : détection des secrets

---

### 2025-12-22 (6) - Convention de langue (code EN / UI FR)
**Contexte:** Standardiser les conventions de langue dans le projet

**Réalisations:**
- Création de CLAUDE.md avec les règles de langue :
  - Commentaires code : anglais
  - Messages commit : anglais (après préfixe [CortexForge])
  - Noms variables/fonctions/classes : anglais
  - Contenu UI visible : français
- Refactoring de tous les fichiers existants :
  - views.py : 1 commentaire FR → EN
  - profile.html : tous les commentaires CSS/HTML/JS → EN
  - home.html : tous les commentaires CSS/HTML → EN
- Vérification models.py et admin.py (déjà conformes)

**Problèmes rencontrés:**
- Tentative d'ajout dans .claude/settings.json échouée (validation error: "Property code_style is not allowed")
- Solution : utiliser CLAUDE.md qui est le bon endroit pour les instructions Claude

**Décisions techniques:**
- **CLAUDE.md** : fichier central pour les instructions de style/conventions
- **Séparation claire** : code interne EN, interface utilisateur FR
- **verbose_name Django** : reste en FR car c'est affiché dans l'admin (UI)

---

### 2025-12-22 (5) - ORM CV/ExtractedLine + Spécification cv-ingestion
**Contexte:** Implémenter l'ORM pour CV et ExtractedLine, connecter la vue profil aux données, écrire les specs du service cv-ingestion

**Réalisations:**
- Modèles Django : CV, CoverLetter, ExtractedLine dans accounts/models.py
- ExtractedLine avec content_type (experience, education, skill_hard, skill_soft, certification, language, interest, summary, other)
- CV avec extraction_status (pending, processing, completed, failed)
- Migration 0002_add_cv_coverletter_extractedline appliquée
- Vue profile_view connectée aux ExtractedLine (querysets par content_type)
- Template profile.html avec affichage conditionnel des données
- Spécification complète cv-ingestion dans docs/cv_ingestion_spec.md :
  - Architecture et flux de traitement
  - Extraction texte (PDF/DOCX)
  - Analyse LLM avec prompt et schema JSON
  - API endpoints
  - Configuration, erreurs, sécurité, tests, roadmap

**Problèmes rencontrés:**
- "no such table: accounts_extractedline" → migration 0002 non appliquée, résolu avec `python manage.py migrate`
- Données vides dans "Parcours professionnel" → normal, sera peuplé par cv-ingestion

**Décisions techniques:**
- **ExtractedLine granulaire** : 1 ligne = 1 unité (1 poste, 1 compétence, 1 diplôme)
- **Tabs "Parcours professionnel"** : mappent directement aux content_types ExtractedLine
- **LLM extraction** : prompt structuré avec JSON schema pour sortie standardisée
- **cv-ingestion en microservice** : déclenchement async via queue (Celery future)

---

### 2025-12-22 (4) - Refonte UI Landing Page et Profil
**Contexte:** Améliorer l'interface utilisateur de la landing page et de la page profil

**Réalisations:**
- Landing page dynamique avec animations CSS (fadeInUp, float, pulse, slideIn)
- Hero section plein écran (100vh) sans scroll
- Navbar conditionnelle : masquée si déconnecté, visible si connecté
- Cartes de "match preview" animées dans le hero
- Stats animées avec gradient (10K+ offres, 95% précision, 30s pour matcher)
- Page profil avec sidebar menu (photo, données perso, CVs, LM, pitch, succès, hobbies)
- Site non-scrollable (overflow: hidden sur body)
- Ajustement itératif des tailles pour tenir dans le viewport

**Problèmes rencontrés:**
- Migration Django manquante → `makemigrations accounts` pour créer 0001_initial.py
- Lignes trop longues dans migration (flake8 E501) → split help_text avec parenthèses
- Django 5+ logout nécessite POST → form avec csrf_token au lieu de lien

**Décisions techniques:**
- **CSS-only animations** : pas de JS pour les animations, tout en CSS
- **Template blocks conditionnels** : `{% block navbar %}` avec `{{ block.super }}` pour héritage sélectif
- **`{% block main_attrs %}`** : permet de customiser les attributs de `<main>` par template
- **clamp() pour responsive** : `font-size: clamp(2.8rem, 5.5vw, 4rem)` adapte la taille au viewport

---

### 2025-12-22 (3) - Configuration multi-environnement
**Contexte:** Permettre au service GUI de tourner en local, Docker dev et Cloud Run prod

**Réalisations:**
- Settings Django avec `ENV_MODE` (local/dev/prod)
- Mode local : `run_local.sh` avec SQLite
- Mode Docker dev : `docker-compose.dev.yml` avec PostgreSQL + hot-reload
- Mode Docker prod : `Dockerfile.prod` multi-stage optimisé
- CI/CD GCloud : `cloudbuild.yaml` pour Cloud Run
- Support Cloud SQL via Unix socket
- Support Cloud Storage pour les uploads (media)
- WhiteNoise pour les fichiers statiques
- README.md avec documentation des 3 modes

**Décisions techniques:**
- **Cloud Run** (serverless) plutôt que GKE (Kubernetes) pour simplifier
- **Cloud SQL PostgreSQL** pour la prod
- **Cloud Storage** pour les uploads CV
- **Multi-stage build** pour image prod légère
- **WhiteNoise** pour servir les static files sans nginx

---

### 2025-12-22 (2) - Service GUI Django
**Contexte:** Implémentation du service GUI avec Django

**Réalisations:**
- Choix framework : Django (malgré architecture microservices, pour batteries incluses)
- Création projet Django dans `app/gui/`
- App `accounts` avec custom User model :
  - Inscription, connexion, déconnexion
  - Profil utilisateur (préférences emploi : salaire, disponibilité, remote)
  - Suppression compte (RGPD)
- Templates Bootstrap 5 (base.html, home, login, register, profile)
- Configuration PostgreSQL via variables d'environnement
- Dockerfile pour le service GUI
- User Stories POC couvertes : US001, US002, US005, US006, US007, US008

**Décisions techniques:**
- **Django vs FastAPI** : Django choisi pour auth intégrée et admin
- **Custom User Model** : email comme USERNAME_FIELD
- **Bootstrap 5 via CDN** : rapidité de développement pour POC

---

### 2025-12-22 (1) - Initialisation projet + Architecture microservices
**Contexte:** Démarrage du projet JobMatch - plateforme de matching CV/offres d'emploi

**Réalisations:**
- Lecture et analyse des documents de contexte (One liner.pdf, Job match.xlsx)
- Compréhension de la vision produit (V1 MVP → V2 avec personnalisation CV)
- Identification de l'équipe (Matthieu, Clément, Mohamed, Maxime)
- Création du fichier POSTMORTEM.md et PITCH.md
- Mise en place architecture microservices :
  - `app/gui` - Interface utilisateur
  - `app/cv-ingestion` - Import et parsing CV
  - `app/offre-ingestion` - Récupération offres (France Travail)
  - `app/matching` - Algorithme de matching
  - `shared/` - Code partagé (interfaces, constants, utils)
- Configuration CI/CD :
  - `.pre-commit-config.yaml` (black, isort, flake8, mypy, bandit, gitleaks)
  - `.github/workflows/ci.yml` (tests par service)
  - `.github/workflows/cd.yml` (build Docker + deploy)
- `docker-compose.yml` avec postgres + redis
- Gestion Git : branche `dev` créée, `DEV_POC` mergée et supprimée

**Problèmes rencontrés:**
- Fichier Excel non lisible directement → résolu avec pandas + openpyxl
- Pre-commit `types-all` incompatible Python 3.12 → retiré de mypy config
- Hook `no-commit-to-branch` bloquait merge sur dev → retiré dev des branches protégées

**Décisions techniques:**
- **Mode vibecoding + équipe classique** : configuration dans `.claude/settings.json`
- **Préfixe commits** : `[CortexForge]` (pas de footer "Generated by Claude Code")
- **Périmètre Matthieu** : gui, cv-ingestion, frontend, shared/utils
- **Zones interdites** : offre-ingestion, matching (équipe classique)
- **Branches protégées** : main uniquement (dev autorisé pour permettre les merges)

## 🧠 Apprentissages clés
- Le projet a deux versions : V1 (matching simple) et V2 (matching + personnalisation CV)
- POC structuré en 4 domaines : Gestion Compte (DE:0), Import CV (DE:1), Ingestion Offres (DE:2), Smart Match (DE:2)
- Priorités MoSCoW définies dans les User Stories
- Mode vibecoding en équipe nécessite un périmètre clair et des règles strictes
- Django 5+ : logout doit être en POST (plus de GET)
- Template blocks Django : `{{ block.super }}` pour hériter conditionnellement
- **CLAUDE.md** est le bon endroit pour les conventions de style (pas settings.json)
- Séparation langue : code EN pour maintenabilité internationale, UI FR pour les utilisateurs
- **Ruff** remplace 4 outils Python (black, isort, flake8, mypy) et est 10-100x plus rapide
- **Factory Pattern** pour LLM providers : permet de switcher OpenAI/Anthropic/Ollama sans changer le code
- **Microservices isolés** : ne partagent pas de DB, communiquent uniquement par API
- **Package pip installable** pour shared : `pip install -e ../../shared` dans requirements.txt
- **Structure package Python** : `shared/src/shared/` avec setuptools pour imports propres
- **Polling async** : pattern simple et robuste pour les traitements longs (préférer à WebSockets pour POC)
- **BackgroundTasks FastAPI** : alternative légère à Celery pour traitement async sans broker
- **docker-compose context root** : nécessaire quand un service a besoin de fichiers hors de son dossier
- **env_file vs environment** : env_file charge un fichier .env, environment définit des vars inline
- **Ollama API** : endpoint doit se terminer par `/v1` pour être compatible OpenAI
- **Vision LLM** : GPT-4o, Claude 3+, LLaVA supportent l'analyse d'images nativement
- **Prompts externalisés** : fichiers .txt séparés facilitent l'itération sans toucher au code
- **Découpage expériences CV** : 1 mission = 1 entrée pour un matching plus précis
- **pdf2image + poppler** : conversion PDF → images pour Vision LLM ou OCR
- **Multi-form pattern Django** : `form_type` hidden field pour gérer plusieurs forms sur une page
- **Re-login après password change** : appeler `login(request, user)` pour éviter la déconnexion
- **get_or_create pour OneToOne** : crée automatiquement la relation si inexistante
- **Export RGPD** : exclure les données sensibles (API keys) même si l'utilisateur les demande
- **Form fields vs JSON** : pour multipart/form-data avec fichier, utiliser Form() pas Body()
- **Restriction fonctionnalités par tier** : double vérification côté serveur ET côté template
- **Modal pricing** : CSS natif avec backdrop-filter pour blur, pas besoin de lib JS
- **Cropper.js** : bibliothèque la plus mature pour recadrage d'images (utilisée par LinkedIn)
- **Port interne vs externe Docker** : `5433:5432` signifie port 5433 exposé sur l'hôte, port 5432 interne au réseau Docker
- **TemplateView vs custom View** : pour passer du contexte dynamique (queries DB), il faut une vue personnalisée
- **get_or_create** : pattern idempotent pour éviter les erreurs IntegrityError sur les contraintes uniques
- **docker cp** : permet de copier des fichiers du container vers l'hôte (utile pour récupérer des migrations générées)
- **Two-step modal** : sépare la sélection de l'édition pour une meilleure UX
- **Canvas toBlob** : conversion côté client avant upload pour optimiser la bande passante
- **requirements-dev.txt** : permet d'avoir des dépendances uniquement pour le dev local
- **Conditional INSTALLED_APPS** : `if ENV_MODE == "local"` + try/except pour apps optionnelles
- **parse_llm_response() extensible** : chaque content_type avec des champs structurés nécessite sa propre branche elif
- **Rendu manuel checkboxes Django** : pour un contrôle CSS total, utiliser `{% for choice in form.field %}{{ choice.tag }}{% endfor %}` au lieu de `{{ form.field }}`
- **Microservices FastAPI identiques** : dupliquer le pattern de cv-ingestion pour nouveaux services (task_store, providers, schemas)
- **MutationObserver** : permet d'initialiser des composants JS quand une section devient visible (lazy init)
- **Prompt engineering STAR** : instructions claires pour guider progressivement S→T→A→R
- **Context snapshot** : sauvegarder le contexte utilisateur au début de la conversation pour cohérence
- **Architecture générique pour coaching** : utiliser un `coaching_type` enum permet d'étendre facilement le module à d'autres types de coaching
- **Données conditionnelles selon le type** : `_build_user_context(coaching_type)` enrichit les données en fonction du besoin (pitch = données STAR complètes)
- **Prompts séparés par type** : un fichier .txt par type de coaching pour faciliter l'itération
- **SSE Streaming** : Server-Sent Events avec format `data: {...}\n\n` pour affichage temps réel
- **ReadableStream API** : `response.body.getReader()` + `TextDecoder` pour parser les chunks SSE en JavaScript
- **Django StreamingHttpResponse** : permet de proxyer un stream SSE depuis un service externe
- **Proxy streaming Django** : accumule le contenu pour sauvegarder la réponse complète en base après le stream
- **LLM streaming** : OpenAI `stream=True`, Anthropic `messages.stream()` context manager
- **Headers SSE** : `Cache-Control: no-cache`, `X-Accel-Buffering: no` pour éviter le buffering nginx
- **marked.js pour markdown** : bibliothèque standard légère pour parser le markdown des réponses LLM
- **Streaming + markdown** : accumuler en `textContent` pendant le stream, appliquer `marked.parse()` une seule fois à la fin
- **Chat expandable** : CSS `position: absolute` avec classe toggle pour superposer un élément sur son voisin
- **Marqueur de fin stream** : `[MARKER]` + JSON dans le prompt permet d'extraire des données structurées du stream SSE sans second appel LLM
- **Prompt engineering strict** : exemples MAUVAIS/BON explicites pour contraindre le comportement verbeux des LLM
- **Phases séquentielles en prompt** : "n'évoque JAMAIS la phase suivante" empêche le LLM de sauter des étapes
- **docx.js browser** : utiliser le build UMD (`index.umd.js`) et non ESM ou min pour compatibilité script tag
- **contextlib.suppress** : remplace `try/except/pass` de façon plus idiomatique (règle Ruff SIM105)
- **yield from vs try/except** : `yield from` ne peut pas être utilisé dans un try/except car les exceptions du générateur ne seraient pas catchées
- **noqa avec explication** : toujours documenter pourquoi une règle est ignorée (ex: `# noqa: UP028 - yield from incompatible with try/except`)
- **Bandit vs Ruff syntaxe** : Bandit utilise `# nosec BXXX`, Ruff utilise `# noqa: SXXX` - ce sont des outils différents avec syntaxes différentes
- **Django QuerySet.first()** : retourne `None` si pas de résultat, ne lève jamais d'exception - pas besoin de try/except
- **drf-spectacular** : documentation OpenAPI 3 automatique pour Django REST Framework, plus moderne que drf-yasg
- **Auto-création modèles liés** : créer les modèles dépendants (Application) directement dans la vue API d'import pour simplifier le workflow
- **JSONField pour history** : simple et efficace pour un event log sans nécessiter une table séparée
- **pgvector** : extension PostgreSQL pour recherche vectorielle, index HNSW pour performances (remplace Faiss/Milvus)
- **Modèle Django `managed=False`** : permet de lire une table créée par un autre service sans que Django la gère
- **Cache lazy refresh** : TTL simple avec invalidation explicite, plus simple que refresh proactif
- **GCP Cloud Run** : serverless containers, scale to zero, idéal pour microservices avec trafic variable
- **Vertex AI text-embedding-004** : embeddings Google optimisés pour français, alternative à sentence-transformers
- **MLflow pour fine-tuning uniquement** : overkill pour modèles pre-trained, utile pour experiment tracking et model registry
- **Contrastive learning** : technique de fine-tuning embeddings avec triplets (anchor, positive, negative)
- **Cross-encoder** : modèle de re-ranking plus précis que bi-encoder, utilisé en second stage
- **Learning to Rank** : approche ML pour optimiser l'ordre des résultats de recherche
- **OfferInteraction pattern** : collecter les interactions utilisateur (vues, clics, applications) pour supervision implicite
- **wkhtmltopdf** : génération PDF depuis HTML sans LaTeX, supporte unicode nativement
- **Base de données partagée dev** : utiliser le même PostgreSQL en local et Docker via port exposé (ex: `localhost:5433`)
- **Script dev interactif** : menu bash avec couleurs + mode CLI rapide pour les commandes fréquentes
- **`set +e` en bash** : permet de continuer même si une commande échoue (utile pour services manquants)
- **`asyncio.create_task()` vs `BackgroundTasks`** : BackgroundTasks de FastAPI n'est PAS vraiment async - il attend la fin de la fonction avant de renvoyer la réponse HTTP. Utiliser `asyncio.create_task()` pour une vraie exécution non-bloquante
- **`asyncio.to_thread()` pour appels synchrones** : Les SDKs LLM (OpenAI, Anthropic) sont synchrones et bloquent l'event loop. Wrapper avec `await asyncio.to_thread(fn, args)` pour exécuter dans un thread pool
- **Pattern task_id + polling** : Pour les traitements longs (>10s), retourner immédiatement un task_id et laisser le client faire du polling sur `/status/{task_id}`
- **ATS optimization** : L'intitulé du CV doit être très proche du titre de l'offre, et reprendre les mots-clés exacts (pas de synonymes)

## ⚠️ Pièges à éviter
- Ne pas oublier la conformité RGPD (tâche assignée à Maxime)
- Gentleman Agreement à signer avant de continuer
- **Vibecoding** : ne jamais modifier les zones de l'équipe classique (offre-ingestion, matching)
- Toujours confirmer avant de modifier fichiers partagés (docker-compose, .env, interfaces)
- **Migrations auto-générées** : peuvent avoir des lignes trop longues (flake8 E501), nécessite reformatage manuel
- **overflow: hidden** sur body empêche tout scroll, s'assurer que le contenu tient dans le viewport
- **Bandit B104** : `host="0.0.0.0"` génère un warning, ajouter `# nosec B104` pour les conteneurs Docker
- **Ruff B904** : dans un `except`, utiliser `raise ... from e` ou `raise ... from None`
- **Import shared sans pip install** : ne pas oublier d'installer le package avant de lancer les microservices
- **Structure package** : bien utiliser `src/package/` pour que setuptools trouve les modules
- **Docker .env changes** : `docker-compose restart` ne relit pas les .env, utiliser `down` puis `up`
- **Ollama endpoint** : toujours ajouter `/v1` à l'URL de base pour compatibilité OpenAI
- **docker-compose context** : si un service a besoin de `../../shared`, mettre context à `.` (root)
- **KeyError ContainerConfig** : bug docker-compose, résoudre avec `down` complet avant `up`
- **Page reload perd la section active** : utiliser URL hash (`#section`) pour persister l'état
- **Polling interrompu par reload** : implémenter `resumeProcessingCVs()` pour reprendre au chargement
- **PDF scannés sans texte** : pdfplumber retourne vide, utiliser Vision LLM ou OCR
- **Prompts trop longs dans le code** : externaliser en fichiers .txt pour maintenabilité
- **Pre-commit hooks modifient les fichiers** : les hooks (trailing whitespace, Ruff, etc.) peuvent modifier les fichiers staged, ce qui les "unstage" et fait échouer le commit. Solution : `git add -A && git commit` pour re-stage et recommit
- **offre-ingestion sans Dockerfile** : `docker-compose build` échoue si un service est déclaré sans Dockerfile
  - Solution : builder explicitement les services existants : `docker-compose build gui cv-ingestion`
- **Django app optionnelle en production** : ne jamais mettre une app dev-only dans INSTALLED_APPS sans condition
  - Solution : `if ENV_MODE == "local": try: import app; INSTALLED_APPS.append(...)`
- **Nouveaux content_types structurés** : lors de l'ajout d'un content_type avec des champs structurés (comme personal_info ou social_link), ne pas oublier d'ajouter le parsing dans `parse_llm_response()` dans analyzer.py
- **Django CheckboxSelectMultiple** : le widget génère un `<ul><li>` avec styles qui peuvent override le CSS. Préférer le rendu manuel pour un contrôle total du layout
- **docx.js CDN jsdelivr** : le path `build/index.min.js` n'existe pas toujours, utiliser unpkg avec `build/index.umd.js` pour browser
- **yield from dans try/except** : Ruff UP028 suggère `yield from` mais cela empêche de catch les erreurs et faire un fallback - utiliser `# noqa: UP028`
- **Bandit `# noqa` ne fonctionne pas** : Bandit ignore la syntaxe `# noqa: SXXX`, utiliser `# nosec BXXX` à la place
- **try/except/pass sur QuerySet** : `.filter().first()` ne lève pas d'exception, retourne `None` - Bandit B110 détecte ce pattern inutile
- **SQLite vs PostgreSQL en dev** : utiliser des bases différentes entre local et Docker cause des pertes de données et incohérences
- **ENV_MODE manquant dans docker-compose.yml** : sans `ENV_MODE=dev`, Django utilise le mode "local" qui essaie de se connecter à `localhost:5433` (inaccessible depuis le container)
- **Migrations créées dans le container** : si `makemigrations` est exécuté dans le container, le fichier de migration n'existe pas dans le code source → utiliser `docker cp` pour récupérer
- **Volume Docker vs base vide** : `docker-compose down` sans `-v` préserve les données, mais un `full-restart` d'un service ne recrée pas les users → créer un superuser après reset
- **`docker-compose down -v`** : le flag `-v` supprime les volumes = perte de toutes les données. Ne jamais utiliser sauf pour reset complet
- **FastAPI BackgroundTasks pour async** : NE PAS utiliser pour les tâches longues car elles bloquent quand même la réponse HTTP. Utiliser `asyncio.create_task()` à la place
- **Async functions avec appels synchrones** : Marquer une fonction `async` ne la rend pas non-bloquante si elle appelle du code synchrone. Utiliser `asyncio.to_thread()` pour wrapper les appels bloquants
- **Timeout court sur POST de démarrage** : Le POST qui lance une tâche async doit retourner en <1s. Si ça prend plus longtemps, vérifier que la tâche n'est pas exécutée de manière synchrone
- **Django `mark_safe()` sans sanitization** : Bandit B703/B308 détecte les risques XSS.
  - **Problème réel** : `mark_safe()` sur du contenu utilisateur = faille XSS critique (injection de `<script>`)
  - **Faux positif** : Bandit ne peut pas savoir si le contenu est sanitizé, il alerte toujours
  - **Solution** : sanitizer avec `bleach.clean()` avant `mark_safe()` avec whitelist stricte de tags/attributs, puis ajouter `# nosec B308 B703` avec un commentaire expliquant pourquoi c'est sécurisé
  - **Exemple** : `return mark_safe(bleach.clean(html, tags=ALLOWED_TAGS))  # nosec B308 B703`
- **Exemples JWT dans la documentation** : Gitleaks détecte les tokens JWT même fictifs comme secrets.
  - **Problème réel** : aucun, ce sont des exemples de documentation, pas de vrais tokens
  - **Faux positif** : Gitleaks ne distingue pas les exemples des vrais secrets
  - **Solution** : utiliser des placeholders explicites comme `<JWT_ACCESS_TOKEN>` au lieu de vrais formats JWT `eyJ0eXAi...`
- **Ollama API OpenAI-compatible vs native** : Ollama expose deux APIs différentes :
  - `/api/tags`, `/api/generate`, `/api/chat` : API native Ollama
  - `/v1/models`, `/v1/chat/completions` : API OpenAI-compatible
  - **Problème** : `/api/tags` peut lister des modèles alors que `/v1/models` retourne une liste vide
  - **Cause** : Les modèles doivent être explicitement exposés via l'API OpenAI-compatible (config Ollama)
  - **Solution** : Vérifier les deux endpoints, ou adapter le code pour utiliser l'API native Ollama si nécessaire
- **GCP Billing account not found** : l'erreur `Billing account for project 'xxx' is not found` survient quand on essaie d'activer des APIs avant d'avoir lié un compte de facturation au projet.
  - **Prérequis obligatoire** : Console GCP → Facturation → Associer le projet au compte de facturation
  - **Ordre** : 1) Créer projet, 2) Activer facturation, 3) Activer APIs
- **Terraform ne déploie pas le code** : Terraform gère l'infrastructure, PAS le code applicatif. Si l'architecture n'a pas changé, `terraform apply` ne fait rien même si le code a changé.
  - **Problème** : Docker peut utiliser des layers cachées et ne pas intégrer le nouveau code
  - **Solution** : Dans le workflow de déploiement, utiliser `docker compose build --no-cache --pull` pour forcer la reconstruction
  - **Workflow correct** : `build --no-cache` → `down` → `up -d`
- **Variable d'environnement non définie dans gsutil** : `gsutil mb gs://bucket-name-$PROJECT_ID` échoue avec "Invalid bucket name" si `$PROJECT_ID` n'est pas défini.
  - **Solution 1** : `export PROJECT_ID=mon-projet-id` avant la commande
  - **Solution 2** : Hardcoder le nom du bucket directement dans les fichiers Terraform
- **Deux types d'authentification gcloud** : `gcloud auth login` et `gcloud auth application-default login` sont DIFFÉRENTS.
  - `gcloud auth login` : Authentifie le CLI gcloud (pour les commandes `gcloud`, `gsutil`)
  - `gcloud auth application-default login` : Crée les credentials pour les SDKs (Terraform, Python, etc.)
  - **Piège** : Faire `gcloud auth login` ne suffit pas pour Terraform, il faut aussi `gcloud auth application-default login`
- **Zone GCP indisponible** : Certains types de VM ne sont pas disponibles dans toutes les zones.
  - **Symptôme** : `e2-standard-2 VM instance is currently unavailable in the europe-west9-b zone`
  - **Solution** : Utiliser `data.google_compute_zones.available` pour sélectionner automatiquement une zone disponible
- **terraform import pour ressources existantes** : Si une ressource existe dans GCP mais pas dans le state Terraform.
  - **Symptôme** : `Error 409: Already Exists`
  - **Solution** : `terraform import google_bigquery_dataset.gold job-match-v0/jobmatch_gold`
- **GitHub Actions secrets non configurés** : Erreur cryptique si les secrets manquent.
  - **Symptôme** : `google-github-actions/auth failed with: must specify exactly one of "workload_identity_provider" or "credentials_json"`
  - **Cause** : Les secrets `GCP_WORKLOAD_IDENTITY_PROVIDER` ou `GCP_DEPLOY_SERVICE_ACCOUNT` ne sont pas définis
  - **Solution** : Configurer tous les secrets dans GitHub Settings → Secrets → Actions
- **Terraform snap --classic** : Terraform via snap nécessite le mode classic.
  - **Symptôme** : `error: This revision of snap "terraform" was published using classic confinement`
  - **Solution** : `sudo snap install terraform --classic`

## 🏗️ Patterns qui fonctionnent
- Documentation structurée dans Google Drive
- User Stories avec priorités MoSCoW et critères d'acceptation
- Répartition des tâches selon les préférences/compétences
- `.claude/settings.json` pour définir les règles de vibecoding
- Préfixe de commit `[CortexForge]` pour identifier les commits vibecoding
- Architecture microservices avec dossiers séparés par domaine

## Dépannage git
- Pour bien recréer la dépendance entre les branches main et dev, il faut bien mettre à jour la baranche main puis écraser la branche dev en resettant l'historique de la branche dev avec les commandes suivantes :

```bash
# Se placer sur la branche dev
git checkout dev
# Ecraser l'historique de la branche dev avec celui de la branche main
git reset --hard main
```

### Workflow Git complet (feature branch → PR → merge)
```bash
# 1. Avant commit : lint et format
ruff check --fix . && ruff format .

# 2. Commit
git add -A && git commit -m "[CortexForge] message"

# 3. Push et créer PR sur GitHub
git push -u origin feature/ma-branche

# 4. Après merge de la PR : retour sur dev et cleanup
git checkout dev && git pull && git branch -d feature/ma-branche
```
- **CSS clamp()** pour des tailles responsive sans media queries
- **Template blocks conditionnels** avec `{% if user.is_authenticated %}{{ block.super }}{% endif %}`
- **Variables CSS** (`:root`) pour cohérence des couleurs/styles
- **Factory Pattern** pour providers interchangeables (LLM, DB, etc.)
- **pydantic-settings** pour config via env vars avec validation
- **Ruff avec --fix** dans pre-commit : auto-correction des erreurs simples
- **URL hash navigation** : `history.replaceState()` + lecture du hash au load pour persister l'état UI
- **Prompts en fichiers .txt** : faciles à éditer, versionner, et itérer sans toucher au code Python
- **Détection auto PDF texte/image** : heuristique simple (min chars) avant de choisir la méthode d'extraction
- **Vision LLM + OCR fallback** : robustesse maximale pour tous types de PDF
- **Pre-commit workflow** : `ruff check --fix . && ruff format .` avant chaque commit pour auto-fix et formatage
- **Documentation avant code** : rédiger ARCHITECTURE.md et IAM_GUIDE.md avant de coder l'infrastructure permet de valider l'approche et facilite la maintenance
- **Workload Identity Federation** : évite les clés JSON service account, auth keyless depuis GitHub Actions vers GCP
- **Terraform modules séparés** : main.tf, variables.tf, network.tf, vm.tf, storage.tf, bigquery.tf, iam.tf, outputs.tf - meilleure lisibilité et maintenance
- **Deux workflows GitHub Actions séparés** : un pour Terraform (infra/), un pour Deploy (app/) - séparation claire des responsabilités

## 📋 TODO / Dette technique
- [x] Choix de la stack technique → architecture microservices Python
- [x] Créer branche feature et commit structure microservices
- [x] Documentation pre-commit (docs/pre_commit_101.md)
- [x] Service GUI Django (accounts app)
- [x] Dockerfile GUI
- [x] Configuration multi-environnement (local/dev/prod)
- [x] CI/CD Cloud Run (cloudbuild.yaml)
- [x] Refonte UI landing page (hero, animations, navbar conditionnelle)
- [x] Page profil avec sidebar menu
- [x] ORM CV/CoverLetter/ExtractedLine
- [x] Connexion vue profil aux ExtractedLine
- [x] Spécification cv-ingestion (docs/cv_ingestion_spec.md)
- [x] Convention de langue (CLAUDE.md) : code EN, UI FR
- [x] **Microservice cv-ingestion Phase 1** : FastAPI, extraction PDF/DOCX, LLM provider-agnostic
- [x] **Migration Ruff** : remplacement black/isort/flake8/mypy par Ruff
- [x] **Documentation pre-commit mise à jour** avec Ruff
- [ ] Gentleman Agreement à rédiger et signer
- [ ] Présentation GitHub à faire (Matthieu)
- [ ] État de l'art scientifique (données, algos, SaaS existants, limites)
- [ ] Se renseigner sur la RGPD (Maxime)
- [ ] Tester `run_local.sh`
- [ ] Tester `docker-compose.dev.yml`
- [ ] Créer projet GCloud + Cloud SQL + Cloud Storage
- [x] Définir les interfaces partagées (schemas CV, offres) → shared package
- [x] **Tester cv-ingestion** avec un vrai CV PDF → script test_integration.py
- [x] Intégrer l'upload de CV dans la GUI (section "Mes documents")
- [ ] Implémenter les sections du profil (LM, pitch, succès, hobbies)
- [x] Upload photo de profil avec Cropper.js (recadrage style LinkedIn)
- [x] **Connecter GUI → cv-ingestion** : appel API après upload CV
- [x] **Test API cv-ingestion** : lancer serveur FastAPI et tester endpoint /extract
- [ ] Installer shared dans les autres microservices (offre-ingestion, matching, gui)
- [x] **Polling asynchrone** : cv-ingestion avec task_id + GUI polling
- [x] **Suppression CV** : endpoint + modal de confirmation
- [x] **Navigation hash URL** : conserver la section active après reload
- [x] **Vision LLM** : support PDF images/scannés avec GPT-4o, Claude, LLaVA
- [x] **Prompts externalisés** : fichiers .txt dans src/prompts/
- [x] **OCR fallback** : Tesseract si Vision LLM non disponible
- [x] **Toggle/Edit UI** : boutons sur les lignes extraites
- [x] **Page Gestion Compte** : settings avec identité, email, password, abonnement, LLM config
- [x] **Export RGPD** : endpoint d'export JSON des données utilisateur
- [x] **UserLLMConfig model** : permet aux users d'utiliser leur propre LLM
- [x] **LLM Config Fallback** : utilise env vars si config user vide
- [x] **Sélecteur d'abonnement** : choix du plan dans Account Settings
- [x] **Modal Pricing** : comparaison des plans avec fonctionnalités et tarifs
- [x] **Restriction LLM Config** : disponible uniquement pour Premium+
- [x] **AI Assistant STAR Chatbot** : microservice + UI chat pour formalisation succès professionnels
- [x] **Extension Pitch Coaching** : coaching_type enum, nouveau prompt, données STAR complètes pour pitch
- [x] **UI Pitch dans profile.html** : interface chat pour section "Mon pitch" (PitchChatbot avec coaching_type=pitch)
- [x] **Modèle Pitch Django** : stocker les pitchs 30s/3min générés (migration 0012)
- [ ] **Sauvegarde pitch depuis chat** : bouton pour extraire et sauvegarder le pitch généré
- [ ] **Édition inline** : permettre de modifier le contenu des lignes extraites
- [ ] **Regroupement expériences** : afficher les missions d'un même poste ensemble dans l'UI
- [ ] **Intégration paiement** : Stripe pour les abonnements payants
- [ ] **Validation email** : confirmation par email lors du changement d'adresse
- [x] **Auto-création succès STAR** : marqueur `[STAR_COMPLETE]` + extraction JSON + création auto en base
- [ ] **Tests E2E chatbot STAR** : tester le flux complet conversation → extraction → création succès
- [x] **Swagger/OpenAPI docs** : drf-spectacular avec `/api/docs/` et `/api/redoc/`
- [x] **Modèle Application** : workflow candidature (added → in_progress → applied → interview → accepted/rejected)
- [x] **Auto-création Application** : chaque ImportedOffer crée automatiquement une Application
- [x] **Page liste candidatures** : cards avec filtrage par status
- [ ] **Page détail candidature** : vue complète avec actions (modifier status, notes, documents)
- [ ] **Intégrer matching service** : appeler POST /match lors de l'import d'une offre
- [ ] **Restreindre CORS production** : limiter aux IDs d'extensions spécifiques
- [x] **Script dev.sh** : menu interactif + commandes CLI pour le workflow de développement
- [x] **Base PostgreSQL partagée** : local et Docker utilisent la même base via port exposé
- [x] **Infrastructure GCP Terraform** : VM, VPC, Cloud Storage, BigQuery, IAM, Workload Identity Federation
- [ ] **Configurer GitHub Secrets** : GCP_PROJECT_ID, GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_SERVICE_ACCOUNT, etc.
- [ ] **Donner accès GCP à Mohamed** : Storage Object Admin + BigQuery Data Editor + BigQuery Job User pour offre-ingestion
- [ ] **Intégration BigQuery** :
  - [ ] Ajouter dépendance `google-cloud-bigquery` aux services concernés
  - [ ] Créer client BigQuery partagé dans shared/
  - [ ] Adapter offre-ingestion pour écrire dans silver.offers
  - [ ] Adapter offre-ingestion pour écrire JSON bruts dans Cloud Storage bronze
  - [ ] Créer schémas BigQuery (skills, formations, languages) dans silver
  - [ ] Adapter matching pour lire depuis BigQuery silver
  - [ ] Créer tables gold (daily_stats, skills_ranking)
  - [ ] Configurer credentials BigQuery dans docker-compose
  - [ ] Tester écriture/lecture BigQuery
- [ ] **Déploiement initial VM** : SSH, clone repo, docker-compose up
- [ ] **Configurer domaine + HTTPS** : Caddy avec Let's Encrypt
- [ ] **Intégration LLM Google** : support Gemini/Vertex AI comme provider LLM alternatif (cv-ingestion, ai-assistant)
