# Pipeline d'Ingestion des Offres France Travail

## 🎯 Présentation

Service d'ingestion automatisé des offres d'emploi depuis l'API France Travail vers Google Cloud (GCS et BigQuery).

**Architecture Médaillon** : Bronze (GCS) → Silver (BigQuery) → Gold (BigQuery + Embeddings)

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  France Travail │────▶│    Bronze    │────▶│    Silver    │────▶│     Gold     │
│      API        │     │     GCS      │     │   BigQuery   │     │  BigQuery +  │
│                 │     │  (JSON brut) │     │  (Structuré) │     │  Embeddings  │
└─────────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

## 🚀 Quick Start

### Prérequis

- Docker et Docker Compose
- Credentials GCP dans `credentials/gcp-service-account-key.json`
- Fichier `.env` configuré (voir `.env.example`)

### Build de l'image

```bash
# Depuis la racine du projet jobmatch
cd /path/to/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### Exécution du pipeline

```bash
cd app/offre-ingestion

# 1️⃣ Bronze : Fetch offres → GCS
docker compose run --rm offre-ingestion fetch 2025-12-31

# 2️⃣ Silver : GCS → BigQuery (structuré)
docker compose run --rm offre-ingestion silver 2025-12-31

# 3️⃣ Gold : Génération embeddings
docker compose run --rm offre-ingestion gold 2025-12-31

# ⚡ Pipeline complet
DATE="2025-12-31"
docker compose run --rm offre-ingestion fetch $DATE && \
docker compose run --rm offre-ingestion silver $DATE && \
docker compose run --rm offre-ingestion gold $DATE
```

**Note** : Sans date spécifiée, le pipeline traite les données de J-1.

## 📁 Structure

```
offre-ingestion/
├── src/pipelines/          # Pipelines Bronze→Silver→Gold
│   ├── fetch_offers_to_gcs.py
│   ├── transform_offers_to_bigquery_silver.py
│   └── transform_offers_to_bigquery_gold.py
├── scripts/
│   ├── setup/              # Création schémas BigQuery
│   ├── utils/              # Scripts utilitaires
│   └── entrypoint.sh       # Point d'entrée Docker
├── docs/                   # Documentation complète
└── credentials/            # GCP credentials
```

## 📖 Documentation

- **[RUN_PIPELINE_WITH_DOCKER.md](RUN_PIPELINE_WITH_DOCKER.md)** : Guide d'exécution complet
- **[PIPELINE.md](PIPELINE.md)** : Architecture détaillée (Bronze → Silver → Gold)
- **[GUIDE_REQUETES.md](GUIDE_REQUETES.md)** : Requêtes SQL BigQuery

## 🔧 Configuration

Fichier `.env` requis :

```env
# GCP
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-service-account-key.json
GCP_PROJECT_ID=votre-project-id
GCS_BUCKET_NAME=votre-bucket
BIGQUERY_DATASET_SILVER=silver_dataset
BIGQUERY_DATASET_GOLD=gold_dataset

# France Travail API
FT_CLIENT_ID=votre_client_id
FT_CLIENT_SECRET=votre_client_secret
```

## 📊 Données Générées

### Bronze (GCS)
- Fichiers JSON bruts : `gs://bucket/bronze/YYYY-MM-DD/offers.json`

### Silver (BigQuery)
- Table principale : `offers` (données structurées)
- 12 tables secondaires (lieu, entreprise, compétences, etc.)

### Gold (BigQuery)
- `offers` : Données enrichies
- `offers_intitule_embeddings` : Embeddings des titres
- `offers_description_embeddings` : Embeddings des descriptions

Pour plus de détails, consultez les fichiers de documentation listés ci-dessus.
