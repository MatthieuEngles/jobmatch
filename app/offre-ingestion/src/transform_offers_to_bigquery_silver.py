"""
Transformation des offres d'emploi France Travail : Bronze (GCS) → Silver (BigQuery)

Ce script lit les fichiers JSON des offres d'emploi depuis Google Cloud Storage (couche Bronze)
et les transforme en tables relationnelles dans BigQuery (couche Silver).

Usage:
    # Par défaut, traite les offres de la veille (J-1)
    python transform_offers_to_bigquery_silver.py

    # Pour une date spécifique
    python transform_offers_to_bigquery_silver.py 2025-12-28

Structure BigQuery (13 tables dans jobmatch_silver):
    - offers                               : Données principales des offres
    - offers_lieu_travail                  : Localisation géographique
    - offers_entreprise                    : Informations entreprise
    - offers_salaire                       : Informations salariales principales
    - offers_salaire_complements           : Compléments de rémunération (primes, etc.)
    - offers_competences                   : Compétences requises
    - offers_qualites_professionnelles     : Qualités professionnelles attendues
    - offers_formations                    : Formations requises/souhaitées
    - offers_permis                        : Permis requis/souhaités
    - offers_langues                       : Langues requises/souhaitées
    - offers_contact                       : Coordonnées de contact
    - offers_origine                       : Origine de l'offre
    - offers_contexte_travail_horaires     : Horaires et contexte de travail

Variables d'environnement requises:
    - GCP_PROJECT_ID : ID du projet GCP
    - GCS_BUCKET     : Nom du bucket GCS (Bronze)
Optionnelles:
    - GCS_PREFIX     : Préfixe dans le bucket (défaut: "france_travail/offers")
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from google.cloud import bigquery, storage


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


def get_env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

GCP_PROJECT_ID = require_env("GCP_PROJECT_ID")
GCS_BUCKET = require_env("GCS_BUCKET")
GCS_PREFIX = get_env("GCS_PREFIX", "france_travail/offers")
DATASET_ID = "jobmatch_silver"


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
# Lecture depuis GCS
# ----------------------------
def read_offers_from_gcs(bucket_name: str, prefix: str, target_date: date) -> list[dict[str, Any]]:
    """
    Lit le fichier JSON des offres depuis GCS pour une date donnée.

    Args:
        bucket_name: Nom du bucket GCS
        prefix: Préfixe dans le bucket
        target_date: Date des offres à lire

    Returns:
        Liste des offres d'emploi
    """
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)

    # Chemin du fichier partitionné par date
    blob_path = f"{prefix}/ingestion_date={target_date.isoformat()}/offer_{target_date.isoformat()}.json"
    blob = bucket.blob(blob_path)

    if not blob.exists():
        print(f"Erreur: fichier introuvable dans GCS: gs://{bucket_name}/{blob_path}")
        sys.exit(1)

    print(f"Lecture du fichier: gs://{bucket_name}/{blob_path}")
    content = blob.download_as_text(encoding="utf-8")
    data = json.loads(content)

    offers = data.get("resultats", [])
    if not offers:
        print("Attention: aucune offre trouvée dans le fichier")

    return offers


# ----------------------------
# Fonctions de transformation
# ----------------------------
def safe_get(obj: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    """Récupère une valeur de manière sécurisée."""
    if obj is None:
        return default
    value = obj.get(key, default)
    return value if value != "" else default


def parse_timestamp(ts_str: str | None) -> str | None:
    """Convertit une date ISO string en format compatible BigQuery."""
    if not ts_str:
        return None
    try:
        # Parse et reformate pour BigQuery
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        return None


def transform_offers_to_bigquery(
    offers: list[dict[str, Any]], target_date: date, client: bigquery.Client
) -> dict[str, int]:
    """
    Transforme les offres JSON et insère dans BigQuery.

    Args:
        offers: Liste des offres d'emploi
        target_date: Date d'ingestion
        client: Client BigQuery

    Returns:
        Dictionnaire avec les statistiques d'insertion
    """
    stats = {}
    ingestion_date_str = target_date.isoformat()

    # Préparer les données pour chaque table
    rows_offers = []
    rows_lieu = []
    rows_entreprise = []
    rows_salaire = []
    rows_salaire_complements = []
    rows_competences = []
    rows_qualites = []
    rows_formations = []
    rows_permis = []
    rows_langues = []
    rows_contact = []
    rows_origine = []
    rows_horaires = []

    print(f"Transformation de {len(offers)} offres...")

    for offer in offers:
        offer_id = offer.get("id", "")

        # 1. Table principale : offers
        rows_offers.append(
            {
                "id": offer_id,
                "intitule": offer.get("intitule"),
                "description": offer.get("description"),
                "dateCreation": parse_timestamp(offer.get("dateCreation")),
                "dateActualisation": parse_timestamp(offer.get("dateActualisation")),
                "romeCode": offer.get("romeCode"),
                "romeLibelle": offer.get("romeLibelle"),
                "appellationlibelle": offer.get("appellationlibelle"),
                "typeContrat": offer.get("typeContrat"),
                "typeContratLibelle": offer.get("typeContratLibelle"),
                "natureContrat": offer.get("natureContrat"),
                "experienceExige": offer.get("experienceExige"),
                "experienceLibelle": offer.get("experienceLibelle"),
                "dureeTravailLibelle": offer.get("dureeTravailLibelle"),
                "dureeTravailLibelleConverti": offer.get("dureeTravailLibelleConverti"),
                "alternance": offer.get("alternance"),
                "nombrePostes": offer.get("nombrePostes"),
                "accessibleTH": offer.get("accessibleTH"),
                "qualificationCode": offer.get("qualificationCode"),
                "qualificationLibelle": offer.get("qualificationLibelle"),
                "codeNAF": offer.get("codeNAF"),
                "secteurActivite": offer.get("secteurActivite"),
                "secteurActiviteLibelle": offer.get("secteurActiviteLibelle"),
                "trancheEffectifEtab": offer.get("trancheEffectifEtab"),
                "offresManqueCandidats": offer.get("offresManqueCandidats"),
                "entrepriseAdaptee": offer.get("entrepriseAdaptee"),
                "employeurHandiEngage": offer.get("employeurHandiEngage"),
                "ingestion_date": ingestion_date_str,
            }
        )

        # 2. Table lieu de travail
        lieu = offer.get("lieuTravail")
        if lieu:
            rows_lieu.append(
                {
                    "offer_id": offer_id,
                    "libelle": safe_get(lieu, "libelle"),
                    "latitude": safe_get(lieu, "latitude"),
                    "longitude": safe_get(lieu, "longitude"),
                    "codePostal": safe_get(lieu, "codePostal"),
                    "commune": safe_get(lieu, "commune"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 3. Table entreprise
        entreprise = offer.get("entreprise")
        if entreprise:
            rows_entreprise.append(
                {
                    "offer_id": offer_id,
                    "nom": safe_get(entreprise, "nom"),
                    "description": safe_get(entreprise, "description"),
                    "entrepriseAdaptee": safe_get(entreprise, "entrepriseAdaptee"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 4. Table salaire
        salaire = offer.get("salaire")
        if salaire:
            rows_salaire.append(
                {
                    "offer_id": offer_id,
                    "libelle": safe_get(salaire, "libelle"),
                    "commentaire": safe_get(salaire, "commentaire"),
                    "complement1": safe_get(salaire, "complement1"),
                    "complement2": safe_get(salaire, "complement2"),
                    "ingestion_date": ingestion_date_str,
                }
            )

            # 5. Table compléments salaire
            complements = salaire.get("listeComplements", [])
            for comp in complements:
                rows_salaire_complements.append(
                    {
                        "offer_id": offer_id,
                        "code": safe_get(comp, "code"),
                        "libelle": safe_get(comp, "libelle"),
                        "ingestion_date": ingestion_date_str,
                    }
                )

        # 6. Table compétences
        competences = offer.get("competences", [])
        for comp in competences:
            rows_competences.append(
                {
                    "offer_id": offer_id,
                    "code": safe_get(comp, "code"),
                    "libelle": safe_get(comp, "libelle"),
                    "exigence": safe_get(comp, "exigence"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 7. Table qualités professionnelles
        qualites = offer.get("qualitesProfessionnelles", [])
        for qual in qualites:
            rows_qualites.append(
                {
                    "offer_id": offer_id,
                    "libelle": safe_get(qual, "libelle"),
                    "description": safe_get(qual, "description"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 8. Table formations
        formations = offer.get("formations", [])
        for form in formations:
            rows_formations.append(
                {
                    "offer_id": offer_id,
                    "codeFormation": safe_get(form, "codeFormation"),
                    "domaineLibelle": safe_get(form, "domaineLibelle"),
                    "niveauLibelle": safe_get(form, "niveauLibelle"),
                    "commentaire": safe_get(form, "commentaire"),
                    "exigence": safe_get(form, "exigence"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 9. Table permis
        permis_list = offer.get("permis", [])
        for permis in permis_list:
            rows_permis.append(
                {
                    "offer_id": offer_id,
                    "libelle": safe_get(permis, "libelle"),
                    "exigence": safe_get(permis, "exigence"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 10. Table langues
        langues = offer.get("langues", [])
        for langue in langues:
            rows_langues.append(
                {
                    "offer_id": offer_id,
                    "libelle": safe_get(langue, "libelle"),
                    "exigence": safe_get(langue, "exigence"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 11. Table contact
        contact = offer.get("contact")
        if contact:
            rows_contact.append(
                {
                    "offer_id": offer_id,
                    "nom": safe_get(contact, "nom"),
                    "coordonnees1": safe_get(contact, "coordonnees1"),
                    "coordonnees2": safe_get(contact, "coordonnees2"),
                    "coordonnees3": safe_get(contact, "coordonnees3"),
                    "courriel": safe_get(contact, "courriel"),
                    "telephone": safe_get(contact, "telephone"),
                    "urlRecruteur": safe_get(contact, "urlRecruteur"),
                    "commentaire": safe_get(contact, "commentaire"),
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 12. Table origine
        origine = offer.get("origineOffre")
        if origine:
            # Convertir la liste de partenaires en JSON string
            partenaires = origine.get("partenaires")
            partenaires_str = json.dumps(partenaires) if partenaires else None

            rows_origine.append(
                {
                    "offer_id": offer_id,
                    "origine": safe_get(origine, "origine"),
                    "urlOrigine": safe_get(origine, "urlOrigine"),
                    "partenaires": partenaires_str,
                    "ingestion_date": ingestion_date_str,
                }
            )

        # 13. Table horaires
        contexte = offer.get("contexteTravail")
        if contexte:
            horaires = contexte.get("horaires", [])
            for horaire in horaires:
                rows_horaires.append(
                    {
                        "offer_id": offer_id,
                        "horaire": horaire,
                        "ingestion_date": ingestion_date_str,
                    }
                )

    # Insertion dans BigQuery
    print("\nInsertion dans BigQuery...")
    print("-" * 80)

    tables_data = {
        "offers": rows_offers,
        "offers_lieu_travail": rows_lieu,
        "offers_entreprise": rows_entreprise,
        "offers_salaire": rows_salaire,
        "offers_salaire_complements": rows_salaire_complements,
        "offers_competences": rows_competences,
        "offers_qualites_professionnelles": rows_qualites,
        "offers_formations": rows_formations,
        "offers_permis": rows_permis,
        "offers_langues": rows_langues,
        "offers_contact": rows_contact,
        "offers_origine": rows_origine,
        "offers_contexte_travail_horaires": rows_horaires,
    }

    jobs: list[tuple[str, bigquery.LoadJob, int]] = []

    # 1) Lancer tous les jobs (sans attendre)
    for table_name, rows in tables_data.items():
        if not rows:
            print(f"  {table_name:45s} : 0 lignes (ignoré)")
            continue

        table_id = f"{GCP_PROJECT_ID}.{DATASET_ID}.{table_name}"

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        )

        job = client.load_table_from_json(rows, table_id, job_config=job_config)
        jobs.append((table_name, job, len(rows)))
        print(f"  {table_name:45s} : job lancé ({len(rows):6d} lignes)")

    print("-" * 80)

    # 2) Attendre la fin de tous les jobs
    for table_name, job, nrows in jobs:
        job.result()  # lève une exception si le job échoue
        stats[table_name] = nrows
        print(f"  {table_name:45s} : {nrows:6d} lignes (terminé)")

    print("-" * 80)
    return stats


# ----------------------------
# Main
# ----------------------------
def main() -> int:
    """Point d'entrée principal du script."""
    debut = datetime.now(UTC)

    # 1. Déterminer la date cible
    target_date = parse_target_date(sys.argv)

    print("=" * 80)
    print("TRANSFORMATION OFFRES : Bronze (GCS) → Silver (BigQuery)")
    print("=" * 80)
    print(f"Date cible       : {target_date.isoformat()}")
    print(f"Projet GCP       : {GCP_PROJECT_ID}")
    print(f"Bucket GCS       : {GCS_BUCKET}")
    print(f"Dataset BigQuery : {DATASET_ID}")
    print("=" * 80)
    print()

    # 2. Lire les offres depuis GCS
    offers = read_offers_from_gcs(GCS_BUCKET, GCS_PREFIX, target_date)
    print(f"✓ Offres chargées depuis GCS: {len(offers)}")
    print()

    # 3. Créer le client BigQuery
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)

    # 4. Transformer et insérer dans BigQuery
    stats = transform_offers_to_bigquery(offers, target_date, bq_client)
    print()

    # 5. Afficher le résumé
    total_lignes = sum(stats.values())
    print("✓ Insertion terminée avec succès !")
    print(f"  Total de lignes insérées: {total_lignes}")
    print(f"  Tables remplies: {len(stats)}")
    print()

    # 6. Durée d'exécution
    fin = datetime.now(UTC)
    duree = (fin - debut).total_seconds()
    print(f"Durée d'exécution: {duree:.2f} secondes")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
