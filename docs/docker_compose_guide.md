# Guide Docker Compose - JobMatch

## Vue d'ensemble

Docker Compose est utilisé pour orchestrer tous les services JobMatch. Ce guide couvre l'utilisation, les services disponibles et les commandes courantes.

## Services disponibles

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5433 | Base de données PostgreSQL 16 |
| `redis` | 6379 | Cache Redis |
| `gui` | 8085 | Interface web principale |
| `cv-ingestion` | 8081 | Parsing et extraction de CV |
| `ai-assistant` | 8084 | Assistant IA |
| `offre-ingestion` | 8082 | Ingestion des offres d'emploi |
| `matching` | 8086 | Moteur de matching CV-Offres |
| `local-ollama` | 11434 | LLM local (optionnel, via profile) |

## Commandes courantes

### Démarrer les services

```bash
# Démarrer les services de base
docker-compose up -d db redis gui

# Démarrer tous les services principaux
docker-compose up -d db redis gui cv-ingestion ai-assistant

# Démarrer avec ollama (profile optionnel)
docker-compose --profile ollama up -d
```

### Arrêter les services

```bash
# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes (ATTENTION : supprime les données)
docker-compose down -v
```

### Voir les logs

```bash
# Tous les services
docker-compose logs -f

# Un service spécifique
docker-compose logs -f gui

# Les 100 dernières lignes
docker-compose logs --tail=100 gui
```

### Reconstruire les services

```bash
# Reconstruire un service spécifique
docker-compose build gui

# Reconstruire sans cache
docker-compose build --no-cache gui

# Reconstruire et redémarrer
docker-compose up -d --build gui
```

### Vérifier le statut

```bash
docker-compose ps
```

## Variables d'environnement

Tous les services utilisent le fichier `.env` à la racine du projet. Variables principales :

```bash
# Ports
GUI_PORT=8085
CV_INGESTION_PORT=8081
AI_ASSISTANT_PORT=8084
MATCHING_PORT=8086
DB_PORT=5433
REDIS_PORT=6379

# Base de données
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=jobmatch
POSTGRES_PASSWORD=jobmatch
POSTGRES_DB=jobmatch

# Configuration LLM
LLM_TYPE=...
LLM_ENDPOINT=...
LLM_API_KEY=...
```

## Dépendances entre services

```
gui
  └── db

cv-ingestion
  └── (autonome)

ai-assistant
  └── (autonome)

matching
  ├── cv-ingestion
  └── offre-ingestion
```

## Profiles

Les services optionnels sont regroupés en profiles :

- `ollama` - LLM local avec Ollama
- `full` - Tous les services y compris optionnels

```bash
# Démarrer avec un profile spécifique
docker-compose --profile ollama up -d
```

---

## Docker Compose V1 vs V2

### Différences de syntaxe

| Action | V1 (Legacy) | V2 (Actuel) |
|--------|-------------|-------------|
| Démarrer | `docker-compose up -d` | `docker compose up -d` |
| Arrêter | `docker-compose down` | `docker compose down` |
| Logs | `docker-compose logs` | `docker compose logs` |
| Build | `docker-compose build` | `docker compose build` |

Notez le **tiret** (`docker-compose`) vs **espace** (`docker compose`).

### Vérifier la version

```bash
# V1 (binaire standalone)
docker-compose --version
# Output: docker-compose version 1.29.x

# V2 (plugin Docker CLI)
docker compose version
# Output: Docker Compose version v2.x.x
```

### Différences clés

| Aspect | V1 | V2 |
|--------|----|----|
| Installation | Binaire Python standalone | Plugin Docker CLI (Go) |
| Performance | Plus lent | Plus rapide (Go natif) |
| Champ `version:` | Requis dans le fichier compose | Optionnel (ignoré) |
| Backend de build | Builder legacy | BuildKit (par défaut) |
| Noms des containers | `projet_service_1` | `projet-service-1` |

### Problèmes connus en V2

Docker Compose V2 a des bugs connus qui peuvent causer des panics, notamment avec :
- Les contextes de build complexes
- Le tracing OpenTelemetry
- Certaines versions de Docker Desktop

**Exemple d'erreur :**
```
panic: runtime error: slice bounds out of range [1:0]
goroutine 32 [running]:
go.opentelemetry.io/otel/sdk/trace.(*recordingSpan).End...
```

### Recommandation pour JobMatch

**Utiliser la syntaxe V1 (`docker-compose`) pour la stabilité :**

```bash
# Recommandé
docker-compose up -d db gui redis

# Peut causer des panics sur certaines versions
docker compose up -d db gui redis
```

Si vous avez besoin des fonctionnalités V2, assurez-vous que Docker Desktop est à jour.

### Migration entre versions

Le format du fichier compose est compatible. Le changement principal est la syntaxe de commande :

```bash
# Créer un alias pour plus de commodité (ajouter à ~/.bashrc ou ~/.zshrc)
alias dc='docker-compose'

# Ou si vous préférez V2
alias dc='docker compose'
```

### Vérifier quelle version est utilisée

```bash
# Vérifier si docker-compose (V1) est installé
which docker-compose

# Vérifier si docker compose (V2) est disponible
docker compose version
```

Les deux peuvent coexister sur le même système.
