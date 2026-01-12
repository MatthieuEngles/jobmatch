# Pipeline d'Ingestion des Offres France Travail

## 🎯 Vue d'ensemble

Pipeline automatisé d'ingestion des offres d'emploi depuis l'API France Travail vers Google Cloud Platform (GCS + BigQuery) avec génération d'embeddings vectoriels.

## 🏗️ Architecture Médaillon

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  France Travail │────▶│    Bronze    │────▶│    Silver    │────▶│     Gold     │
│      API        │     │     GCS      │     │   BigQuery   │     │  BigQuery +  │
│                 │     │  (JSON brut) │     │  (Structuré) │     │  Embeddings  │
└─────────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## 1️⃣ Bronze Layer : Extraction vers GCS

### Script
`src/pipelines/fetch_offers_to_gcs.py`

### Objectif
Extraire les offres d'emploi depuis l'API France Travail et les stocker dans Google Cloud Storage.

### Processus
1. **Authentification OAuth2** avec cache token (30 minutes)
2. **Parcours des codes ROME** : 1585 métiers référencés
3. **Pagination automatique** : 150 offres par requête
4. **Throttling** : respect intervalle 0.11s entre requêtes
5. **Gestion erreurs** : retry automatique sur 401/429
6. **Upload GCS** : stockage JSON brut partitionné par date

### Exécution

```bash
# Docker (recommandé)
docker compose run --rm offre-ingestion fetch 2025-12-31

# Par défaut : données de J-1
docker compose run --rm offre-ingestion fetch
```

### Configuration

Fichier `.env` :
```env
# GCP
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name

# France Travail API
FT_CLIENT_ID=your_client_id
FT_CLIENT_SECRET=your_client_secret
FT_SCOPE=the_list_of_scopes
FT_OAUTH_URL=the_oauth_url
FT_API_URL_BASE=the_api_base_url
FT_ROMECODES_PATH=/path/to/romecodes.txt
```

### Sortie

**GCS** : `gs://france-travail-bronze-offers/france_travail/offers/ingestion_date=YYYY-MM-DD/offers_YYYY-MM-DD.json`

Structure JSON :
```json
{
  "resultats": [
    {
      "id": "201VPGR",
      "intitule": "Développeur Python H/F",
      "description": "...",
      "dateCreation": "2025-12-31T10:30:00Z",
      "lieuTravail": {...},
      "entreprise": {...},
      "competences": [...]
    }
  ]
}
```

---

## 2️⃣ Silver Layer : Transformation BigQuery

### Script
`src/pipelines/transform_offers_to_bigquery_silver.py`

### Objectif
Transformer les fichiers JSON bruts depuis GCS en tables BigQuery structurées et normalisées.

### Processus
1. **Lecture depuis GCS** : chargement du JSON brut de la date cible
2. **Normalisation** : structuration en 13 tables relationnelles
3. **Insertion BigQuery** : chargement batch avec gestion des doublons
4. **Indexation** : création d'index sur `offer_id` pour performances

### Exécution

```bash
# Docker (recommandé)
docker compose run --rm offre-ingestion silver 2025-12-31

# Par défaut : données de J-1
docker compose run --rm offre-ingestion silver
```

### Sortie

**BigQuery Dataset** : `silver_dataset`

**Tables créées** (13 tables) :
- `offers` (table principale, 27 colonnes)
- `offers_lieu_travail`
- `offers_entreprise`
- `offers_salaire`
- `offers_salaire_complements`
- `offers_competences`
- `offers_qualites_professionnelles`
- `offers_formations`
- `offers_permis`
- `offers_langues`
- `offers_contact`
- `offers_origine`
- `offers_contexte_travail_horaires`

---

## 3️⃣ Gold Layer : Embeddings Vectoriels

### Script
`src/pipelines/transform_offers_to_bigquery_gold.py`

### Objectif
Générer des embeddings vectoriels (sentence-transformers) pour les champs `intitule` et `description` afin de permettre la recherche sémantique.

### Processus
1. **Lecture BigQuery Silver** : extraction des offres de la date cible
2. **Génération embeddings** :
   - Modèle : `sentence-transformers/all-MiniLM-L6-v2`
   - Dimension : 384
   - Batch processing pour optimisation
3. **Stockage BigQuery Gold** :
   - Table `offers` (données métier)
   - Table `offers_intitule_embeddings` (vecteurs titres)
   - Table `offers_description_embeddings` (vecteurs descriptions)

### Exécution

```bash
# Docker (recommandé)
docker compose run --rm offre-ingestion gold 2025-12-31

# Par défaut : données de J-1
docker compose run --rm offre-ingestion gold
```

### Sortie

**BigQuery Dataset** : `gold_dataset`

**Tables créées** :
- `offers` : Données métier
- `offers_intitule_embeddings` : Vecteurs 384D des titres
- `offers_description_embeddings` : Vecteurs 384D des descriptions

**Index vectoriels** : Créés automatiquement pour recherche sémantique rapide

---

## 📋 Structure des Données

### Table principale : `offers` (Silver & Gold)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | STRING | Identifiant unique (clé primaire) |
| `intitule` | STRING | Titre du poste |
| `description` | STRING | Description complète |
| `romeCode` | STRING | Code ROME du métier |
| `romeLibelle` | STRING | Libellé du métier |
| `typeContrat` | STRING | CDI, CDD, MIS, etc. |
| `experienceExige` | STRING | D=Débutant, E=Expérimenté, S=Souhaité |
| `dateCreation` | TIMESTAMP | Date de création |
| `dateActualisation` | TIMESTAMP | Dernière mise à jour |
| `nombrePostes` | INTEGER | Nombre de postes |
| `accessibleTH` | BOOLEAN | Accessible handicap |
| ... | ... | (27 colonnes au total) |

### Tables secondaires (reliées par `offer_id`)

Toutes les tables ont une clé étrangère `offer_id` pointant vers `offers.id`.

---

## ⚡ Performances

- **Bronze** : ~30-60 secondes pour 1584 codes ROME (selon volume)
- **Silver** : ~10-20 secondes pour transformation et insertion
- **Gold** : ~20-60 min pour génération embeddings (dépend du nombre d'offres)

---

## 🛠️ Maintenance

### Scripts de setup

```bash
# Créer les schémas BigQuery
python scripts/setup/create_bigquery_silver_schema.py
python scripts/setup/create_bigquery_gold_schema.py

# Créer les index vectoriels
python scripts/setup/create_bigquery_gold_vector_indexes.py
```

### Scripts utilitaires

```bash
# Compter les offres dans GCS
python scripts/utils/count_total_offers_in_gcs.py

# Lire les offres depuis GCS
python scripts/utils/read_offers_from_gcs.py 2025-12-31
```

---

## Notes Importantes

### Filtres de date

L'API France Travail retourne les offres créées entre `minCreationDate` et `maxCreationDate`.
Par défaut, le script récupère les offres créées le jour J-1 (24h).

---

## Support

Pour toute question sur le pipeline, consulter :
- `README.md` dans ce répertoire
- `GUIDE_REQUETES.md` pour l'utilisation de la base de données
- Les scripts eux-mêmes (bien documentés)
