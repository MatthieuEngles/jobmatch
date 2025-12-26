# JobMatch

Plateforme intelligente de matching CV/offres d'emploi avec generation automatique de CV et lettres de motivation personnalises.

## Architecture

```
jobmatch/
├── app/
│   ├── gui/                 # Frontend Django (port 8085)
│   ├── ai-assistant/        # Service IA - generation CV/LM (port 8084)
│   ├── cv-ingestion/        # Ingestion et parsing de CV (port 8081)
│   ├── offre-ingestion/     # Ingestion offres France Travail (port 8082)
│   ├── matching/            # Service de matching CV/offres (port 8083)
│   └── local_ollama/        # Ollama local avec modeles Mistral (port 11434)
├── shared/                  # Code partage entre services
├── docs/                    # Documentation technique
└── docker-compose.yml       # Orchestration des services
```

## Services

| Service | Port | Status | Description |
|---------|------|--------|-------------|
| **gui** | 8085 | OK | Application web Django avec API REST |
| **ai-assistant** | 8084 | OK | FastAPI pour generation IA (CV, lettres) |
| **cv-ingestion** | 8081 | OK | Extraction de donnees structurees depuis CV |
| **offre-ingestion** | 8082 | OK | Pipeline d'ingestion offres France Travail |
| **matching** | 8083 | WIP | Service de matching CV/offres |
| **local-ollama** | 11434 | OK | Serveur Ollama avec modeles Mistral |
| **db** | 5433 | OK | PostgreSQL 16 |
| **redis** | 6379 | OK | Cache et files d'attente |

## Demarrage rapide

### Prerequis

- Docker et Docker Compose
- Python 3.12+ (pour dev local)

### Lancer les services

```bash
# Demarrer les services principaux
docker-compose up -d db gui

# Demarrer avec l'assistant IA
docker-compose up -d db gui ai-assistant

# Demarrer Ollama local (modeles Mistral)
docker-compose up -d local-ollama
```

### Script de developpement

```bash
# Menu interactif
./dev.sh

# Commandes rapides
./dev.sh start              # Demarre db + gui
./dev.sh stop               # Arrete tout
./dev.sh rebuild gui        # Rebuild + restart
./dev.sh logs gui           # Voir les logs
./dev.sh migrate            # Appliquer migrations
./dev.sh shell              # Django shell
./dev.sh full-restart gui   # Stop + rm + build + up
```

## Fonctionnalites

### Application Web (GUI)

- **Gestion de profil** : CV structure, competences, experiences, formations
- **Import d'offres** : Extension navigateur pour capturer des offres depuis n'importe quel site
- **Suivi des candidatures** : Workflow added → in_progress → applied → interview → accepted/rejected
- **Generation IA** : CV et lettres de motivation personnalises par offre
- **Export DOCX** : Templates personnalisables pour l'export Word

### API REST

- **Authentification JWT** : Access token 15min, refresh 7 jours
- **Documentation Swagger** : `/api/docs/`
- **Endpoints** :
  - `POST /api/auth/token/` - Login
  - `POST /api/offers/import/` - Importer une offre
  - `GET /api/offers/` - Liste des offres importees

### Service IA (ai-assistant)

- **Generation de CV** : Optimise ATS avec mots-cles de l'offre
- **Generation de lettres** : Personnalisees selon le CV et l'offre
- **Pattern async** : Task-based polling pour eviter les timeouts
- **Niveau d'adaptation** : Slider 1-4 (conservateur → creatif)

### Ollama Local

Serveur Ollama Docker avec modeles pre-telecharges :

- `mistral:latest` - Modele par defaut (leger)
- `mistral:7b` - Modele plus puissant

```bash
# Tester Ollama
curl http://localhost:11434/api/tags

# Generer une completion
curl http://localhost:11434/api/generate -d '{
  "model": "mistral:latest",
  "prompt": "Bonjour"
}'
```

### CV Ingestion (cv-ingestion)

Service FastAPI d'extraction de donnees structurees depuis les CV :

- **Formats supportes** : PDF, DOCX
- **Detection intelligente** : PDF texte vs PDF image (scan)
- **Extraction LLM** : Analyse du contenu avec modeles IA
- **Vision LLM** : Support des CV scannes via modeles vision
- **Fallback OCR** : Tesseract si vision non disponible
- **Pattern async** : Task-based avec polling status

```bash
# Soumettre un CV pour extraction
curl -X POST http://localhost:8081/extract \
  -F "file=@mon_cv.pdf"

# Verifier le status
curl http://localhost:8081/status/{task_id}
```

### Offre Ingestion (offre-ingestion)

Pipeline d'ingestion des offres d'emploi depuis l'API France Travail :

- **Architecture Bronze/Silver** : JSON brut → donnees structurees
- **Sources** : API France Travail (offres d'emploi v2)
- **Extraction** : Par code ROME avec pagination automatique
- **Transformation** : 13 tables relationnelles (SQLite ou CSV)
- **Logging** : Suivi des requetes API dans logs.xlsx

```bash
# Extraction des offres de la veille
python src/fetch_offers_with_pagination.py

# Transformation vers SQLite
python src/transform_offers_to_db_silver.py 2025-12-23
```

**Tables generees** :
- `offers` : Table principale (27 colonnes)
- Tables secondaires : lieu, entreprise, salaire, competences, formations, permis, langues...

### Matching (matching)

Service de matching CV/offres d'emploi (en developpement) :

- **Score de compatibilite** : 0-100% par offre
- **Criteres** : Competences, experience, localisation, salaire
- **Synonymes intelligents** : Detection des equivalences (React ≈ ReactJS)
- **Multi-sources** : Aggregation des offres de differentes sources

## Configuration

### Variables d'environnement

```bash
# Base de donnees
POSTGRES_USER=jobmatch
POSTGRES_PASSWORD=jobmatch
POSTGRES_DB=jobmatch

# Ports (optionnel)
GUI_PORT=8085
AI_ASSISTANT_PORT=8084
OLLAMA_PORT=11434
DB_PORT=5433

# AI Assistant
AI_ASSISTANT_URL=http://ai-assistant:8084
```

### Fichiers .env

- `app/ai-assistant/.env` - Configuration LLM (cles API)
- `app/cv-ingestion/.env` - Configuration parsing

## Documentation

- [POSTMORTEM.md](POSTMORTEM.md) - Historique des sessions de developpement
- [PITCH.md](PITCH.md) - Vision produit
- [docs/ASYNC_PATTERNS.md](docs/ASYNC_PATTERNS.md) - Pattern async pour generation IA
- [docs/api_extension.md](docs/api_extension.md) - API pour extension navigateur

## Stack technique

- **Frontend** : Django 5.0, Django REST Framework
- **Backend IA** : FastAPI, LiteLLM
- **Base de donnees** : PostgreSQL 16
- **LLM** : Ollama (local), OpenAI, Anthropic (cloud)
- **Conteneurisation** : Docker, Docker Compose

## Conventions

- **Code** : Commentaires et noms en anglais
- **UI** : Interface en francais

---

> *JobMatch - Les offres viennent a vous*
