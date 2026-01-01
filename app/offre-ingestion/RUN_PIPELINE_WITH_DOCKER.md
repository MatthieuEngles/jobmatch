# 🚀 Quick Start - Pipeline Offre Ingestion

## Prérequis
- Docker et Docker Compose installés
- Fichier `.env` configuré avec `GOOGLE_APPLICATION_CREDENTIALS`
- Credentials GCP dans `credentials/gcp-service-account-key.json`

## Build de l'image

```bash
cd /home/mohamede.madiouni/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

## Exécution du pipeline

### 1️⃣ Fetch - Récupérer les offres depuis France Travail → GCS

```bash
cd /home/mohamede.madiouni/jobmatch/app/offre-ingestion
docker compose run --rm offre-ingestion fetch 2025-08-31
```

### 2️⃣ Silver - Transformer les offres GCS → BigQuery Silver

```bash
docker compose run --rm offre-ingestion silver 2025-08-31
```

### 3️⃣ Gold - Générer les embeddings BigQuery Silver → BigQuery Gold

```bash
docker compose run --rm offre-ingestion gold 2025-08-31
```

## Pipeline complet (enchaînement)

```bash
DATE="2025-08-31"
docker compose run --rm offre-ingestion fetch $DATE && \
docker compose run --rm offre-ingestion silver $DATE && \
docker compose run --rm offre-ingestion gold $DATE
```

## Notes
- Sans date spécifiée, le pipeline traite les données de J-1
- Architecture médaillon : **Bronze (GCS)** → **Silver (BigQuery)** → **Gold (BigQuery + Embeddings)**
