# =============================================================================
# JobMatch V0 - BigQuery
# =============================================================================

# -----------------------------------------------------------------------------
# Silver Dataset (Transformed offers data)
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "silver" {
  dataset_id                 = "jobmatch_silver"
  project                    = var.project_id
  location                   = var.region
  description                = "Silver layer - Transformed job offers data"
  delete_contents_on_destroy = true

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Gold Dataset (Aggregated data and KPIs)
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset" "gold" {
  dataset_id                 = "jobmatch_gold"
  project                    = var.project_id
  location                   = var.region
  description                = "Gold layer - Aggregated data and KPIs"
  delete_contents_on_destroy = true

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Silver Tables
# -----------------------------------------------------------------------------

# Main offers table
resource "google_bigquery_table" "offers" {
  dataset_id          = google_bigquery_dataset.silver.dataset_id
  table_id            = "offers"
  project             = var.project_id
  deletion_protection = false
  description         = "Main job offers table"

  schema = jsonencode([
    { name = "id", type = "STRING", mode = "REQUIRED", description = "Offer ID" },
    { name = "intitule", type = "STRING", mode = "NULLABLE", description = "Job title" },
    { name = "description", type = "STRING", mode = "NULLABLE", description = "Job description" },
    { name = "date_creation", type = "TIMESTAMP", mode = "NULLABLE", description = "Creation date" },
    { name = "date_actualisation", type = "TIMESTAMP", mode = "NULLABLE", description = "Last update date" },
    { name = "lieu_travail_libelle", type = "STRING", mode = "NULLABLE", description = "Work location" },
    { name = "lieu_travail_code_postal", type = "STRING", mode = "NULLABLE", description = "Postal code" },
    { name = "entreprise_nom", type = "STRING", mode = "NULLABLE", description = "Company name" },
    { name = "type_contrat", type = "STRING", mode = "NULLABLE", description = "Contract type" },
    { name = "type_contrat_libelle", type = "STRING", mode = "NULLABLE", description = "Contract type label" },
    { name = "nature_contrat", type = "STRING", mode = "NULLABLE", description = "Contract nature" },
    { name = "experience_exige", type = "STRING", mode = "NULLABLE", description = "Required experience" },
    { name = "experience_libelle", type = "STRING", mode = "NULLABLE", description = "Experience label" },
    { name = "salaire_libelle", type = "STRING", mode = "NULLABLE", description = "Salary label" },
    { name = "salaire_min", type = "FLOAT64", mode = "NULLABLE", description = "Minimum salary" },
    { name = "salaire_max", type = "FLOAT64", mode = "NULLABLE", description = "Maximum salary" },
    { name = "duree_travail_libelle", type = "STRING", mode = "NULLABLE", description = "Work duration" },
    { name = "code_rome", type = "STRING", mode = "NULLABLE", description = "ROME code" },
    { name = "libelle_rome", type = "STRING", mode = "NULLABLE", description = "ROME label" },
    { name = "secteur_activite", type = "STRING", mode = "NULLABLE", description = "Business sector" },
    { name = "qualification_code", type = "STRING", mode = "NULLABLE", description = "Qualification code" },
    { name = "qualification_libelle", type = "STRING", mode = "NULLABLE", description = "Qualification label" },
    { name = "origine_offre", type = "STRING", mode = "NULLABLE", description = "Offer source" },
    { name = "url_origine", type = "STRING", mode = "NULLABLE", description = "Original URL" },
    { name = "ingestion_date", type = "TIMESTAMP", mode = "NULLABLE", description = "Ingestion timestamp" },
    { name = "source_file", type = "STRING", mode = "NULLABLE", description = "Source file name" },
  ])

  labels = var.labels
}

# Skills table
resource "google_bigquery_table" "offer_skills" {
  dataset_id          = google_bigquery_dataset.silver.dataset_id
  table_id            = "offer_skills"
  project             = var.project_id
  deletion_protection = false
  description         = "Required skills per offer"

  schema = jsonencode([
    { name = "offer_id", type = "STRING", mode = "REQUIRED", description = "Foreign key to offers" },
    { name = "skill_code", type = "STRING", mode = "NULLABLE", description = "Skill code" },
    { name = "skill_libelle", type = "STRING", mode = "NULLABLE", description = "Skill label" },
    { name = "skill_exigence", type = "STRING", mode = "NULLABLE", description = "Requirement level (E/S)" },
  ])

  labels = var.labels
}

# Formations table
resource "google_bigquery_table" "offer_formations" {
  dataset_id          = google_bigquery_dataset.silver.dataset_id
  table_id            = "offer_formations"
  project             = var.project_id
  deletion_protection = false
  description         = "Required formations per offer"

  schema = jsonencode([
    { name = "offer_id", type = "STRING", mode = "REQUIRED", description = "Foreign key to offers" },
    { name = "formation_code", type = "STRING", mode = "NULLABLE", description = "Formation code" },
    { name = "formation_libelle", type = "STRING", mode = "NULLABLE", description = "Formation label" },
    { name = "formation_niveau", type = "STRING", mode = "NULLABLE", description = "Education level" },
    { name = "formation_exigence", type = "STRING", mode = "NULLABLE", description = "Requirement level" },
  ])

  labels = var.labels
}

# Languages table
resource "google_bigquery_table" "offer_languages" {
  dataset_id          = google_bigquery_dataset.silver.dataset_id
  table_id            = "offer_languages"
  project             = var.project_id
  deletion_protection = false
  description         = "Required languages per offer"

  schema = jsonencode([
    { name = "offer_id", type = "STRING", mode = "REQUIRED", description = "Foreign key to offers" },
    { name = "langue_code", type = "STRING", mode = "NULLABLE", description = "Language code" },
    { name = "langue_libelle", type = "STRING", mode = "NULLABLE", description = "Language label" },
    { name = "langue_niveau", type = "STRING", mode = "NULLABLE", description = "Language level" },
    { name = "langue_exigence", type = "STRING", mode = "NULLABLE", description = "Requirement level" },
  ])

  labels = var.labels
}

# -----------------------------------------------------------------------------
# Gold Tables
# -----------------------------------------------------------------------------

# Daily statistics
resource "google_bigquery_table" "offers_daily_stats" {
  dataset_id          = google_bigquery_dataset.gold.dataset_id
  table_id            = "offers_daily_stats"
  project             = var.project_id
  deletion_protection = false
  description         = "Daily offer statistics"

  schema = jsonencode([
    { name = "date", type = "DATE", mode = "REQUIRED", description = "Statistics date" },
    { name = "total_offers", type = "INT64", mode = "NULLABLE", description = "Total offers count" },
    { name = "new_offers", type = "INT64", mode = "NULLABLE", description = "New offers today" },
    { name = "cdi_count", type = "INT64", mode = "NULLABLE", description = "CDI offers count" },
    { name = "cdd_count", type = "INT64", mode = "NULLABLE", description = "CDD offers count" },
    { name = "interim_count", type = "INT64", mode = "NULLABLE", description = "Interim offers count" },
    { name = "avg_salary_min", type = "FLOAT64", mode = "NULLABLE", description = "Average min salary" },
    { name = "avg_salary_max", type = "FLOAT64", mode = "NULLABLE", description = "Average max salary" },
  ])

  labels = var.labels
}

# Skills ranking
resource "google_bigquery_table" "skills_ranking" {
  dataset_id          = google_bigquery_dataset.gold.dataset_id
  table_id            = "skills_ranking"
  project             = var.project_id
  deletion_protection = false
  description         = "Most requested skills ranking"

  schema = jsonencode([
    { name = "date", type = "DATE", mode = "REQUIRED", description = "Ranking date" },
    { name = "skill_code", type = "STRING", mode = "NULLABLE", description = "Skill code" },
    { name = "skill_libelle", type = "STRING", mode = "NULLABLE", description = "Skill label" },
    { name = "offer_count", type = "INT64", mode = "NULLABLE", description = "Number of offers" },
    { name = "rank", type = "INT64", mode = "NULLABLE", description = "Ranking position" },
  ])

  labels = var.labels
}

# -----------------------------------------------------------------------------
# IAM - VM Service Account access to BigQuery
# -----------------------------------------------------------------------------

resource "google_bigquery_dataset_iam_member" "vm_silver_editor" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_bigquery_dataset_iam_member" "vm_gold_editor" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.vm.email}"
}
