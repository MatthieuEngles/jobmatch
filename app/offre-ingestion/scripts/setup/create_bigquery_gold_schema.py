"""
Création d'une structure BigQuery Gold permettant d'avoir
un index vectoriel sur 2 champs via 2 tables séparées (1 index par table).

Objectif :
- Une table "source" avec les champs métier
- Une table dédiée à l'index vectoriel sur l'intitulé (1 seule colonne embedding)
- Une table dédiée à l'index vectoriel sur la description (1 seule colonne embedding)

Usage:
    python scripts/create_bigquery_gold_schema.py
"""

from google.api_core.exceptions import Conflict
from google.cloud import bigquery

PROJECT_ID = "jobmatch-482415"
DATASET_ID = "jobmatch_gold"
LOCATION = "europe-west9"

client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("Création de la structure BigQuery Gold (dataset + tables)")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1) Création du dataset
# -----------------------------------------------------------------------------
dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
dataset_ref.location = LOCATION

print(f"\n[1/3] Création du dataset: {PROJECT_ID}.{DATASET_ID} (location={LOCATION})")
try:
    client.create_dataset(dataset_ref)
    print("✓ Dataset créé")
except Conflict:
    print("⚠ Dataset déjà existant")
except Exception as e:
    print(f"✗ Erreur création dataset: {e}")
    raise

# -----------------------------------------------------------------------------
# 2) Définition des schémas
# Note: all-MiniLM-L6-v2 -> dimension 384 (ARRAY<FLOAT64>)
# -----------------------------------------------------------------------------

# Table principale (métier)
schema_offers = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("intitule", "STRING"),
    bigquery.SchemaField("description", "STRING"),
    bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

# Table dédiée index "intitulé" (une seule colonne vecteur)
schema_intitule_idx = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("intitule_embedded", "FLOAT64", mode="REPEATED"),
    bigquery.SchemaField("embedding_model", "STRING"),
    bigquery.SchemaField("embedding_dimension", "INT64"),
    bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

# Table dédiée index "description" (une seule colonne vecteur)
schema_description_idx = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("description_embedded", "FLOAT64", mode="REPEATED"),
    bigquery.SchemaField("embedding_model", "STRING"),
    bigquery.SchemaField("embedding_dimension", "INT64"),
    bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

tables_schemas = {
    "offers": schema_offers,
    "offers_intitule_embeddings": schema_intitule_idx,
    "offers_description_embeddings": schema_description_idx,
}

# -----------------------------------------------------------------------------
# 3) Création des tables
# Partition: ingestion_date (DAY)
# Clustering: id
# -----------------------------------------------------------------------------
print("\n[2/3] Création des tables...")
print("-" * 80)


def create_table_if_not_exists(full_table_id: str, schema, partition_field="ingestion_date", clustering_fields=None):
    table = bigquery.Table(full_table_id, schema=schema)

    # Partitionnement par ingestion_date (recommandé pour gros volumes)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field=partition_field,
    )

    # Clustering (souvent utile pour joins/lookup par id)
    if clustering_fields:
        table.clustering_fields = clustering_fields

    try:
        client.create_table(table)
        return "created", table
    except Conflict:
        # Table déjà existante
        existing = client.get_table(full_table_id)
        return "exists", existing


for table_name, schema in tables_schemas.items():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    try:
        status, table_obj = create_table_if_not_exists(
            table_id,
            schema,
            partition_field="ingestion_date",
            clustering_fields=["id"],
        )
        if status == "created":
            print(f"✓ Table créée: {table_name}")
        else:
            print(f"⚠ Table déjà existante: {table_name}")

        print("  - Partitionnée par: ingestion_date")
        print(f"  - Clustering: {table_obj.clustering_fields}")
        print(f"  - Colonnes: {len(schema)}")
        print("  - Type embeddings: ARRAY<FLOAT64>")
    except Exception as e:
        print(f"✗ Erreur {table_name}: {e}")
        raise

# -----------------------------------------------------------------------------
# 4) Résumé + notes d'utilisation
# -----------------------------------------------------------------------------
print("\n[3/3] Résumé structure créée")
print("-" * 80)
print(f"Dataset: {PROJECT_ID}.{DATASET_ID}")
print("Tables:")
print(f"  - {DATASET_ID}.offers")
print(f"  - {DATASET_ID}.offers_intitule_embeddings")
print(f"  - {DATASET_ID}.offers_description_embeddings")

print("\n" + "=" * 80)
print("✓ Structure Gold créée.")
print("=" * 80)
