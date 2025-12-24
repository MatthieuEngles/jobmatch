# Guide d'Accès à la Base de Données Offres d'Emploi

## Fichier de Base de Données

- **Emplacement** : `data/silver/offers.db`
- **Type** : SQLite (aucun serveur requis)
- **Format** : Données silver de l'API France Travail

---

## Installation et Configuration

### 1. Dépendances Python

```bash
cd /chemin/vers/offre-ingestion
pip install -r requirements.txt
```

Le fichier `requirements.txt` contient :
- `sqlalchemy` : ORM pour interagir avec la base
- `python-dotenv` : Gestion des variables d'environnement
- Autres dépendances nécessaires

### 2. Vérification de la Base

Testez l'accès à la base de données :

```bash
python src/verify_db.py
```

Ce script affiche :
- Le nombre de lignes dans chaque table

---

## Structure de la Base

### Table Principale : `offers`

Contient **toutes les informations principales** de chaque offre (27 colonnes).

**Colonnes principales** :
- `id` (PRIMARY KEY) : Identifiant unique de l'offre
- `intitule` : Titre du poste
- `description` : Description complète de l'offre
- `romeCode` / `romeLibelle` : Code et libellé du métier
- `typeContrat` / `typeContratLibelle` : Type de contrat (CDI, CDD, MIS, etc.)
- `experienceExige` / `experienceLibelle` : Expérience requise (D=Débutant, E=Expérimenté, S=Souhaité)
- `dateCreation` / `dateActualisation` : Dates de publication et mise à jour
- `nombrePostes` : Nombre de postes à pourvoir
- `qualificationCode` / `qualificationLibelle` : Niveau de qualification
- `codeNAF` / `secteurActivite` / `secteurActiviteLibelle` : Secteur d'activité
- `dureeTravailLibelle` / `dureeTravailLibelleConverti` : Temps de travail
- `alternance` / `accessibleTH` / `entrepriseAdaptee` : Indicateurs booléens

### Tables Secondaires (reliées par `offer_id`)

| Table | Contenu | Cardinalité |
|-------|---------|-------------|
| `offers_lieu_travail` | Localisation (libellé, latitude, longitude, code postal, commune) | 1-1 |
| `offers_entreprise` | Nom de l'entreprise et statut | 1-1 |
| `offers_salaire` | Informations salariales (libellé, commentaire, compléments) | 0-1 |
| `offers_salaire_complements` | Détail des avantages (primes, intéressement, etc.) | 0-N |
| `offers_competences` | Compétences requises avec code et niveau d'exigence | 0-N |
| `offers_qualites_professionnelles` | Qualités professionnelles attendues | 0-N |
| `offers_formations` | Formations requises ou souhaitées | 0-N |
| `offers_permis` | Permis de conduire requis ou souhaités | 0-N |
| `offers_langues` | Langues requises ou souhaitées | 0-N |
| `offers_contact` | Coordonnées pour postuler | 0-1 |
| `offers_origine` | Source de l'offre et partenaires | 0-1 |
| `offers_contexte_travail_horaires` | Horaires de travail détaillés | 0-N |

---

## Accès aux Données

### Option 1 : Python avec SQLAlchemy (Recommandé)

```python
from sqlalchemy import create_engine, text

# Connexion
engine = create_engine('sqlite:///data/silver/offers.db')

# Exemple de requête
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, intitule, typeContrat, romeCode
        FROM offers
        LIMIT 10
    """))
    for row in result:
        print(f"{row.id}: {row.intitule} [{row.typeContrat}]")
```

### Option 2 : Python avec Pandas

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/silver/offers.db')

# Charger la table offers
df = pd.read_sql_query("SELECT * FROM offers", conn)
print(df.head())

# Vos requêtes SQL personnalisées ici
df_custom = pd.read_sql_query("""
    SELECT o.intitule, l.libelle as ville, c.libelle as competence
    FROM offers o
    JOIN offers_lieu_travail l ON o.id = l.offer_id
    JOIN offers_competences c ON o.id = c.offer_id
    WHERE c.libelle LIKE '%Python%'
""", conn)

conn.close()
```

### Option 3 : Interface Graphique

- **DB Browser for SQLite** : https://sqlitebrowser.org/
- **DBeaver** : https://dbeaver.io/

Ouvrez simplement le fichier `data/silver/offers.db` avec l'un de ces outils.

---

## Notes Importantes

### Codes d'Exigence

- **E** = Exigé (requis)
- **S** = Souhaité (préféré mais pas obligatoire)
- **D** = Débutant accepté

### Jointures

Utilisez `offer_id` pour joindre les tables secondaires à la table principale `offers`.

```sql
-- Exemple de jointure
SELECT o.intitule, l.libelle as ville, c.libelle as competence
FROM offers o
JOIN offers_lieu_travail l ON o.id = l.offer_id
JOIN offers_competences c ON o.id = c.offer_id
WHERE o.typeContrat = 'CDI'
LIMIT 10;
```

---

## Support

- **Pipeline complet** : Voir [PIPELINE.md](PIPELINE.md)
- **Script de vérification** : `python src/verify_db.py`
