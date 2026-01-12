# ✅ Checklist Production - Airflow JobMatch

## 📋 Pour les développeurs

### 1️⃣ Prérequis système
- [ ] Docker et Docker Compose installés
- [ ] Git configuré
- [ ] Minimum 4 GB RAM disponibles pour Docker
- [ ] Accès au repository Git du projet
- [ ] Credentials GCP (fichier JSON service account)
- [ ] Credentials API France Travail (Client ID + Secret)

### 2️⃣ Setup initial (première fois)

```bash
# Cloner le projet
git clone <URL_DU_REPO>
cd jobmatch/app/airflow

# Configurer l'environnement
cp .env.example .env
nano .env  # Adapter avec VOS valeurs

# Variables OBLIGATOIRES à modifier dans .env :
# - HOST_AIRFLOW_PATH : votre chemin absolu
# - AIRFLOW_UID : votre UID (echo $(id -u))
# - GOOGLE_APPLICATION_CREDENTIALS
# - SMTP_USER et SMTP_PASSWORD
# - FT_CLIENT_ID et FT_CLIENT_SECRET

# Ajouter les credentials GCP
mkdir -p ./credentials
cp /chemin/vers/votre-cle-gcp.json ./credentials/gcp-service-account-key.json
chmod 600 ./credentials/gcp-service-account-key.json

# Configurer offre-ingestion
cd ../offre-ingestion
cp .env.example .env
nano .env  # Mêmes valeurs que airflow/.env

mkdir -p ./credentials
cp /chemin/vers/votre-cle-gcp.json ./credentials/gcp-service-account-key.json
```

### 3️⃣ Build des images Docker

```bash
# Depuis la RACINE du projet (important pour la dépendance 'shared')
cd /chemin/vers/jobmatch

# Build de l'image offre-ingestion
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .

# Vérification
docker images | grep offre-ingestion
```

### 4️⃣ Démarrage d'Airflow

```bash
cd app/airflow

# Permissions (Linux uniquement)
mkdir -p ./logs ./plugins
chmod -R 777 ./logs ./plugins

# Lancement
docker compose up -d

# Vérification
docker compose ps
# Tous les services doivent être UP et HEALTHY
```

### 5️⃣ Accès et activation

```
URL: http://localhost:8080
Username: airflow
Password: airflow
```

1. Se connecter à l'interface
2. Chercher le DAG `offre_ingestion_pipeline`
3. L'activer (toggle ON)
4. Tester avec le bouton ▶️ (Play)

---

## 🧪 Tests de validation

```bash
cd /chemin/vers/jobmatch/app/airflow

# 1. Vérifier que les conteneurs sont UP
docker compose ps

# 2. Vérifier que le DAG est chargé
docker compose exec airflow-scheduler airflow dags list | grep offre_ingestion

# 3. Vérifier l'accès Docker depuis Airflow
docker compose exec airflow-scheduler docker ps

# 4. Test d'exécution manuelle (optionnel, peut être long)
docker compose exec airflow-scheduler airflow tasks test offre_ingestion_pipeline fetch_offers_to_gcs 2026-01-05
```

---

## 🚨 Problèmes courants

### "Permission denied" sur /var/run/docker.sock
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### "Image offre-ingestion-pipeline not found"
```bash
# Rebuilder depuis la RACINE du projet
cd /chemin/vers/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### Le DAG n'apparaît pas
```bash
# Vérifier les logs du scheduler
docker compose logs airflow-scheduler --tail=100

# Recharger le DAG
docker compose restart airflow-scheduler
```

### Erreur "Credentials not found"
- Vérifier que le chemin dans `.env` est correct
- Vérifier que le fichier existe : `ls -la ./credentials/gcp-service-account-key.json`
- Vérifier les permissions : `chmod 600 ./credentials/gcp-service-account-key.json`

---

## 🔄 Mise à jour du code

Quand le code change :

```bash
cd /chemin/vers/jobmatch/app/airflow

# Arrêter Airflow
docker compose down

# Mettre à jour le code
git pull

# Rebuilder les images si nécessaire
cd /chemin/vers/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .

cd app/airflow
docker compose build

# Redémarrer
docker compose up -d
```

---

## 📊 Monitoring

### Via l'interface Web (recommandé)
- http://localhost:8080
- Vue "Grid" : historique des exécutions
- Vue "Graph" : visualisation du pipeline
- Vue "Logs" : logs détaillés par tâche

### Via CLI
```bash
# Logs en temps réel
docker compose logs -f airflow-scheduler

# État du DAG
docker compose exec airflow-scheduler airflow dags state offre_ingestion_pipeline
```

---

## 🛑 Arrêt et nettoyage

```bash
# Arrêt propre
docker compose down

# Arrêt avec suppression des volumes (⚠️ perte de données)
docker compose down -v

# Nettoyage des images Docker
docker system prune -a
```

---

## 📚 Documentation

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) : Guide détaillé de setup
- [README.md](./README.md) : Vue d'ensemble du projet
- [offre-ingestion README](../offre-ingestion/README.md) : Documentation du pipeline

---

## 🔐 Sécurité - IMPORTANT

### ⚠️ Ne JAMAIS commiter :
- Le fichier `.env` (contient les secrets)
- Les fichiers dans `credentials/`
- Les fichiers `*.json` (sauf exemples)
- Les logs dans `logs/`

### ✅ À commiter :
- `.env.example` (template sans secrets)
- `docker-compose.yml`
- `Dockerfile`
- Les DAGs dans `dags/`
- La documentation

### 🔒 Pour la production :
- Changer les mots de passe par défaut dans `.env`
- Utiliser des secrets managers (Vault, GCP Secret Manager)
- Limiter les permissions du service account GCP
- Activer l'authentification RBAC dans Airflow
- Configurer HTTPS pour l'interface Web
