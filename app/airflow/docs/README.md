# 🚀 Airflow Orchestration - JobMatch

Orchestration du pipeline ETL offre-ingestion avec Apache Airflow.

## 📋 Vue d'ensemble

Ce module orchestre le pipeline ETL d'ingestion des offres d'emploi France Travail :
1. **Fetch** : Récupération des offres depuis l'API → GCS
2. **Silver** : Transformation et nettoyage → BigQuery Silver
3. **Gold** : Enrichissement avec embeddings → BigQuery Gold

## 🏗️ Architecture

```
airflow/
├── docker-compose.yml    # Configuration des services Airflow
├── Dockerfile            # Image Airflow personnalisée
├── requirements.txt      # Dépendances Python
├── .env                  # Variables d'environnement
├── dags/                 # DAGs Airflow
│   └── offre_ingestion_dag.py
├── logs/                 # Logs d'exécution
├── plugins/              # Plugins personnalisés
└── config/               # Configuration supplémentaire
```

## 🚀 Quick Start

### 1. Configuration initiale

```bash
# Se placer dans le dossier airflow
cd /home/mohamede.madiouni/jobmatch/app/airflow

# Copier et adapter le fichier .env
cp .env .env.local
# Éditer .env.local pour pointer vers vos credentials GCP
```

### 2. Configurer les permissions (Linux uniquement)

```bash
# Obtenir votre UID
echo $(id -u)

# Mettre à jour AIRFLOW_UID dans .env.local si nécessaire
echo "AIRFLOW_UID=$(id -u)" >> .env.local

# Créer les dossiers avec les bonnes permissions
mkdir -p ./logs ./plugins
chmod -R 777 ./logs ./plugins
```

### 3. Build de l'image offre-ingestion (si pas déjà fait)

```bash
cd /home/mohamede.madiouni/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### 4. Démarrage d'Airflow

```bash
cd /home/mohamede.madiouni/jobmatch/app/airflow

# Initialiser la base de données et créer les services
docker compose up -d

# Vérifier que tous les services sont lancés
docker compose ps
```

### 5. Accéder à l'interface Airflow

```
URL: http://localhost:8080
Username: airflow
Password: airflow
```

## 📊 Utilisation

### Interface Web

1. Aller sur http://localhost:8080
2. Se connecter avec `airflow/airflow`
3. Activer le DAG `offre_ingestion_pipeline`
4. Déclencher manuellement : bouton ▶️ (Play)

### Configuration des variables Airflow

Le DAG nécessite la variable `GOOGLE_APPLICATION_CREDENTIALS` :

```bash
# Via CLI
docker compose exec airflow-webserver airflow variables set \
  GOOGLE_APPLICATION_CREDENTIALS \
  /opt/airflow/credentials/gcp-key.json

# Ou via l'interface Web :
Admin → Variables → + →
Key: GOOGLE_APPLICATION_CREDENTIALS
Value: /opt/airflow/credentials/gcp-key.json
```

### Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f airflow-scheduler

# Lister les DAGs
docker compose exec airflow-webserver airflow dags list

# Tester un DAG sans l'exécuter
docker compose exec airflow-webserver airflow dags test offre_ingestion_pipeline 2025-01-01

# Lancer manuellement une tâche spécifique
docker compose exec airflow-webserver airflow tasks test offre_ingestion_pipeline fetch_offers_to_gcs 2025-01-01

# Arrêter Airflow
docker compose down

# Supprimer tout (y compris la base de données)
docker compose down -v
```

## ⚙️ Configuration du DAG

### Scheduling

Par défaut : **Tous les jours à 2h du matin**

Modifier dans [dags/offre_ingestion_dag.py](dags/offre_ingestion_dag.py):
```python
schedule_interval='0 2 * * *',  # Cron expression
```

### Paramètres d'exécution

- **Date d'exécution** : `{{ ds }}` (format YYYY-MM-DD)
- **Retry** : 1 tentative avec 5 minutes de délai
- **Catchup** : Désactivé (ne rattrape pas les exécutions passées)

### Structure du DAG

```
fetch_offers_to_gcs
        ↓
transform_to_bigquery_silver
        ↓
transform_to_bigquery_gold
```

## 🔧 Troubleshooting

### Problème de permissions

```bash
# Donner les permissions aux dossiers
chmod -R 777 logs/ plugins/

# Ou changer l'ownership
chown -R $(id -u):$(id -g) logs/ plugins/
```

### Image offre-ingestion non trouvée

```bash
# Rebuilder l'image depuis la racine du projet
cd /home/mohamede.madiouni/jobmatch
docker build -f app/offre-ingestion/Dockerfile -t offre-ingestion-pipeline:latest .
```

### Erreur de connexion Docker

Le conteneur Airflow doit avoir accès au socket Docker :
- Vérifier que `/var/run/docker.sock` est bien monté dans docker-compose.yml
- Vérifier les permissions : `ls -la /var/run/docker.sock`

### Credentials GCP non trouvés

```bash
# Vérifier le chemin dans .env
cat .env.local | grep GOOGLE_APPLICATION_CREDENTIALS

# Vérifier que le fichier existe
ls -la /chemin/vers/gcp-key.json

# Mettre à jour la variable Airflow
docker compose exec airflow-webserver airflow variables set \
  GOOGLE_APPLICATION_CREDENTIALS \
  /opt/airflow/credentials/gcp-key.json
```

### Configuration Auto-Shutdown de la VM

Le DAG peut automatiquement éteindre la VM GCP après succès du pipeline pour réduire les coûts.

**Prérequis :**
1. Configurer les variables dans `.env` :
   ```bash
   GCP_VM_NAME=votre-vm-name
   GCP_VM_ZONE=europe-west9-b
   ```

2. Donner les permissions au service account :
   ```bash
   gcloud projects add-iam-policy-binding jobmatch-482415 \
     --member="serviceAccount:VOTRE_SERVICE_ACCOUNT@jobmatch-482415.iam.gserviceaccount.com" \
     --role="roles/compute.instanceAdmin.v1"
   ```

3. Rebuilder l'image Airflow pour inclure gcloud CLI :
   ```bash
   docker compose build
   docker compose up -d
   ```

**Comment ça fonctionne :**
- Le callback `shutdown_vm_on_success` s'exécute uniquement si tout le DAG réussit
- Un délai de 30 secondes permet à Airflow de finaliser les logs
- La VM s'éteint via l'API GCP de manière propre et auditable
- En cas d'échec du pipeline, la VM reste allumée pour debug

## 📚 Documentation

- [Apache Airflow](https://airflow.apache.org/docs/)
- [DockerOperator](https://airflow.apache.org/docs/apache-airflow-providers-docker/stable/operators/docker.html)
- [Pipeline offre-ingestion](../offre-ingestion/docs/README.md)

## 🔐 Sécurité

- Ne commitez **jamais** le fichier `.env.local` avec vos credentials
- Les credentials GCP sont montés en **read-only** dans les conteneurs
- Changez les mots de passe par défaut dans `.env.local` pour la production
