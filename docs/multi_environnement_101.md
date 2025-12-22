# Configuration Multi-Environnement - Guide Pratique

## 🎯 Objectif

Permettre à une même application de tourner dans différents contextes :
- **Local** : développement rapide sur sa machine
- **Dev** : environnement partagé proche de la prod
- **Prod** : environnement de production réel

## 📁 Structure mise en place

```
app/gui/
├── config/
│   └── settings.py          # Settings unifiés avec ENV_MODE
├── run_local.sh              # Script lancement local
├── entrypoint.sh             # Entrypoint Docker (dev/prod)
├── Dockerfile                # Image dev
├── Dockerfile.prod           # Image prod (multi-stage)
├── docker-compose.dev.yml    # Stack dev complète
├── docker-compose.prod.yml   # Stack prod (test local)
└── cloudbuild.yaml           # CI/CD Google Cloud
```

## 🔧 Comment ça marche

### Variable `ENV_MODE`

Le cœur du système repose sur une variable d'environnement :

```python
ENV_MODE = os.environ.get("ENV_MODE", "local")  # local | dev | prod
```

Cette variable détermine :
- La base de données (SQLite vs PostgreSQL)
- Le niveau de debug
- Les hosts autorisés
- Le stockage des fichiers (local vs Cloud Storage)

### Mode Local

```bash
./run_local.sh
```

| Aspect | Configuration |
|--------|---------------|
| BDD | SQLite (db.sqlite3) |
| Debug | Activé |
| Static files | Django runserver |
| Dépendances | Pas de Docker |

**Avantages** : Démarrage instantané, pas besoin de Docker, idéal pour tester rapidement.

### Mode Dev (Docker)

```bash
docker-compose -f docker-compose.dev.yml up
```

| Aspect | Configuration |
|--------|---------------|
| BDD | PostgreSQL conteneurisé |
| Debug | Activé |
| Static files | Django runserver |
| Hot-reload | Oui (volumes montés) |

**Avantages** : Environnement isolé, proche de la prod, partage facile avec l'équipe.

### Mode Prod (Cloud Run)

```bash
gcloud builds submit --config=cloudbuild.yaml
```

| Aspect | Configuration |
|--------|---------------|
| BDD | Cloud SQL (PostgreSQL) |
| Debug | Désactivé |
| Static files | WhiteNoise |
| Secrets | Secret Manager |
| Scaling | Auto (0-10 instances) |

## 🏗️ Éléments clés

### 1. Settings conditionnels

```python
if ENV_MODE == "local":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "jobmatch"),
            # ...
        }
    }
```

### 2. Multi-stage Docker build

```dockerfile
# Stage 1: Builder (compilations, wheels)
FROM python:3.12-slim as builder
RUN pip wheel --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime (image légère)
FROM python:3.12-slim
COPY --from=builder /app/wheels /wheels
RUN pip install /wheels/*
```

**Résultat** : Image finale ~150MB au lieu de ~500MB.

### 3. Cloud SQL via Unix Socket

```python
if os.environ.get("CLOUD_SQL_CONNECTION_NAME"):
    DATABASES["default"]["HOST"] = f"/cloudsql/{connection_name}"
```

Cloud Run monte automatiquement le socket, pas besoin d'IP.

### 4. Secrets via Secret Manager

```yaml
--set-secrets:
  - 'SECRET_KEY=jobmatch-secret-key:latest'
  - 'POSTGRES_PASSWORD=jobmatch-db-password:latest'
```

Les secrets ne sont jamais dans le code ni les variables d'environnement en clair.

## ✅ Bonnes pratiques respectées

| Pratique | Implémentation |
|----------|----------------|
| **12-Factor App** | Config via variables d'environnement |
| **Immutable Infrastructure** | Images Docker versionnées |
| **Secret Management** | GCloud Secret Manager |
| **Principle of Least Privilege** | User non-root dans le conteneur |
| **Dev/Prod Parity** | Même code, config différente |

## ⚠️ Compromis acceptés

### 1. SQLite en local
**Pourquoi** : Simplicité, pas de Docker requis pour débuter.
**Risque** : Comportement différent de PostgreSQL (ex: contraintes, JSON).
**Mitigation** : Tests importants en mode dev (PostgreSQL).

### 2. Un seul fichier settings.py
**Alternative** : `settings/base.py`, `settings/local.py`, `settings/prod.py`
**Pourquoi ce choix** : Moins de fichiers, tout visible d'un coup.
**Limite** : Peut devenir complexe si beaucoup de différences.

### 3. WhiteNoise plutôt que CDN/Nginx
**Pourquoi** : Simplicité, pas de reverse proxy à gérer.
**Limite** : Moins performant pour les gros fichiers.
**Accepté car** : POC, peu de static files, Cloud Run scale horizontalement.

## 🚀 Workflow recommandé

```
Développeur           Dev partagé          Production
     │                     │                    │
     ▼                     ▼                    ▼
run_local.sh    →    docker-compose    →    Cloud Run
  (SQLite)            (PostgreSQL)        (Cloud SQL)
     │                     │                    │
     └─────── feature branch ────────┘         │
                    │                          │
                    └───── PR vers main ───────┘
```

1. **Développement** : `run_local.sh` pour itérer rapidement
2. **Validation** : `docker-compose.dev.yml` pour tester avec PostgreSQL
3. **Review** : PR avec tests CI
4. **Déploiement** : Merge → Cloud Build → Cloud Run

## 📊 Comparaison des approches

| Approche | Complexité | Parité Dev/Prod | Temps setup |
|----------|------------|-----------------|-------------|
| Un seul mode (local) | ⭐ | ❌ | 5 min |
| **Multi-env (notre choix)** | ⭐⭐ | ✅ | 30 min |
| K8s partout | ⭐⭐⭐⭐ | ✅✅ | 2h+ |

## 🎓 Conclusion

Cette configuration multi-environnement est une **bonne pratique standard** pour les projets sérieux car elle :

1. **Réduit les "ça marche sur ma machine"** - Environnements reproductibles
2. **Facilite l'onboarding** - Nouveau dev = `./run_local.sh` et c'est parti
3. **Sécurise la prod** - Secrets managés, debug désactivé
4. **Permet le scaling** - Cloud Run s'adapte à la charge
5. **Reste simple** - Pas de Kubernetes pour un POC

C'est le bon compromis entre simplicité et professionnalisme pour un projet en phase POC.
