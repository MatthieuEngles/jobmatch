# JobMatch GUI

Service Django pour l'interface utilisateur de JobMatch.

## Modes de lancement

### 1. Mode Local (développement rapide)

```bash
cd app/gui
./run_local.sh
```

- Base de données : SQLite
- URL : http://localhost:8000
- Admin : http://localhost:8000/admin (admin@jobmatch.local / admin)

### 2. Mode Docker Dev

```bash
cd app/gui
docker-compose -f docker-compose.dev.yml up --build
```

- Base de données : PostgreSQL
- URL : http://localhost:8080
- Hot-reload activé (volumes montés)

### 3. Mode Docker Prod (local)

```bash
cd app/gui
cp .env.example .env
# Éditer .env avec vos valeurs
docker-compose -f docker-compose.prod.yml up --build
```

### 4. Déploiement Cloud Run

```bash
# Depuis la racine du repo
gcloud builds submit app/gui --config=app/gui/cloudbuild.yaml
```

## Variables d'environnement

| Variable | Description | Local | Dev | Prod |
|----------|-------------|-------|-----|------|
| `ENV_MODE` | Mode d'exécution | local | dev | prod |
| `DEBUG` | Mode debug | True | True | False |
| `SECRET_KEY` | Clé secrète Django | auto | dev-key | Secret Manager |
| `POSTGRES_*` | Config PostgreSQL | - | docker | Cloud SQL |
| `GCS_BUCKET_NAME` | Bucket GCS pour uploads | - | - | jobmatch-uploads |

## Structure

```
app/gui/
├── accounts/           # App gestion utilisateurs
├── config/             # Configuration Django
├── templates/          # Templates HTML
├── static/             # Fichiers statiques
├── Dockerfile          # Image dev
├── Dockerfile.prod     # Image prod (multi-stage)
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── cloudbuild.yaml     # CI/CD GCloud
├── run_local.sh        # Script lancement local
└── entrypoint.sh       # Entrypoint Docker
```
