# ⚡ Quickstart - Airflow Orchestration

Guide rapide pour lancer Airflow après un `git pull`.

## 🚀 Setup en 5 minutes

### 1. Configuration de l'environnement

```bash
cd app/airflow

# Copier et éditer le .env
cp .env.example .env
nano .env
```

**À modifier dans `.env` :**
```bash
HOST_AIRFLOW_PATH=/home/VOTRE_USERNAME/jobmatch/app/airflow  # Votre chemin absolu
AIRFLOW_UID=$(id -u)  # Votre UID (1000, 1001, etc.)

# Vos credentials Gmail pour notifications
SMTP_USER=votre.email@gmail.com
SMTP_PASSWORD=votre_app_password

# Vos credentials France Travail
FT_CLIENT_ID=votre_client_id
FT_CLIENT_SECRET=votre_client_secret
```

### 2. Ajouter les credentials GCP

```bash
# Placer votre fichier de clé GCP
mkdir -p ./credentials
cp /chemin/vers/votre-cle.json ./credentials/gcp-service-account-key.json
```

### 3. Configurer offre-ingestion

```bash
cd ../offre-ingestion

# Copier et éditer (mêmes valeurs que airflow)
cp .env.example .env
nano .env

# Ajouter aussi les credentials GCP ici
mkdir -p ./credentials
cp /chemin/vers/votre-cle.json ./credentials/gcp-service-account-key.json
```

### 4. Build de l'image offre-ingestion

```bash
# IMPORTANT : depuis la RACINE du projet (pour la dépendance 'shared')
cd /home/VOTRE_USERNAME/jobmatch

docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### 5. Lancer Airflow

```bash
cd app/airflow

# Permissions (Linux uniquement)
mkdir -p ./logs ./plugins
chmod -R 777 ./logs ./plugins

# Démarrage
docker compose up -d

# Vérifier que tout tourne
docker compose ps
```

### 6. Utiliser Airflow

**Interface web :** http://localhost:8080
**Login :** `airflow` / `airflow`

1. Activer le DAG `offre_ingestion_pipeline` (toggle)
2. Cliquer sur ▶️ pour lancer manuellement

---

## ✅ Test rapide

```bash
cd app/airflow

# Vérifier les conteneurs
docker compose ps

# Vérifier le DAG
docker compose exec airflow-scheduler airflow dags list | grep offre_ingestion
```

---

## 🐛 Problèmes courants

**"Image offre-ingestion-pipeline not found"**
```bash
cd /home/VOTRE_USERNAME/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

**"Permission denied" sur Docker**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Le DAG n'apparaît pas**
```bash
docker compose restart airflow-scheduler
```

---

## 📚 Plus de détails

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) : Guide complet avec explications
- [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md) : Checklist de validation
