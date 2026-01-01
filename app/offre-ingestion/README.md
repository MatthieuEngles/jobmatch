# Offre Ingestion Service

Service d'ingestion des offres d'emploi France Travail.

## 📖 Documentation

Toute la documentation se trouve dans `docs/`:
- [README principal](docs/README.md)
- [Architecture du pipeline](docs/PIPELINE.md)
- [Guide des requêtes SQL](docs/GUIDE_REQUETES.md)
- [Exécution avec Docker](docs/RUN_PIPELINE_WITH_DOCKER.md)

## 🚀 Quick Start

```bash
# Build depuis la racine du projet
cd /home/mohamede.madiouni/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .

# Exécuter le pipeline complet
cd app/offre-ingestion
docker compose run --rm offre-ingestion fetch 2025-12-31
docker compose run --rm offre-ingestion silver 2025-12-31
docker compose run --rm offre-ingestion gold 2025-12-31
```

## 📁 Structure

```
offre-ingestion/
├── docs/              # Documentation complète
├── src/
│   ├── pipelines/     # Pipelines Bronze→Silver→Gold (Docker)
│   ├── deprecated/    # Anciens scripts (local SQLite/CSV)
│   └── utils/         # Scripts de vérification
└── scripts/
    ├── setup/         # Scripts de création de schémas BigQuery
    └── utils/         # Utilitaires (lecture GCS, etc.)
```

## 🏗️ Architecture

**Médaillon Bronze → Silver → Gold**

- **Bronze (GCS)**: Offres brutes depuis France Travail API
- **Silver (BigQuery)**: Données nettoyées et structurées
- **Gold (BigQuery)**: Embeddings vectoriels pour matching
