"""
Transformation des offres d'emploi France Travail du format JSON (bronze) vers CSV (silver).

Ce script lit un fichier JSON d'offres d'emploi et le transforme en plusieurs fichiers CSV
normalisés, selon une structure relationnelle adaptée à un POC.

Usage:
    # Par défaut, traite les offres de la veille (J-1)
    python transform_offers_to_csv_silver.py

    # Pour une date spécifique
    python transform_offers_to_csv_silver.py 2025-12-10

Structure de sortie (13 fichiers CSV):
    - offers.csv                               : Données principales des offres
    - offers_lieu_travail.csv                  : Localisation géographique
    - offers_entreprise.csv                    : Informations entreprise
    - offers_salaire.csv                       : Informations salariales principales
    - offers_salaire_complements.csv           : Compléments de rémunération (primes, etc.)
    - offers_competences.csv                   : Compétences requises
    - offers_qualites_professionnelles.csv     : Qualités professionnelles attendues
    - offers_formations.csv                    : Formations requises/souhaitées
    - offers_permis.csv                        : Permis requis/souhaités
    - offers_langues.csv                       : Langues requises/souhaitées
    - offers_contact.csv                       : Coordonnées de contact
    - offers_origine.csv                       : Origine de l'offre
    - offers_contexte_travail_horaires.csv     : Horaires et contexte de travail
"""

import csv
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

# ----------------------------
# Configuration
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SILVER_DIR = DATA_DIR / "silver"


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
        print("Exemple: python transform_offers_to_csv_silver.py 2025-12-10")
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


def safe_get(obj: dict[str, Any] | None, key: str, default: Any = "") -> Any:
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
    return obj.get(key, default)


def clean_text(value: Any) -> str:
    """
    Nettoie une valeur texte en remplaçant les retours à la ligne par \\n (séquence échappée).

    Cela permet de préserver l'information des retours à la ligne tout en évitant
    qu'ils cassent la structure du CSV. Plus tard, on pourra reconvertir \\n en \n.

    Args:
        value: Valeur à nettoyer (peut être None, str, ou autre type)

    Returns:
        Chaîne nettoyée avec retours à la ligne échappés
    """
    if value is None:
        return ""
    text = str(value)
    # Remplace \r\n, \n, et \r par la séquence littérale \\n
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def write_csv(filepath: Path, data: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """
    Écrit des données dans un fichier CSV.

    Utilise QUOTE_ALL pour garantir que tous les champs sont entre guillemets,
    ce qui permet de préserver les retours à la ligne (\n) dans les cellules.

    Args:
        filepath: Chemin du fichier CSV de sortie
        data: Données à écrire (liste de dictionnaires)
        fieldnames: Noms des colonnes
    """
    if not data:
        # Créer un fichier vide avec juste les en-têtes
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
        return

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)


def transform_offers_to_csv(offers: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    """
    Transforme les offres JSON en plusieurs fichiers CSV normalisés.

    Args:
        offers: Liste des offres d'emploi
        output_dir: Répertoire de sortie pour les CSV

    Returns:
        Dictionnaire avec les statistiques de transformation (nombre de lignes par table)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialiser les listes pour chaque table
    main_offers = []
    lieu_travail_rows = []
    entreprise_rows = []
    salaire_rows = []
    salaire_complements_rows = []
    competences_rows = []
    qualites_rows = []
    formations_rows = []
    permis_rows = []
    langues_rows = []
    contact_rows = []
    origine_rows = []
    horaires_rows = []

    # Parcourir toutes les offres
    for offer in offers:
        offer_id = offer.get("id", "")

        # 1. Table principale : offers.csv
        main_offers.append(
            {
                "id": offer_id,
                "intitule": clean_text(offer.get("intitule", "")),
                "description": clean_text(offer.get("description", "")),
                "dateCreation": offer.get("dateCreation", ""),
                "dateActualisation": offer.get("dateActualisation", ""),
                "romeCode": offer.get("romeCode", ""),
                "romeLibelle": clean_text(offer.get("romeLibelle", "")),
                "appellationlibelle": clean_text(offer.get("appellationlibelle", "")),
                "typeContrat": offer.get("typeContrat", ""),
                "typeContratLibelle": clean_text(offer.get("typeContratLibelle", "")),
                "natureContrat": clean_text(offer.get("natureContrat", "")),
                "experienceExige": offer.get("experienceExige", ""),
                "experienceLibelle": clean_text(offer.get("experienceLibelle", "")),
                "dureeTravailLibelle": clean_text(offer.get("dureeTravailLibelle", "")),
                "dureeTravailLibelleConverti": clean_text(offer.get("dureeTravailLibelleConverti", "")),
                "alternance": offer.get("alternance", ""),
                "nombrePostes": offer.get("nombrePostes", ""),
                "accessibleTH": offer.get("accessibleTH", ""),
                "qualificationCode": offer.get("qualificationCode", ""),
                "qualificationLibelle": clean_text(offer.get("qualificationLibelle", "")),
                "codeNAF": offer.get("codeNAF", ""),
                "secteurActivite": offer.get("secteurActivite", ""),
                "secteurActiviteLibelle": clean_text(offer.get("secteurActiviteLibelle", "")),
                "trancheEffectifEtab": clean_text(offer.get("trancheEffectifEtab", "")),
                "offresManqueCandidats": offer.get("offresManqueCandidats", ""),
                "entrepriseAdaptee": offer.get("entrepriseAdaptee", ""),
                "employeurHandiEngage": offer.get("employeurHandiEngage", ""),
            }
        )

        # 2. Table lieu de travail : offers_lieu_travail.csv
        lieu = offer.get("lieuTravail")
        if lieu:
            lieu_travail_rows.append(
                {
                    "offer_id": offer_id,
                    "libelle": clean_text(safe_get(lieu, "libelle")),
                    "latitude": safe_get(lieu, "latitude"),
                    "longitude": safe_get(lieu, "longitude"),
                    "codePostal": safe_get(lieu, "codePostal"),
                    "commune": safe_get(lieu, "commune"),
                }
            )

        # 3. Table entreprise : offers_entreprise.csv
        entreprise = offer.get("entreprise")
        if entreprise:
            entreprise_rows.append(
                {
                    "offer_id": offer_id,
                    "nom": clean_text(safe_get(entreprise, "nom")),
                    "entrepriseAdaptee": safe_get(entreprise, "entrepriseAdaptee"),
                }
            )

        # 4. Table salaire : offers_salaire.csv
        salaire = offer.get("salaire")
        if salaire:
            salaire_rows.append(
                {
                    "offer_id": offer_id,
                    "libelle": clean_text(safe_get(salaire, "libelle")),
                    "commentaire": clean_text(safe_get(salaire, "commentaire")),
                    "complement1": clean_text(safe_get(salaire, "complement1")),
                    "complement2": clean_text(safe_get(salaire, "complement2")),
                }
            )

            # 5. Table compléments salaire : offers_salaire_complements.csv
            complements = salaire.get("listeComplements", [])
            for comp in complements:
                salaire_complements_rows.append(
                    {
                        "offer_id": offer_id,
                        "code": safe_get(comp, "code"),
                        "libelle": clean_text(safe_get(comp, "libelle")),
                    }
                )

        # 6. Table compétences : offers_competences.csv
        competences = offer.get("competences", [])
        for comp in competences:
            competences_rows.append(
                {
                    "offer_id": offer_id,
                    "code": safe_get(comp, "code"),
                    "libelle": clean_text(safe_get(comp, "libelle")),
                    "exigence": safe_get(comp, "exigence"),
                }
            )

        # 7. Table qualités professionnelles : offers_qualites_professionnelles.csv
        qualites = offer.get("qualitesProfessionnelles", [])
        for qual in qualites:
            qualites_rows.append(
                {
                    "offer_id": offer_id,
                    "libelle": clean_text(safe_get(qual, "libelle")),
                    "description": clean_text(safe_get(qual, "description")),
                }
            )

        # 8. Table formations : offers_formations.csv
        formations = offer.get("formations", [])
        for form in formations:
            formations_rows.append(
                {
                    "offer_id": offer_id,
                    "codeFormation": safe_get(form, "codeFormation"),
                    "domaineLibelle": clean_text(safe_get(form, "domaineLibelle")),
                    "niveauLibelle": clean_text(safe_get(form, "niveauLibelle")),
                    "commentaire": clean_text(safe_get(form, "commentaire")),
                    "exigence": safe_get(form, "exigence"),
                }
            )

        # 9. Table permis : offers_permis.csv
        permis_list = offer.get("permis", [])
        for permis in permis_list:
            permis_rows.append(
                {
                    "offer_id": offer_id,
                    "libelle": clean_text(safe_get(permis, "libelle")),
                    "exigence": safe_get(permis, "exigence"),
                }
            )

        # 10. Table langues : offers_langues.csv
        langues = offer.get("langues", [])
        for langue in langues:
            langues_rows.append(
                {
                    "offer_id": offer_id,
                    "libelle": clean_text(safe_get(langue, "libelle")),
                    "exigence": safe_get(langue, "exigence"),
                }
            )

        # 11. Table contact : offers_contact.csv
        contact = offer.get("contact")
        if contact:
            contact_rows.append(
                {
                    "offer_id": offer_id,
                    "nom": clean_text(safe_get(contact, "nom")),
                    "coordonnees1": clean_text(safe_get(contact, "coordonnees1")),
                    "coordonnees2": clean_text(safe_get(contact, "coordonnees2")),
                    "coordonnees3": clean_text(safe_get(contact, "coordonnees3")),
                    "courriel": clean_text(safe_get(contact, "courriel")),
                    "telephone": clean_text(safe_get(contact, "telephone")),
                    "urlRecruteur": clean_text(safe_get(contact, "urlRecruteur")),
                    "commentaire": clean_text(safe_get(contact, "commentaire")),
                }
            )

        # 12. Table origine : offers_origine.csv
        origine = offer.get("origineOffre")
        if origine:
            origine_rows.append(
                {
                    "offer_id": offer_id,
                    "origine": safe_get(origine, "origine"),
                    "urlOrigine": clean_text(safe_get(origine, "urlOrigine")),
                    "partenaires": clean_text(safe_get(origine, "partenaires")),
                }
            )

        # 13. Table horaires : offers_contexte_travail_horaires.csv
        contexte = offer.get("contexteTravail")
        if contexte:
            horaires = contexte.get("horaires", [])
            for horaire in horaires:
                horaires_rows.append({"offer_id": offer_id, "horaire": clean_text(horaire)})

    # Écriture de tous les fichiers CSV
    csv_files = [
        ("offers.csv", main_offers, list(main_offers[0].keys()) if main_offers else []),
        (
            "offers_lieu_travail.csv",
            lieu_travail_rows,
            ["offer_id", "libelle", "latitude", "longitude", "codePostal", "commune"],
        ),
        (
            "offers_entreprise.csv",
            entreprise_rows,
            ["offer_id", "nom", "entrepriseAdaptee"],
        ),
        (
            "offers_salaire.csv",
            salaire_rows,
            ["offer_id", "libelle", "commentaire", "complement1", "complement2"],
        ),
        (
            "offers_salaire_complements.csv",
            salaire_complements_rows,
            ["offer_id", "code", "libelle"],
        ),
        (
            "offers_competences.csv",
            competences_rows,
            ["offer_id", "code", "libelle", "exigence"],
        ),
        (
            "offers_qualites_professionnelles.csv",
            qualites_rows,
            ["offer_id", "libelle", "description"],
        ),
        (
            "offers_formations.csv",
            formations_rows,
            [
                "offer_id",
                "codeFormation",
                "domaineLibelle",
                "niveauLibelle",
                "commentaire",
                "exigence",
            ],
        ),
        ("offers_permis.csv", permis_rows, ["offer_id", "libelle", "exigence"]),
        ("offers_langues.csv", langues_rows, ["offer_id", "libelle", "exigence"]),
        (
            "offers_contact.csv",
            contact_rows,
            [
                "offer_id",
                "nom",
                "coordonnees1",
                "coordonnees2",
                "coordonnees3",
                "courriel",
                "telephone",
                "urlRecruteur",
                "commentaire",
            ],
        ),
        (
            "offers_origine.csv",
            origine_rows,
            ["offer_id", "origine", "urlOrigine", "partenaires"],
        ),
        (
            "offers_contexte_travail_horaires.csv",
            horaires_rows,
            ["offer_id", "horaire"],
        ),
    ]

    stats = {}
    for filename, data, fieldnames in csv_files:
        filepath = output_dir / filename
        write_csv(filepath, data, fieldnames)
        stats[filename] = len(data)
        print(f"✓ {filename:45s} : {len(data):6d} lignes")

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
    print("TRANSFORMATION OFFRES D'EMPLOI : JSON (bronze) → CSV (silver)")
    print("=" * 80)
    print(f"Date cible       : {target_date.isoformat()}")
    print(f"Fichier JSON     : {json_path}")
    print(f"Répertoire sortie: {SILVER_DIR}")
    print("=" * 80)
    print()

    # 2. Charger les offres depuis le JSON
    offers = load_offers_json(json_path)
    print(f"Offres chargées: {len(offers)}")
    print()

    # 3. Transformer en CSV
    print("Transformation en cours...")
    print("-" * 80)
    stats = transform_offers_to_csv(offers, SILVER_DIR)
    print("-" * 80)
    print()

    # 4. Afficher le résumé
    total_lignes = sum(stats.values())
    print("✓ Transformation terminée avec succès !")
    print(f"  Total de lignes générées: {total_lignes}")
    print(f"  Fichiers CSV créés: {len(stats)}")
    print()

    # 5. Afficher les statistiques détaillées
    print("Statistiques détaillées:")
    print("-" * 80)
    for filename, count in sorted(stats.items()):
        print(f"  {filename:45s} : {count:6d} lignes")
    print("-" * 80)
    print()

    # 6. Durée d'exécution
    fin = datetime.now(UTC)
    duree = (fin - debut).total_seconds()
    print(f"Durée d'exécution: {duree:.2f} secondes")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
