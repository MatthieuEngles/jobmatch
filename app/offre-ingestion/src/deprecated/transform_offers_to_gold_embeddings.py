"""
Transformation des offres d'emploi de la base Silver vers la base Gold avec embeddings.

Ce script lit les offres depuis la base de données Silver (SQLite), génère des embeddings
pour les champs 'intitule' et 'description' via sentence-transformers, puis stocke
le résultat dans une base de données Gold optimisée pour la recherche sémantique.

Architecture médaillon :
    Bronze → Silver → Gold (embeddings)

Usage:
    python transform_offers_to_gold_embeddings.py

Entrée : data/silver/offers.db
Sortie : data/gold/offers.db
"""

import sys
from pathlib import Path

import numpy as np

# Import de la fonction d'embedding depuis le shared module
from shared.embeddings.providers import create_sentence_transformers_embedder
from sqlalchemy import BLOB, Column, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

SILVER_DB_PATH = SILVER_DIR / "offers.db"
GOLD_DB_PATH = GOLD_DIR / "offers.db"

# Configuration du modèle d'embedding
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 32
NORMALIZE = True  # Pour des similarités cosinus directes

Base = declarative_base()


# ----------------------------
# Modèle SQLAlchemy pour Silver (lecture)
# ----------------------------


class OfferSilver:
    """Représentation simplifiée de la table offers de Silver (lecture seule)"""

    __tablename__ = "offers"


# ----------------------------
# Modèle SQLAlchemy pour Gold (écriture)
# ----------------------------


class OfferGold(Base):
    """Table optimisée pour la recherche sémantique"""

    __tablename__ = "offers"

    id = Column(String(50), primary_key=True)
    intitule_embedded = Column(BLOB, nullable=False)
    description_embedded = Column(BLOB, nullable=False)


# ----------------------------
# Fonctions utilitaires
# ----------------------------


def numpy_to_blob(arr: np.ndarray) -> bytes:
    """Convertit un array numpy en bytes pour stockage BLOB."""
    return arr.tobytes()


def blob_to_numpy(blob: bytes, shape: tuple[int, ...], dtype=np.float64) -> np.ndarray:
    """Reconstruit un array numpy depuis un BLOB."""
    return np.frombuffer(blob, dtype=dtype).reshape(shape)


def create_gold_database():
    """Crée la base de données Gold avec le schéma requis."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{GOLD_DB_PATH}")
    Base.metadata.create_all(engine)
    print(f"✓ Base de données Gold créée : {GOLD_DB_PATH}")
    return engine


def read_offers_from_silver():
    """Lit les offres depuis la base Silver."""
    engine = create_engine(f"sqlite:///{SILVER_DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Requête SQL directe pour lire id, intitule, description
    query = text("SELECT id, intitule, description FROM offers")
    result = session.execute(query)
    offers = result.fetchall()

    session.close()
    print(f"✓ {len(offers)} offres lues depuis Silver")
    return offers


def process_and_store_embeddings(offers: list[tuple[str, str, str]]):
    """
    Génère les embeddings et les stocke dans la base Gold.

    Args:
        offers: Liste de tuples (id, intitule, description)
    """
    if not offers:
        print("⚠ Aucune offre à traiter")
        return

    # Créer l'embedder
    print(f"Initialisation du modèle d'embedding : {EMBEDDING_MODEL}")
    embedder = create_sentence_transformers_embedder(
        model=EMBEDDING_MODEL, device="cpu", batch_size=BATCH_SIZE, normalize=NORMALIZE
    )

    # Préparer les données
    ids = [offer[0] for offer in offers]
    intitules = [offer[1] or "" for offer in offers]  # Gérer les valeurs NULL
    descriptions = [offer[2] or "" for offer in offers]

    # Générer les embeddings par batch
    print(f"Génération des embeddings pour {len(offers)} offres...")
    intitules_embeddings = embedder(intitules)
    descriptions_embeddings = embedder(descriptions)

    print(f"✓ Embeddings générés : shape {intitules_embeddings.shape}")

    # Stocker dans Gold
    engine = create_gold_database()
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Insertion des données dans la base Gold...")
    for i, offer_id in enumerate(ids):
        gold_offer = OfferGold(
            id=offer_id,
            intitule_embedded=numpy_to_blob(intitules_embeddings[i]),
            description_embedded=numpy_to_blob(descriptions_embeddings[i]),
        )
        session.add(gold_offer)

        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(ids)} offres insérées")

    session.commit()
    session.close()

    print(f"✓ {len(ids)} offres avec embeddings stockées dans Gold")


# ----------------------------
# Script principal
# ----------------------------


def main():
    """Pipeline de transformation Silver → Gold"""
    print("=" * 60)
    print("Transformation Silver → Gold (Embeddings)")
    print("=" * 60)

    # Vérifications préalables
    if not SILVER_DB_PATH.exists():
        print(f"✗ Erreur : Base Silver introuvable à {SILVER_DB_PATH}")
        sys.exit(1)

    # Étape 1 : Lecture de Silver
    print("\n[1/2] Lecture des offres depuis Silver...")
    offers = read_offers_from_silver()

    # Étape 2 : Génération des embeddings et stockage dans Gold
    print("\n[2/2] Génération des embeddings et stockage dans Gold...")
    process_and_store_embeddings(offers)

    print("\n" + "=" * 60)
    print("✓ Transformation terminée avec succès")
    print(f"  Base Gold : {GOLD_DB_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
