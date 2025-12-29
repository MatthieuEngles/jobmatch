from google.cloud import bigquery

client = bigquery.Client(project="jobmatch-482415")
dataset_id = "jobmatch_silver"

# Définition des schémas pour les 13 tables
tables_schemas = {
    "offers": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("intitule", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("dateCreation", "TIMESTAMP"),
        bigquery.SchemaField("dateActualisation", "TIMESTAMP"),
        bigquery.SchemaField("romeCode", "STRING"),
        bigquery.SchemaField("romeLibelle", "STRING"),
        bigquery.SchemaField("appellationlibelle", "STRING"),
        bigquery.SchemaField("typeContrat", "STRING"),
        bigquery.SchemaField("typeContratLibelle", "STRING"),
        bigquery.SchemaField("natureContrat", "STRING"),
        bigquery.SchemaField("experienceExige", "STRING"),
        bigquery.SchemaField("experienceLibelle", "STRING"),
        bigquery.SchemaField("dureeTravailLibelle", "STRING"),
        bigquery.SchemaField("dureeTravailLibelleConverti", "STRING"),
        bigquery.SchemaField("alternance", "BOOLEAN"),
        bigquery.SchemaField("nombrePostes", "INT64"),
        bigquery.SchemaField("accessibleTH", "BOOLEAN"),
        bigquery.SchemaField("qualificationCode", "STRING"),
        bigquery.SchemaField("qualificationLibelle", "STRING"),
        bigquery.SchemaField("codeNAF", "STRING"),
        bigquery.SchemaField("secteurActivite", "STRING"),
        bigquery.SchemaField("secteurActiviteLibelle", "STRING"),
        bigquery.SchemaField("trancheEffectifEtab", "STRING"),
        bigquery.SchemaField("offresManqueCandidats", "BOOLEAN"),
        bigquery.SchemaField("entrepriseAdaptee", "BOOLEAN"),
        bigquery.SchemaField("employeurHandiEngage", "BOOLEAN"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_lieu_travail": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("latitude", "FLOAT64"),
        bigquery.SchemaField("longitude", "FLOAT64"),
        bigquery.SchemaField("codePostal", "STRING"),
        bigquery.SchemaField("commune", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_entreprise": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("nom", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("entrepriseAdaptee", "BOOLEAN"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_salaire": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("commentaire", "STRING"),
        bigquery.SchemaField("complement1", "STRING"),
        bigquery.SchemaField("complement2", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_salaire_complements": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("code", "STRING"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_competences": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("code", "STRING"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("exigence", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_qualites_professionnelles": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_formations": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("codeFormation", "STRING"),
        bigquery.SchemaField("domaineLibelle", "STRING"),
        bigquery.SchemaField("niveauLibelle", "STRING"),
        bigquery.SchemaField("commentaire", "STRING"),
        bigquery.SchemaField("exigence", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_permis": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("exigence", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_langues": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("libelle", "STRING"),
        bigquery.SchemaField("exigence", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_contact": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("nom", "STRING"),
        bigquery.SchemaField("coordonnees1", "STRING"),
        bigquery.SchemaField("coordonnees2", "STRING"),
        bigquery.SchemaField("coordonnees3", "STRING"),
        bigquery.SchemaField("courriel", "STRING"),
        bigquery.SchemaField("telephone", "STRING"),
        bigquery.SchemaField("urlRecruteur", "STRING"),
        bigquery.SchemaField("commentaire", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_origine": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("origine", "STRING"),
        bigquery.SchemaField("urlOrigine", "STRING"),
        bigquery.SchemaField("partenaires", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
    "offers_contexte_travail_horaires": [
        bigquery.SchemaField("offer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("horaire", "STRING"),
        bigquery.SchemaField("ingestion_date", "DATE", mode="REQUIRED"),
    ],
}

print("Création des tables BigQuery dans jobmatch_silver...")
print("=" * 80)

for table_name, schema in tables_schemas.items():
    table_id = f"jobmatch-482415.{dataset_id}.{table_name}"

    table = bigquery.Table(table_id, schema=schema)

    # Partitionnement par ingestion_date pour optimiser les requêtes
    table.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="ingestion_date")

    # Clustering sur offer_id pour optimiser les jointures
    if table_name != "offers":
        table.clustering_fields = ["offer_id"]
    else:
        table.clustering_fields = ["id", "romeCode"]

    try:
        table = client.create_table(table)
        print(f"✓ Table créée: {table_name}")
        print("  - Partitionnée par: ingestion_date")
        print(f"  - Clustering: {table.clustering_fields}")
        print(f"  - Colonnes: {len(schema)}")
    except Exception as e:
        print(f"✗ Erreur {table_name}: {str(e)}")

print("=" * 80)
print("Création des tables terminée!")
