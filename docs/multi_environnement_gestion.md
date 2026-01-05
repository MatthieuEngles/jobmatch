# Gestion Multi-Environnement : Guide et Bonnes Pratiques

## Contexte

Ce document analyse les différentes approches pour gérer plusieurs environnements (local, dev, staging, prod) dans une architecture de services conteneurisés avec des ressources cloud (GCS, BigQuery).

**Problématique principale :** Comment les services savent-ils dans quel environnement ils s'exécutent, et comment pointer vers les bonnes ressources (buckets, datasets, bases de données) ?

---

## État des lieux JobMatch

### Services concernés

| Service | Consomme | Produit |
|---------|----------|---------|
| GUI | BigQuery Gold | - |
| offre-ingestion | GCS Bronze | BigQuery Silver, BigQuery Gold |
| cv-ingestion | - | PostgreSQL |
| ai-assistant | - | - |
| matching | BigQuery/SQLite | - |

### Configuration actuelle

```
┌─────────────────────────────────────────────────────────────┐
│                    Problèmes identifiés                      │
├─────────────────────────────────────────────────────────────┤
│ 1. ENV_MODE existe uniquement dans GUI                       │
│ 2. Datasets BigQuery hardcodés dans offre-ingestion          │
│ 3. deploy.yml génère un .env incomplet                       │
│ 4. Pas de distinction staging/prod dans le CI/CD            │
│ 5. Variables GCP absentes du déploiement                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Les 3 approches possibles

### Option A : Variable d'environnement globale (`ENV_MODE`)

**Principe :** Une seule variable `ENV_MODE` (local/dev/staging/prod) contrôle tout le comportement.

```python
# Exemple dans chaque service
ENV_MODE = os.environ.get("ENV_MODE", "local")

if ENV_MODE == "prod":
    DATASET = "gold"
    BUCKET = "jobmatch-bronze-job-match-v0"
elif ENV_MODE == "staging":
    DATASET = "staging_gold"
    BUCKET = "jobmatch-staging-bronze-job-match-v0"
else:
    DATASET = "dev_gold"
    BUCKET = "jobmatch-dev-bronze"
```

**Avantages :**
- Configuration minimale (1 seule variable)
- Cohérence garantie entre services
- Simple à comprendre et débugger
- Facile à ajouter dans le CI/CD

**Inconvénients :**
- Logique conditionnelle dispersée dans le code
- Couplage fort : changer un nom de bucket = modifier le code
- Risque d'oubli lors de l'ajout d'un nouvel environnement
- Difficile de tester un service staging avec des données prod
- Anti-pattern : configuration dans le code

**Verdict :** ❌ **Non recommandé** - Viole le principe de séparation config/code

---

### Option B : Variables explicites par ressource

**Principe :** Chaque ressource externe a sa propre variable d'environnement, sans logique dans le code.

```bash
# .env.staging
GCP_PROJECT_ID=job-match-v0
GCS_BUCKET=jobmatch-staging-bronze-job-match-v0
BIGQUERY_SILVER_DATASET=staging_silver
BIGQUERY_GOLD_DATASET=staging_gold
```

```python
# Code service - aucune logique conditionnelle
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
BUCKET = os.environ.get("GCS_BUCKET")
SILVER_DATASET = os.environ.get("BIGQUERY_SILVER_DATASET")
GOLD_DATASET = os.environ.get("BIGQUERY_GOLD_DATASET")
```

**Avantages :**
- Zéro logique conditionnelle dans le code
- Flexibilité totale (staging avec données prod possible)
- Respect du 12-Factor App (config via environnement)
- Changement de ressource = changement de variable, pas de code
- Testabilité maximale

**Inconvénients :**
- Plus de variables à gérer
- Risque d'incohérence (staging bucket + prod dataset)
- Pas de "source of truth" unique pour l'environnement
- Plus de secrets à maintenir dans GitHub

**Verdict :** ✅ **Recommandé pour les ressources externes**

---

### Option C : Approche hybride (Recommandé)

**Principe :** Combiner les deux approches selon le type de configuration.

| Type de config | Approche | Exemple |
|----------------|----------|---------|
| Comportement applicatif | `ENV_MODE` | Niveau de log, debug, migrations auto |
| Ressources externes | Variables explicites | Buckets, datasets, URLs |
| Secrets | Variables explicites | API keys, passwords |

```bash
# .env.staging
# --- Comportement applicatif ---
ENV_MODE=staging
DEBUG=true
LOG_LEVEL=DEBUG

# --- Ressources GCP (explicites) ---
GCP_PROJECT_ID=job-match-v0
GCS_BUCKET=jobmatch-staging-bronze-job-match-v0
BIGQUERY_SILVER_DATASET=staging_silver
BIGQUERY_GOLD_DATASET=staging_gold

# --- Secrets ---
LLM_API_KEY=xxx
POSTGRES_PASSWORD=xxx
```

```python
# settings.py - Comportement basé sur ENV_MODE
ENV_MODE = os.environ.get("ENV_MODE", "local")
DEBUG = ENV_MODE in ("local", "dev", "staging")
LOG_LEVEL = "DEBUG" if ENV_MODE != "prod" else "INFO"

# Ressources - Lecture directe, pas de logique
BUCKET = os.environ.get("GCS_BUCKET")  # Pas de if/else
DATASET = os.environ.get("BIGQUERY_GOLD_DATASET")  # Pas de if/else
```

**Avantages :**
- Meilleur des deux mondes
- `ENV_MODE` pour le comportement, variables pour les ressources
- Flexibilité pour les tests (staging avec données prod)
- Code propre sans logique de mapping
- Conforme aux bonnes pratiques

**Inconvénients :**
- Légèrement plus complexe à documenter
- Nécessite une convention claire

**Verdict :** ✅ **Recommandé - C'est l'approche standard en entreprise**

---

## Bonnes pratiques Data Engineering

### 1. The Twelve-Factor App (Facteur III : Configuration)

> "Store config in the environment"

La configuration qui varie entre environnements doit être stockée dans des variables d'environnement, **jamais dans le code**.

```python
# ❌ Mauvais
if ENV_MODE == "prod":
    BUCKET = "prod-bucket"

# ✅ Bon
BUCKET = os.environ["GCS_BUCKET"]
```

### 2. Principe de moindre surprise

Un développeur doit pouvoir comprendre la configuration d'un environnement en regardant **un seul fichier** (`.env`, `terraform.tfvars`, ou GitHub Secrets).

```bash
# ✅ Bon : tout est explicite dans .env.staging
GCS_BUCKET=jobmatch-staging-bronze-job-match-v0
BIGQUERY_SILVER_DATASET=staging_silver

# ❌ Mauvais : il faut lire le code pour savoir quel bucket
ENV_MODE=staging  # Et ensuite chercher dans le code...
```

### 3. Infrastructure as Code (IaC) cohérent

Les noms de ressources doivent être générés de manière cohérente entre Terraform et l'application.

```hcl
# terraform/variables.tf
variable "environment" {
  default = "prod"
}

# terraform/storage.tf
resource "google_storage_bucket" "bronze" {
  name = "jobmatch-${var.environment}-bronze-${var.project_id}"
}

# Output pour l'application
output "gcs_bucket" {
  value = google_storage_bucket.bronze.name
}
```

Le nom du bucket est **calculé** par Terraform et **passé** à l'application, pas l'inverse.

### 4. Fail fast

L'application doit échouer immédiatement si une variable requise est manquante.

```python
# ✅ Bon
def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

BUCKET = require_env("GCS_BUCKET")

# ❌ Mauvais
BUCKET = os.environ.get("GCS_BUCKET", "default-bucket")  # Silencieux
```

### 5. Séparation des secrets

Les secrets ne doivent **jamais** être dans le code ou les fichiers `.env` versionnés.

| Environnement | Stockage des secrets |
|---------------|---------------------|
| Local | `.env` (gitignored) |
| CI/CD | GitHub Secrets / Secret Manager |
| Production | Secret Manager / Vault |

### 6. Immutabilité des environnements

Chaque environnement doit avoir ses propres ressources, jamais de partage.

```
# ✅ Bon
staging_silver (dataset) → staging uniquement
gold (dataset) → prod uniquement

# ❌ Mauvais
silver (dataset) → partagé staging + prod  # Risque de corruption
```

### 7. Parité Dev/Prod

Les environnements doivent être aussi similaires que possible.

```bash
# ✅ Bon : même structure, noms différents
prod:    gs://jobmatch-bronze-job-match-v0/france_travail/offers/
staging: gs://jobmatch-staging-bronze-job-match-v0/france_travail/offers/

# ❌ Mauvais : structures différentes
prod:    gs://jobmatch-bronze/offers/
staging: gs://test-bucket/staging/data/offers/  # Structure différente
```

---

## Recommandation pour JobMatch

### Architecture cible

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GitHub Environments                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   staging    │  │  production  │  │     dev      │               │
│  │   secrets    │  │   secrets    │  │   secrets    │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
└─────────┼─────────────────┼─────────────────┼───────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (deploy.yml)                       │
│                                                                      │
│  Génère .env dynamiquement selon la branche :                       │
│  - main → production secrets                                         │
│  - staging → staging secrets                                         │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    .env (généré sur la VM)                          │
│                                                                      │
│  ENV_MODE=staging                                                    │
│  GCP_PROJECT_ID=job-match-v0                                        │
│  GCS_BUCKET=jobmatch-staging-bronze-job-match-v0                    │
│  BIGQUERY_SILVER_DATASET=staging_silver                             │
│  BIGQUERY_GOLD_DATASET=staging_gold                                 │
│  ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Services (docker-compose)                         │
│                                                                      │
│  ┌─────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │   GUI   │  │ cv-ingestion │  │ai-assistant │  │offre-ingestion│  │
│  │         │  │              │  │             │  │               │  │
│  │ Lit     │  │ Lit          │  │ Lit         │  │ Lit           │  │
│  │ BIGQUERY│  │ variables    │  │ variables   │  │ GCS_BUCKET    │  │
│  │ _GOLD.. │  │ d'env        │  │ d'env       │  │ BIGQUERY_*    │  │
│  └─────────┘  └──────────────┘  └─────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Variables à définir par environnement

| Variable | Local | Staging | Production |
|----------|-------|---------|------------|
| `ENV_MODE` | local | staging | prod |
| `DEBUG` | true | true | false |
| `GCP_PROJECT_ID` | job-match-v0 | job-match-v0 | job-match-v0 |
| `GCS_BUCKET` | - | jobmatch-staging-bronze-* | jobmatch-bronze-* |
| `BIGQUERY_SILVER_DATASET` | - | staging_silver | silver |
| `BIGQUERY_GOLD_DATASET` | - | staging_gold | gold |
| `USE_SQLITE_OFFERS` | true | false | false |

### Modifications de code requises

1. **offre-ingestion** : Remplacer `DATASET_ID = "jobmatch_silver"` par lecture de variable
2. **deploy.yml** : Ajouter toutes les variables GCP au `.env` généré
3. **GitHub** : Créer un environment `staging` avec ses secrets

---

## Comparaison avec les standards industrie

| Pratique | Netflix | Spotify | Airbnb | JobMatch (cible) |
|----------|---------|---------|--------|------------------|
| Config externalisée | ✅ | ✅ | ✅ | ✅ |
| Secrets dans Secret Manager | ✅ | ✅ | ✅ | ⚠️ GitHub Secrets |
| Infra as Code | ✅ Spinnaker | ✅ | ✅ Terraform | ✅ Terraform |
| Environnements isolés | ✅ | ✅ | ✅ | ✅ (à implémenter) |
| Feature flags | ✅ | ✅ | ✅ | ❌ (hors scope) |

---

## Conclusion

**Recommandation finale : Option C (Hybride)**

1. `ENV_MODE` pour le comportement applicatif (logs, debug, migrations)
2. Variables explicites pour toutes les ressources externes
3. GitHub Environments pour isoler les secrets par environnement
4. Terraform outputs pour générer les noms de ressources

Cette approche est :
- Conforme au 12-Factor App
- Standard en entreprise (Google, AWS, Netflix)
- Maintenable et testable
- Évolutive (ajout d'environnements facile)

---

## Gestion des secrets : Panorama complet

### 1. Fichiers `.env` (Basique)

```bash
# .env (gitignored)
POSTGRES_PASSWORD=supersecret
LLM_API_KEY=sk-xxx
```

| Avantage | Inconvénient |
|----------|--------------|
| Simple, universel | Aucun audit |
| Fonctionne partout | Pas de rotation |
| Pas de dépendance externe | Facile à fuiter |
| | Stocké en clair sur disque |

**Usage :** Dev local uniquement

---

### 2. Variables d'environnement système

```bash
export POSTGRES_PASSWORD=supersecret
# ou dans systemd, docker run -e, etc.
```

| Avantage | Inconvénient |
|----------|--------------|
| Standard Unix | Visible dans `ps`, `/proc` |
| Pas de fichier | Pas d'audit |
| Isolé par process | Pas de rotation |

**Usage :** Conteneurs, avec source sécurisée

---

### 3. GitHub Secrets (Actuel JobMatch)

```yaml
# deploy.yml
POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
```

| Avantage | Inconvénient |
|----------|--------------|
| Simple | Pas d'audit trail |
| Gratuit | Rotation manuelle |
| Intégré GitHub Actions | Vendor lock-in GitHub |
| | Pas accessible hors CI/CD |

**Usage :** CI/CD simple, petites équipes

---

### 4. GCP Secret Manager

```bash
# Créer un secret
echo -n "supersecret" | gcloud secrets create postgres-password --data-file=-

# Lire un secret
gcloud secrets versions access latest --secret="postgres-password"
```

```python
# Dans le code Python
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret = client.access_secret_version(name="projects/xxx/secrets/postgres-password/versions/latest")
password = secret.payload.data.decode("UTF-8")
```

| Avantage | Inconvénient |
|----------|--------------|
| Audit trail complet | Coût (~0.06$/secret/mois) |
| Rotation automatique possible | Dépendance GCP |
| IAM granulaire | Latence réseau |
| Versioning des secrets | Setup initial |
| Intégration native GCP | |

**Usage :** Production GCP, équipes moyennes/grandes

---

### 5. AWS Secrets Manager

```bash
# Créer
aws secretsmanager create-secret --name postgres-password --secret-string "supersecret"

# Lire
aws secretsmanager get-secret-value --secret-id postgres-password
```

| Avantage | Inconvénient |
|----------|--------------|
| Rotation automatique native | Coût (~0.40$/secret/mois) |
| Intégration RDS | Dépendance AWS |
| Audit CloudTrail | |

**Usage :** Production AWS

---

### 6. HashiCorp Vault

```bash
# Écrire
vault kv put secret/jobmatch postgres_password=supersecret

# Lire
vault kv get secret/jobmatch
```

| Avantage | Inconvénient |
|----------|--------------|
| Multi-cloud | Complexité opérationnelle |
| Dynamic secrets (génération à la volée) | Infrastructure à maintenir |
| Rotation automatique | Courbe d'apprentissage |
| Encryption as a Service | |
| Audit complet | |
| Open source (ou Enterprise) | |

**Usage :** Multi-cloud, grandes entreprises, besoins avancés

---

### 7. Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: jobmatch-secrets
type: Opaque
data:
  postgres-password: <BASE64_ENCODED_PASSWORD>  # base64 (PAS chiffré!)
```

| Avantage | Inconvénient |
|----------|--------------|
| Natif Kubernetes | Base64 ≠ chiffrement |
| Intégré aux pods | Stocké en clair dans etcd |
| | Nécessite K8s |

**Amélioration :** Combiner avec Sealed Secrets, External Secrets Operator, ou Vault

---

### 8. SOPS (Secrets OPerationS)

```bash
# Chiffrer un fichier avec GCP KMS
sops --encrypt --gcp-kms projects/xxx/locations/global/keyRings/xxx/cryptoKeys/xxx .env > .env.enc

# Déchiffrer
sops --decrypt .env.enc > .env
```

| Avantage | Inconvénient |
|----------|--------------|
| Fichiers chiffrés versionnables | Setup KMS requis |
| GitOps friendly | Pas d'audit centralisé |
| Multi-backend (GCP, AWS, PGP) | |
| Open source | |

**Usage :** GitOps, Infrastructure as Code

---

### 9. Doppler / 1Password Secrets Automation

```bash
# Doppler
doppler secrets download --no-file --format env > .env

# 1Password
op read "op://vault/item/field"
```

| Avantage | Inconvénient |
|----------|--------------|
| UI intuitive | Coût (SaaS) |
| Multi-environnement natif | Dépendance externe |
| Intégrations CI/CD | |
| Partage équipe facile | |

**Usage :** Startups, équipes non-ops

---

### Comparaison globale

| Solution | Sécurité | Audit | Rotation | Coût | Complexité |
|----------|----------|-------|----------|------|------------|
| `.env` fichier | ⭐ | ❌ | ❌ | Gratuit | ⭐ |
| GitHub Secrets | ⭐⭐⭐ | ⭐ | ❌ | Gratuit | ⭐ |
| GCP Secret Manager | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ~0.06$/secret | ⭐⭐ |
| AWS Secrets Manager | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~0.40$/secret | ⭐⭐ |
| HashiCorp Vault | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gratuit/Payant | ⭐⭐⭐⭐ |
| K8s Secrets | ⭐⭐ | ⭐ | ❌ | Gratuit | ⭐⭐ |
| SOPS | ⭐⭐⭐⭐ | ⭐⭐ | ❌ | Gratuit | ⭐⭐⭐ |
| Doppler/1Password | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | $$$ | ⭐ |

---

### Recommandation pour JobMatch

**Approche retenue : Lecture directe depuis Secret Manager (niveau "gros projet à risque")**

| Critère | Approche basique (.env avec secrets) | Approche sécurisée (Secret Manager direct) |
|---------|--------------------------------------|-------------------------------------------|
| Secrets sur disque VM | ✅ Oui (.env) | ❌ Non (mémoire uniquement) |
| Secrets dans CI/CD | ✅ Oui (deploy.yml) | ❌ Non |
| Audit d'accès | ❌ Non | ✅ Secret Manager logs |
| Rotation sans restart | ❌ Non | ✅ Oui (cache TTL) |
| Complexité | Faible | Moyenne |
| Coût | Gratuit | ~3€/mois |

---

### Architecture cible avec Secret Manager (lecture directe)

**Principes de sécurité :**
- **Secrets JAMAIS écrits sur disque** (ni dans .env, ni dans les logs)
- **Secrets JAMAIS dans le pipeline CI/CD**
- **Applications lisent DIRECTEMENT Secret Manager au démarrage**
- **Workload Identity** pour l'authentification (pas de credentials)

```
┌───────────────────────────────────────────────────────────────────────┐
│  1. deploy.yml - Config NON-SENSIBLE uniquement                       │
│     ───────────────────────────────────────────                       │
│     • ENV_MODE, GCP_PROJECT_ID                                        │
│     • GCS_BUCKET, BIGQUERY_*_DATASET (noms de ressources)            │
│     • Ports, URLs internes                                            │
│     • ⚠️ AUCUN secret (pas de passwords, API keys, etc.)             │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│  2. .env sur VM - Config SANS secrets                                 │
│     ─────────────────────────────────                                 │
│     ENV_MODE=prod                                                     │
│     GCP_PROJECT_ID=job-match-v0                                       │
│     GCS_BUCKET=jobmatch-bronze-job-match-v0                          │
│     BIGQUERY_GOLD_DATASET=gold                                       │
│     POSTGRES_HOST=db                                                  │
│     POSTGRES_USER=jobmatch                                            │
│     # ⚠️ PAS de POSTGRES_PASSWORD, LLM_API_KEY, DJANGO_SECRET_KEY    │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│  3. Application au démarrage                                          │
│     ─────────────────────────                                         │
│     • Lit config depuis .env (buckets, datasets, hosts)              │
│     • Lit SECRETS depuis GCP Secret Manager directement              │
│     • Auth via Workload Identity (VM service account)                │
│     • Secrets en mémoire uniquement, JAMAIS sur disque               │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│  GCP Secret Manager                                                   │
│  ───────────────────                                                  │
│  Naming convention: jobmatch-{env}-{secret-name}                     │
│                                                                       │
│  jobmatch-staging-postgres-password                                   │
│  jobmatch-staging-llm-api-key                                        │
│  jobmatch-staging-django-secret-key                                  │
│  jobmatch-staging-france-travail-api-key                             │
│                                                                       │
│  jobmatch-prod-postgres-password                                      │
│  jobmatch-prod-llm-api-key                                           │
│  jobmatch-prod-django-secret-key                                     │
│  jobmatch-prod-france-travail-api-key                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

### Implémentation : Module secrets partagé

```python
# app/shared/secrets.py
"""
Secure secrets management for JobMatch.

In local development: reads from environment variables (.env file)
In staging/prod: reads directly from GCP Secret Manager

SECURITY PRINCIPLES:
- Secrets are NEVER written to disk in staging/prod
- Secrets are NEVER passed through CI/CD pipeline
- Applications read secrets directly from Secret Manager at startup
- Authentication via Workload Identity (no credentials needed)
"""

import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Cache TTL for secrets (allows rotation without restart)
_secret_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def get_secret(secret_name: str, required: bool = True) -> Optional[str]:
    """
    Get secret from environment (local) or Secret Manager (staging/prod).

    Naming convention in Secret Manager:
    - jobmatch-{env}-{secret_name}
    - Example: POSTGRES_PASSWORD -> jobmatch-prod-postgres-password

    Args:
        secret_name: The secret name (e.g., "POSTGRES_PASSWORD", "LLM_API_KEY")
        required: If True, raises exception when secret not found

    Returns:
        The secret value, or None if not found and not required

    Raises:
        ValueError: If required secret is missing in local mode
        RuntimeError: If required secret cannot be fetched from Secret Manager
    """
    # 1. Check environment variable first (local dev + allows override)
    env_value = os.getenv(secret_name)
    if env_value:
        return env_value

    # 2. Determine environment
    env_mode = os.getenv("ENV_MODE", "local")

    if env_mode == "local":
        if required:
            raise ValueError(
                f"Missing required secret: {secret_name}. "
                f"Add it to your .env file for local development."
            )
        return None

    # 3. In staging/prod, read from GCP Secret Manager
    return _get_from_secret_manager(secret_name, env_mode, required)


def _get_from_secret_manager(
    secret_name: str,
    env_mode: str,
    required: bool
) -> Optional[str]:
    """Fetch secret from GCP Secret Manager with caching."""
    import time

    cache_key = f"{env_mode}:{secret_name}"

    # Check cache
    if cache_key in _secret_cache:
        value, timestamp = _secret_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return value

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT_ID", "job-match-v0")

        # Convert POSTGRES_PASSWORD -> postgres-password
        secret_key = secret_name.lower().replace("_", "-")
        name = f"projects/{project_id}/secrets/jobmatch-{env_mode}-{secret_key}/versions/latest"

        logger.debug(f"Fetching secret from Secret Manager: {name}")
        response = client.access_secret_version(name=name)
        value = response.payload.data.decode("UTF-8")

        # Cache the result
        _secret_cache[cache_key] = (value, time.time())

        return value

    except Exception as e:
        logger.error(f"Failed to get secret {secret_name} from Secret Manager: {e}")
        if required:
            raise RuntimeError(
                f"Failed to get required secret {secret_name} from Secret Manager: {e}"
            )
        return None


def clear_cache():
    """Clear the secret cache. Useful for testing or forcing refresh."""
    _secret_cache.clear()


# Convenience functions for common secrets
def get_postgres_password() -> str:
    return get_secret("POSTGRES_PASSWORD", required=True)


def get_llm_api_key() -> str:
    return get_secret("LLM_API_KEY", required=True)


def get_django_secret_key() -> str:
    return get_secret("DJANGO_SECRET_KEY", required=True)


def get_france_travail_api_key() -> str:
    return get_secret("FRANCE_TRAVAIL_API_KEY", required=True)
```

---

### Intégration dans les services

#### GUI (Django)

```python
# app/gui/config/settings.py
import os
from shared.secrets import get_secret

# --- Config non-sensible (depuis .env) ---
ENV_MODE = os.environ.get("ENV_MODE", "local")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "job-match-v0")
BIGQUERY_GOLD_DATASET = os.environ.get("BIGQUERY_GOLD_DATASET", "gold")

# --- Secrets (depuis Secret Manager en staging/prod) ---
SECRET_KEY = get_secret("DJANGO_SECRET_KEY")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "jobmatch"),
        "USER": os.environ.get("POSTGRES_USER", "jobmatch"),
        "PASSWORD": get_secret("POSTGRES_PASSWORD"),  # From Secret Manager
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
```

#### cv-ingestion / ai-assistant

```python
# app/cv-ingestion/config.py
import os
from shared.secrets import get_secret

# Config
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
LLM_TYPE = os.environ.get("LLM_TYPE", "openai")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4")

# Secrets
LLM_API_KEY = get_secret("LLM_API_KEY")
LLM_ENDPOINT = get_secret("LLM_ENDPOINT", required=False) or "https://api.openai.com/v1"
```

#### offre-ingestion

```python
# app/offre-ingestion/config.py
import os
from shared.secrets import get_secret

# Config
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "job-match-v0")
GCS_BUCKET = os.environ.get("GCS_BUCKET")
BIGQUERY_SILVER_DATASET = os.environ.get("BIGQUERY_SILVER_DATASET", "silver")

# Secrets
FRANCE_TRAVAIL_API_KEY = get_secret("FRANCE_TRAVAIL_API_KEY")
```

---

### CI/CD : Workflows séparés (Infrastructure vs Application)

**Principe :** Terraform et le déploiement applicatif sont découplés. L'infrastructure change rarement, l'application souvent.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  infra.yml                              deploy.yml                       │
│  ─────────                              ──────────                       │
│  Déclenché si:                          Déclenché si:                    │
│  • Push sur infra/terraform/**          • Push sur app/**                │
│  • Manuel (workflow_dispatch)           • Push docker-compose.yml        │
│                                         • Manuel                         │
│         │                                      │                         │
│         ▼                                      │                         │
│  ┌──────────────┐                             │                         │
│  │ terraform    │                             │                         │
│  │ plan + apply │                             │                         │
│  └──────┬───────┘                             │                         │
│         │                                      │                         │
│         ▼                                      ▼                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │            GitHub Variables (stockage des outputs)            │       │
│  │                                                               │       │
│  │  GCS_BUCKET_STAGING    = jobmatch-staging-bronze-xxx         │       │
│  │  GCS_BUCKET_PROD       = jobmatch-bronze-xxx                 │       │
│  │  BQ_SILVER_STAGING     = staging_silver                      │       │
│  │  BQ_SILVER_PROD        = silver                              │       │
│  │  BQ_GOLD_STAGING       = staging_gold                        │       │
│  │  BQ_GOLD_PROD          = gold                                │       │
│  │  VM_NAME_STAGING       = jobmatch-staging-vm                 │       │
│  │  VM_NAME_PROD          = jobmatch-prod-vm                    │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### infra.yml - Workflow Infrastructure

```yaml
# .github/workflows/infra.yml
name: Infrastructure (Terraform)

on:
  push:
    branches: [main, staging]
    paths:
      - 'infra/terraform/**'
  pull_request:
    branches: [main, staging]
    paths:
      - 'infra/terraform/**'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - prod
      action:
        description: 'Action to perform'
        required: true
        type: choice
        options:
          - plan
          - apply

jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      pull-requests: write  # Pour commenter les PRs avec le plan

    steps:
      - uses: actions/checkout@v4

      # Auth GCP via Workload Identity
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      # Determine environment
      - id: env
        run: |
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            echo "name=${{ inputs.environment }}" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "name=prod" >> $GITHUB_OUTPUT
          else
            echo "name=staging" >> $GITHUB_OUTPUT
          fi

      # Terraform Init
      - name: Terraform Init
        working-directory: infra/terraform/environments/${{ steps.env.outputs.name }}
        run: |
          terraform init \
            -backend-config="bucket=jobmatch-terraform-state" \
            -backend-config="prefix=${{ steps.env.outputs.name }}"

      # Terraform Plan
      - name: Terraform Plan
        id: plan
        working-directory: infra/terraform/environments/${{ steps.env.outputs.name }}
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      # Comment PR with plan (only on PRs)
      - name: Comment PR with Plan
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const plan = `${{ steps.plan.outputs.stdout }}`;
            const truncated = plan.length > 60000 ? plan.substring(0, 60000) + '\n\n... (truncated)' : plan;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `### Terraform Plan for \`${{ steps.env.outputs.name }}\`\n\n\`\`\`terraform\n${truncated}\n\`\`\``
            });

      # Terraform Apply (only on push to main/staging, not on PRs)
      - name: Terraform Apply
        if: |
          (github.event_name == 'push') ||
          (github.event_name == 'workflow_dispatch' && inputs.action == 'apply')
        working-directory: infra/terraform/environments/${{ steps.env.outputs.name }}
        run: terraform apply -auto-approve tfplan

      # Update GitHub Variables with Terraform outputs
      - name: Update GitHub Variables
        if: |
          (github.event_name == 'push') ||
          (github.event_name == 'workflow_dispatch' && inputs.action == 'apply')
        working-directory: infra/terraform/environments/${{ steps.env.outputs.name }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          ENV="${{ steps.env.outputs.name }}"
          ENV_UPPER=$(echo "$ENV" | tr '[:lower:]' '[:upper:]')

          # Get Terraform outputs
          GCS_BUCKET=$(terraform output -raw gcs_bucket 2>/dev/null || echo "")
          BQ_SILVER=$(terraform output -raw bigquery_silver_dataset 2>/dev/null || echo "")
          BQ_GOLD=$(terraform output -raw bigquery_gold_dataset 2>/dev/null || echo "")
          VM_NAME=$(terraform output -raw vm_name 2>/dev/null || echo "")

          # Update GitHub repository variables
          if [[ -n "$GCS_BUCKET" ]]; then
            gh variable set "GCS_BUCKET_${ENV_UPPER}" --body "$GCS_BUCKET"
            echo "✅ Updated GCS_BUCKET_${ENV_UPPER}=$GCS_BUCKET"
          fi

          if [[ -n "$BQ_SILVER" ]]; then
            gh variable set "BQ_SILVER_${ENV_UPPER}" --body "$BQ_SILVER"
            echo "✅ Updated BQ_SILVER_${ENV_UPPER}=$BQ_SILVER"
          fi

          if [[ -n "$BQ_GOLD" ]]; then
            gh variable set "BQ_GOLD_${ENV_UPPER}" --body "$BQ_GOLD"
            echo "✅ Updated BQ_GOLD_${ENV_UPPER}=$BQ_GOLD"
          fi

          if [[ -n "$VM_NAME" ]]; then
            gh variable set "VM_NAME_${ENV_UPPER}" --body "$VM_NAME"
            echo "✅ Updated VM_NAME_${ENV_UPPER}=$VM_NAME"
          fi

          echo "🎉 GitHub Variables updated for $ENV environment"
```

---

### deploy.yml - Workflow Application (sans Terraform)

```yaml
# .github/workflows/deploy.yml
name: Deploy Application

on:
  push:
    branches: [main, staging]
    paths:
      - 'app/**'
      - 'docker-compose.yml'
      - 'requirements*.txt'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - prod

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      # Auth GCP via Workload Identity
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      # Determine environment and get variables
      - id: config
        run: |
          # Determine environment from branch or input
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            ENV="${{ inputs.environment }}"
          elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            ENV="prod"
          else
            ENV="staging"
          fi

          echo "env=$ENV" >> $GITHUB_OUTPUT

          # Get environment-specific variables from GitHub Variables
          if [[ "$ENV" == "prod" ]]; then
            echo "gcs_bucket=${{ vars.GCS_BUCKET_PROD }}" >> $GITHUB_OUTPUT
            echo "bq_silver=${{ vars.BQ_SILVER_PROD }}" >> $GITHUB_OUTPUT
            echo "bq_gold=${{ vars.BQ_GOLD_PROD }}" >> $GITHUB_OUTPUT
            echo "vm_name=${{ vars.VM_NAME_PROD }}" >> $GITHUB_OUTPUT
            echo "debug=false" >> $GITHUB_OUTPUT
          else
            echo "gcs_bucket=${{ vars.GCS_BUCKET_STAGING }}" >> $GITHUB_OUTPUT
            echo "bq_silver=${{ vars.BQ_SILVER_STAGING }}" >> $GITHUB_OUTPUT
            echo "bq_gold=${{ vars.BQ_GOLD_STAGING }}" >> $GITHUB_OUTPUT
            echo "vm_name=${{ vars.VM_NAME_STAGING }}" >> $GITHUB_OUTPUT
            echo "debug=true" >> $GITHUB_OUTPUT
          fi

      # Validate that infrastructure exists
      - name: Validate Infrastructure
        run: |
          if [[ -z "${{ steps.config.outputs.vm_name }}" ]]; then
            echo "❌ ERROR: VM_NAME not set for ${{ steps.config.outputs.env }}"
            echo "Run the Infrastructure workflow first (infra.yml)"
            exit 1
          fi
          echo "✅ Infrastructure validated for ${{ steps.config.outputs.env }}"

      # Generate .env WITHOUT secrets
      - name: Generate config file
        run: |
          cat > /tmp/.env << EOF
          # ============================================
          # JobMatch ${{ steps.config.outputs.env }} Configuration
          # Generated by deploy.yml on $(date -u +"%Y-%m-%d %H:%M:%S UTC")
          # DO NOT EDIT - Secrets are read from GCP Secret Manager
          # ============================================

          ENV_MODE=${{ steps.config.outputs.env }}
          DEBUG=${{ steps.config.outputs.debug }}

          # GCP Resources (from Terraform via GitHub Variables)
          GCP_PROJECT_ID=${{ vars.GCP_PROJECT_ID }}
          GCS_BUCKET=${{ steps.config.outputs.gcs_bucket }}
          BIGQUERY_SILVER_DATASET=${{ steps.config.outputs.bq_silver }}
          BIGQUERY_GOLD_DATASET=${{ steps.config.outputs.bq_gold }}

          # Database (password from Secret Manager at runtime)
          POSTGRES_HOST=db
          POSTGRES_PORT=5432
          POSTGRES_USER=jobmatch
          POSTGRES_DB=jobmatch

          # Service URLs (internal Docker network)
          CV_INGESTION_URL=http://cv-ingestion:8081
          AI_ASSISTANT_URL=http://ai-assistant:8084
          MATCHING_URL=http://matching:8086

          # Feature flags
          USE_SQLITE_OFFERS=false
          USE_MOCK_MATCHING=false

          # LLM Config (API key from Secret Manager at runtime)
          LLM_TYPE=openai
          LLM_MODEL=gpt-4
          LLM_MAX_TOKENS=4096

          # Ports
          GUI_PORT=8080
          CV_INGESTION_PORT=8081
          AI_ASSISTANT_PORT=8084
          MATCHING_PORT=8086
          DB_PORT=5432
          REDIS_PORT=6379
          EOF

          echo "✅ Config file generated for ${{ steps.config.outputs.env }}"

      # Deploy to VM
      - name: Deploy to VM
        run: |
          VM="${{ steps.config.outputs.vm_name }}"
          ZONE="${{ vars.GCP_ZONE }}"

          echo "🚀 Deploying to $VM in $ZONE..."

          # Copy config (no secrets!)
          gcloud compute scp /tmp/.env "$VM:/opt/jobmatch/.env" --zone="$ZONE"

          # Pull latest code and restart services
          gcloud compute ssh "$VM" --zone="$ZONE" --command="
            cd /opt/jobmatch &&
            git fetch origin &&
            git checkout ${{ github.ref_name }} &&
            git pull origin ${{ github.ref_name }} &&
            docker-compose pull &&
            docker-compose up -d --remove-orphans
          "

          echo "✅ Deployment complete!"

      # Health check
      - name: Health Check
        run: |
          VM="${{ steps.config.outputs.vm_name }}"
          ZONE="${{ vars.GCP_ZONE }}"

          echo "🏥 Running health check..."

          # Wait for services to start
          sleep 30

          # Check if GUI is responding
          gcloud compute ssh "$VM" --zone="$ZONE" --command="
            curl -sf http://localhost:8080/health/ || echo 'Health check failed'
          " || echo "⚠️ Health check inconclusive"
```

---

### Résumé : Variables GitHub à configurer

```bash
# Variables statiques (à configurer une fois)
gh variable set GCP_PROJECT_ID --body "job-match-v0"
gh variable set GCP_ZONE --body "europe-west1-b"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "projects/xxx/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
gh variable set GCP_SERVICE_ACCOUNT --body "github-actions@job-match-v0.iam.gserviceaccount.com"

# Variables dynamiques (mises à jour par infra.yml après terraform apply)
# GCS_BUCKET_STAGING, GCS_BUCKET_PROD
# BQ_SILVER_STAGING, BQ_SILVER_PROD
# BQ_GOLD_STAGING, BQ_GOLD_PROD
# VM_NAME_STAGING, VM_NAME_PROD
```

---

## Fichiers .env : Structure recommandée

### Ce qu'il faut avoir dans le repo

```
repo/
├── .env.example              # Template complet (versionné, SANS secrets)
├── .env                      # gitignored - fichier actif local
├── environments/
│   ├── staging.env.example   # Valeurs staging SANS secrets (versionné)
│   └── production.env.example # Valeurs prod SANS secrets (versionné)
```

### .env.example (versionné)

```bash
# ============================================
# JobMatch Configuration Template
# ============================================
# Copy to .env and fill in the values
# For staging/prod, values come from Terraform + Secret Manager

# --- Environment ---
ENV_MODE=local  # local | staging | prod

# --- Ports (defaults work for all envs) ---
GUI_PORT=8085
CV_INGESTION_PORT=8081
AI_ASSISTANT_PORT=8084
MATCHING_PORT=8086
DB_PORT=5433
REDIS_PORT=6379

# --- Database ---
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=jobmatch
POSTGRES_PASSWORD=           # ⚠️ Required - Set manually or from Secret Manager
POSTGRES_DB=jobmatch

# --- GCP Resources (staging/prod only) ---
GCP_PROJECT_ID=job-match-v0
GCS_BUCKET=                  # ⚠️ From Terraform output: terraform output -raw gcs_bucket
BIGQUERY_SILVER_DATASET=     # ⚠️ From Terraform output
BIGQUERY_GOLD_DATASET=       # ⚠️ From Terraform output

# --- Feature Flags ---
USE_SQLITE_OFFERS=true       # true for local, false for staging/prod
USE_MOCK_MATCHING=true       # true for local, false for staging/prod

# --- LLM Configuration ---
LLM_TYPE=openai
LLM_ENDPOINT=                # ⚠️ Required
LLM_API_KEY=                 # ⚠️ Required - Set manually or from Secret Manager
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=4096

# --- Django (GUI only) ---
DJANGO_SECRET_KEY=           # ⚠️ Required - Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=true
```

### environments/staging.env.example (versionné)

```bash
# ============================================
# JobMatch Staging Environment
# ============================================
# These values are for reference only.
# In CI/CD, they come from Terraform outputs and Secret Manager.

ENV_MODE=staging
DEBUG=true

# --- GCP Resources (from Terraform) ---
GCP_PROJECT_ID=job-match-v0
GCS_BUCKET=jobmatch-staging-bronze-job-match-v0
BIGQUERY_SILVER_DATASET=staging_silver
BIGQUERY_GOLD_DATASET=staging_gold

# --- Feature Flags ---
USE_SQLITE_OFFERS=false
USE_MOCK_MATCHING=false

# --- Secrets (from Secret Manager) ---
# POSTGRES_PASSWORD  → gcloud secrets versions access latest --secret="jobmatch-staging-postgres-password"
# LLM_API_KEY        → gcloud secrets versions access latest --secret="jobmatch-staging-llm-api-key"
# DJANGO_SECRET_KEY  → gcloud secrets versions access latest --secret="jobmatch-staging-django-secret-key"
```

### environments/production.env.example (versionné)

```bash
# ============================================
# JobMatch Production Environment
# ============================================

ENV_MODE=prod
DEBUG=false

# --- GCP Resources (from Terraform) ---
GCP_PROJECT_ID=job-match-v0
GCS_BUCKET=jobmatch-bronze-job-match-v0
BIGQUERY_SILVER_DATASET=silver
BIGQUERY_GOLD_DATASET=gold

# --- Feature Flags ---
USE_SQLITE_OFFERS=false
USE_MOCK_MATCHING=false

# --- Secrets (from Secret Manager) ---
# Same pattern as staging, with "prod" prefix
```

---

## Workflow par environnement

### Développeur local

```bash
# 1. Copier le template
cp .env.example .env

# 2. Remplir les secrets manuellement
vim .env  # Ajouter POSTGRES_PASSWORD, LLM_API_KEY, etc.

# 3. Lancer
docker-compose up -d
```

### CI/CD (staging ou prod)

```yaml
# deploy.yml - Simplifié
jobs:
  deploy:
    steps:
      # 1. Auth GCP (Workload Identity - pas de secrets)
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/.../providers/github-provider

      # 2. Déterminer l'environnement
      - id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "name=prod" >> $GITHUB_OUTPUT
          else
            echo "name=staging" >> $GITHUB_OUTPUT
          fi

      # 3. Récupérer config Terraform + secrets
      - name: Build .env
        run: |
          ENV=${{ steps.env.outputs.name }}

          # Terraform outputs
          cd infra/terraform/environments/$ENV
          terraform init
          GCS_BUCKET=$(terraform output -raw gcs_bucket)
          BQ_SILVER=$(terraform output -raw bigquery_silver_dataset)
          BQ_GOLD=$(terraform output -raw bigquery_gold_dataset)

          # Secret Manager
          POSTGRES_PWD=$(gcloud secrets versions access latest --secret="jobmatch-${ENV}-postgres-password")
          LLM_KEY=$(gcloud secrets versions access latest --secret="jobmatch-${ENV}-llm-api-key")
          DJANGO_KEY=$(gcloud secrets versions access latest --secret="jobmatch-${ENV}-django-secret-key")

          # Generate .env
          cat > /tmp/.env << EOF
          ENV_MODE=$ENV
          GCS_BUCKET=$GCS_BUCKET
          BIGQUERY_SILVER_DATASET=$BQ_SILVER
          BIGQUERY_GOLD_DATASET=$BQ_GOLD
          POSTGRES_PASSWORD=$POSTGRES_PWD
          LLM_API_KEY=$LLM_KEY
          DJANGO_SECRET_KEY=$DJANGO_KEY
          # ... autres variables
          EOF

      # 4. Deploy sur la VM
      - name: Deploy
        run: |
          gcloud compute scp /tmp/.env $VM:/opt/jobmatch/.env
          gcloud compute ssh $VM --command="cd /opt/jobmatch && docker-compose up -d"
```

---

## Checklist d'implémentation

### Phase 1 : GCP Secret Manager

```bash
# 1. Activer l'API
gcloud services enable secretmanager.googleapis.com

# 2. Créer les secrets staging
echo -n "votre_password" | gcloud secrets create jobmatch-staging-postgres-password --data-file=-
echo -n "sk-xxx" | gcloud secrets create jobmatch-staging-llm-api-key --data-file=-
echo -n "django-secret-xxx" | gcloud secrets create jobmatch-staging-django-secret-key --data-file=-
echo -n "ft-api-key" | gcloud secrets create jobmatch-staging-france-travail-api-key --data-file=-

# 3. Créer les secrets prod (même pattern)
echo -n "votre_password_prod" | gcloud secrets create jobmatch-prod-postgres-password --data-file=-
# ... etc

# 4. Donner accès au service account de la VM
gcloud secrets add-iam-policy-binding jobmatch-staging-postgres-password \
  --member="serviceAccount:VM_SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

- [ ] Activer l'API Secret Manager
- [ ] Créer les 4 secrets pour staging : `jobmatch-staging-{postgres-password, llm-api-key, django-secret-key, france-travail-api-key}`
- [ ] Créer les 4 secrets pour prod : `jobmatch-prod-*`
- [ ] Donner accès `secretmanager.secretAccessor` au service account de la VM staging
- [ ] Donner accès `secretmanager.secretAccessor` au service account de la VM prod
- [ ] Tester l'accès : `gcloud secrets versions access latest --secret="jobmatch-staging-postgres-password"`

### Phase 2 : Module secrets partagé

- [ ] Créer `app/shared/secrets.py` (code fourni dans la documentation)
- [ ] Ajouter `google-cloud-secret-manager` aux requirements.txt de chaque service
- [ ] Tester en local avec variables d'environnement

### Phase 3 : Intégration dans les services

- [ ] **GUI** : Modifier `config/settings.py` pour utiliser `get_secret()` pour SECRET_KEY et POSTGRES_PASSWORD
- [ ] **cv-ingestion** : Modifier config pour utiliser `get_secret("LLM_API_KEY")`
- [ ] **ai-assistant** : Modifier config pour utiliser `get_secret("LLM_API_KEY")`
- [ ] **offre-ingestion** : Modifier config pour utiliser `get_secret("FRANCE_TRAVAIL_API_KEY")` + lire `BIGQUERY_SILVER_DATASET` depuis env
- [ ] **matching** : Vérifier si des secrets sont nécessaires

### Phase 4 : Terraform

- [ ] Restructurer en `infra/terraform/environments/staging/` et `infra/terraform/environments/prod/`
- [ ] Ajouter les outputs nécessaires (bucket names, dataset IDs)
- [ ] Créer les ressources staging (VM, buckets, datasets)
- [ ] Configurer les service accounts des VMs avec accès Secret Manager

### Phase 5 : CI/CD

- [ ] Modifier `deploy.yml` pour générer .env SANS secrets
- [ ] Ajouter la logique de détection d'environnement (branche → env)
- [ ] Supprimer toute référence aux secrets dans le workflow
- [ ] Tester le déploiement staging

### Phase 6 : Documentation et .env

- [ ] Créer `.env.example` complet (sans secrets, avec commentaires)
- [ ] Créer `environments/staging.env.example`
- [ ] Créer `environments/production.env.example`
- [ ] Mettre à jour le README avec les nouvelles instructions
- [ ] Documenter la procédure d'ajout d'un nouveau secret

### Phase 7 : Tests et validation

- [ ] Tester le démarrage des services en staging avec Secret Manager
- [ ] Vérifier les logs d'audit dans GCP Console > Secret Manager
- [ ] Tester la rotation d'un secret (modifier dans Secret Manager, vérifier que l'app récupère la nouvelle valeur après TTL)
- [ ] Valider que les secrets ne sont PAS dans les logs docker

---

## Références

- [The Twelve-Factor App](https://12factor.net/config)
- [Google Cloud Best Practices for Enterprise Organizations](https://cloud.google.com/docs/enterprise/best-practices-for-enterprise-organizations)
- [Terraform Workspaces vs Directory Structure](https://developer.hashicorp.com/terraform/language/state/workspaces)
- [GCP Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
