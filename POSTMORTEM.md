# Postmortem - JobMatch

## 📅 Sessions

### 2025-12-23 (12) - LLM Config Fallback + Sélecteur d'abonnement + Modal Pricing
**Contexte:** Améliorer la gestion de la config LLM et ajouter un sélecteur d'abonnement avec comparaison des plans

**Réalisations:**
- **LLM Config Fallback environnement** :
  - Si l'utilisateur n'a pas configuré son LLM, le système utilise les variables d'environnement
  - Classe `LLMConfig` dans `analyzer.py` pour passer une config optionnelle
  - `get_llm_provider(config: LLMConfig | None)` : utilise config custom si fournie, sinon env vars
  - `analyze_cv_text()` et `analyze_cv_images()` acceptent un paramètre `llm_config` optionnel
  - Endpoint `/extract/async` accepte des Form fields : `llm_endpoint`, `llm_model`, `llm_api_key`

- **Transmission config LLM GUI → cv-ingestion** :
  - `cv_upload_view` envoie la config LLM de l'utilisateur si activée ET si abonnement Premium+
  - Vérification `user.subscription_tier not in ("free", "basic")` avant envoi
  - Données transmises via multipart form data

- **Sélecteur d'abonnement** dans Account Settings :
  - 5 plans : Free (0€), Basic (9€), Premium (29€), Head Hunter (49€), Enterprise (99€)
  - Radio buttons stylisés avec prix et descriptions
  - Handler `form_type == "subscription"` pour mise à jour du tier

- **Modal Pricing "Voir les offres"** :
  - Bouton gradient "Voir les offres" sur la carte abonnement
  - Modal plein écran avec comparaison des 5 plans
  - Tableau des fonctionnalités : CVs, Offres, Analyses LLM, Support, etc.
  - Checkmarks verts / croix rouges pour chaque fonctionnalité
  - Prix affichés pour chaque plan

- **Restriction LLM Config par abonnement** :
  - Section LLM Config visible uniquement pour Premium, Head Hunter, Enterprise
  - Message explicatif pour Free/Basic : "disponible à partir du plan Premium"
  - Section grisée (opacity: 0.6) pour plans non éligibles

**Problèmes rencontrés:**
- **File not read error** : tentative d'édition sans lecture préalable
  - Solution : toujours lire le fichier avant de l'éditer

**Décisions techniques:**
- **Form fields plutôt que JSON body** : compatible avec multipart/form-data pour upload fichier
- **Config optionnelle avec fallback** : pattern robuste, pas de breaking change
- **Restriction par tier** : vérification côté serveur ET côté template
- **Modal CSS natif** : pas de dépendance JS externe, animation simple

---

### 2025-12-23 (11) - Page Gestion Compte + LLM Config + Export RGPD
**Contexte:** Remplacer "Supprimer mon compte" par une page complète de gestion du compte utilisateur

**Réalisations:**
- **Page Account Settings** (`/accounts/settings/`) :
  - Sections : Identité, Email, Mot de passe, Abonnement, Config LLM, Export données, Suppression compte
  - Multi-formulaires sur une page (pattern `form_type` hidden field)
  - Messages de succès/erreur par section
  - Danger zone en rouge pour suppression compte

- **Modèles ajoutés** :
  - `SUBSCRIPTION_TIER_CHOICES` : Free, Basic, Premium, Head Hunter, Enterprise
  - `subscription_tier` field sur User (default="free")
  - `UserLLMConfig` model (OneToOne avec User) :
    - `is_enabled`, `llm_endpoint`, `llm_model`, `llm_api_key`
    - Permet aux utilisateurs d'utiliser leur propre LLM

- **Formulaires créés** :
  - `AccountIdentityForm` : prénom, nom
  - `AccountEmailForm` : changement email avec vérification unicité
  - `AccountPasswordForm` : mot de passe actuel + nouveau + confirmation
  - `UserLLMConfigForm` : activation + endpoint + modèle + API key

- **Export RGPD** (`/accounts/export/`) :
  - Endpoint `export_data_view`
  - Export JSON complet : profil, CVs, lignes extraites, lettres motivation, config LLM
  - Clé API exclue de l'export pour sécurité
  - Téléchargement fichier `jobmatch_data_{user_id}.json`

- **UI/UX** :
  - Sidebar profil : "Supprimer mon compte" → "Gérer mon compte" avec icône engrenage
  - Template `settings.html` avec design cohérent (cards, gradients)
  - Formulaires stylisés Bootstrap 5

- **Migration 0004** : `add_subscription_and_llm_config`

**Problèmes rencontrés:**
- **File not read error** : outil Edit échoue si fichier non lu préalablement
  - Solution : toujours lire le fichier avant de l'éditer
- **docker-compose KeyError 'ContainerConfig'** (récurrent)
  - Solution : `docker-compose down` complet avant `up`

**Décisions techniques:**
- **Multi-form pattern** : un seul template, plusieurs formulaires indépendants via `form_type`
- **Re-login après password change** : `login(request, user)` après `form.save()` pour éviter déconnexion
- **get_or_create pour LLM config** : crée automatiquement la config si inexistante
- **OneToOneField avec related_name** : `user.llm_config` pour accès direct
- **API key non exportée** : sécurité RGPD (données sensibles exclues)

---

### 2025-12-23 (10) - Vision LLM + Prompts externalisés + Toggle/Edit UI
**Contexte:** Améliorer cv-ingestion pour supporter les PDF image (scannés) via Vision LLM, externaliser les prompts, et ajouter des contrôles UI sur les lignes extraites

**Réalisations:**
- **Support Vision LLM** dans cv-ingestion :
  - Méthode `supports_vision()` sur `LLMProvider` base class
  - Méthode `analyze_images()` pour traiter les images avec Vision LLM
  - Support OpenAI (GPT-4V, GPT-4o), Anthropic (Claude 3/4), Ollama (LLaVA)
  - Nouvelle fonction `analyze_cv_images()` exportée

- **Extraction PDF intelligente** :
  - `is_text_based_pdf()` : détection auto texte vs image (heuristique: min 100 chars total, 50 chars/page)
  - `extract_pdf_content()` : retourne `PDFContent(is_text_based, text, images)`
  - `convert_pdf_to_images()` : PDF → PNG via pdf2image/poppler
  - `ocr_images()` : fallback OCR via Tesseract si Vision LLM non disponible
  - Logique dans main.py : texte → LLM texte, image → Vision LLM ou OCR fallback

- **Prompts externalisés** :
  - Dossier `src/prompts/` avec fichiers .txt séparés
  - `cv_extraction_text.txt` : prompt pour extraction texte
  - `cv_extraction_vision.txt` : prompt pour extraction images
  - `__init__.py` avec `load_prompt()`, `get_cv_text_prompt()`, `get_cv_vision_prompt()`
  - Prompts traduits en français
  - Règle expériences : 1 mission = 1 entrée (découpage si trop long)

- **UI Toggle/Edit sur ExtractedLines** :
  - Toggle switch actif/inactif (vert/rouge) sur chaque ligne extraite
  - Bouton édition (pictogramme crayon)
  - Endpoint `line/toggle/<int:line_id>/` avec `extracted_line_toggle_view`
  - JavaScript pour appels API et mise à jour visuelle
  - `resumeProcessingCVs()` pour reprendre le polling des CVs "En cours" au chargement

- **Dépendances ajoutées** :
  - requirements.txt : `pdf2image`, `pytesseract`, `Pillow`
  - Dockerfile : `poppler-utils`, `tesseract-ocr`, `tesseract-ocr-fra`, `tesseract-ocr-eng`

**Problèmes rencontrés:**
- **CV stuck "En cours..."** après page reload
  - Cause : polling interrompu par le reload avant réception du status "completed"
  - Solution : `resumeProcessingCVs()` qui reprend le polling pour les CVs avec `data-status="processing"`
- **docker-compose KeyError 'ContainerConfig'**
  - Cause : bug docker-compose avec rebuild
  - Solution : `docker-compose stop && rm -f && up` au lieu de `up -d` direct

**Décisions techniques:**
- **Vision LLM natif plutôt qu'OCR seul** : meilleure qualité d'extraction, compréhension du layout
- **OCR en fallback** : Tesseract si le provider LLM ne supporte pas la vision
- **Prompts en fichiers .txt** : facilite l'itération et le versioning des prompts
- **Découpage expériences** : 1 mission = 1 entrée pour granularité fine dans le matching
- **Prompt en français** : le LLM comprend mieux le contexte des CVs français

---

### 2025-12-22 (9) - Intégration GUI ↔ cv-ingestion + Polling asynchrone + Suppression CV
**Contexte:** Connecter la GUI Django au microservice cv-ingestion en mode Docker, implémenter le polling asynchrone pour les traitements longs, et ajouter la suppression des CVs

**Réalisations:**
- **Configuration Docker multi-service** :
  - docker-compose.yml : context root pour accès au package shared
  - app/cv-ingestion/Dockerfile : copie shared/ et install pip
  - app/gui/Dockerfile : adapté pour context root
  - env_file dans docker-compose pour charger app/cv-ingestion/.env
  - Ports exposés via variables : GUI_PORT=8085, DB_PORT=5433

- **Configuration environnement** :
  - `.env` root avec config commune (DATABASE_URL, ports, URLs inter-services)
  - `.envrc` pour direnv (charge tous les .env du projet)
  - `app/cv-ingestion/.env` : LLM_TYPE=ollama, LLM_ENDPOINT=http://ollama.molp.fr/v1

- **Polling asynchrone cv-ingestion** (pattern async/polling) :
  - `task_store.py` : store en mémoire thread-safe (TaskStatus enum, Task dataclass)
  - `POST /extract/async` : retourne immédiatement un task_id
  - `GET /extract/status/{task_id}` : retourne pending/processing/completed/failed
  - BackgroundTasks FastAPI pour traitement asynchrone
  - Ancien endpoint synchrone `/extract` conservé pour rétrocompatibilité

- **Intégration GUI polling** :
  - `cv_upload_view` : appelle `/extract/async`, retourne task_id au frontend
  - `cv_status_view` : nouvelle vue pour polling depuis le frontend
  - Modèle CV : ajout champ `task_id` (migration 0003)
  - JavaScript : polling toutes les 2s avec messages de progression dynamiques
  - Timeout max 4 minutes (MAX_POLL_ATTEMPTS=120)

- **Suppression CV** :
  - `cv_delete_view` : endpoint DELETE/POST pour supprimer un CV
  - Supprime le fichier du storage + cascade sur ExtractedLines
  - Modal de confirmation avec nom du CV
  - Bouton corbeille sur chaque document dans la liste

- **Navigation par hash URL** :
  - `showSection()` met à jour `window.location.hash` avec `history.replaceState()`
  - Au chargement de la page, lecture du hash pour restaurer la section active
  - Après upload/suppression CV : `window.location.hash = 'documents'` avant reload
  - Permet de rester sur la bonne section après n'importe quelle action

**Problèmes rencontrés:**
- **`shared` package not found** en Docker build
  - Cause : context `./app/cv-ingestion` n'inclut pas `../../shared`
  - Solution : context `.` (root) + `COPY shared/` dans Dockerfile
- **Port 5432 already allocated**
  - Cause : PostgreSQL local déjà sur le port
  - Solution : DB_PORT=5433 dans .env
- **Port 8080 already allocated**
  - Cause : autre service sur le port
  - Solution : GUI_PORT=8085 dans .env
- **`LLM_API_KEY is required for OpenAI`** en Docker
  - Cause : Docker ne chargeait pas le .env du service
  - Solution : ajouter `env_file: app/cv-ingestion/.env` dans docker-compose.yml
- **404 Not Found `/chat/completions`** sur Ollama
  - Cause : LLM_ENDPOINT sans `/v1` suffix
  - Solution : `http://ollama.molp.fr/v1` (pas `http://ollama.molp.fr`)
- **Container ne pick up pas les changements .env**
  - Solution : `docker-compose down && docker-compose up -d` (pas juste restart)
- **docker-compose `KeyError: 'ContainerConfig'`**
  - Cause : bug docker-compose avec rebuild
  - Solution : `docker-compose down` puis `up` au lieu de juste `up -d`

**Décisions techniques:**
- **Polling plutôt que WebSockets** : plus simple, suffisant pour le POC
- **Store en mémoire** plutôt que Redis : simplicité, pas de dépendance externe
- **BackgroundTasks FastAPI** plutôt que Celery : léger, pas de broker à gérer
- **task_id UUID** : unique, non prédictible, pas besoin de séquence DB
- **Cascade delete** : supprimer un CV supprime automatiquement ses ExtractedLines

---

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

- **Fix CI check-branch** :
  - Job ne se déclenchait pas correctement (github.head_ref vide sur push)
  - Ajout condition `if: github.event_name == 'pull_request' && github.base_ref == 'main'`
  - Maintenant le check ne tourne que pour les PRs vers main

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
- **CI check-branch exécuté sur push** : `github.head_ref` vide sur event push
  - Solution : ajouter condition `if: github.event_name == 'pull_request' && github.base_ref == 'main'`

**Commandes utiles:**
- Supprimer branche locale : `git branch -d feature/matthieu-cv-ingestion`
- Supprimer branche distante : `git push origin --delete feature/matthieu-cv-ingestion`

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
- **Polling async** : pattern simple et robuste pour les traitements longs (préférer à WebSockets pour POC)
- **BackgroundTasks FastAPI** : alternative légère à Celery pour traitement async sans broker
- **docker-compose context root** : nécessaire quand un service a besoin de fichiers hors de son dossier
- **env_file vs environment** : env_file charge un fichier .env, environment définit des vars inline
- **Ollama API** : endpoint doit se terminer par `/v1` pour être compatible OpenAI
- **Vision LLM** : GPT-4o, Claude 3+, LLaVA supportent l'analyse d'images nativement
- **Prompts externalisés** : fichiers .txt séparés facilitent l'itération sans toucher au code
- **Découpage expériences CV** : 1 mission = 1 entrée pour un matching plus précis
- **pdf2image + poppler** : conversion PDF → images pour Vision LLM ou OCR
- **Multi-form pattern Django** : `form_type` hidden field pour gérer plusieurs forms sur une page
- **Re-login après password change** : appeler `login(request, user)` pour éviter la déconnexion
- **get_or_create pour OneToOne** : crée automatiquement la relation si inexistante
- **Export RGPD** : exclure les données sensibles (API keys) même si l'utilisateur les demande
- **Form fields vs JSON** : pour multipart/form-data avec fichier, utiliser Form() pas Body()
- **Restriction fonctionnalités par tier** : double vérification côté serveur ET côté template
- **Modal pricing** : CSS natif avec backdrop-filter pour blur, pas besoin de lib JS

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
- **Docker .env changes** : `docker-compose restart` ne relit pas les .env, utiliser `down` puis `up`
- **Ollama endpoint** : toujours ajouter `/v1` à l'URL de base pour compatibilité OpenAI
- **docker-compose context** : si un service a besoin de `../../shared`, mettre context à `.` (root)
- **KeyError ContainerConfig** : bug docker-compose, résoudre avec `down` complet avant `up`
- **Page reload perd la section active** : utiliser URL hash (`#section`) pour persister l'état
- **Polling interrompu par reload** : implémenter `resumeProcessingCVs()` pour reprendre au chargement
- **PDF scannés sans texte** : pdfplumber retourne vide, utiliser Vision LLM ou OCR
- **Prompts trop longs dans le code** : externaliser en fichiers .txt pour maintenabilité

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
- **URL hash navigation** : `history.replaceState()` + lecture du hash au load pour persister l'état UI
- **Prompts en fichiers .txt** : faciles à éditer, versionner, et itérer sans toucher au code Python
- **Détection auto PDF texte/image** : heuristique simple (min chars) avant de choisir la méthode d'extraction
- **Vision LLM + OCR fallback** : robustesse maximale pour tous types de PDF

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
- [x] Intégrer l'upload de CV dans la GUI (section "Mes documents")
- [ ] Implémenter les sections du profil (LM, pitch, succès, hobbies)
- [ ] Upload photo de profil
- [x] **Connecter GUI → cv-ingestion** : appel API après upload CV
- [x] **Test API cv-ingestion** : lancer serveur FastAPI et tester endpoint /extract
- [ ] Installer shared dans les autres microservices (offre-ingestion, matching, gui)
- [x] **Polling asynchrone** : cv-ingestion avec task_id + GUI polling
- [x] **Suppression CV** : endpoint + modal de confirmation
- [x] **Navigation hash URL** : conserver la section active après reload
- [x] **Vision LLM** : support PDF images/scannés avec GPT-4o, Claude, LLaVA
- [x] **Prompts externalisés** : fichiers .txt dans src/prompts/
- [x] **OCR fallback** : Tesseract si Vision LLM non disponible
- [x] **Toggle/Edit UI** : boutons sur les lignes extraites
- [x] **Page Gestion Compte** : settings avec identité, email, password, abonnement, LLM config
- [x] **Export RGPD** : endpoint d'export JSON des données utilisateur
- [x] **UserLLMConfig model** : permet aux users d'utiliser leur propre LLM
- [x] **LLM Config Fallback** : utilise env vars si config user vide
- [x] **Sélecteur d'abonnement** : choix du plan dans Account Settings
- [x] **Modal Pricing** : comparaison des plans avec fonctionnalités et tarifs
- [x] **Restriction LLM Config** : disponible uniquement pour Premium+
- [ ] **Édition inline** : permettre de modifier le contenu des lignes extraites
- [ ] **Regroupement expériences** : afficher les missions d'un même poste ensemble dans l'UI
- [ ] **Intégration paiement** : Stripe pour les abonnements payants
- [ ] **Validation email** : confirmation par email lors du changement d'adresse
