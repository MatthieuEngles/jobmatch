# Guide d'Accès aux Données BigQuery

## 📊 Base de Données

- **Type** : Google BigQuery
- **Datasets** :
  - `silver_dataset` : Données structurées
  - `gold_dataset` : Données + embeddings vectoriels
- **Source** : Offres France Travail via pipeline d'ingestion

---

## 🔧 Configuration

### Prérequis

```bash
pip install google-cloud-bigquery pandas
```

### Credentials GCP

Fichier `.env` :
```env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCP_PROJECT_ID=your-project-id
BIGQUERY_DATASET_SILVER=silver_dataset
BIGQUERY_DATASET_GOLD=gold_dataset
```

### Scripts de Création

```bash
# Créer les schémas Silver et Gold
python scripts/setup/create_bigquery_silver_schema.py
python scripts/setup/create_bigquery_gold_schema.py

# Créer les index vectoriels (Gold)
python scripts/setup/create_bigquery_gold_vector_indexes.py
```

---

## Structure de la Base

### Table Principale : `offers`

Contient **toutes les informations principales** de chaque offre (27 colonnes).

**Colonnes principales** :
- `id` (STRING, PRIMARY KEY) : Identifiant unique de l'offre
- `intitule` : Titre du poste
- `description` : Description complète de l'offre
- `romeCode` / `romeLibelle` : Code et libellé du métier
- `typeContrat` / `typeContratLibelle` : Type de contrat (CDI, CDD, MIS, etc.)
- `experienceExige` / `experienceLibelle` : Expérience requise (D=Débutant, E=Expérimenté, S=Souhaité)
- `dateCreation` / `dateActualisation` : Dates de publication et mise à jour
- `nombrePostes` : Nombre de postes à pourvoir
- `qualificationCode` / `qualificationLibelle` : Niveau de qualification
- `codeNAF` / `secteurActivite` / `secteurActiviteLibelle` : Secteur d'activité
- `accessibleTH` / `entrepriseAdaptee` : Indicateurs handicap

### Tables Secondaires (reliées par `offer_id`)

| Table | Contenu | Cardinalité |
|-------|---------|-------------|
| `offers_lieu_travail` | Localisation (libellé, latitude, longitude, code postal, commune) | 1-1 |
| `offers_entreprise` | Nom de l'entreprise et statut | 1-1 |
| `offers_salaire` | Informations salariales | 0-1 |
| `offers_salaire_complements` | Avantages (primes, intéressement, etc.) | 0-N |
| `offers_competences` | Compétences requises avec code et niveau | 0-N |
| `offers_qualites_professionnelles` | Qualités professionnelles | 0-N |
| `offers_formations` | Formations requises | 0-N |
| `offers_permis` | Permis de conduire requis | 0-N |
| `offers_langues` | Langues requises | 0-N |
| `offers_contact` | Coordonnées pour postuler | 0-1 |
| `offers_origine` | Source de l'offre | 0-1 |
| `offers_contexte_travail_horaires` | Horaires de travail | 0-N |

---

## 💻 Accès aux Données

### Option 1 : Python avec google-cloud-bigquery

```python
from google.cloud import bigquery
import os

# Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./credentials/gcp-service-account-key.json"
project_id = "your-project-id"

# Client BigQuery
client = bigquery.Client(project=project_id)

# Requête simple
query = """
    SELECT id, intitule, typeContrat, romeCode
    FROM `your-project.silver_dataset.offers`
    LIMIT 10
"""

results = client.query(query).result()
for row in results:
    print(f"{row.id}: {row.intitule} [{row.typeContrat}]")
```

### Option 2 : Python avec Pandas

```python
import pandas as pd
from google.cloud import bigquery

client = bigquery.Client(project="your-project-id")

# Charger la table offers
df = pd.read_gbq("SELECT * FROM silver_dataset.offers LIMIT 100", project_id="your-project-id")
print(df.head())

# Requête personnalisée avec jointure
query = """
    SELECT o.intitule, l.libelle as ville, c.libelle as competence
    FROM `your-project.silver_dataset.offers` o
    JOIN `your-project.silver_dataset.offers_lieu_travail` l ON o.id = l.offer_id
    JOIN `your-project.silver_dataset.offers_competences` c ON o.id = c.offer_id
    WHERE c.libelle LIKE '%Python%'
    LIMIT 50
"""
df_custom = pd.read_gbq(query, project_id="your-project-id")
```

### Option 3 : Console BigQuery

1. Accédez à [console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery)
2. Sélectionnez votre projet
3. Naviguez vers `silver_dataset` ou `gold_dataset`
4. Exécutez vos requêtes SQL

---

## 📖 Exemples de Requêtes

### Requêtes simples

```sql
-- Compter le nombre total d'offres
SELECT COUNT(*) as total
FROM `your-project.silver_dataset.offers`;

-- Offres CDI en Île-de-France
SELECT o.id, o.intitule, l.libelle as ville
FROM `your-project.silver_dataset.offers` o
JOIN `your-project.silver_dataset.offers_lieu_travail` l ON o.id = l.offer_id
WHERE o.typeContrat = 'CDI' AND l.codePostal LIKE '75%'
LIMIT 20;

-- Top 10 des métiers les plus demandés
SELECT romeLibelle, COUNT(*) as count
FROM `your-project.silver_dataset.offers`
GROUP BY romeLibelle
ORDER BY count DESC
LIMIT 10;
```

### Requêtes avec jointures

```sql
-- Offres avec compétences Python
SELECT o.intitule, o.typeContrat, c.libelle as competence
FROM `your-project.silver_dataset.offers` o
JOIN `your-project.silver_dataset.offers_competences` c ON o.id = c.offer_id
WHERE c.libelle LIKE '%Python%'
LIMIT 50;

-- Offres avec salaire mentionné
SELECT o.intitule, s.libelle as salaire, l.libelle as ville
FROM `your-project.silver_dataset.offers` o
JOIN `your-project.silver_dataset.offers_salaire` s ON o.id = s.offer_id
JOIN `your-project.silver_dataset.offers_lieu_travail` l ON o.id = l.offer_id
WHERE s.libelle IS NOT NULL;
```

### Recherche sémantique (Gold)

```sql
-- Recherche vectorielle sur les titres
SELECT
    o.id,
    o.intitule,
    COSINE_DISTANCE(e.embedding, query_embedding) as distance
FROM `your-project.gold_dataset.offers` o
JOIN `your-project.gold_dataset.offers_intitule_embeddings` e ON o.id = e.offer_id
WHERE COSINE_DISTANCE(e.embedding, query_embedding) < 0.5
ORDER BY distance ASC
LIMIT 10;
```

---

## ⚠️ Notes Importantes

### Codes d'Exigence

- **E** = Exigé (requis)
- **S** = Souhaité (préféré mais pas obligatoire)
- **D** = Débutant accepté

### Jointures

Utilisez `offer_id` pour joindre les tables secondaires à la table principale `offers`.

### Coûts BigQuery

- **Stockage** : Gratuit jusqu'à 10 GB/mois
- **Requêtes** : 1 TB gratuit/mois
- **Conseils** : Utilisez constamment des filtres sur les champs 'ingestion_date' pour minimiser les coûts car les tables sont partitionnées sur cette colonne.


### Sécurité
- Ne partagez pas vos credentials GCP
- Utilisez des rôles IAM appropriés pour restreindre l'accès
