"""
Transformation des offres d'emploi : Silver (BigQuery) → Gold (BigQuery) avec embeddings

Ce script lit les offres depuis BigQuery Silver, génère des embeddings vectoriels
pour les champs 'intitule' et 'description', puis alimente BigQuery Gold dans 3 tables :
- offers (données métier)
- offers_intitule_embeddings (embeddings + métadonnées)
- offers_description_embeddings (embeddings + métadonnées)

Usage:
    # Par défaut, traite les offres de la veille (J-1)
    python transform_offers_to_bigquery_gold.py

    # Pour une date spécifique (format YYYY-MM-DD)
    python transform_offers_to_bigquery_gold.py 2025-12-28

Architecture médaillon :
    Bronze (GCS) → Silver (BigQuery) → Gold (BigQuery + Vector Search)

"""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from google.cloud import bigquery

# Import de la fonction d'embedding depuis le shared module
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "src"))
from shared.embeddings.providers import create_sentence_transformers_embedder


# ----------------------------
# Utilitaires .env
# ----------------------------
def load_dotenv(dotenv_path: Path) -> None:
    """Charge un .env simple (KEY=VALUE) dans os.environ."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    """Récupère une variable d'env obligatoire."""
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Erreur: variable d'environnement manquante: {name}")
        sys.exit(1)
    return val


# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

GCP_PROJECT_ID = require_env("GCP_PROJECT_ID")
DATASET_SILVER = "jobmatch_silver"
DATASET_GOLD = "jobmatch_gold"

# Tables Gold
TABLE_GOLD_OFFERS = "offers"
TABLE_GOLD_TITLE = "offers_intitule_embeddings"
TABLE_GOLD_DESC = "offers_description_embeddings"

# Embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension pour all-MiniLM-L6-v2
BATCH_SIZE = 32
NORMALIZE = True  # Pour des similarités cosinus directes


# ----------------------------
# Gestion de la date
# ----------------------------
def parse_target_date(argv: list[str]) -> date:
    """Parse la date cible depuis les arguments ou prend la veille."""
    if len(argv) <= 1:
        return datetime.now(UTC).date() - timedelta(days=1)

    date_str = argv[1]
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Erreur: format de date invalide '{date_str}'. Format: YYYY-MM-DD")
        sys.exit(1)


# ----------------------------
# Lecture depuis BigQuery Silver
# ----------------------------
def read_offers_from_silver(client: bigquery.Client, target_date: date) -> list[dict[str, Any]]:
    """
    Lit les offres depuis BigQuery Silver pour une date donnée.

    Args:
        client: Client BigQuery
        target_date: Date des offres à lire

    Returns:
        Liste de dictionnaires avec id, intitule, description
    """
    table_id = f"{GCP_PROJECT_ID}.{DATASET_SILVER}.offers"
    query = f"""
    SELECT
        id,
        intitule,
        description
    FROM `{table_id}`
    WHERE ingestion_date = @target_date
    """  # nosec B608 (table_id contrôlé, valeurs provenant de variables d'env)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("target_date", "DATE", target_date)]
    )

    print(f"Lecture des offres depuis Silver (date: {target_date.isoformat()})...")
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    offers = []
    for row in results:
        offers.append(
            {
                "id": row["id"],
                "intitule": row["intitule"] or "",
                "description": row["description"] or "",
            }
        )

    if not offers:
        print(f"⚠ Attention: aucune offre trouvée pour la date {target_date.isoformat()}")
        return []

    print(f"✓ {len(offers)} offres lues depuis Silver")
    return offers


# ----------------------------
# Génération des embeddings
# ----------------------------
def generate_embeddings(offers: list[dict[str, Any]]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """
    Génère les embeddings pour les intitulés et descriptions.

    Args:
        offers: Liste des offres avec id, intitule, description

    Returns:
        Tuple (ids, intitules_embeddings, descriptions_embeddings)
    """
    if not offers:
        return [], np.array([]), np.array([])

    print(f"\nInitialisation du modèle d'embedding : {EMBEDDING_MODEL}")
    embedder = create_sentence_transformers_embedder(
        model=EMBEDDING_MODEL,
        device="cpu",
        batch_size=BATCH_SIZE,
        normalize=NORMALIZE,
    )

    # Préparer les données
    ids = [offer["id"] for offer in offers]
    intitules = [offer["intitule"] for offer in offers]
    descriptions = [offer["description"] for offer in offers]

    # Générer les embeddings par batch
    print(f"Génération des embeddings pour {len(offers)} offres...")
    print(f"  - Modèle: {EMBEDDING_MODEL}")
    print(f"  - Batch size: {BATCH_SIZE}")
    print(f"  - Normalisation: {NORMALIZE}")

    all_texts = intitules + descriptions
    all_embeddings = embedder(all_texts)

    n = len(offers)
    intitules_embeddings = all_embeddings[:n]
    descriptions_embeddings = all_embeddings[n : 2 * n]

    print("✓ Embeddings générés:")
    print(f"  - Intitulés: {intitules_embeddings.shape}")
    print(f"  - Descriptions: {descriptions_embeddings.shape}")

    return ids, intitules_embeddings, descriptions_embeddings


# ----------------------------
# Helpers insertion
# ----------------------------
def numpy_to_list(arr: np.ndarray) -> list[float]:
    """Convertit un array numpy en liste Python pour BigQuery."""
    return arr.tolist()


def delete_existing_partition(client: bigquery.Client, dataset: str, table: str, target_date: date) -> None:
    """Supprime les lignes de la partition ingestion_date = target_date (idempotence)."""
    table_id = f"{GCP_PROJECT_ID}.{dataset}.{table}"
    query = f"DELETE FROM `{table_id}` WHERE ingestion_date = @target_date"  # nosec B608
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("target_date", "DATE", target_date)]
    )
    client.query(query, job_config=job_config).result()


def load_json_rows(client: bigquery.Client, full_table_id: str, rows: list[dict[str, Any]]) -> int:
    """Charge des lignes JSON dans une table BigQuery."""
    if not rows:
        return 0

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(rows, full_table_id, job_config=job_config)
    job.result()
    return len(rows)


# ----------------------------
# Insertion dans Gold (3 tables)
# ----------------------------
def insert_to_gold(
    client: bigquery.Client,
    offers: list[dict[str, Any]],
    ids: list[str],
    intitules_embeddings: np.ndarray,
    descriptions_embeddings: np.ndarray,
    target_date: date,
) -> tuple[int, int, int]:
    """
    Insère les données dans les 3 tables BigQuery Gold.
    Args:
        client: Client BigQuery
        offers: Liste des offres (id, intitule, description)
        ids: Liste des ids des offres
        intitules_embeddings: Embeddings des intitulés
        descriptions_embeddings: Embeddings des descriptions
        target_date: Date d'ingestion

    Returns:
        Tuple (n_offers, n_title, n_desc) nombre de lignes insérées dans chaque table
    """
    if not ids:
        return 0, 0, 0

    print("\nPréparation des données pour insertion...")

    # Créer un mapping id -> offer pour récupérer les textes
    offers_by_id = {offer["id"]: offer for offer in offers}

    # 1) Table offers (métier)
    offers_rows: list[dict[str, Any]] = []
    for offer_id in ids:
        offer = offers_by_id[offer_id]
        offers_rows.append(
            {
                "id": offer_id,
                "intitule": offer["intitule"],
                "description": offer["description"],
                "ingestion_date": target_date.isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    # 2) Table offers_intitule_embeddings
    title_rows: list[dict[str, Any]] = []
    for i, offer_id in enumerate(ids):
        title_rows.append(
            {
                "id": offer_id,
                "intitule_embedded": numpy_to_list(intitules_embeddings[i]),
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": EMBEDDING_DIMENSION,
                "ingestion_date": target_date.isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    # 3) Table offers_description_embeddings
    desc_rows: list[dict[str, Any]] = []
    for i, offer_id in enumerate(ids):
        desc_rows.append(
            {
                "id": offer_id,
                "description_embedded": numpy_to_list(descriptions_embeddings[i]),
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": EMBEDDING_DIMENSION,
                "ingestion_date": target_date.isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    # Idempotence: on purge la partition de la date cible dans chaque table
    print("\nPurge des partitions existantes (idempotence)...")
    delete_existing_partition(client, DATASET_GOLD, TABLE_GOLD_OFFERS, target_date)
    delete_existing_partition(client, DATASET_GOLD, TABLE_GOLD_TITLE, target_date)
    delete_existing_partition(client, DATASET_GOLD, TABLE_GOLD_DESC, target_date)
    print("✓ Partitions purgées")

    # Chargements
    full_offers_id = f"{GCP_PROJECT_ID}.{DATASET_GOLD}.{TABLE_GOLD_OFFERS}"
    full_title_id = f"{GCP_PROJECT_ID}.{DATASET_GOLD}.{TABLE_GOLD_TITLE}"
    full_desc_id = f"{GCP_PROJECT_ID}.{DATASET_GOLD}.{TABLE_GOLD_DESC}"

    print("\nInsertion dans BigQuery Gold...")
    print(f"  - offers: {full_offers_id}")
    print(f"  - intitule: {full_title_id}")
    print(f"  - description: {full_desc_id}")
    print(f"  - lignes: {len(ids)}")

    n1 = load_json_rows(client, full_offers_id, offers_rows)
    n2 = load_json_rows(client, full_title_id, title_rows)
    n3 = load_json_rows(client, full_desc_id, desc_rows)

    print(f"✓ Insertions terminées: offers={n1}, intitule_embeddings={n2}, description_embeddings={n3}")
    return n1, n2, n3


# ----------------------------
# Main
# ----------------------------
def main() -> int:
    """Point d'entrée principal du script."""
    debut = datetime.now(UTC)

    # 1. Déterminer la date cible
    target_date = parse_target_date(sys.argv)
    print("=" * 80)
    print("TRANSFORMATION OFFRES : Silver (BigQuery) → Gold (BigQuery + Embeddings)")
    print("=" * 80)
    print(f"Date cible         : {target_date.isoformat()}")
    print(f"Projet GCP         : {GCP_PROJECT_ID}")
    print(f"Dataset Silver     : {DATASET_SILVER}")
    print(f"Dataset Gold       : {DATASET_GOLD}")
    print(f"Tables Gold        : {TABLE_GOLD_OFFERS}, {TABLE_GOLD_TITLE}, {TABLE_GOLD_DESC}")
    print(f"Modèle embedding   : {EMBEDDING_MODEL}")
    print(f"Dimension vecteurs : {EMBEDDING_DIMENSION}")
    print("=" * 80)
    print()

    # 2. Créer le client BigQuery
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)

    # 3. Lire les offres depuis Silver
    print("[1/3] Lecture des offres depuis BigQuery Silver...")
    print("-" * 80)
    debut_lecture = datetime.now(UTC)
    offers = read_offers_from_silver(bq_client, target_date)
    fin_lecture = datetime.now(UTC)

    if not offers:
        print("\n⚠ Aucune offre à traiter. Script terminé.")
        return 0

    # 4. Générer les embeddings
    print("\n[2/3] Génération des embeddings vectoriels...")
    print("-" * 80)
    debut_embedding = datetime.now(UTC)
    ids, intitules_embeddings, descriptions_embeddings = generate_embeddings(offers)
    fin_embedding = datetime.now(UTC)

    # 5. Insérer dans Gold
    print("\n[3/3] Insertion dans BigQuery Gold...")
    print("-" * 80)
    debut_insertion = datetime.now(UTC)
    n_offers, n_title, n_desc = insert_to_gold(
        bq_client,
        offers,
        ids,
        intitules_embeddings,
        descriptions_embeddings,
        target_date,
    )
    fin_insertion = datetime.now(UTC)

    # 6. Résumé
    print()
    print("=" * 80)
    print("✓ Transformation Silver → Gold terminée !")
    print(f"  Offres traitées            : {len(offers)}")
    print(f"  Lignes insérées offers     : {n_offers}")
    print(f"  Lignes insérées intitulé   : {n_title}")
    print(f"  Lignes insérées description: {n_desc}")
    print(f"  Embeddings créés           : {len(offers) * 2}")
    print()

    # 7. Durée d'exécution
    fin = datetime.now(UTC)
    print("Durée d'exécution:")
    print(f"  - Total              : {(fin - debut).total_seconds():.2f} s")
    print(f"  - Lecture Silver     : {(fin_lecture - debut_lecture).total_seconds():.2f} s")
    print(f"  - Génération embeds  : {(fin_embedding - debut_embedding).total_seconds():.2f} s")
    print(f"  - Insertion Gold     : {(fin_insertion - debut_insertion).total_seconds():.2f} s")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
