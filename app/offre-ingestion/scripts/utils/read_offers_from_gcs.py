"""
read_offers_from_gcs.py

Lit un fichier JSON d'offres d'emploi depuis Google Cloud Storage (GCS)
et en affiche un aperçu pour inspection manuelle (volume, colonnes, exemples).
Ce script est destiné au debug et à la validation de données.
Il ne modifie ni n'écrit aucune donnée.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
from google.cloud import storage

# ----------------------------
# Config (via variables d'env)
# ----------------------------
GCS_BUCKET = os.environ.get("GCS_BUCKET", "france-travail-bronze-offers")
GCS_OBJECT = os.environ.get(
    "GCS_OBJECT",
    "france_travail/offers/ingestion_date=2025-12-25/offer_2025-12-25.json",
)

# Optionnel mais recommandé
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")


# ----------------------------
# Lecture GCS
# ----------------------------
def load_json_from_gcs(bucket_name: str, object_name: str) -> dict[str, Any]:
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    raw = blob.download_as_text(encoding="utf-8")
    return json.loads(raw)


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    payload = load_json_from_gcs(GCS_BUCKET, GCS_OBJECT)

    offers = payload.get("resultats", [])
    print(f"Nombre d'offres chargées: {len(offers)}")

    df = pd.DataFrame(offers)

    # Affiche uniquement les 2 premières lignes
    print("\nAperçu (2 premières lignes) :")
    print(df["dateCreation"].head(2))

    print("\nColonnes détectées :")
    print(list(df.columns))


if __name__ == "__main__":
    main()
