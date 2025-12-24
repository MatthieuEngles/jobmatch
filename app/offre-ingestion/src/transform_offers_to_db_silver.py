"""
Transformation des offres d'emploi France Travail du format JSON (bronze) vers base de données SQLite (silver).

Ce script lit un fichier JSON d'offres d'emploi et insère les données dans une base de données SQLite
avec une structure relationnelle adaptée à un POC.

Usage:
    # Par défaut, traite les offres de la veille (J-1)
    python transform_offers_to_db_silver.py

    # Pour une date spécifique
    python transform_offers_to_db_silver.py 2025-12-10

Structure de la base de données (13 tables):
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

Fichier de sortie: data/silver/offers.db
"""

import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SILVER_DIR = DATA_DIR / "silver"
DB_PATH = SILVER_DIR / "offers.db"

Base = declarative_base()


# ----------------------------
# Définition des modèles SQLAlchemy
# ----------------------------


class Offer(Base):
    """Table principale des offres d'emploi"""

    __tablename__ = "offers"

    id = Column(String(50), primary_key=True)
    intitule = Column(Text)
    description = Column(Text)
    dateCreation = Column(String(50))
    dateActualisation = Column(String(50))
    romeCode = Column(String(10))
    romeLibelle = Column(String(255))
    appellationlibelle = Column(String(255))
    typeContrat = Column(String(10))
    typeContratLibelle = Column(String(100))
    natureContrat = Column(String(100))
    experienceExige = Column(String(10))
    experienceLibelle = Column(String(100))
    dureeTravailLibelle = Column(Text)
    dureeTravailLibelleConverti = Column(String(100))
    alternance = Column(String(10))
    nombrePostes = Column(Integer)
    accessibleTH = Column(String(10))
    qualificationCode = Column(String(10))
    qualificationLibelle = Column(String(100))
    codeNAF = Column(String(20))
    secteurActivite = Column(String(20))
    secteurActiviteLibelle = Column(String(255))
    trancheEffectifEtab = Column(String(100))
    offresManqueCandidats = Column(String(10))
    entrepriseAdaptee = Column(String(10))
    employeurHandiEngage = Column(String(10))


class LieuTravail(Base):
    """Localisation géographique des offres"""

    __tablename__ = "offers_lieu_travail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    libelle = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    codePostal = Column(String(10))
    commune = Column(String(10))


class Entreprise(Base):
    """Informations sur les entreprises"""

    __tablename__ = "offers_entreprise"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    nom = Column(String(255))
    entrepriseAdaptee = Column(String(10))


class Salaire(Base):
    """Informations salariales"""

    __tablename__ = "offers_salaire"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    libelle = Column(Text)
    commentaire = Column(Text)
    complement1 = Column(String(255))
    complement2 = Column(String(255))


class SalaireComplement(Base):
    """Compléments de rémunération (primes, etc.)"""

    __tablename__ = "offers_salaire_complements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    code = Column(String(20))
    libelle = Column(String(255))


class Competence(Base):
    """Compétences requises pour les offres"""

    __tablename__ = "offers_competences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    code = Column(String(20))
    libelle = Column(Text)
    exigence = Column(String(10))


class QualiteProfessionnelle(Base):
    """Qualités professionnelles attendues"""

    __tablename__ = "offers_qualites_professionnelles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    libelle = Column(String(255))
    description = Column(Text)


class Formation(Base):
    """Formations requises ou souhaitées"""

    __tablename__ = "offers_formations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    codeFormation = Column(String(20))
    domaineLibelle = Column(String(255))
    niveauLibelle = Column(String(255))
    commentaire = Column(Text)
    exigence = Column(String(10))


class Permis(Base):
    """Permis requis ou souhaités"""

    __tablename__ = "offers_permis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    libelle = Column(String(255))
    exigence = Column(String(10))


class Langue(Base):
    """Langues requises ou souhaitées"""

    __tablename__ = "offers_langues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    libelle = Column(String(255))
    exigence = Column(String(10))


class Contact(Base):
    """Coordonnées de contact pour postuler"""

    __tablename__ = "offers_contact"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    nom = Column(String(255))
    coordonnees1 = Column(Text)
    coordonnees2 = Column(Text)
    coordonnees3 = Column(Text)
    courriel = Column(Text)
    telephone = Column(String(50))
    urlRecruteur = Column(Text)
    commentaire = Column(Text)


class Origine(Base):
    """Origine et partenaires de l'offre"""

    __tablename__ = "offers_origine"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    origine = Column(String(10))
    urlOrigine = Column(Text)
    partenaires = Column(Text)


class ContexteTravailHoraire(Base):
    """Horaires et contexte de travail"""

    __tablename__ = "offers_contexte_travail_horaires"

    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(String(50), nullable=False, index=True)
    horaire = Column(Text)


# ----------------------------
# Fonctions utilitaires
# ----------------------------


def parse_target_date(argv: list[str]) -> date:
    """
    Parse la date cible depuis les arguments.

    - Sans argument : prend la veille (J-1 en UTC)
    - Avec argument : attend le format YYYY-MM-DD

    Args:
        argv: Arguments de la ligne de commande

    Returns:
        Date cible à traiter

    Raises:
        SystemExit: Si le format de date est invalide
    """
    if len(argv) <= 1:
        return datetime.now(UTC).date() - timedelta(days=1)

    date_str = argv[1]
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Erreur: format de date invalide '{date_str}'. Format attendu: YYYY-MM-DD")
        print("Exemple: python transform_offers_to_db_silver.py 2025-12-10")
        sys.exit(1)


def load_offers_json(json_path: Path) -> list[dict[str, Any]]:
    """
    Charge le fichier JSON des offres d'emploi.

    Args:
        json_path: Chemin vers le fichier JSON

    Returns:
        Liste des offres

    Raises:
        SystemExit: Si le fichier n'existe pas ou est invalide
    """
    if not json_path.exists():
        print(f"Erreur: fichier JSON introuvable: {json_path}")
        sys.exit(1)

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        offers = data.get("resultats", [])
        if not offers:
            print(f"Attention: aucune offre trouvée dans {json_path}")
        return offers
    except json.JSONDecodeError as e:
        print(f"Erreur: JSON invalide dans {json_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de la lecture de {json_path}: {e}")
        sys.exit(1)


def safe_get(obj: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    """
    Récupère une valeur de manière sécurisée dans un dictionnaire.

    Args:
        obj: Dictionnaire ou None
        key: Clé à récupérer
        default: Valeur par défaut si la clé n'existe pas

    Returns:
        Valeur associée à la clé ou valeur par défaut
    """
    if obj is None:
        return default
    value = obj.get(key, default)
    return value if value != "" else default


def create_database(db_url: str) -> tuple:
    """
    Crée la base de données et les tables.

    Args:
        db_url: URL de connexion à la base de données

    Returns:
        Tuple (engine, Session)
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.drop_all(engine)  # Supprime les tables existantes
    Base.metadata.create_all(engine)  # Crée toutes les tables
    Session = sessionmaker(bind=engine)
    return engine, Session


def transform_offers_to_db(offers: list[dict[str, Any]], session) -> dict[str, int]:
    """
    Transforme les offres JSON et insère dans la base de données.

    Args:
        offers: Liste des offres d'emploi
        session: Session SQLAlchemy

    Returns:
        Dictionnaire avec les statistiques d'insertion (nombre de lignes par table)
    """
    stats = {}

    # Parcourir toutes les offres
    for offer in offers:
        offer_id = offer.get("id", "")

        # 1. Table principale : offers
        offer_obj = Offer(
            id=offer_id,
            intitule=offer.get("intitule"),
            description=offer.get("description"),
            dateCreation=offer.get("dateCreation"),
            dateActualisation=offer.get("dateActualisation"),
            romeCode=offer.get("romeCode"),
            romeLibelle=offer.get("romeLibelle"),
            appellationlibelle=offer.get("appellationlibelle"),
            typeContrat=offer.get("typeContrat"),
            typeContratLibelle=offer.get("typeContratLibelle"),
            natureContrat=offer.get("natureContrat"),
            experienceExige=offer.get("experienceExige"),
            experienceLibelle=offer.get("experienceLibelle"),
            dureeTravailLibelle=offer.get("dureeTravailLibelle"),
            dureeTravailLibelleConverti=offer.get("dureeTravailLibelleConverti"),
            alternance=offer.get("alternance"),
            nombrePostes=offer.get("nombrePostes"),
            accessibleTH=offer.get("accessibleTH"),
            qualificationCode=offer.get("qualificationCode"),
            qualificationLibelle=offer.get("qualificationLibelle"),
            codeNAF=offer.get("codeNAF"),
            secteurActivite=offer.get("secteurActivite"),
            secteurActiviteLibelle=offer.get("secteurActiviteLibelle"),
            trancheEffectifEtab=offer.get("trancheEffectifEtab"),
            offresManqueCandidats=offer.get("offresManqueCandidats"),
            entrepriseAdaptee=offer.get("entrepriseAdaptee"),
            employeurHandiEngage=offer.get("employeurHandiEngage"),
        )
        session.add(offer_obj)
        stats["offers"] = stats.get("offers", 0) + 1

        # 2. Table lieu de travail
        lieu = offer.get("lieuTravail")
        if lieu:
            lieu_obj = LieuTravail(
                offer_id=offer_id,
                libelle=safe_get(lieu, "libelle"),
                latitude=safe_get(lieu, "latitude"),
                longitude=safe_get(lieu, "longitude"),
                codePostal=safe_get(lieu, "codePostal"),
                commune=safe_get(lieu, "commune"),
            )
            session.add(lieu_obj)
            stats["offers_lieu_travail"] = stats.get("offers_lieu_travail", 0) + 1

        # 3. Table entreprise
        entreprise = offer.get("entreprise")
        if entreprise:
            entreprise_obj = Entreprise(
                offer_id=offer_id,
                nom=safe_get(entreprise, "nom"),
                entrepriseAdaptee=safe_get(entreprise, "entrepriseAdaptee"),
            )
            session.add(entreprise_obj)
            stats["offers_entreprise"] = stats.get("offers_entreprise", 0) + 1

        # 4. Table salaire
        salaire = offer.get("salaire")
        if salaire:
            salaire_obj = Salaire(
                offer_id=offer_id,
                libelle=safe_get(salaire, "libelle"),
                commentaire=safe_get(salaire, "commentaire"),
                complement1=safe_get(salaire, "complement1"),
                complement2=safe_get(salaire, "complement2"),
            )
            session.add(salaire_obj)
            stats["offers_salaire"] = stats.get("offers_salaire", 0) + 1

            # 5. Table compléments salaire
            complements = salaire.get("listeComplements", [])
            for comp in complements:
                comp_obj = SalaireComplement(
                    offer_id=offer_id,
                    code=safe_get(comp, "code"),
                    libelle=safe_get(comp, "libelle"),
                )
                session.add(comp_obj)
                stats["offers_salaire_complements"] = stats.get("offers_salaire_complements", 0) + 1

        # 6. Table compétences
        competences = offer.get("competences", [])
        for comp in competences:
            comp_obj = Competence(
                offer_id=offer_id,
                code=safe_get(comp, "code"),
                libelle=safe_get(comp, "libelle"),
                exigence=safe_get(comp, "exigence"),
            )
            session.add(comp_obj)
            stats["offers_competences"] = stats.get("offers_competences", 0) + 1

        # 7. Table qualités professionnelles
        qualites = offer.get("qualitesProfessionnelles", [])
        for qual in qualites:
            qual_obj = QualiteProfessionnelle(
                offer_id=offer_id,
                libelle=safe_get(qual, "libelle"),
                description=safe_get(qual, "description"),
            )
            session.add(qual_obj)
            stats["offers_qualites_professionnelles"] = stats.get("offers_qualites_professionnelles", 0) + 1

        # 8. Table formations
        formations = offer.get("formations", [])
        for form in formations:
            form_obj = Formation(
                offer_id=offer_id,
                codeFormation=safe_get(form, "codeFormation"),
                domaineLibelle=safe_get(form, "domaineLibelle"),
                niveauLibelle=safe_get(form, "niveauLibelle"),
                commentaire=safe_get(form, "commentaire"),
                exigence=safe_get(form, "exigence"),
            )
            session.add(form_obj)
            stats["offers_formations"] = stats.get("offers_formations", 0) + 1

        # 9. Table permis
        permis_list = offer.get("permis", [])
        for permis in permis_list:
            permis_obj = Permis(
                offer_id=offer_id,
                libelle=safe_get(permis, "libelle"),
                exigence=safe_get(permis, "exigence"),
            )
            session.add(permis_obj)
            stats["offers_permis"] = stats.get("offers_permis", 0) + 1

        # 10. Table langues
        langues = offer.get("langues", [])
        for langue in langues:
            langue_obj = Langue(
                offer_id=offer_id,
                libelle=safe_get(langue, "libelle"),
                exigence=safe_get(langue, "exigence"),
            )
            session.add(langue_obj)
            stats["offers_langues"] = stats.get("offers_langues", 0) + 1

        # 11. Table contact
        contact = offer.get("contact")
        if contact:
            contact_obj = Contact(
                offer_id=offer_id,
                nom=safe_get(contact, "nom"),
                coordonnees1=safe_get(contact, "coordonnees1"),
                coordonnees2=safe_get(contact, "coordonnees2"),
                coordonnees3=safe_get(contact, "coordonnees3"),
                courriel=safe_get(contact, "courriel"),
                telephone=safe_get(contact, "telephone"),
                urlRecruteur=safe_get(contact, "urlRecruteur"),
                commentaire=safe_get(contact, "commentaire"),
            )
            session.add(contact_obj)
            stats["offers_contact"] = stats.get("offers_contact", 0) + 1

        # 12. Table origine
        origine = offer.get("origineOffre")
        if origine:
            origine_obj = Origine(
                offer_id=offer_id,
                origine=safe_get(origine, "origine"),
                urlOrigine=safe_get(origine, "urlOrigine"),
                partenaires=safe_get(origine, "partenaires"),
            )
            session.add(origine_obj)
            stats["offers_origine"] = stats.get("offers_origine", 0) + 1

        # 13. Table horaires
        contexte = offer.get("contexteTravail")
        if contexte:
            horaires = contexte.get("horaires", [])
            for horaire in horaires:
                horaire_obj = ContexteTravailHoraire(offer_id=offer_id, horaire=horaire)
                session.add(horaire_obj)
                stats["offers_contexte_travail_horaires"] = stats.get("offers_contexte_travail_horaires", 0) + 1

    # Commit toutes les insertions
    session.commit()

    return stats


def main() -> int:
    """
    Point d'entrée principal du script.

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    debut = datetime.now(UTC)

    # 1. Déterminer la date cible
    target_date = parse_target_date(sys.argv)
    json_filename = f"offer_{target_date.isoformat()}.json"
    json_path = DATA_DIR / json_filename

    print("=" * 80)
    print("TRANSFORMATION OFFRES D'EMPLOI : JSON (bronze) → SQLite (silver)")
    print("=" * 80)
    print(f"Date cible       : {target_date.isoformat()}")
    print(f"Fichier JSON     : {json_path}")
    print(f"Base de données  : {DB_PATH}")
    print("=" * 80)
    print()

    # 2. Charger les offres depuis le JSON
    offers = load_offers_json(json_path)
    print(f"Offres chargées: {len(offers)}")
    print()

    # 3. Créer la base de données
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{DB_PATH}"
    print("Création de la base de données...")
    engine, Session = create_database(db_url)
    session = Session()
    print("✓ Base de données créée avec 13 tables")
    print()

    # 4. Transformer et insérer dans la BDD
    print("Insertion des données en cours...")
    print("-" * 80)
    stats = transform_offers_to_db(offers, session)
    print("-" * 80)
    print()

    # 5. Afficher le résumé
    total_lignes = sum(stats.values())
    print("✓ Insertion terminée avec succès !")
    print(f"  Total de lignes insérées: {total_lignes}")
    print(f"  Tables remplies: {len(stats)}")
    print()

    # 6. Afficher les statistiques détaillées
    print("Statistiques détaillées:")
    print("-" * 80)
    for table_name in sorted(stats.keys()):
        count = stats[table_name]
        print(f"  {table_name:45s} : {count:6d} lignes")
    print("-" * 80)
    print()

    # 7. Fermer la session
    session.close()

    # 8. Taille du fichier DB
    db_size = DB_PATH.stat().st_size / (1024 * 1024)  # Taille en MB
    print(f"Taille du fichier DB: {db_size:.2f} MB")
    print()

    # 9. Durée d'exécution
    fin = datetime.now(UTC)
    duree = (fin - debut).total_seconds()
    print(f"Durée d'exécution: {duree:.2f} secondes")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
