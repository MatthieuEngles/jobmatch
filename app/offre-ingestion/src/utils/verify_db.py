#!/usr/bin/env python3
"""
Script de vérification du contenu de la base de données offers.db
"""

from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select


def verify_database():
    """Affiche le nombre de lignes dans chaque table de la base offers.db"""
    # Chemin vers la base de données
    db_path = Path(__file__).resolve().parents[1] / "data" / "silver" / "offers.db"

    if not db_path.exists():
        print(f"❌ Base de données introuvable : {db_path}")
        return

    # Connexion à la base
    engine = create_engine(f"sqlite:///{db_path}")
    metadata = MetaData()

    print(f"\n📊 Vérification de la base : {db_path}\n")
    print("=" * 60)

    with engine.connect() as conn:
        inspector = inspect(engine)

        for table_name in sorted(inspector.get_table_names()):
            # Utiliser l'API SQLAlchemy au lieu de SQL brut
            table = Table(table_name, metadata, autoload_with=engine)
            stmt = select(func.count()).select_from(table)
            result = conn.execute(stmt)
            count = result.scalar()

            print(f"Table '{table_name}': {count} lignes")

    print("=" * 60)
    print("\n✅ Vérification terminée\n")


if __name__ == "__main__":
    verify_database()
