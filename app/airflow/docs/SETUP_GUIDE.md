# 🚀 Guide de Setup Airflow - JobMatch

Ce guide vous permet de configurer Airflow sur votre machine en partant de zéro.

## 📋 Prérequis

- **Docker** et **Docker Compose** installés
- **Git** pour cloner le projet
- **Credentials GCP** (fichier JSON de service account)
- **API France Travail** (Client ID et Secret)
- Minimum **4 GB de RAM** disponibles pour Docker

## 🏁 Setup complet (nouvel utilisateur)

### 1️⃣ Cloner le projet

```bash
git clone <URL_DU_REPO>
cd jobmatch/app/airflow
```

### 2️⃣ Configurer les variables d'environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos valeurs
nano .env  # ou vim, code, etc.
```

**Variables OBLIGATOIRES à modifier :**
- `HOST_AIRFLOW_PATH` : Chemin absolu vers votre dossier airflow
- `AIRFLOW_UID` : Votre UID Linux (obtenu avec `echo $(id -u)`)
- `GOOGLE_APPLICATION_CREDENTIALS` : Chemin vers votre clé GCP
- `SMTP_USER` et `SMTP_PASSWORD` : Pour les notifications email
- `FT_CLIENT_ID` et `FT_CLIENT_SECRET` : Credentials API France Travail

**Exemple de configuration :**
```bash
HOST_AIRFLOW_PATH=/home/jean.dupont/jobmatch/app/airflow
AIRFLOW_UID=1000
SMTP_USER=jean.dupont@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
```

### 3️⃣ Ajouter les credentials GCP

```bash
# Créer le dossier credentials
mkdir -p ./credentials

# Copier votre fichier de service account GCP
cp /chemin/vers/votre/cle-gcp.json ./credentials/gcp-service-account-key.json

# Vérifier les permissions
chmod 600 ./credentials/gcp-service-account-key.json
```

### 4️⃣ Configurer le fichier .env dans offre-ingestion

```bash
cd ../offre-ingestion

# Copier le template
cp .env.example .env

# Éditer avec les mêmes valeurs que pour Airflow
nano .env
```

**Important :** Les credentials doivent aussi être copiés dans offre-ingestion :
```bash
mkdir -p ./credentials
cp /chemin/vers/votre/cle-gcp.json ./credentials/gcp-service-account-key.json
```

### 5️⃣ Construire l'image Docker offre-ingestion

```bash
# Retour à la racine du projet
cd /home/VOTRE_USERNAME/jobmatch

# Build de l'image (depuis la racine car dépendance de 'shared')
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

Cette commande :
- Installe le package `jobmatch-shared` avec les embeddings
- Installe les dépendances Python
- Configure le entrypoint pour router les commandes (fetch/silver/gold)

**Vérification :**
```bash
docker images | grep offre-ingestion
# Doit afficher : offre-ingestion-pipeline:latest
```

### 6️⃣ Configurer les permissions (Linux uniquement)

```bash
cd app/airflow

# Créer les dossiers nécessaires
mkdir -p ./logs ./plugins ./config

# Donner les permissions
chmod -R 777 ./logs ./plugins
```

### 7️⃣ Lancer Airflow

```bash
# Build et démarrage
docker compose up -d

# Vérifier que tous les services sont UP
docker compose ps
```

Vous devriez voir 4 conteneurs :
- `airflow-webserver` (port 8080)
- `airflow-scheduler`
- `airflow-init` (état: Exited 0)
- `postgres`

### 8️⃣ Accéder à l'interface Airflow

```
URL: http://localhost:8080
Username: airflow
Password: airflow
```

(À moins que vous ayez changé dans .env)

### 9️⃣ Activer et tester le DAG

1. Dans l'interface, chercher le DAG `offre_ingestion_pipeline`
2. Activer le toggle (bouton ON/OFF)
3. Cliquer sur le bouton ▶️ (Play) pour lancer manuellement
4. Observer l'exécution dans la vue Graph ou Grid

## 🧪 Test de validation complet

Exécutez ces commandes pour valider que tout fonctionne :

```bash
# 1. Vérifier que les conteneurs sont actifs
docker compose ps

# 2. Vérifier les logs du scheduler
docker compose logs airflow-scheduler --tail=50

# 3. Tester l'accès au webserver
curl http://localhost:8080/health

# 4. Vérifier que l'image offre-ingestion est disponible
docker images | grep offre-ingestion

# 5. Tester l'exécution d'un script du pipeline (en dehors d'Airflow)
docker run --rm \
  -v $PWD/../offre-ingestion/credentials/gcp-service-account-key.json:/app/credentials/gcp-key.json:ro \
  -v $PWD/../offre-ingestion/.env:/app/src/.env:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-key.json \
  offre-ingestion-pipeline:latest fetch --help
```

## 🐛 Troubleshooting

### Erreur : "Permission denied" sur /var/run/docker.sock

```bash
# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer la session
newgrp docker
```

### Erreur : "Image offre-ingestion-pipeline not found"

```bash
# Rebuilder l'image depuis la racine
cd /chemin/vers/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### Erreur : "Credentials not found"

Vérifier que le chemin dans `.env` pointe vers le bon fichier :
```bash
ls -la $(grep GOOGLE_APPLICATION_CREDENTIALS .env | cut -d'=' -f2 | tr -d '"')
```

### Le DAG ne démarre pas

```bash
# Consulter les logs du scheduler
docker compose logs airflow-scheduler -f

# Vérifier que le fichier DAG n'a pas d'erreur
docker compose exec airflow-scheduler python -c "from dags.offre_ingestion_dag import dag"
```

### Les tâches Docker échouent

```bash
# Vérifier l'accès au socket Docker depuis le conteneur
docker compose exec airflow-scheduler docker ps

# Si erreur, vérifier les permissions
ls -la /var/run/docker.sock
```

## 📊 Surveillance et logs

```bash
# Logs en temps réel
docker compose logs -f

# Logs d'un service spécifique
docker compose logs airflow-scheduler -f

# Logs d'une tâche Airflow (dans l'interface web)
http://localhost:8080/dags/offre_ingestion_pipeline/grid
```

## 🛑 Arrêter Airflow

```bash
# Arrêt propre
docker compose down

# Arrêt avec suppression des volumes (⚠️ perte des données)
docker compose down -v
```

## 🔄 Mise à jour

Quand le code change :

```bash
# 1. Arrêter Airflow
docker compose down

# 2. Rebuild l'image offre-ingestion si nécessaire
cd /chemin/vers/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .

# 3. Rebuild Airflow si le Dockerfile a changé
cd app/airflow
docker compose build

# 4. Redémarrer
docker compose up -d
```

## 📚 Ressources

- [Documentation Airflow](https://airflow.apache.org/docs/)
- [Pipeline offre-ingestion](../offre-ingestion/docs/README.md)
- [DockerOperator Guide](https://airflow.apache.org/docs/apache-airflow-providers-docker/stable/operators/docker.html)
