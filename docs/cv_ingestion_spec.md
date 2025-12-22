# Specifications Service CV-Ingestion

## Vue d'ensemble

Le service `cv-ingestion` est responsable de l'extraction automatique des informations structurees depuis les fichiers CV uploades par les candidats.

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   GUI       │────>│  CV-Ingestion    │────>│  Database   │
│  (upload)   │     │  (extraction)    │     │  (accounts) │
└─────────────┘     └──────────────────┘     └─────────────┘
                            │
                            v
                    ┌──────────────────┐
                    │  LLM / Parser    │
                    │  (extraction)    │
                    └──────────────────┘
```

---

## Flux de traitement

### 1. Declenchement

Le service est declenche quand :
- Un nouveau CV est uploade (status = `pending`)
- Une reextraction est demandee manuellement

### 2. Etapes de traitement

```
1. Recuperer les CVs avec extraction_status = "pending"
2. Pour chaque CV :
   a. Mettre status = "processing"
   b. Telecharger le fichier depuis le storage
   c. Extraire le texte (PDF/DOCX -> texte brut)
   d. Analyser avec LLM pour structurer les donnees
   e. Creer les ExtractedLine dans la base
   f. Mettre status = "completed" + extracted_at = now()
   g. En cas d'erreur : status = "failed"
```

---

## Extraction de texte

### Formats supportes

| Format | Bibliotheque | Notes |
|--------|--------------|-------|
| PDF | `pdfplumber` ou `PyMuPDF` | Gestion des multi-pages |
| DOCX | `python-docx` | Extraction paragraphes |
| DOC | `antiword` ou conversion | Legacy, best effort |

### Sortie

Texte brut concatene, avec separateurs de sections preserves si possible.

---

## Analyse LLM

### Prompt systeme

```
Tu es un expert en analyse de CV. Extrait les informations suivantes
du CV fourni et retourne-les au format JSON structure.

Pour chaque information, indique :
- Le type (experience, education, skill_hard, skill_soft, language, certification, interest, summary)
- Le contenu exact extrait
- L'ordre d'apparition (0, 1, 2...)

Regles de granularite :
- experience : 1 poste = 1 entree (inclure entreprise, titre, dates, description)
- education : 1 diplome = 1 entree
- skill_hard : 1 competence technique = 1 entree
- skill_soft : 1 soft skill = 1 entree
- language : 1 langue = 1 entree (inclure niveau si present)
- certification : 1 certification = 1 entree
- interest : 1 centre d'interet = 1 entree
- summary : 1 paragraphe d'accroche = 1 entree
```

### Schema de sortie attendu

```json
{
  "extracted_lines": [
    {
      "content_type": "experience",
      "content": "Senior Developer chez TechCorp (2020-2023)\nDeveloppement d'applications web...",
      "order": 0
    },
    {
      "content_type": "experience",
      "content": "Developer chez StartupX (2018-2020)\nCreation de MVP...",
      "order": 1
    },
    {
      "content_type": "skill_hard",
      "content": "Python",
      "order": 0
    },
    {
      "content_type": "skill_hard",
      "content": "Django",
      "order": 1
    },
    {
      "content_type": "education",
      "content": "Master Informatique - Universite Paris-Saclay (2018)",
      "order": 0
    }
  ]
}
```

---

## Modele de donnees cible

### ExtractedLine (dans accounts app)

| Champ | Type | Description |
|-------|------|-------------|
| user | FK -> User | Proprietaire |
| source_cv | FK -> CV | CV source (CASCADE) |
| content_type | CharField | Type de contenu |
| content | TextField | Texte extrait |
| is_active | Boolean | Actif pour matching (default: True) |
| order | Integer | Ordre d'affichage |
| created_at | DateTime | Date creation |
| modified_at | DateTime | Date modification |
| modified_by_user | Boolean | Modifie manuellement |

### content_type (choices)

- `summary` : Resume / Accroche
- `experience` : Experience professionnelle
- `education` : Formation
- `skill_hard` : Competence technique
- `skill_soft` : Soft skill
- `language` : Langue
- `certification` : Certification
- `interest` : Centre d'interet
- `other` : Autre

---

## API Endpoints (si expose en REST)

### POST /extract

Declenche l'extraction pour un CV specifique.

```json
Request:
{
  "cv_id": 123
}

Response:
{
  "status": "processing",
  "message": "Extraction demarree"
}
```

### GET /status/{cv_id}

Verifie le statut d'extraction.

```json
Response:
{
  "cv_id": 123,
  "extraction_status": "completed",
  "extracted_at": "2025-12-22T16:00:00Z",
  "lines_count": 15
}
```

---

## Configuration

### Variables d'environnement

```bash
# LLM Provider
LLM_PROVIDER=openai|anthropic|local
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4|claude-3-sonnet|...

# Storage
STORAGE_BACKEND=local|gcs|s3
STORAGE_BUCKET=jobmatch-cvs

# Database
DATABASE_URL=postgresql://...

# Processing
MAX_FILE_SIZE_MB=10
SUPPORTED_FORMATS=pdf,docx,doc
EXTRACTION_TIMEOUT_SECONDS=120
```

---

## Gestion des erreurs

### Codes d'erreur

| Code | Description | Action |
|------|-------------|--------|
| `ERR_FILE_NOT_FOUND` | Fichier introuvable | Status = failed |
| `ERR_UNSUPPORTED_FORMAT` | Format non supporte | Status = failed |
| `ERR_EXTRACTION_FAILED` | Echec extraction texte | Status = failed |
| `ERR_LLM_TIMEOUT` | Timeout LLM | Retry x3, puis failed |
| `ERR_INVALID_RESPONSE` | Reponse LLM invalide | Retry x3, puis failed |

### Logging

Chaque etape doit etre loggee :
- INFO : Debut/fin de traitement
- DEBUG : Details extraction
- ERROR : Erreurs avec traceback
- WARNING : Retries, timeouts

---

## Securite

### Validation fichiers

- Verifier le MIME type reel (pas juste l'extension)
- Scanner antivirus si disponible
- Limiter la taille max (10 MB par defaut)
- Nettoyer les metadonnees sensibles

### Isolation

- Traitement dans un environnement isole (container)
- Timeout strict sur l'extraction
- Pas d'execution de code externe

---

## Performance

### Optimisations

- Queue de traitement (Celery/RQ) pour async
- Batch processing si plusieurs CVs
- Cache des modeles LLM si local
- Compression des fichiers en storage

### Metriques a suivre

- Temps moyen d'extraction
- Taux d'echec par format
- Nombre de lignes extraites par CV
- Cout LLM par extraction

---

## Tests

### Cas de test

1. **PDF simple** : 1 page, texte clair
2. **PDF multi-pages** : 3+ pages
3. **PDF scanne** : OCR necessaire
4. **DOCX standard** : Format Word moderne
5. **DOC legacy** : Ancien format Word
6. **CV vide** : Pas de contenu extractible
7. **CV corrompu** : Fichier invalide
8. **CV multilingue** : FR + EN

### Fixtures de test

Creer des CVs de test dans `tests/fixtures/cvs/` :
- `cv_simple.pdf`
- `cv_multipage.pdf`
- `cv_scanned.pdf`
- `cv_standard.docx`
- `cv_empty.pdf`
- `cv_corrupted.pdf`

---

## Roadmap

### Phase 1 - MVP
- [ ] Extraction PDF basique
- [ ] Analyse LLM (OpenAI)
- [ ] Creation ExtractedLine
- [ ] Status tracking

### Phase 2 - Ameliorations
- [ ] Support DOCX
- [ ] OCR pour PDFs scannes
- [ ] Retry automatique
- [ ] Webhooks de notification

### Phase 3 - Optimisations
- [ ] Queue async (Celery)
- [ ] Multi-provider LLM
- [ ] Cache et batch
- [ ] Dashboard metriques
