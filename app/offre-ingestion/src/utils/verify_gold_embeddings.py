#!/usr/bin/env python3
"""
Script de vérification des embeddings dans la base Gold.

Affiche des statistiques et échantillons pour vérifier que les embeddings
ont été correctement générés et stockés.
"""

import sys
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLD_DB_PATH = PROJECT_ROOT / "data" / "gold" / "offers.db"


def blob_to_numpy(blob: bytes, dtype=np.float64) -> np.ndarray:
    """Reconstruit un array numpy depuis un BLOB."""
    return np.frombuffer(blob, dtype=dtype)


def verify_gold_database():
    """Vérifie et affiche des statistiques sur les embeddings de la base Gold."""

    if not GOLD_DB_PATH.exists():
        print(f"✗ Base de données Gold introuvable : {GOLD_DB_PATH}")
        sys.exit(1)

    print("=" * 70)
    print("Vérification de la base Gold (Embeddings)")
    print("=" * 70)
    print(f"📁 Fichier : {GOLD_DB_PATH}\n")

    # Connexion
    engine = create_engine(f"sqlite:///{GOLD_DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Nombre total d'offres
    count_query = text("SELECT COUNT(*) FROM offers")
    total_offers = session.execute(count_query).scalar()
    print(f"📊 Nombre total d'offres : {total_offers}")

    if total_offers == 0:
        print("\n⚠ Aucune offre dans la base Gold")
        session.close()
        return

    # 2. Récupérer quelques exemples
    sample_query = text("SELECT id, intitule_embedded, description_embedded FROM offers LIMIT 3")
    samples = session.execute(sample_query).fetchall()

    print("\n" + "=" * 70)
    print("📝 Échantillons d'embeddings")
    print("=" * 70)

    for i, (offer_id, intitule_blob, description_blob) in enumerate(samples, 1):
        print(f"\n[Offre {i}]")
        print(f"  ID: {offer_id}")

        # Convertir les blobs en arrays
        intitule_emb = blob_to_numpy(intitule_blob)
        description_emb = blob_to_numpy(description_blob)

        print("  Intitulé embedding:")
        print(f"    - Shape: {intitule_emb.shape}")
        print(f"    - Dimension: {len(intitule_emb)}")
        print(f"    - Type: {intitule_emb.dtype}")
        print(f"    - Min/Max: [{intitule_emb.min():.4f}, {intitule_emb.max():.4f}]")
        print(f"    - Norme L2: {np.linalg.norm(intitule_emb):.4f}")
        print(f"    - Premiers 5 valeurs: {intitule_emb[:5]}")

        print("  Description embedding:")
        print(f"    - Shape: {description_emb.shape}")
        print(f"    - Dimension: {len(description_emb)}")
        print(f"    - Type: {description_emb.dtype}")
        print(f"    - Min/Max: [{description_emb.min():.4f}, {description_emb.max():.4f}]")
        print(f"    - Norme L2: {np.linalg.norm(description_emb):.4f}")
        print(f"    - Premiers 5 valeurs: {description_emb[:5]}")

    # 3. Vérifier la cohérence des dimensions
    print("\n" + "=" * 70)
    print("🔍 Vérification de cohérence")
    print("=" * 70)

    # Récupérer un échantillon plus large pour vérifier
    verify_query = text("SELECT intitule_embedded, description_embedded FROM offers LIMIT 10")
    verify_samples = session.execute(verify_query).fetchall()

    dimensions_intitule = set()
    dimensions_description = set()

    for intitule_blob, description_blob in verify_samples:
        intitule_emb = blob_to_numpy(intitule_blob)
        description_emb = blob_to_numpy(description_blob)
        dimensions_intitule.add(len(intitule_emb))
        dimensions_description.add(len(description_emb))

    print(f"✓ Dimensions des embeddings d'intitulé : {dimensions_intitule}")
    print(f"✓ Dimensions des embeddings de description : {dimensions_description}")

    if len(dimensions_intitule) == 1 and len(dimensions_description) == 1:
        print("\n✅ Toutes les dimensions sont cohérentes")
    else:
        print("\n⚠ Attention : dimensions incohérentes détectées")

    # 4. Récupérer les intitulés depuis Silver pour comparaison
    silver_db_path = PROJECT_ROOT / "data" / "silver" / "offers.db"
    if silver_db_path.exists():
        engine_silver = create_engine(f"sqlite:///{silver_db_path}")
        Session_silver = sessionmaker(bind=engine_silver)
        session_silver = Session_silver()

        print("\n" + "=" * 70)
        print("📋 Comparaison avec les données source (Silver)")
        print("=" * 70)

        # Récupérer les mêmes IDs depuis Silver
        sample_ids = [s[0] for s in samples]
        placeholders = ", ".join([f":id_{i}" for i in range(len(sample_ids))])
        compare_query = text(f"SELECT id, intitule, description FROM offers WHERE id IN ({placeholders})")  # nosec B608
        params = {f"id_{i}": id_ for i, id_ in enumerate(sample_ids)}
        source_data = session_silver.execute(compare_query, params).fetchall()

        for source_id, intitule, description in source_data:
            print(f"\n[ID: {source_id}]")
            print(f"  Intitulé: {intitule[:80]}{'...' if len(intitule) > 80 else ''}")
            print(
                f"  Description: {description[:100] if description else '(vide)'}{'...' if description and len(description) > 100 else ''}"
            )

        session_silver.close()

    session.close()

    print("\n" + "=" * 70)
    print("✅ Vérification terminée")
    print("=" * 70)


if __name__ == "__main__":
    verify_gold_database()
