"""
Création des index vectoriels pour BigQuery Gold (structure 3 tables).

⚠️ PRÉREQUIS :
- Les tables suivantes doivent contenir des embeddings :
  - jobmatch_gold.offers_intitule_embeddings (colonne: intitule_embedded)
  - jobmatch_gold.offers_description_embeddings (colonne: description_embedded)
- Exécuter d'abord le script Silver → Gold qui alimente ces tables.

Ce script crée 2 index vectoriels (1 par table, conformément à la contrainte BigQuery) :
- idx_intitule_embeddings      sur offers_intitule_embeddings(intitule_embedded)
- idx_description_embeddings   sur offers_description_embeddings(description_embedded)

Les index utilisent :
- distance_type='COSINE' : similarité cosinus (optimal pour embeddings normalisés)
- index_type='IVF' : Inverted File Index (recherche KNN rapide)

Usage:
    python scripts/create_bigquery_gold_vector_indexes.py
"""

from google.cloud import bigquery

PROJECT_ID = "jobmatch-482415"
DATASET_ID = "jobmatch_gold"
LOCATION = "europe-west9"  # utile pour le debug / cohérence région

TABLE_TITLE = "offers_intitule_embeddings"
TABLE_DESC = "offers_description_embeddings"

client = bigquery.Client(project=PROJECT_ID)

print("=" * 80)
print("Création des index vectoriels pour BigQuery Gold")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1) Vérification des données (dans les 2 tables)
# -----------------------------------------------------------------------------
checks = [
    {
        "table": TABLE_TITLE,
        "column": "intitule_embedded",
        "label": "intitulé",
    },
    {
        "table": TABLE_DESC,
        "column": "description_embedded",
        "label": "description",
    },
]

print("\n[1/3] Vérification des données dans les tables...")
print("-" * 80)

row_counts: dict[str, int] = {}

for c in checks:
    table_fq = f"{PROJECT_ID}.{DATASET_ID}.{c['table']}"
    check_query = f"""
    SELECT COUNT(*) as count
    FROM `{table_fq}`
    WHERE {c["column"]} IS NOT NULL
    """  # nosec B608
    try:
        result = client.query(check_query, location=LOCATION).result()
        count = list(result)[0]["count"]
        row_counts[c["table"]] = count

        if count == 0:
            print(f"✗ ERREUR : {table_fq} est vide ou ne contient pas d'embeddings ({c['label']}).")
            print("   Veuillez d'abord exécuter le script de transformation Gold.")
        else:
            print(f"✓ {table_fq} contient {count} lignes avec embeddings ({c['label']})")
    except Exception as e:
        print(f"✗ Erreur lors de la vérification sur {table_fq}: {e}")
        raise SystemExit(1) from e

# Si une des tables est vide, on stoppe (sinon création d'index inutile)
if any(count == 0 for count in row_counts.values()):
    print("\n✗ Arrêt : au moins une table ne contient pas d'embeddings.")
    print("  → Exécute d'abord ton pipeline Silver → Gold pour la/les tables concernées.")
    raise SystemExit(1)

# -----------------------------------------------------------------------------
# 2) Création des index (1 index par table)
# -----------------------------------------------------------------------------
vector_indexes = [
    {
        "name": "idx_intitule_embeddings",
        "table": TABLE_TITLE,
        "column": "intitule_embedded",
        "description": "Index vectoriel sur les embeddings des intitulés",
    },
    {
        "name": "idx_description_embeddings",
        "table": TABLE_DESC,
        "column": "description_embedded",
        "description": "Index vectoriel sur les embeddings des descriptions",
    },
]

print("\n[2/3] Création des index vectoriels...")
print("-" * 80)

for idx in vector_indexes:
    idx_name = idx["name"]
    table_fq = f"{PROJECT_ID}.{DATASET_ID}.{idx['table']}"
    idx_column = idx["column"]

    # SQL pour créer l'index vectoriel
    create_index_query = f"""
    CREATE VECTOR INDEX IF NOT EXISTS {idx_name}
    ON `{table_fq}`({idx_column})
    OPTIONS(
        distance_type='COSINE',
        index_type='IVF'
    )
    """

    try:
        print(f"\nCréation de l'index: {idx_name}")
        print(f"  - Table: {table_fq}")
        print(f"  - Colonne: {idx_column}")
        print("  - Type de distance: COSINE")
        print("  - Type d'index: IVF")
        print(f"  - Description: {idx['description']}")

        job = client.query(create_index_query, location=LOCATION)
        job.result()

        print(f"✓ Index créé avec succès: {idx_name}")

    except Exception as e:
        error_msg = str(e).strip()
        # Important: ici "Already Exists" peut aussi signifier contrainte 1 index/table
        # mais avec notre architecture (1 index par table) ça ne devrait pas arriver,
        # sauf si tu relances le script ou si le nom existe déjà dans le dataset.
        if "already exists" in error_msg.lower():
            print(f"⚠ Index déjà existant (ou conflit) : {idx_name}\nerror : {error_msg}")
        else:
            print(f"✗ Erreur lors de la création de {idx_name}: {error_msg}")
            raise

# -----------------------------------------------------------------------------
# 3) Vérification des index (sur les 2 tables)
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[3/3] Vérification des index créés...")
print("-" * 80)

# Liste les index de la table
list_indexes_query = f"""
SELECT
  table_name,
  index_name,
  index_status,
  coverage_percentage
FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.VECTOR_INDEXES`
WHERE table_name IN ('{TABLE_TITLE}', '{TABLE_DESC}')
ORDER BY table_name, index_name
"""  # nosec B608

try:
    result = client.query(list_indexes_query, location=LOCATION).result()
    indexes = list(result)

    if indexes:
        print("\nIndex vectoriels :")
        for r in indexes:
            print(
                f"  - {r['table_name']}.{r['index_name']}: {r['index_status']} ({r['coverage_percentage']}% coverage)"
            )
    else:
        print("⚠ Aucun index trouvé (peut prendre quelques minutes pour apparaître)")
except Exception as e:
    print(f"⚠ Impossible de lister les index : {e}")

print("\n" + "=" * 80)
print("✓ Configuration de la recherche vectorielle terminée!")
print("=" * 80)
print("\n💡 Conseil : Les index peuvent prendre quelques minutes pour être")
print("   complètement optimisés. La recherche vectorielle est maintenant active.")
