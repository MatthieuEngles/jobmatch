from google.cloud import bigquery

client = bigquery.Client(project="jobmatch-482415")
dataset_id = "jobmatch_gold"

# Définition du schéma pour la table Gold
# Note: all-MiniLM-L6-v2 génère des embeddings de dimension 384
tables_schemas = {
    "offers_embeddings": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("intitule", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("intitule_embedded", "FLOAT64", mode="REPEATED"),
        bigquery.SchemaField("description_embedded", "FLOAT64", mode="REPEATED"),
        bigquery.SchemaField("embedding_model", "STRING"),
        bigquery.SchemaField("embedding_dimension", "INT64"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ],
}

print("Création de la table BigQuery dans jobmatch_gold...")
print("=" * 80)

for table_name, schema in tables_schemas.items():
    table_id = f"jobmatch-482415.{dataset_id}.{table_name}"

    table = bigquery.Table(table_id, schema=schema)

    # Partitionnement par ingestion_date pour optimiser les requêtes
    table.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="ingestion_date")

    # Clustering sur id pour optimiser les recherches
    table.clustering_fields = ["id"]

    try:
        table = client.create_table(table)
        print(f"✓ Table créée: {table_name}")
        print("  - Partitionnée par: ingestion_date")
        print(f"  - Clustering: {table.clustering_fields}")
        print(f"  - Colonnes: {len(schema)}")
        print("  - Type embeddings: ARRAY<FLOAT64>")
    except Exception as e:
        print(f"✗ Erreur {table_name}: {str(e)}")

print("=" * 80)
print("✓ Création de la table terminée!")
print("=" * 80)
print("\n⚠️  IMPORTANT : Les index vectoriels seront créés automatiquement")
print("après la première insertion de données avec embeddings.")
print("\nUtilisez le script 'create_bigquery_gold_vector_indexes.py'")
print("après avoir inséré vos premières offres avec embeddings.")
print("=" * 80)
