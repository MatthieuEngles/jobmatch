# Postmortem - JobMatch

## 📅 Sessions

### 2025-12-22 (8) - Tests intégration cv-ingestion + Package shared installable
**Contexte:** Tester cv-ingestion avec serveur Ollama distant et rendre le package shared installable

**Réalisations:**
- **Script de test d'intégration** (`scripts/test_integration.py`) :
  - Test extraction PDF (pdfplumber)
  - Test analyse LLM avec Ollama distant (`llm.molp.fr`)
  - Testé avec plusieurs modèles : llama3.1:8b, gpt-oss:20b, gemma3:4b
  - Sortie vers `data_test/output.txt` avec résultats complets
  - Extraction réussie : 22-45 lignes selon le modèle

- **Package shared installable** (`shared/`) :
  - Structure `shared/src/shared/` pour package pip standard
  - `pyproject.toml` avec setuptools
  - Installation via `pip install -e ../../shared` dans requirements.txt
  - Plus besoin de PYTHONPATH pour les imports
  - Microservices vraiment indépendants

- **Interfaces partagées créées** :
  - `shared.constants.ContentType` : enum pour CV et offres
  - `shared.interfaces.ExtractedLine` : ligne extraite avec type et ordre
  - `shared.interfaces.CVData` : données CV avec helpers (skills_hard, experiences, etc.)
  - `shared.interfaces.ServiceHealth` : health check standard

**Problèmes rencontrés:**
- **ModuleNotFoundError: No module named 'shared'** lors du lancement serveur
  - Cause : PYTHONPATH non configuré
  - Solution : transformer shared en package pip installable
- **Structure package incorrecte** : hatchling vs setuptools
  - Solution : utiliser setuptools avec structure `src/shared/`

**Décisions techniques:**
- **Package pip installable** plutôt que PYTHONPATH : vraie indépendance des microservices
- **Mode éditable** (`-e`) : modifications shared reflétées sans réinstallation
- **Helpers dans CVData** : `skills_hard`, `experiences`, `get_by_type()` pour faciliter l'usage

---

### 2025-12-22 (7) - Microservice cv-ingestion + Migration Ruff
**Contexte:** Implémenter le microservice cv-ingestion et migrer les outils de linting vers Ruff

**Réalisations:**
- **Microservice cv-ingestion complet** :
  - FastAPI sur port 8081 (standalone, pas Django)
  - Extraction PDF (pdfplumber + PyMuPDF)
  - Extraction DOCX (python-docx)
  - LLM provider-agnostic avec Factory Pattern :
    - `OpenAIProvider` (OpenAI + OpenAI-compatible APIs)
    - `AnthropicProvider` (Claude)
    - `OllamaProvider` (local, utilise API compatible OpenAI)
  - Configuration via env vars : LLM_TYPE, LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL
  - Endpoint POST /extract avec validation fichier
  - Dockerfile et .env.example

- **Migration pre-commit vers Ruff** :
  - Remplacement de black, isort, flake8, mypy par Ruff
  - Configuration dans pyproject.toml (line-length=120, Python 3.12)
  - Règles activées : E, W, F, I, B, C4, UP, SIM
  - CI mis à jour avec job lint Ruff dédié
  - Documentation pre_commit_101.md mise à jour

**Problèmes rencontrés:**
- **Bandit B104** : "Possible binding to all interfaces" sur `0.0.0.0`
  - Solution : `# nosec B104 - Docker container` (faux positif pour conteneur)
- **Ruff B904** : "raise ... from err" dans except clause
  - Solution : `raise HTTPException(...) from e`
- **mypy bloquait le CI** pour membres sans assistant de code
  - Solution : migration complète vers Ruff (plus simple, plus rapide)

**Décisions techniques:**
- **cv-ingestion isolé** : microservice indépendant, ne partage pas la DB Django
- **Factory Pattern LLM** : permet de changer de provider sans modifier le code métier
- **Ruff plutôt que black+isort+flake8+mypy** : 1 outil au lieu de 4, 10-100x plus rapide
- **bandit conservé** : Ruff ne fait pas l'analyse sécurité
- **gitleaks conservé** : détection des secrets

---

### 2025-12-22 (6) - Convention de langue (code EN / UI FR)
**Contexte:** Standardiser les conventions de langue dans le projet

**Réalisations:**
- Création de CLAUDE.md avec les règles de langue :
  - Commentaires code : anglais
  - Messages commit : anglais (après préfixe [CortexForge])
  - Noms variables/fonctions/classes : anglais
  - Contenu UI visible : français
- Refactoring de tous les fichiers existants :
  - views.py : 1 commentaire FR → EN
  - profile.html : tous les commentaires CSS/HTML/JS → EN
  - home.html : tous les commentaires CSS/HTML → EN
- Vérification models.py et admin.py (déjà conformes)

**Problèmes rencontrés:**
- Tentative d'ajout dans .claude/settings.json échouée (validation error: "Property code_style is not allowed")
- Solution : utiliser CLAUDE.md qui est le bon endroit pour les instructions Claude

**Décisions techniques:**
- **CLAUDE.md** : fichier central pour les instructions de style/conventions
- **Séparation claire** : code interne EN, interface utilisateur FR
- **verbose_name Django** : reste en FR car c'est affiché dans l'admin (UI)

---

### 2025-12-22 (5) - ORM CV/ExtractedLine + Spécification cv-ingestion
**Contexte:** Implémenter l'ORM pour CV et ExtractedLine, connecter la vue profil aux données, écrire les specs du service cv-ingestion

**Réalisations:**
- Modèles Django : CV, CoverLetter, ExtractedLine dans accounts/models.py
- ExtractedLine avec content_type (experience, education, skill_hard, skill_soft, certification, language, interest, summary, other)
- CV avec extraction_status (pending, processing, completed, failed)
- Migration 0002_add_cv_coverletter_extractedline appliquée
- Vue profile_view connectée aux ExtractedLine (querysets par content_type)
- Template profile.html avec affichage conditionnel des données
- Spécification complète cv-ingestion dans docs/cv_ingestion_spec.md :
  - Architecture et flux de traitement
  - Extraction texte (PDF/DOCX)
  - Analyse LLM avec prompt et schema JSON
  - API endpoints
  - Configuration, erreurs, sécurité, tests, roadmap

**Problèmes rencontrés:**
- "no such table: accounts_extractedline" → migration 0002 non appliquée, résolu avec `python manage.py migrate`
- Données vides dans "Parcours professionnel" → normal, sera peuplé par cv-ingestion

**Décisions techniques:**
- **ExtractedLine granulaire** : 1 ligne = 1 unité (1 poste, 1 compétence, 1 diplôme)
- **Tabs "Parcours professionnel"** : mappent directement aux content_types ExtractedLine
- **LLM extraction** : prompt structuré avec JSON schema pour sortie standardisée
- **cv-ingestion en microservice** : déclenchement async via queue (Celery future)

---

### 2025-12-22 (4) - Refonte UI Landing Page et Profil
**Contexte:** Améliorer l'interface utilisateur de la landing page et de la page profil

**Réalisations:**
- Landing page dynamique avec animations CSS (fadeInUp, float, pulse, slideIn)
- Hero section plein écran (100vh) sans scroll
- Navbar conditionnelle : masquée si déconnecté, visible si connecté
- Cartes de "match preview" animées dans le hero
- Stats animées avec gradient (10K+ offres, 95% précision, 30s pour matcher)
- Page profil avec sidebar menu (photo, données perso, CVs, LM, pitch, succès, hobbies)
- Site non-scrollable (overflow: hidden sur body)
- Ajustement itératif des tailles pour tenir dans le viewport

**Problèmes rencontrés:**
- Migration Django manquante → `makemigrations accounts` pour créer 0001_initial.py
- Lignes trop longues dans migration (flake8 E501) → split help_text avec parenthèses
- Django 5+ logout nécessite POST → form avec csrf_token au lieu de lien

**Décisions techniques:**
- **CSS-only animations** : pas de JS pour les animations, tout en CSS
- **Template blocks conditionnels** : `{% block navbar %}` avec `{{ block.super }}` pour héritage sélectif
- **`{% block main_attrs %}`** : permet de customiser les attributs de `<main>` par template
- **clamp() pour responsive** : `font-size: clamp(2.8rem, 5.5vw, 4rem)` adapte la taille au viewport

---

### 2025-12-22 (3) - Configuration multi-environnement
**Contexte:** Permettre au service GUI de tourner en local, Docker dev et Cloud Run prod

**Réalisations:**
- Settings Django avec `ENV_MODE` (local/dev/prod)
- Mode local : `run_local.sh` avec SQLite
- Mode Docker dev : `docker-compose.dev.yml` avec PostgreSQL + hot-reload
- Mode Docker prod : `Dockerfile.prod` multi-stage optimisé
- CI/CD GCloud : `cloudbuild.yaml` pour Cloud Run
- Support Cloud SQL via Unix socket
- Support Cloud Storage pour les uploads (media)
- WhiteNoise pour les fichiers statiques
- README.md avec documentation des 3 modes

**Décisions techniques:**
- **Cloud Run** (serverless) plutôt que GKE (Kubernetes) pour simplifier
- **Cloud SQL PostgreSQL** pour la prod
- **Cloud Storage** pour les uploads CV
- **Multi-stage build** pour image prod légère
- **WhiteNoise** pour servir les static files sans nginx

---

### 2025-12-22 (2) - Service GUI Django
**Contexte:** Implémentation du service GUI avec Django

**Réalisations:**
- Choix framework : Django (malgré architecture microservices, pour batteries incluses)
- Création projet Django dans `app/gui/`
- App `accounts` avec custom User model :
  - Inscription, connexion, déconnexion
  - Profil utilisateur (préférences emploi : salaire, disponibilité, remote)
  - Suppression compte (RGPD)
- Templates Bootstrap 5 (base.html, home, login, register, profile)
- Configuration PostgreSQL via variables d'environnement
- Dockerfile pour le service GUI
- User Stories POC couvertes : US001, US002, US005, US006, US007, US008

**Décisions techniques:**
- **Django vs FastAPI** : Django choisi pour auth intégrée et admin
- **Custom User Model** : email comme USERNAME_FIELD
- **Bootstrap 5 via CDN** : rapidité de développement pour POC

---

### 2025-12-22 (1) - Initialisation projet + Architecture microservices
**Contexte:** Démarrage du projet JobMatch - plateforme de matching CV/offres d'emploi

**Réalisations:**
- Lecture et analyse des documents de contexte (One liner.pdf, Job match.xlsx)
- Compréhension de la vision produit (V1 MVP → V2 avec personnalisation CV)
- Identification de l'équipe (Matthieu, Clément, Mohamed, Maxime)
- Création du fichier POSTMORTEM.md et PITCH.md
- Mise en place architecture microservices :
  - `app/gui` - Interface utilisateur
  - `app/cv-ingestion` - Import et parsing CV
  - `app/offre-ingestion` - Récupération offres (France Travail)
  - `app/matching` - Algorithme de matching
  - `shared/` - Code partagé (interfaces, constants, utils)
- Configuration CI/CD :
  - `.pre-commit-config.yaml` (black, isort, flake8, mypy, bandit, gitleaks)
  - `.github/workflows/ci.yml` (tests par service)
  - `.github/workflows/cd.yml` (build Docker + deploy)
- `docker-compose.yml` avec postgres + redis
- Gestion Git : branche `dev` créée, `DEV_POC` mergée et supprimée

**Problèmes rencontrés:**
- Fichier Excel non lisible directement → résolu avec pandas + openpyxl
- Pre-commit `types-all` incompatible Python 3.12 → retiré de mypy config
- Hook `no-commit-to-branch` bloquait merge sur dev → retiré dev des branches protégées

**Décisions techniques:**
- **Mode vibecoding + équipe classique** : configuration dans `.claude/settings.json`
- **Préfixe commits** : `[CortexForge]` (pas de footer "Generated by Claude Code")
- **Périmètre Matthieu** : gui, cv-ingestion, frontend, shared/utils
- **Zones interdites** : offre-ingestion, matching (équipe classique)
- **Branches protégées** : main uniquement (dev autorisé pour permettre les merges)

## 🧠 Apprentissages clés
- Le projet a deux versions : V1 (matching simple) et V2 (matching + personnalisation CV)
- POC structuré en 4 domaines : Gestion Compte (DE:0), Import CV (DE:1), Ingestion Offres (DE:2), Smart Match (DE:2)
- Priorités MoSCoW définies dans les User Stories
- Mode vibecoding en équipe nécessite un périmètre clair et des règles strictes
- Django 5+ : logout doit être en POST (plus de GET)
- Template blocks Django : `{{ block.super }}` pour hériter conditionnellement
- **CLAUDE.md** est le bon endroit pour les conventions de style (pas settings.json)
- Séparation langue : code EN pour maintenabilité internationale, UI FR pour les utilisateurs
- **Ruff** remplace 4 outils Python (black, isort, flake8, mypy) et est 10-100x plus rapide
- **Factory Pattern** pour LLM providers : permet de switcher OpenAI/Anthropic/Ollama sans changer le code
- **Microservices isolés** : ne partagent pas de DB, communiquent uniquement par API
- **Package pip installable** pour shared : `pip install -e ../../shared` dans requirements.txt
- **Structure package Python** : `shared/src/shared/` avec setuptools pour imports propres

## ⚠️ Pièges à éviter
- Ne pas oublier la conformité RGPD (tâche assignée à Maxime)
- Gentleman Agreement à signer avant de continuer
- **Vibecoding** : ne jamais modifier les zones de l'équipe classique (offre-ingestion, matching)
- Toujours confirmer avant de modifier fichiers partagés (docker-compose, .env, interfaces)
- **Migrations auto-générées** : peuvent avoir des lignes trop longues (flake8 E501), nécessite reformatage manuel
- **overflow: hidden** sur body empêche tout scroll, s'assurer que le contenu tient dans le viewport
- **Bandit B104** : `host="0.0.0.0"` génère un warning, ajouter `# nosec B104` pour les conteneurs Docker
- **Ruff B904** : dans un `except`, utiliser `raise ... from e` ou `raise ... from None`
- **Import shared sans pip install** : ne pas oublier d'installer le package avant de lancer les microservices
- **Structure package** : bien utiliser `src/package/` pour que setuptools trouve les modules

## 🏗️ Patterns qui fonctionnent
- Documentation structurée dans Google Drive
- User Stories avec priorités MoSCoW et critères d'acceptation
- Répartition des tâches selon les préférences/compétences
- `.claude/settings.json` pour définir les règles de vibecoding
- Préfixe de commit `[CortexForge]` pour identifier les commits vibecoding
- Architecture microservices avec dossiers séparés par domaine
- **CSS clamp()** pour des tailles responsive sans media queries
- **Template blocks conditionnels** avec `{% if user.is_authenticated %}{{ block.super }}{% endif %}`
- **Variables CSS** (`:root`) pour cohérence des couleurs/styles
- **Factory Pattern** pour providers interchangeables (LLM, DB, etc.)
- **pydantic-settings** pour config via env vars avec validation
- **Ruff avec --fix** dans pre-commit : auto-correction des erreurs simples

## 📋 TODO / Dette technique
- [x] Choix de la stack technique → architecture microservices Python
- [x] Créer branche feature et commit structure microservices
- [x] Documentation pre-commit (docs/pre_commit_101.md)
- [x] Service GUI Django (accounts app)
- [x] Dockerfile GUI
- [x] Configuration multi-environnement (local/dev/prod)
- [x] CI/CD Cloud Run (cloudbuild.yaml)
- [x] Refonte UI landing page (hero, animations, navbar conditionnelle)
- [x] Page profil avec sidebar menu
- [x] ORM CV/CoverLetter/ExtractedLine
- [x] Connexion vue profil aux ExtractedLine
- [x] Spécification cv-ingestion (docs/cv_ingestion_spec.md)
- [x] Convention de langue (CLAUDE.md) : code EN, UI FR
- [x] **Microservice cv-ingestion Phase 1** : FastAPI, extraction PDF/DOCX, LLM provider-agnostic
- [x] **Migration Ruff** : remplacement black/isort/flake8/mypy par Ruff
- [x] **Documentation pre-commit mise à jour** avec Ruff
- [ ] Gentleman Agreement à rédiger et signer
- [ ] Présentation GitHub à faire (Matthieu)
- [ ] État de l'art scientifique (données, algos, SaaS existants, limites)
- [ ] Se renseigner sur la RGPD (Maxime)
- [ ] Tester `run_local.sh`
- [ ] Tester `docker-compose.dev.yml`
- [ ] Créer projet GCloud + Cloud SQL + Cloud Storage
- [x] Définir les interfaces partagées (schemas CV, offres) → shared package
- [x] **Tester cv-ingestion** avec un vrai CV PDF → script test_integration.py
- [ ] Intégrer l'upload de CV dans la GUI (section "Mes documents")
- [ ] Implémenter les sections du profil (LM, pitch, succès, hobbies)
- [ ] Upload photo de profil
- [ ] **Connecter GUI → cv-ingestion** : appel API après upload CV
- [ ] **Test API cv-ingestion** : lancer serveur FastAPI et tester endpoint /extract
- [ ] Installer shared dans les autres microservices (offre-ingestion, matching, gui)
