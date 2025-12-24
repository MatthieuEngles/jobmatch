# Pipeline d'Ingestion des Offres d'Emploi France Travail

## Vue d'ensemble

Ce pipeline extrait les offres d'emploi depuis l'API France Travail et les transforme en données structurées exploitables (formats CSV et SQLite).

## Architecture du Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API France    │────▶│  Bronze Layer    │────▶│  Silver Layer    │
│    Travail      │     │   (JSON brut)    │     │  (CSV + SQLite)  │
└─────────────────┘     └──────────────────┘     └──────────────────┘
```

### 1. Bronze Layer : Extraction des données brutes

**Script** : `src/fetch_offers_with_pagination.py`

**Fonction** : Extraction complète des offres d'emploi depuis l'API France Travail

**Processus** :
1. Authentification OAuth2 avec gestion du cache de token
2. Parcours systématique de **1585 codes ROME** (métiers)
3. Pagination automatique (150 offres par requête)
4. Throttling : respect d'un intervalle minimum de 0.11s entre requêtes
5. Gestion des erreurs et retry automatique sur 401
6. Logging détaillé dans `logs.xlsx` (timestamp, status HTTP, nombre d'offres, etc.)

**Paramètres** :
```bash
# Par défaut : offres de la veille (J-1)
python src/fetch_offers_with_pagination.py

# Pour une date spécifique
python src/fetch_offers_with_pagination.py 2025-12-23
```

**Configuration** (fichier `.env`) :
```env
FT_CLIENT_ID=votre_client_id
FT_CLIENT_SECRET=votre_client_secret
FT_SCOPE=api_offresdemploiv2 o2dsoffre
FT_OAUTH_URL=https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire
FT_API_URL_BASE=https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
FT_ROMECODES_PATH=src/data_persist/rome_codes.txt
FT_LOGS_XLSX=logs.xlsx
```

**Sortie** :
- Fichier JSON : `data/offer_YYYY-MM-DD.json`
- Fichier de logs : `logs.xlsx`

**Exemple de structure JSON** :
```json
{
  "resultats": [
    {
      "id": "201VPGR",
      "intitule": "INJECTEUR FORAGE H/F",
      "description": "...",
      "dateCreation": "2025-12-22T16:57:57.187Z",
      "lieuTravail": {...},
      "entreprise": {...},
      "competences": [...],
      ...
    }
  ]
}
```

---

### 2. Silver Layer : Transformation et structuration

#### Option A : Export CSV

**Script** : `src/transform_offers_to_csv_silver.py`

**Fonction** : Transformation du JSON en 13 fichiers CSV normalisés

**Processus** :
1. Lecture du fichier JSON de la date cible
2. Structuration en 13 tables relationnelles
3. Export CSV avec `QUOTE_ALL` pour garantir l'intégrité
4. Les retours à la ligne sont échappés (`\n` → `\\n`) pour compatibilité CSV

**Paramètres** :
```bash
# Par défaut : offres de la veille (J-1)
python src/transform_offers_to_csv_silver.py

# Pour une date spécifique
python src/transform_offers_to_csv_silver.py 2025-12-23
```

**Sortie** (répertoire `data/silver/`) :
- `offers.csv` (table principale)
- `offers_lieu_travail.csv`
- `offers_entreprise.csv`
- `offers_salaire.csv`
- `offers_salaire_complements.csv`
- `offers_competences.csv`
- `offers_qualites_professionnelles.csv`
- `offers_formations.csv`
- `offers_permis.csv`
- `offers_langues.csv`
- `offers_contact.csv`
- `offers_origine.csv`
- `offers_contexte_travail_horaires.csv`

#### Option B : Base de données SQLite

**Script** : `src/transform_offers_to_db_silver.py`

**Fonction** : Création d'une base SQLite avec structure relationnelle

**Processus** :
1. Lecture du fichier JSON de la date cible
2. Création de la base de données avec SQLAlchemy
3. Définition de 13 tables avec leurs schémas
4. Insertion des données brutes (sans transformation)
5. Création automatique des index sur `offer_id`

**Paramètres** :
```bash
# Par défaut : offres de la veille (J-1)
python src/transform_offers_to_db_silver.py

# Pour une date spécifique
python src/transform_offers_to_db_silver.py 2025-12-23
```

**Sortie** :
- Base de données : `data/silver/offers.db`

**Avantages de SQLite** :
- ✅ Fichier unique portable
- ✅ Requêtes SQL complexes possibles
- ✅ Pas de serveur requis
- ✅ Compatible avec tous les outils SQL

---

## Structure des Données

### Table principale : `offers`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | String | Identifiant unique de l'offre (clé primaire) |
| `intitule` | Text | Titre du poste |
| `description` | Text | Description complète du poste |
| `dateCreation` | String | Date de création (ISO 8601) |
| `dateActualisation` | String | Date de dernière mise à jour |
| `romeCode` | String | Code ROME du métier |
| `romeLibelle` | String | Libellé du métier ROME |
| `appellationlibelle` | String | Appellation précise du poste |
| `typeContrat` | String | Code du type de contrat (CDI, CDD, MIS, etc.) |
| `typeContratLibelle` | String | Libellé du type de contrat |
| `natureContrat` | String | Nature du contrat |
| `experienceExige` | String | Code d'exigence d'expérience (D=Débutant, E=Expérimenté, S=Souhaité) |
| `experienceLibelle` | String | Libellé de l'expérience requise |
| `dureeTravailLibelle` | Text | Description de la durée de travail |
| `dureeTravailLibelleConverti` | String | Durée convertie (Temps plein/partiel) |
| `alternance` | String | Indicateur alternance |
| `nombrePostes` | Integer | Nombre de postes à pourvoir |
| `accessibleTH` | String | Accessible aux travailleurs handicapés |
| `qualificationCode` | String | Code de qualification |
| `qualificationLibelle` | String | Libellé de la qualification |
| `codeNAF` | String | Code NAF de l'entreprise |
| `secteurActivite` | String | Code du secteur d'activité |
| `secteurActiviteLibelle` | String | Libellé du secteur |
| `trancheEffectifEtab` | String | Taille de l'établissement |
| `offresManqueCandidats` | String | Indicateur de manque de candidats |
| `entrepriseAdaptee` | String | Entreprise adaptée |
| `employeurHandiEngage` | String | Employeur engagé handicap |

### Tables secondaires (toutes reliées par `offer_id`)

- **`offers_lieu_travail`** : Localisation (libellé, latitude, longitude, code postal, commune)
- **`offers_entreprise`** : Informations entreprise (nom, entreprise adaptée)
- **`offers_salaire`** : Rémunération (libellé, commentaire, compléments)
- **`offers_salaire_complements`** : Détail des avantages (code, libellé)
- **`offers_competences`** : Compétences requises (code, libellé, exigence)
- **`offers_qualites_professionnelles`** : Qualités attendues (libellé, description)
- **`offers_formations`** : Formations (code, domaine, niveau, exigence)
- **`offers_permis`** : Permis requis (libellé, exigence)
- **`offers_langues`** : Langues requises (libellé, exigence)
- **`offers_contact`** : Coordonnées (nom, email, téléphone, URL)
- **`offers_origine`** : Source de l'offre (origine, URL, partenaires)
- **`offers_contexte_travail_horaires`** : Horaires de travail

---

## Notes Importantes

### Codes d'exigence courants

- **E** : Exigé (requis)
- **S** : Souhaité (préféré mais pas obligatoire)
- **D** : Débutant accepté

### Filtres de date

L'API France Travail retourne les offres créées entre `minCreationDate` et `maxCreationDate`.
Par défaut, le script récupère les offres créées le jour J-1 (24h).

---

## Commandes Utiles

### Extraction des offres
```bash
# Offres de la veille
python src/fetch_offers_with_pagination.py

# Offres du 20 décembre 2025
python src/fetch_offers_with_pagination.py 2025-12-20
```

### Transformation CSV
```bash
python src/transform_offers_to_csv_silver.py 2025-12-23
```

### Transformation SQLite
```bash
python src/transform_offers_to_db_silver.py 2025-12-23
```

### Vérification de la BDD
```bash
python src/verify_db.py
```

---

## Monitoring et Logs

Le fichier `logs.xlsx` contient pour chaque requête API :
- Timestamp UTC
- Code ROME interrogé
- Range de pagination (ex: 0-149)
- Status HTTP
- Nombre d'offres retournées
- Total disponible (header Content-Range)

**Utilisation** : Permet de détecter les problèmes (timeouts, 401, etc.) et d'analyser la couverture.

---

## Support

Pour toute question sur le pipeline, consulter :
- `README.md` dans ce répertoire
- `GUIDE_REQUETES.md` pour l'utilisation de la base de données
- Les scripts eux-mêmes (bien documentés)
