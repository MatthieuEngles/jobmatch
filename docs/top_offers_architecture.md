# Fonctionnalité "Top Offres" - Documentation Architecture

## Vue d'ensemble

La fonctionnalité "Top offres pour vous" propose des recommandations d'emploi personnalisées aux utilisateurs connectés, basées sur leurs profils candidat.

---

## 1. Parcours Utilisateur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PARCOURS UTILISATEUR                               │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  Utilisateur │
    │  (connecté)  │
    └──────┬───────┘
           │
           ▼
┌─────────────────────┐
│  Chargement de la   │
│  page d'accueil     │
└──────────┬──────────┘
           │
           │ Chargement automatique
           ▼
┌─────────────────────────────────────────┐
│  Carte "Top offres pour vous"           │
│  ┌───────────────────────────────────┐  │
│  │  Spinner de chargement...         │  │
│  └───────────────────────────────────┘  │
└──────────┬──────────────────────────────┘
           │
           │ GET /accounts/api/top-offers/refresh/
           ▼
┌─────────────────────────────────────────┐
│  Affichage des cartes d'offres (max 20) │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Offre 1 │ │ Offre 2 │ │ Offre 3 │   │
│  │  92%    │ │  88%    │ │  85%    │   │
│  └────┬────┘ └─────────┘ └─────────┘   │
│       │                                 │
└───────┼─────────────────────────────────┘
        │
        │ Clic sur une carte d'offre
        ▼
┌─────────────────────────────────────────┐
│  Modale de détail de l'offre            │
│  ┌───────────────────────────────────┐  │
│  │ Titre: Data Scientist             │  │
│  │ Entreprise: EDF                   │  │
│  │ Lieu: Paris                       │  │
│  │ Contrat: CDI                      │  │
│  │ Expérience: 3-5 ans               │  │
│  │ Description: ...                  │  │
│  │ Compétences: Python, ML, ...      │  │
│  │                                   │  │
│  │ ┌─────────────────────────────┐   │  │
│  │ │ Ajouter à mes candidatures │   │  │
│  │ └──────────────┬──────────────┘   │  │
│  └────────────────┼──────────────────┘  │
└───────────────────┼─────────────────────┘
                    │
                    │ POST /accounts/api/offers/{id}/add/
                    ▼
┌─────────────────────────────────────────┐
│  Candidature créée                      │
│  ┌───────────────────────────────────┐  │
│  │ ImportedOffer + Application       │  │
│  │ sauvegardés dans PostgreSQL       │  │
│  └───────────────────────────────────┘  │
└──────────┬──────────────────────────────┘
           │
           │ Rechargement de la page
           ▼
┌─────────────────────────────────────────┐
│  Carte "Suivi des candidatures" MAJ     │
│  ┌───────────────────────────────────┐  │
│  │ Nouvelle candidature visible (7)  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 2. Architecture Mode Mock (Développement/Test)

**Variables d'environnement :**
- `USE_MOCK_MATCHING=true`
- `USE_SQLITE_OFFERS=true`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ARCHITECTURE MODE MOCK                                  │
│                (USE_MOCK_MATCHING=true, USE_SQLITE_OFFERS=true)              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Navigateur  │
└──────┬───────┘
       │
       │ GET /accounts/api/top-offers/refresh/
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Django GUI (Port 8080)                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    top_offers_refresh_view                          │  │
│  │                                                                     │  │
│  │  1. Récupération des CandidateProfiles de l'utilisateur            │  │
│  │     ┌─────────────────────────┐                                    │  │
│  │     │ CandidateProfile        │                                    │  │
│  │     │ - title: str            │                                    │  │
│  │     │ - description: str      │                                    │  │
│  │     │ - is_default: bool      │                                    │  │
│  │     │ - selected_lines: []    │                                    │  │
│  │     └─────────────────────────┘                                    │  │
│  │                                                                     │  │
│  │  2. Appel get_top_offers_for_user()                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                services/top_offers.py                               │  │
│  │                                                                     │  │
│  │  get_top_offers_for_user(user, top_k=20)                           │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ Pour chaque CandidateProfile :                               │  │  │
│  │  │                                                              │  │  │
│  │  │   MODE MOCK:                                                 │  │  │
│  │  │   - title_embedding = [0.0] * 384  (vecteur dummy)           │  │  │
│  │  │   - cv_embedding = [0.0] * 384     (vecteur dummy)           │  │  │
│  │  │                                                              │  │  │
│  │  │   - Appel matching_service.get_matches(                      │  │  │
│  │  │       title_embedding,                                       │  │  │
│  │  │       cv_embedding,                                          │  │  │
│  │  │       top_k                                                  │  │  │
│  │  │     )                                                        │  │  │
│  │  │   - Collecte des résultats                                   │  │  │
│  │  │                                                              │  │  │
│  │  │ Fusion & dédoublonnage (meilleur score par offre)            │  │  │
│  │  │ Tri par score décroissant                                    │  │  │
│  │  │ Retourne top_k résultats                                     │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                      │  │
│  │                              │                                      │  │
│  │  ┌───────────────────────────┼───────────────────────────────────┐ │  │
│  │  │                           ▼                                    │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐  │ │  │
│  │  │  │           services/matching.py                          │  │ │  │
│  │  │  │                                                         │  │ │  │
│  │  │  │  MockMatchingService                                    │  │ │  │
│  │  │  │  ┌───────────────────────────────────────────────────┐  │  │ │  │
│  │  │  │  │ get_matches(                                      │  │  │ │  │
│  │  │  │  │   title_embedding: list[float],                   │  │  │ │  │
│  │  │  │  │   cv_embedding: list[float],                      │  │  │ │  │
│  │  │  │  │   top_k: int                                      │  │  │ │  │
│  │  │  │  │ ) -> list[MatchResult]                            │  │  │ │  │
│  │  │  │  │                                                   │  │  │ │  │
│  │  │  │  │ 1. Ignore les embeddings (mode mock)              │  │  │ │  │
│  │  │  │  │ 2. Requête offres aléatoires depuis SQLite Silver │  │  │ │  │
│  │  │  │  │ 3. Génération scores aléatoires (0.5 - 0.98)      │  │  │ │  │
│  │  │  │  │ 4. Retourne liste MatchResult triée               │  │  │ │  │
│  │  │  │  └───────────────────────────────────────────────────┘  │  │ │  │
│  │  │  │                         │                               │  │ │  │
│  │  │  │  ┌──────────────────────┼────────────────────────────┐  │  │ │  │
│  │  │  │  │      MatchResult     │                            │  │  │ │  │
│  │  │  │  │  - offer_id: str     │                            │  │  │ │  │
│  │  │  │  │  - score: float      ▼                            │  │  │ │  │
│  │  │  │  └──────────────────────────────────────────────────┘  │  │ │  │
│  │  │  └─────────────────────────┬───────────────────────────────┘  │ │  │
│  │  │                            │                                   │ │  │
│  │  └────────────────────────────┼───────────────────────────────────┘ │  │
│  │                               │                                      │  │
│  │                               ▼                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐    │  │
│  │  │           services/offers_db.py                              │    │  │
│  │  │                                                              │    │  │
│  │  │  SQLiteOffersDB                                              │    │  │
│  │  │  ┌────────────────────────────────────────────────────────┐  │    │  │
│  │  │  │ get_offers_by_ids(offer_ids) -> dict[str, OfferDetails]│  │    │  │
│  │  │  │                                                        │  │    │  │
│  │  │  │ Requêtes: tables offers, offers_entreprise             │  │    │  │
│  │  │  └────────────────────────────────────────────────────────┘  │    │  │
│  │  │                                                              │    │  │
│  │  │  ┌────────────────────────────────────────────────────────┐  │    │  │
│  │  │  │           OfferDetails                                 │  │    │  │
│  │  │  │  - id: str                                             │  │    │  │
│  │  │  │  - intitule: str                                       │  │    │  │
│  │  │  │  - entreprise: str | None                              │  │    │  │
│  │  │  │  - description: str | None                             │  │    │  │
│  │  │  └────────────────────────────────────────────────────────┘  │    │  │
│  │  └──────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
└──────────────────────────────┼────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     Base SQLite Silver                                    │
│                     (temp_BQ/Silver/offers.db)                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Tables :                                                           │  │
│  │  - offers (id, intitule, description, typeContratLibelle, ...)     │  │
│  │  - offers_entreprise (offer_id, nom)                               │  │
│  │  - offers_lieu_travail (offer_id, libelle)                         │  │
│  │  - offers_salaire (offer_id, libelle)                              │  │
│  │  - offers_competences (offer_id, libelle)                          │  │
│  │  - offers_qualites_professionnelles (offer_id, libelle)            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Réponse au navigateur                              │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  TopOfferResult[]                                                   │  │
│  │  [                                                                  │  │
│  │    {                                                                │  │
│  │      "offer_id": "201VNXL",                                        │  │
│  │      "score": 0.92,                                                │  │
│  │      "intitule": "Data Scientist",                                 │  │
│  │      "entreprise": "EDF",                                          │  │
│  │      "description": "..."                                          │  │
│  │    },                                                               │  │
│  │    ...                                                              │  │
│  │  ]                                                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Mode Production

**Variables d'environnement :**
- `USE_MOCK_MATCHING=false`
- `USE_SQLITE_OFFERS=false`
- `MATCHING_SERVICE_URL=http://matching:8086`
- `GCP_PROJECT_ID=job-match-v0`
- `BIGQUERY_GOLD_DATASET=gold`
- `EMBEDDINGS_PROVIDER=sentence_transformers`
- `EMBEDDINGS_MODEL=all-MiniLM-L6-v2`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ARCHITECTURE MODE PRODUCTION                            │
│                (USE_MOCK_MATCHING=false, USE_SQLITE_OFFERS=false)            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Navigateur  │
└──────┬───────┘
       │
       │ GET /accounts/api/top-offers/refresh/
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Django GUI (Port 8080)                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    top_offers_refresh_view                          │  │
│  │                                                                     │  │
│  │  1. Récupération des CandidateProfiles depuis PostgreSQL           │  │
│  │  2. Appel get_top_offers_for_user()                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                services/top_offers.py                               │  │
│  │                                                                     │  │
│  │  get_top_offers_for_user(user, top_k=20)                           │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │ Pour chaque CandidateProfile :                               │  │  │
│  │  │                                                              │  │  │
│  │  │   GÉNÉRATION DES EMBEDDINGS:                                 │  │  │
│  │  │   ┌────────────────────────────────────────────────────────┐ │  │  │
│  │  │   │ 1. title_embedding:                                    │ │  │  │
│  │  │   │    - Source: profile.description ou profile.title      │ │  │  │
│  │  │   │    - Modèle: sentence_transformers / all-MiniLM-L6-v2  │ │  │  │
│  │  │   │    - Résultat: vecteur float[384]                      │ │  │  │
│  │  │   │                                                        │ │  │  │
│  │  │   │ 2. cv_embedding:                                       │ │  │  │
│  │  │   │    - Source: profile.get_selected_lines() (contenu CV) │ │  │  │
│  │  │   │    - Fallback: title_text si pas de lignes             │ │  │  │
│  │  │   │    - Modèle: sentence_transformers / all-MiniLM-L6-v2  │ │  │  │
│  │  │   │    - Résultat: vecteur float[384]                      │ │  │  │
│  │  │   └────────────────────────────────────────────────────────┘ │  │  │
│  │  │                                                              │  │  │
│  │  │   - Appel matching_service.get_matches(                      │  │  │
│  │  │       title_embedding,                                       │  │  │
│  │  │       cv_embedding,                                          │  │  │
│  │  │       top_k                                                  │  │  │
│  │  │     )                                                        │  │  │
│  │  │                                                              │  │  │
│  │  │ Fusion, dédoublonnage, tri, retourne top_k                   │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                      │  │
│  └──────────────────────────────┼──────────────────────────────────────┘  │
│                                 │                                         │
└─────────────────────────────────┼─────────────────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          │                                               │
          ▼                                               ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│   Service Matching (8086)       │       │        Google BigQuery          │
│                                 │       │        (GCP Cloud)              │
│  ┌───────────────────────────┐  │       │                                 │
│  │   RealMatchingService     │  │       │  ┌───────────────────────────┐  │
│  │                           │  │       │  │   BigQueryOffersDB        │  │
│  │  POST /api/match          │  │       │  │                           │  │
│  │  {                        │  │       │  │   Projet: job-match-v0    │  │
│  │   "title_embedding": [    │  │       │  │   Dataset: gold           │  │
│  │     0.123, 0.456, ...     │  │       │  │                           │  │
│  │   ],  // 384 dimensions   │  │       │  │   Table gold.offers :     │  │
│  │   "cv_embedding": [       │  │       │  │   - id                    │  │
│  │     0.789, 0.012, ...     │  │       │  │   - intitule              │  │
│  │   ],  // 384 dimensions   │  │       │  │   - description           │  │
│  │   "top_k": 50             │  │       │  │   - title_embedding[]     │  │
│  │  }                        │  │       │  │   - cv_embedding[]        │  │
│  │                           │  │       │  │   - ...                   │  │
│  │  Réponse :                │  │       │  └───────────────────────────┘  │
│  │  {                        │  │       │                                 │
│  │   "matches": [            │  │       │  ┌───────────────────────────┐  │
│  │     {"offer_id": "...",   │  │       │  │   OfferFullDetails        │  │
│  │      "score": 0.95},      │  │       │  │   - id                    │  │
│  │     ...                   │  │       │  │   - intitule              │  │
│  │   ]                       │  │       │  │   - description           │  │
│  │  }                        │  │       │  │   - entreprise            │  │
│  └───────────────────────────┘  │       │  │   - type_contrat          │  │
│                                 │       │  │   - experience            │  │
│  Le service matching :          │       │  │   - duree_travail         │  │
│  - Lit les embeddings depuis    │       │  │   - lieu                  │  │
│    la table gold.offers         │       │  │   - salaire               │  │
│  - Calcule similarité cosinus   │       │  │   - date_creation         │  │
│  - Combine scores title + cv    │       │  │   - rome_libelle          │  │
│  - Retourne top_k résultats     │       │  │   - secteur_activite      │  │
│                                 │       │  │   - competences[]         │  │
│                                 │       │  │   - qualites[]            │  │
│                                 │       │  └───────────────────────────┘  │
│                                 │       │                                 │
└─────────────────────────────────┘       └─────────────────────────────────┘
          │                                               │
          │ MatchResult[]                                 │ OfferDetails
          │ - offer_id: str                               │
          │ - score: float                                │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Django GUI                                      │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Combine MatchResults + OfferDetails -> TopOfferResult[]           │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  TopOfferResult                                              │  │  │
│  │  │  - offer_id: str                                             │  │  │
│  │  │  - score: float (depuis Service Matching)                    │  │  │
│  │  │  - intitule: str (depuis BigQuery)                           │  │  │
│  │  │  - entreprise: str | None (depuis BigQuery)                  │  │  │
│  │  │  - description: str | None (depuis BigQuery)                 │  │  │
│  │  │  - matching_profiles: list[str] (noms des profils matchés)   │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Réponse au navigateur                              │
│                         (JSON TopOfferResult[])                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Résumé des Modèles de Données

### Modèles d'entrée (PostgreSQL - Django ORM)

```
┌─────────────────────────────────────────┐
│            CandidateProfile             │
├─────────────────────────────────────────┤
│ id: int                                 │
│ user: ForeignKey(User)                  │
│ title: str                              │
│ description: str                        │
│ is_default: bool                        │
│ created_at: datetime                    │
│                                         │
│ Méthodes:                               │
│ - get_selected_lines() -> [ExtractedLine]│
└─────────────────────────────────────────┘

         │
         │ Utilisé pour générer
         ▼

┌─────────────────────────────────────────┐
│          Embeddings (Production)        │
├─────────────────────────────────────────┤
│ title_embedding: float[384]             │
│   Source: profile.description           │
│           ou profile.title              │
│                                         │
│ cv_embedding: float[384]                │
│   Source: selected_lines.content        │
│           (lignes CV sélectionnées)     │
└─────────────────────────────────────────┘
```

### Modèles intermédiaires (Couche Services)

```
┌─────────────────────────────────────────┐
│             MatchResult                 │
│         (services/matching.py)          │
├─────────────────────────────────────────┤
│ offer_id: str                           │
│ score: float (0.0 - 1.0)                │
│   Score combiné title + cv matching     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            OfferDetails                 │
│         (services/offers_db.py)         │
├─────────────────────────────────────────┤
│ id: str                                 │
│ intitule: str                           │
│ entreprise: str | None                  │
│ description: str | None                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│          OfferFullDetails               │
│         (services/offers_db.py)         │
├─────────────────────────────────────────┤
│ id: str                                 │
│ intitule: str                           │
│ description: str | None                 │
│ entreprise: str | None                  │
│ type_contrat: str | None                │
│ experience: str | None                  │
│ duree_travail: str | None               │
│ lieu: str | None                        │
│ salaire: str | None                     │
│ date_creation: str | None               │
│ rome_libelle: str | None                │
│ secteur_activite: str | None            │
│ competences: list[str] | None           │
│ qualites: list[str] | None              │
└─────────────────────────────────────────┘
```

### Modèles de sortie

```
┌─────────────────────────────────────────┐
│           TopOfferResult                │
│        (services/top_offers.py)         │
├─────────────────────────────────────────┤
│ offer_id: str                           │
│ score: float                            │
│ intitule: str                           │
│ entreprise: str | None                  │
│ description: str | None                 │
│ matching_profiles: list[str]            │
│   (noms des profils ayant matché)       │
└─────────────────────────────────────────┘
```

### Modèles persistés (PostgreSQL - Django ORM)

```
┌─────────────────────────────────────────┐
│           ImportedOffer                 │
│         (accounts/models.py)            │
├─────────────────────────────────────────┤
│ id: int                                 │
│ user: ForeignKey(User)                  │
│ candidate_profile: FK(CandidateProfile) │
│ source_url: str                         │
│ source_domain: str                      │
│ captured_at: datetime                   │
│ title: str                              │
│ company: str                            │
│ location: str                           │
│ description: str                        │
│ contract_type: str                      │
│ skills: JSONField (list[str])           │
│ status: str                             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            Application                  │
│         (accounts/models.py)            │
├─────────────────────────────────────────┤
│ id: int                                 │
│ user: ForeignKey(User)                  │
│ candidate_profile: FK(CandidateProfile) │
│ imported_offer: FK(ImportedOffer)       │
│ status: str                             │
│ notes: str                              │
│ generated_cv: str                       │
│ generated_cover_letter: str             │
│ created_at: datetime                    │
│ updated_at: datetime                    │
└─────────────────────────────────────────┘
```

---

## 5. Points d'accès API

### API GUI (Django)

| Endpoint | Méthode | Description | Auth |
|----------|---------|-------------|------|
| `/accounts/api/top-offers/refresh/` | GET | Récupérer les top offres personnalisées | Requis |
| `/accounts/api/offers/<offer_id>/` | GET | Récupérer les détails complets d'une offre (modale) | Requis |
| `/accounts/api/offers/<offer_id>/add/` | POST | Ajouter une offre aux candidatures de l'utilisateur | Requis |

### API Matching Service (Production)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/match` | POST | Recherche d'offres similaires |

**Payload `/api/match`:**
```json
{
  "title_embedding": [0.123, 0.456, ...],  // 384 dimensions
  "cv_embedding": [0.789, 0.012, ...],     // 384 dimensions
  "top_k": 50
}
```

**Réponse:**
```json
{
  "matches": [
    {"offer_id": "201VNXL", "score": 0.95},
    {"offer_id": "201VMKP", "score": 0.89},
    ...
  ]
}
```

---

## 6. Configuration Environnement

### Développement (docker-compose.yml)

```yaml
environment:
  - USE_MOCK_MATCHING=true
  - USE_SQLITE_OFFERS=true
```

### Production

```yaml
environment:
  # Matching service
  - USE_MOCK_MATCHING=false
  - MATCHING_SERVICE_URL=http://matching:8086

  # Offers database
  - USE_SQLITE_OFFERS=false
  - GCP_PROJECT_ID=job-match-v0
  - BIGQUERY_GOLD_DATASET=gold

  # Embeddings
  - EMBEDDINGS_PROVIDER=sentence_transformers
  - EMBEDDINGS_MODEL=all-MiniLM-L6-v2
```

---

## 7. Structure des Fichiers

```
app/gui/
├── services/
│   ├── __init__.py          # Exports du module
│   ├── matching.py          # MatchingService (Mock/Real)
│   │                        # - get_matches(title_embedding, cv_embedding, top_k)
│   ├── offers_db.py         # OffersDB (SQLite/BigQuery)
│   │                        # - get_offers_by_ids()
│   │                        # - get_offer_full_details()
│   └── top_offers.py        # Orchestrateur
│                            # - get_top_offers_for_user()
│                            # - get_embedder() pour production
├── accounts/
│   ├── views.py             # Views:
│   │                        # - top_offers_refresh_view
│   │                        # - offer_details_view
│   │                        # - add_offer_to_applications_view
│   ├── urls.py              # Routes API
│   └── models.py            # ImportedOffer, Application
├── templates/
│   └── home.html            # Frontend (cartes offres, modale, JS)
└── temp_BQ/
    └── Silver/
        └── offers.db        # Base SQLite pour mode mock
```

---

## 8. Flux de données détaillé (Production)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUX DÉTAILLÉ - MODE PRODUCTION                           │
└─────────────────────────────────────────────────────────────────────────────┘

CandidateProfile
       │
       ├──► profile.description ──────► embedder() ──► title_embedding[384]
       │    (ou profile.title)                              │
       │                                                    │
       └──► profile.get_selected_lines() ──► embedder() ──► cv_embedding[384]
            (lignes CV sélectionnées)                       │
                                                            │
                                                            ▼
                                              ┌─────────────────────────┐
                                              │   Matching Service      │
                                              │   POST /api/match       │
                                              │   {                     │
                                              │     title_embedding,    │
                                              │     cv_embedding,       │
                                              │     top_k: 50           │
                                              │   }                     │
                                              └───────────┬─────────────┘
                                                          │
                                                          ▼
                                              ┌─────────────────────────────────┐
                                              │   BigQuery (gold.offers)        │
                                              │                                 │
                                              │   Colonnes embeddings :         │
                                              │   - title_embedding: float[384] │
                                              │   - cv_embedding: float[384]    │
                                              │                                 │
                                              │   Recherche :                   │
                                              │   - Similarité cosinus          │
                                              │     title_emb candidat          │
                                              │     vs title_emb offres         │
                                              │   - Similarité cosinus          │
                                              │     cv_emb candidat             │
                                              │     vs cv_emb offres            │
                                              │   - Score combiné               │
                                              └───────────┬─────────────────────┘
                                                          │
                                                          ▼
                                              MatchResult[]: offer_id + score
                                                          │
                                                          ▼
                                              ┌─────────────────────────┐
                                              │   BigQuery              │
                                              │   get_offers_by_ids()   │
                                              │   (détails affichage)   │
                                              └───────────┬─────────────┘
                                                          │
                                                          ▼
                                              TopOfferResult[]:
                                              score + offer details
```

### Structure de la table gold.offers (BigQuery)

```
┌────────────────────────────────────────────────────────────────────┐
│                        gold.offers                                  │
├────────────────────────────────────────────────────────────────────┤
│  id: STRING                    -- Identifiant unique offre         │
│  intitule: STRING              -- Titre du poste                   │
│  description: STRING           -- Description complète             │
│  typeContratLibelle: STRING    -- Type de contrat (CDI, CDD...)    │
│  experienceLibelle: STRING     -- Expérience requise               │
│  dureeTravailLibelleConverti: STRING -- Durée de travail           │
│  dateCreation: STRING          -- Date de publication              │
│  romeLibelle: STRING           -- Code ROME libellé                │
│  secteurActiviteLibelle: STRING -- Secteur d'activité              │
│                                                                    │
│  -- Colonnes d'embeddings pour le matching vectoriel --            │
│  title_embedding: ARRAY<FLOAT64>  -- Embedding du titre [384]      │
│  cv_embedding: ARRAY<FLOAT64>     -- Embedding du contenu [384]    │
└────────────────────────────────────────────────────────────────────┘
```
