# Pipeline d'Ingestion des Offres France Travail

## Présentation

Cette partie du projet extrait automatiquement les offres d'emploi depuis l'API France Travail et les structure dans des formats exploitables (CSV et SQLite).

**Architecture** : Bronze Layer (JSON brut) → Silver Layer (données structurées)

## Installation

### 1. Prérequis

- Python 3.8+
- Compte France Travail avec identifiants API (CLIENT_ID et CLIENT_SECRET)

### 2. Dépendances

```bash
pip install -r requirements.txt
```

### 3. Configuration

Créez un fichier `.env` à la racine du projet :

```env
FT_CLIENT_ID=votre_client_id
FT_CLIENT_SECRET=votre_client_secret
FT_SCOPE=api_offresdemploiv2 o2dsoffre
FT_OAUTH_URL=https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire
FT_API_URL_BASE=https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
FT_ROMECODES_PATH=src/data_persist/rome_codes.txt
FT_LOGS_XLSX=logs.xlsx
```

## Utilisation

### Extraction des Offres (Bronze Layer)

```bash
# Offres de la veille (par défaut)
python src/fetch_offers_with_pagination.py

# Offres d'une date spécifique
python src/fetch_offers_with_pagination.py 2025-12-23
```

**Sortie** : Fichier JSON dans `data/offer_YYYY-MM-DD.json`

**Note** : Le token OAuth2 est généré automatiquement par le script et mis en cache.

### Transformation des Données (Silver Layer)

#### Option A : Export CSV (13 fichiers)

```bash
python src/transform_offers_to_csv_silver.py 2025-12-23
```

**Sortie** : 13 fichiers CSV dans `data/silver/`

#### Option B : Base de données SQLite

```bash
python src/transform_offers_to_db_silver.py 2025-12-23
```

**Sortie** : Base de données `data/silver/offers.db`

### Vérification de la Base de Données

```bash
python src/verify_db.py
```

Affiche le nombre de lignes par table et des exemples de données.

## Documentation

- **[PIPELINE.md](PIPELINE.md)** : Architecture détaillée du pipeline (Bronze → Silver)
- **[GUIDE_REQUETES.md](GUIDE_REQUETES.md)** : Guide d'accès à la base de données SQLite

## Structure des Données

Le pipeline génère **13 tables relationnelles** :

- **Table principale** : `offers` (27 colonnes : id, intitulé, description, type de contrat, etc.)
- **12 tables secondaires** : lieu de travail, entreprise, salaire, compétences, formations, permis, langues, etc.

Toutes les tables secondaires sont reliées à `offers` via `offer_id`.

## Logs et Monitoring

Le fichier `logs.xlsx` enregistre chaque requête API :
- Timestamp
- Code ROME
- Status HTTP
- Nombre d'offres récupérées

## Support

Pour plus de détails, consultez les fichiers de documentation listés ci-dessus.
