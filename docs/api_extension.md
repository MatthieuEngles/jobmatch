# API Extension Navigateur

Documentation de l'API REST pour l'extension navigateur JobMatch.

## Authentification

L'API utilise JWT (JSON Web Tokens) pour l'authentification.

### Obtenir un token

```http
POST /api/auth/token/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Réponse (200 OK):**
```json
{
  "access": "<JWT_ACCESS_TOKEN>",
  "refresh": "<JWT_REFRESH_TOKEN>"
}
```

**Configuration des tokens:**
- Access token: expire après **15 minutes**
- Refresh token: expire après **7 jours**

### Rafraîchir le token

```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "<JWT_REFRESH_TOKEN>"
}
```

**Réponse (200 OK):**
```json
{
  "access": "<JWT_ACCESS_TOKEN>",
  "refresh": "<JWT_REFRESH_TOKEN>"
}
```

> **Note:** Les refresh tokens sont rotatifs. Après chaque refresh, un nouveau refresh token est émis et l'ancien est blacklisté.

### Utilisateur courant

```http
GET /api/auth/user/
Authorization: Bearer <access_token>
```

**Réponse (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Déconnexion

```http
POST /api/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Réponse (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

---

## Offres d'emploi

### Importer une offre

```http
POST /api/offers/import/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "offer": {
    "sourceUrl": "https://linkedin.com/jobs/view/123456",
    "sourceDomain": "linkedin.com",
    "title": "Développeur Python Senior",
    "company": "TechCorp",
    "location": "Paris, France",
    "description": "Nous recherchons un développeur Python expérimenté...",
    "contractType": "CDI",
    "salary": {
      "min": 55000,
      "max": 70000,
      "currency": "EUR",
      "period": "year"
    },
    "skills": ["Python", "Django", "PostgreSQL", "Docker"],
    "remoteType": "hybrid",
    "capturedAt": "2025-12-24T21:00:00Z"
  },
  "profileId": 1
}
```

**Champs requis:**
- `offer.sourceUrl` (string): URL complète de l'offre
- `offer.sourceDomain` (string): Nom de domaine source
- `offer.title` (string): Titre du poste
- `offer.capturedAt` (ISO datetime): Date/heure de capture

**Champs optionnels:**
- `offer.company` (string): Nom de l'entreprise
- `offer.location` (string): Lieu de travail
- `offer.description` (string): Description complète
- `offer.contractType` (string): Type de contrat (CDI, CDD, etc.)
- `offer.salary` (object): Informations salariales
- `offer.skills` (array): Liste des compétences
- `offer.remoteType` (string): Type de remote (onsite, hybrid, remote)
- `profileId` (integer): ID du profil candidat à utiliser pour le matching

**Réponse (201 Created):**
```json
{
  "offerId": 42,
  "matchScore": null,
  "message": "Offer imported successfully"
}
```

**Réponse si déjà importée (200 OK):**
```json
{
  "offerId": 42,
  "matchScore": 0.85,
  "message": "Offer already imported"
}
```

### Lister les offres

```http
GET /api/offers/
Authorization: Bearer <access_token>
```

**Réponse (200 OK):**
```json
[
  {
    "id": 42,
    "sourceUrl": "https://linkedin.com/jobs/view/123456",
    "sourceDomain": "linkedin.com",
    "capturedAt": "2025-12-24T21:00:00Z",
    "title": "Développeur Python Senior",
    "company": "TechCorp",
    "location": "Paris, France",
    "description": "...",
    "contractType": "CDI",
    "remoteType": "hybrid",
    "salary": {"min": 55000, "max": 70000, "currency": "EUR", "period": "year"},
    "skills": ["Python", "Django", "PostgreSQL", "Docker"],
    "matchScore": null,
    "matchedAt": null,
    "status": "new",
    "candidateProfileId": 1,
    "createdAt": "2025-12-24T21:05:00Z",
    "updatedAt": "2025-12-24T21:05:00Z"
  }
]
```

### Détail d'une offre

```http
GET /api/offers/{id}/
Authorization: Bearer <access_token>
```

### Mettre à jour le statut

```http
PATCH /api/offers/{id}/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "applied"
}
```

**Valeurs possibles pour `status`:**
- `new` - Nouvelle offre
- `viewed` - Offre consultée
- `saved` - Offre sauvegardée
- `applied` - Candidature envoyée
- `rejected` - Offre rejetée

### Supprimer une offre

```http
DELETE /api/offers/{id}/
Authorization: Bearer <access_token>
```

**Réponse (204 No Content)**

---

## Health Check

```http
GET /api/health/
```

**Réponse (200 OK):**
```json
{
  "status": "ok"
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| 400 | Bad Request - Données invalides |
| 401 | Unauthorized - Token manquant ou invalide |
| 403 | Forbidden - Accès refusé |
| 404 | Not Found - Ressource inexistante |
| 500 | Internal Server Error |

**Exemple d'erreur (401):**
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is invalid or expired"
    }
  ]
}
```

---

## CORS

### Développement

En mode développement (`DEBUG=True`), toutes les origines sont autorisées :
```python
CORS_ALLOW_ALL_ORIGINS = True
```

### Production

En production, seules les extensions navigateur autorisées peuvent accéder à l'API :

```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^chrome-extension://[a-z]{32}$",
    r"^moz-extension://[a-f0-9-]{36}$",
]
```

**TODO: SECURITY**

Avant la mise en production :
1. Désactiver `CORS_ALLOW_ALL_ORIGINS`
2. Configurer `CORS_ALLOWED_ORIGINS` avec les IDs spécifiques des extensions
3. L'ID d'une extension Chrome est fixe une fois publiée sur le Chrome Web Store
4. L'ID d'une extension Firefox change à chaque installation (utiliser regex)

Exemple de configuration sécurisée :
```python
CORS_ALLOWED_ORIGINS = [
    "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef",  # Extension Chrome publiée
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^moz-extension://[a-f0-9-]{36}$",  # Extensions Firefox
]
```

---

## TODO: Matching Service Integration

L'intégration avec le service de matching n'est pas encore implémentée.

Quand le service sera prêt, le flux sera :

1. **À l'import d'une offre :**
   ```python
   # 1. Récupérer l'embedding du CV de l'utilisateur
   cv_embedding = get_user_cv_embedding(user)

   # 2. Générer l'embedding de l'offre
   offer_embedding = generate_offer_embedding(offer)

   # 3. Calculer le score de matching
   match_score = cosine_similarity(cv_embedding, offer_embedding)

   # 4. Sauvegarder le résultat
   imported_offer.match_score = match_score
   imported_offer.matched_at = timezone.now()
   imported_offer.save()
   ```

2. **Endpoint matching (Maxime) :**
   ```http
   POST /match
   {
     "cv_embedding": [0.1, 0.2, ...],
     "offer_id": "external_id"
   }
   ```

---

## Modèle de données

### ImportedOffer

| Champ | Type | Description |
|-------|------|-------------|
| id | integer | ID unique |
| user | FK(User) | Utilisateur propriétaire |
| candidate_profile | FK(CandidateProfile) | Profil candidat (optionnel) |
| source_url | URL | URL de l'offre originale |
| source_domain | string | Domaine source |
| captured_at | datetime | Date de capture |
| title | string | Titre du poste |
| company | string | Entreprise |
| location | string | Lieu |
| description | text | Description |
| contract_type | string | Type de contrat |
| remote_type | string | Type de remote |
| salary | JSON | Infos salariales |
| skills | JSON | Liste des compétences |
| match_score | float | Score de matching (0-1) |
| matched_at | datetime | Date du calcul de matching |
| status | string | Statut (new, viewed, saved, applied, rejected) |
| created_at | datetime | Date de création |
| updated_at | datetime | Date de mise à jour |

**Contrainte d'unicité:** `(user, source_url)` - Un utilisateur ne peut pas importer deux fois la même offre.
