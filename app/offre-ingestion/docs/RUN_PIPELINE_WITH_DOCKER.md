# 🚀 Exécution du Pipeline avec Docker

## 📋 Prérequis

- Docker et Docker Compose installés
- Credentials GCP configurés
- Fichier `.env` à la racine du service

## ⚙️ Configuration

### 1. Créer le fichier `.env`

```bash
cd app/offre-ingestion
cp .env.example .env
# Éditer .env avec vos credentials
```

Contenu du `.env` :
```env
# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket
BIGQUERY_DATASET_SILVER=silver_dataset
BIGQUERY_DATASET_GOLD=gold_dataset

# France Travail API
FT_CLIENT_ID=your_client_id
FT_CLIENT_SECRET=your_client_secret
FT_SCOPE=list_of_scopes
FT_OAUTH_URL=the_oauth_url
FT_API_URL_BASE=the_api_base_url
FT_ROMECODES_PATH=path/to/romecodes.txt
```

## 🏗️ Build de l'image

**Important** : Le build doit être lancé depuis la **racine du projet** pour accéder au package `shared`.

```bash
# Depuis la racine du projet jobmatch
cd /path/to/jobmatch

# Build avec le contexte racine
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

## 🚀 Exécution du Pipeline

### Commandes individuelles

```bash
# Se placer dans le dossier du service
cd app/offre-ingestion

# 1️⃣ Bronze : Fetch offres → GCS
docker compose run --rm offre-ingestion fetch 2025-12-31

# 2️⃣ Silver : GCS → BigQuery (structuration)
docker compose run --rm offre-ingestion silver 2025-12-31

# 3️⃣ Gold : Silver → Gold (embeddings)
docker compose run --rm offre-ingestion gold 2025-12-31
```

### Pipeline complet

```bash
# Exécution séquentielle avec date spécifique
DATE="2025-12-31"
docker compose run --rm offre-ingestion fetch $DATE && \
docker compose run --rm offre-ingestion silver $DATE && \
docker compose run --rm offre-ingestion gold $DATE

# Ou avec la date de J-1 (par défaut)
docker compose run --rm offre-ingestion fetch && \
docker compose run --rm offre-ingestion silver && \
docker compose run --rm offre-ingestion gold
```

## 📊 Architecture du Pipeline

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   France    │ API  │   Bronze    │ GCS  │   Silver    │ BQ   │    Gold     │
│  Travail    │─────▶│    Layer    │─────▶│    Layer    │─────▶│    Layer    │
│             │      │ (JSON brut) │      │ (Structuré) │      │ (Embeddings)│
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
     API                  GCS               BigQuery            BigQuery+AI
```

## 🔍 Vérification

### Vérifier les logs Docker

```bash
# Logs d'un service
docker compose logs offre-ingestion

# Suivre les logs en temps réel
docker compose logs -f offre-ingestion
```

### Vérifier les données GCS

```bash
# Liste les fichiers bronze
gsutil ls gs://your-bucket/bronze/

# Voir le contenu d'une date
gsutil ls gs://your-bucket/bronze/2025-12-31/
```

### Vérifier les tables BigQuery

```bash
# Silver tables
bq ls silver_dataset

# Gold tables
bq ls gold_dataset

# Compter les offres dans Silver
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) as total FROM `project.silver_dataset.offers`'
```

## ⚠️ Notes importantes

- **Sans date** : Le pipeline traite automatiquement les données de J-1
- **Architecture médaillon** : Bronze (GCS) → Silver (BigQuery) → Gold (BigQuery + Embeddings)
- **Idempotence** : Chaque étape peut être relancée sans risque de duplication
- **Dépendances** : Chaque étape dépend de la précédente (fetch → silver → gold)

## 🐛 Dépannage

### Erreur "No space left on device"

```bash
# Nettoyer les images et conteneurs inutilisés
docker system prune -a --volumes -f
```

### Erreur d'authentification GCP

```bash
# Vérifier le fichier de credentials
cat credentials/gcp-service-account-key.json

# Tester l'authentification
docker compose run --rm offre-ingestion python -c "from google.cloud import storage; print(storage.Client())"
```

### Rebuild forcé

```bash
# Rebuild sans cache
cd /path/to/jobmatch
docker build --no-cache -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```
