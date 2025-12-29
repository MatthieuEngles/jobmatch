"""
count_total_offers_in_gcs.py

Compte le nombre total d'offres présentes dans tous les fichiers JSON
du bucket GCS france-travail-bronze-offers.

Usage:
  python scripts/count_total_offers_in_gcs.py

Variables d'environnement requises:
- GCS_BUCKET (défaut: "france-travail-bronze-offers")
- GCS_PREFIX (défaut: "france_travail/offers")
- GCP_PROJECT_ID
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.cloud import storage


# ----------------------------
# Utilitaires .env
# ----------------------------
def load_dotenv(dotenv_path: Path) -> None:
    """Charge un .env simple (KEY=VALUE) dans os.environ si la variable n'existe pas déjà."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ----------------------------
# Config
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

GCS_BUCKET = os.environ.get("GCS_BUCKET", "france-travail-bronze-offers")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "france_travail/offers")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")


# ----------------------------
# Fonctions
# ----------------------------
def count_offers_in_blob(bucket: storage.Bucket, blob_name: str) -> int:
    """
    Lit un fichier JSON depuis GCS et retourne le nombre d'offres (clé "resultats").
    """
    try:
        blob = bucket.blob(blob_name)
        content = blob.download_as_text(encoding="utf-8")
        data = json.loads(content)
        offers = data.get("resultats", [])
        return len(offers)
    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture de {blob_name}: {e}")
        return 0


def count_all_offers() -> None:
    """
    Liste tous les fichiers JSON dans le bucket GCS et compte le nombre total d'offres.
    """
    print(f"🔍 Connexion au bucket: gs://{GCS_BUCKET}/{GCS_PREFIX}")

    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)

    # Lister tous les blobs avec le préfixe
    blobs = list(bucket.list_blobs(prefix=GCS_PREFIX))

    # Filtrer uniquement les fichiers JSON (offre_*.json)
    json_blobs = [blob.name for blob in blobs if blob.name.endswith(".json") and "offer_" in blob.name]

    print(f"📁 {len(json_blobs)} fichiers JSON trouvés")
    print()

    total_offers = 0
    files_processed = 0

    for blob_name in json_blobs:
        count = count_offers_in_blob(bucket, blob_name)
        total_offers += count
        files_processed += 1

        # Extraire la date du chemin
        date_part = blob_name.split("/")[-2] if "/" in blob_name else "unknown"
        print(f"  ✅ {date_part}: {count:,} offres")

    print()
    print("=" * 60)
    print(f"📊 TOTAL: {total_offers:,} offres")
    print(f"📁 Fichiers traités: {files_processed}")
    print("=" * 60)


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    try:
        count_all_offers()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise


if __name__ == "__main__":
    main()
