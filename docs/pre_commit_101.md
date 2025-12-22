# Pre-commit 101

## Qu'est-ce que pre-commit ?

Pre-commit est un framework qui exécute des vérifications automatiques **avant chaque commit**. Si une vérification échoue, le commit est bloqué.

## Comment ça marche ?

```
git commit -m "mon message"
       │
       ▼
┌─────────────────────────┐
│   Pre-commit hooks      │
│  ─────────────────────  │
│  ✓ trailing-whitespace  │
│  ✓ check-yaml           │
│  ✓ black (formatting)   │
│  ✗ flake8 (erreur!)     │
└─────────────────────────┘
       │
       ▼
   COMMIT BLOQUÉ
   (corriger et réessayer)
```

## Les hooks configurés dans le projet

| Hook | Rôle | Auto-fix ? |
|------|------|------------|
| **trailing-whitespace** | Supprime les espaces en fin de ligne | Oui |
| **end-of-file-fixer** | Ajoute une ligne vide en fin de fichier | Oui |
| **check-yaml** | Vérifie la syntaxe YAML | Non |
| **check-json** | Vérifie la syntaxe JSON | Non |
| **check-added-large-files** | Bloque les fichiers > 1MB | Non |
| **check-merge-conflict** | Détecte les marqueurs de conflit | Non |
| **detect-private-key** | Bloque les clés privées | Non |
| **no-commit-to-branch** | Interdit commit sur main/dev | Non |
| **black** | Formate le code Python | Oui |
| **isort** | Trie les imports Python | Oui |
| **flake8** | Vérifie le style Python (PEP8) | Non |
| **mypy** | Vérifie les types Python | Non |
| **bandit** | Détecte les failles de sécurité | Non |
| **gitleaks** | Détecte les secrets (API keys, passwords) | Non |

## Commandes utiles

```bash
# Installer les hooks (à faire une seule fois après clone)
pre-commit install

# Exécuter manuellement sur tous les fichiers
pre-commit run --all-files

# Exécuter un hook spécifique
pre-commit run black --all-files

# Mettre à jour les versions des hooks
pre-commit autoupdate

# Bypasser temporairement (déconseillé)
git commit --no-verify -m "message"

# Réinstaller les hooks
pre-commit install
```

## Workflow typique

```bash
# 1. Tu modifies du code
vim app/gui/src/main.py

# 2. Tu ajoutes et commit
git add .
git commit -m "[CortexForge] Ajout feature X"

# 3. Pre-commit s'exécute automatiquement
#    - Si OK → commit créé
#    - Si KO → commit bloqué, corriger et réessayer

# 4. Si black/isort ont auto-corrigé des fichiers :
git add .
git commit -m "[CortexForge] Ajout feature X"  # réessayer
```

## Exemple concret

```bash
$ git commit -m "test"

black....................................................................Failed
- hook id: black
- files were modified by this hook

reformatted app/gui/src/main.py

# Black a reformaté le fichier automatiquement
# Il suffit de re-add et re-commit :

$ git add .
$ git commit -m "test"
# Cette fois ça passe ✓
```

## Configuration

Le fichier `.pre-commit-config.yaml` à la racine du projet définit tous les hooks.

Tu peux :
- Ajouter/supprimer des hooks
- Changer les arguments (ex: `--max-line-length=120`)
- Exclure des fichiers avec `exclude: '^tests/'`

## Installation pour les nouveaux développeurs

```bash
# 1. Cloner le repo
git clone https://github.com/MatthieuEngles/jobmatch.git
cd jobmatch

# 2. Installer pre-commit
pip install pre-commit

# 3. Installer les hooks
pre-commit install

# 4. (Optionnel) Vérifier que tout fonctionne
pre-commit run --all-files
```
