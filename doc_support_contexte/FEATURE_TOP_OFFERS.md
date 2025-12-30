# Feature: Top Offres Pour Vous

## Resume

Cette fonctionnalite permet aux utilisateurs connectes de rafraichir leurs recommandations d'offres d'emploi personnalisees basees sur leurs profils de candidature.

---

## Parcours Utilisateur

1. L'utilisateur clique sur le bouton **Rafraichir** sur la carte "Top offres pour vous" (page d'accueil)
2. Le systeme calcule les scores de matching pour tous les profils de candidature de l'utilisateur
3. Les resultats sont fusionnes, dedupliques et affiches tries par score

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    GUI      │────▶│   Shared    │────▶│  Matching   │────▶│  Gold DB    │
│  (Django)   │     │ (Embeddings)│     │  Service    │     │ (embeddings)│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                                           │
       │                                                           │
       ▼                                                           │
┌─────────────┐                                                    │
│  Gold DB    │◀───────────────────────────────────────────────────┘
│  (details)  │         (details des offres pour affichage)
└─────────────┘
```

---

## Flux Detaille

### Etape 1: Interaction Utilisateur
- L'utilisateur clique sur le bouton rafraichir (`id="refresh-offers-btn"`)
- Le frontend envoie une requete AJAX au backend GUI

### Etape 2: Recuperation des Profils Utilisateur
- La GUI interroge PostgreSQL pour tous les `ApplicationProfile` de l'utilisateur
- Chaque profil contient :
  - `description` : Description du profil (ex: "Data Engineer", "Developpeur Backend")
  - `selected_extracted_lines` : Liste des lignes CV selectionnees pour ce profil

### Etape 3: Generation des Embeddings (pour chaque profil)
- **Embedding titre** : `embed(profile.description)`
- **Embedding CV** : `embed(concatenation des selected_extracted_lines)`
- Utilise la fonction d'embedding partagee depuis `app/shared/`

### Etape 4: Appel au Service Matching (pour chaque profil)
- **Endpoint** : `POST http://matching:8086/api/match`
- **Requete** :
```json
{
  "title_embedding": [0.123, 0.456, ...],
  "cv_embedding": [0.789, 0.012, ...],
  "top_k": 20
}
```
- **Reponse** :
```json
{
  "matches": [
    {"offer_id": "abc123", "score": 0.95},
    {"offer_id": "def456", "score": 0.87},
    ...
  ]
}
```

### Etape 5: Fusion des Resultats
- Combiner les resultats de tous les profils
- Trier par score (decroissant)
- Dedupliquer : garder le meilleur score, tracker tous les noms de profils correspondants
- Garder les 20 meilleurs au total

### Etape 6: Recuperation des Details des Offres
- Requete vers **Gold DB** (`temp_BQ/Gold/offers.db`) pour les donnees d'affichage
- SQL :
```sql
SELECT
    o.id,
    o.intitule,
    o.description,
    e.nom as entreprise
FROM offers o
LEFT JOIN offers_entreprise e ON o.id = e.offer_id
WHERE o.id IN (?, ?, ...)
```

### Etape 7: Affichage des Resultats
Chaque carte d'offre affiche :
- **Titre** (`intitule`)
- **Entreprise** (`entreprise`)
- **Description** (tronquee)
- **Score** (pourcentage)
- **Badge(s) profil(s)** (quel(s) profil(s) ont matche cette offre)

---

## Schemas de Base de Donnees

### Gold DB (`temp_BQ/Gold/offers.db`)
Contient les donnees des offres pour le matching (embeddings) et l'affichage (details).

**Table principale : `offers`**
| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(50) | Cle primaire |
| intitule | TEXT | Titre du poste |
| description | TEXT | Description du poste |
| typeContrat | VARCHAR(10) | Code type de contrat |
| typeContratLibelle | VARCHAR(100) | Libelle type de contrat |
| ... | ... | (autres champs) |

**Table liee : `offers_entreprise`**
| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER | Cle primaire |
| offer_id | VARCHAR(50) | Cle etrangere vers offers |
| nom | VARCHAR(255) | Nom de l'entreprise |

**Colonnes embeddings (dans la table `offers`)**
| Colonne | Type | Description |
|---------|------|-------------|
| intitule_embedded | BLOB | Vecteur embedding du titre |
| description_embedded | BLOB | Vecteur embedding de la description |

---

## Contrats API

### GUI → Service Matching

**POST `/api/match`**

Requete :
```json
{
  "title_embedding": [float],    // Tableau de floats (vecteur embedding)
  "cv_embedding": [float],       // Tableau de floats (vecteur embedding)
  "top_k": 20                    // Nombre de resultats a retourner
}
```

Reponse :
```json
{
  "matches": [
    {
      "offer_id": "string",      // ID de l'offre depuis Gold DB
      "score": float             // Score de matching (0-1)
    }
  ]
}
```

---

## Composants Frontend

### Bouton Rafraichir
- **Emplacement** : `app/gui/templates/home.html`
- **Element** : `<button id="refresh-offers-btn">`
- **Comportement** : Declenche un appel AJAX, affiche un etat de chargement, met a jour le contenu de la carte

### Carte d'Affichage
- **Emplacement** : Carte "Top offres pour vous" sur la page d'accueil
- **Contenu** : Liste des offres matchees avec details et badges de profils

---

## Configuration

### Variables d'Environnement
| Variable | Service | Description |
|----------|---------|-------------|
| `MATCHING_SERVICE_URL` | GUI | URL du service matching (defaut : `http://matching:8086`) |

### Chemins des Fichiers
| Chemin | Description |
|--------|-------------|
| `app/gui/temp_BQ/Gold/offers.db` | Base Gold (details + embeddings) |
| `app/shared/` | Fonctions d'embedding partagees |

---

## Gestion des Erreurs

| Scenario | Comportement |
|----------|--------------|
| Pas de profils | Afficher message "Creez d'abord un profil" |
| Service matching indisponible | Afficher message d'erreur, permettre de reessayer |
| Aucun match trouve | Afficher message "Aucune offre correspondante trouvee" |
| Erreur base de donnees | Logger l'erreur, afficher message d'erreur generique |

---

## Ameliorations Futures

- [ ] Cache des resultats par profil (invalider lors de mise a jour du profil)
- [ ] Rafraichissement en arriere-plan a la connexion
- [ ] Pagination pour plus de resultats
- [ ] Filtrage par type de contrat, localisation, etc.
- [ ] Sauvegarder/mettre en favoris des offres

---

## Responsabilites

| Composant | Responsable |
|-----------|-------------|
| GUI (frontend + backend) | Matthieu |
| Embeddings partages | Matthieu |
| Service Matching | Maxime |
| Gold DB (embeddings + details) | Data pipeline / Maxime |
