"""
DAG Airflow pour orchestrer le pipeline ETL offre-ingestion
Exécute les 3 étapes : fetch → silver → gold
"""

import os
import subprocess
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator


def shutdown_vm_on_success(context):
    """
    Callback exécuté après le succès complet du DAG.
    Arrête la VM GCP avec un délai de 30 secondes pour permettre
    à Airflow de finaliser l'écriture des statuts et logs.
    """
    vm_name = os.environ.get("GCP_VM_NAME")
    zone = os.environ.get("GCP_VM_ZONE", "europe-west9-b")

    if not vm_name:
        print("⚠️ GCP_VM_NAME non défini, impossible d'arrêter la VM")
        return

    print(f"✅ Pipeline terminé avec succès ! Arrêt de la VM {vm_name} dans 30 secondes...")

    # Authentification avec le service account et arrêt de la VM
    cmd = f"""sleep 30 && \
        gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS && \
        gcloud compute instances stop {vm_name} --zone={zone}"""

    # Lancer le shutdown en arrière-plan (détaché) pour que le callback se termine proprement
    subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("⏰ Commande d'arrêt GCP programmée.")


# Configuration par défaut du DAG
default_args = {
    "owner": "jobmatch-FT-ingestion",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "email": ["mohamede.madiouni@gmail.com"],
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "on_success_callback": shutdown_vm_on_success,
}

# Initialisation du DAG
with DAG(
    "offre_ingestion_pipeline",
    default_args=default_args,
    description="Pipeline ETL pour ingestion des offres d'emploi France Travail",
    schedule_interval="57 22 * * *",  # Tous les jours à 9h30 (heure de Paris)
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Paris"),  # Un jour avant pour exécution aujourd'hui
    catchup=False,
    tags=["etl", "offre-ingestion", "bigquery"],
) as dag:
    # Chemin vers les credentials GCP (construit dynamiquement depuis HOST_AIRFLOW_PATH)
    # Chaque développeur configure HOST_AIRFLOW_PATH dans son .env local
    host_airflow_path = os.environ.get("HOST_AIRFLOW_PATH", "/home/mohamede.madiouni/jobmatch/app/airflow")
    gcp_credentials_path = f"{host_airflow_path}/credentials/gcp-service-account-key.json"

    # Chemin vers le .env du pipeline offre-ingestion (sur le HOST)
    offre_ingestion_env_path = f"{host_airflow_path}/../offre-ingestion/.env"

    # Configuration commune pour tous les opérateurs Docker
    docker_common_config = {
        "image": "offre-ingestion-pipeline:latest",
        "api_version": "auto",
        "auto_remove": True,
        "docker_url": "unix://var/run/docker.sock",
        "network_mode": "bridge",
        "mount_tmp_dir": False,
        # Montage des volumes nécessaires
        "mounts": [
            # Credentials GCP (le script les cherche à /app/credentials/gcp-key.json)
            {
                "source": gcp_credentials_path,
                "target": "/app/credentials/gcp-key.json",
                "type": "bind",
                "read_only": True,
            },
            # Fichier .env d'offre-ingestion (le script le cherche à /app/src/.env)
            # car PROJECT_ROOT = parents[1] depuis /app/src/pipelines/script.py
            {"source": offre_ingestion_env_path, "target": "/app/src/.env", "type": "bind", "read_only": True},
        ],
        "environment": {"GOOGLE_APPLICATION_CREDENTIALS": "/app/credentials/gcp-key.json"},
    }

    # Tâche 1: Fetch des offres depuis l'API France Travail vers GCS
    fetch_offers = DockerOperator(
        task_id="fetch_offers_to_gcs",
        command=["fetch"],
        **docker_common_config,
    )

    # Tâche 2: Transformation vers BigQuery Silver (nettoyage et structuration)
    transform_to_silver = DockerOperator(
        task_id="transform_to_bigquery_silver",
        command=["silver"],
        **docker_common_config,
    )

    # Tâche 3: Transformation vers BigQuery Gold (embeddings vectoriels)
    transform_to_gold = DockerOperator(
        task_id="transform_to_bigquery_gold",
        command=["gold"],
        **docker_common_config,
    )

    # Définition de l'ordre d'exécution des tâches
    fetch_offers >> transform_to_silver >> transform_to_gold
