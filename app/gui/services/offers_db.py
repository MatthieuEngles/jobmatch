"""
Offers database abstraction for retrieving offer details.

Provides interface to get offer details for display.
Supports both BigQuery (production) and SQLite (development/testing).
"""

import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OfferDetails:
    """Offer details for display in the UI."""

    id: str
    intitule: str  # Job title
    entreprise: str | None  # Company name
    description: str | None  # Job description


@dataclass
class OfferFullDetails:
    """Complete offer details for modal display."""

    id: str
    intitule: str
    description: str | None
    entreprise: str | None
    type_contrat: str | None
    experience: str | None
    duree_travail: str | None
    lieu: str | None
    salaire: str | None
    date_creation: str | None
    rome_libelle: str | None
    secteur_activite: str | None
    competences: list[str] | None
    qualites: list[str] | None


class OffersDB(ABC):
    """Abstract base class for offers database implementations."""

    @abstractmethod
    def get_offers_by_ids(self, offer_ids: list[str]) -> dict[str, OfferDetails]:
        """
        Get offer details for a list of offer IDs.

        Args:
            offer_ids: List of offer IDs to retrieve

        Returns:
            Dictionary mapping offer_id to OfferDetails
        """
        pass

    @abstractmethod
    def get_offer_full_details(self, offer_id: str) -> OfferFullDetails | None:
        """
        Get complete offer details for modal display.

        Args:
            offer_id: The offer ID to retrieve

        Returns:
            OfferFullDetails or None if not found
        """
        pass


class SQLiteOffersDB(OffersDB):
    """SQLite implementation for development and testing."""

    def __init__(self, db_path: str | Path):
        """
        Initialize with path to SQLite database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)

    def get_offers_by_ids(self, offer_ids: list[str]) -> dict[str, OfferDetails]:
        """Get offer details from SQLite database."""
        if not offer_ids:
            return {}

        if not self.db_path.exists():
            logger.warning(f"SQLite DB not found at {self.db_path}")
            return {}

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build query with placeholders
            placeholders = ",".join("?" * len(offer_ids))

            # Query offers with enterprise join
            cursor.execute(
                f"""
                SELECT
                    o.id,
                    o.intitule,
                    o.description,
                    e.nom as entreprise
                FROM offers o
                LEFT JOIN offers_entreprise e ON o.id = e.offer_id
                WHERE o.id IN ({placeholders})
                """,
                offer_ids,
            )

            results = {}
            for row in cursor.fetchall():
                results[row["id"]] = OfferDetails(
                    id=row["id"],
                    intitule=row["intitule"] or "Sans titre",
                    entreprise=row["entreprise"],
                    description=row["description"],
                )

            conn.close()
            return results

        except sqlite3.Error as e:
            logger.error(f"SQLite error getting offers: {e}")
            return {}

    def get_offer_full_details(self, offer_id: str) -> OfferFullDetails | None:
        """Get complete offer details from SQLite database."""
        if not self.db_path.exists():
            logger.warning(f"SQLite DB not found at {self.db_path}")
            return None

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get main offer data with joins
            cursor.execute(
                """
                SELECT
                    o.id,
                    o.intitule,
                    o.description,
                    o.typeContratLibelle,
                    o.experienceLibelle,
                    o.dureeTravailLibelleConverti,
                    o.dateCreation,
                    o.romeLibelle,
                    o.secteurActiviteLibelle,
                    e.nom as entreprise,
                    l.libelle as lieu,
                    s.libelle as salaire
                FROM offers o
                LEFT JOIN offers_entreprise e ON o.id = e.offer_id
                LEFT JOIN offers_lieu_travail l ON o.id = l.offer_id
                LEFT JOIN offers_salaire s ON o.id = s.offer_id
                WHERE o.id = ?
                """,
                (offer_id,),
            )

            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            # Get competences
            cursor.execute(
                "SELECT libelle FROM offers_competences WHERE offer_id = ?",
                (offer_id,),
            )
            competences = [r["libelle"] for r in cursor.fetchall() if r["libelle"]]

            # Get qualites professionnelles
            cursor.execute(
                "SELECT libelle FROM offers_qualites_professionnelles WHERE offer_id = ?",
                (offer_id,),
            )
            qualites = [r["libelle"] for r in cursor.fetchall() if r["libelle"]]

            conn.close()

            return OfferFullDetails(
                id=row["id"],
                intitule=row["intitule"] or "Sans titre",
                description=row["description"],
                entreprise=row["entreprise"],
                type_contrat=row["typeContratLibelle"],
                experience=row["experienceLibelle"],
                duree_travail=row["dureeTravailLibelleConverti"],
                lieu=row["lieu"],
                salaire=row["salaire"],
                date_creation=row["dateCreation"],
                rome_libelle=row["romeLibelle"],
                secteur_activite=row["secteurActiviteLibelle"],
                competences=competences if competences else None,
                qualites=qualites if qualites else None,
            )

        except sqlite3.Error as e:
            logger.error(f"SQLite error getting full offer details: {e}")
            return None


class BigQueryOffersDB(OffersDB):
    """BigQuery implementation for production."""

    def __init__(self, project_id: str, dataset: str = "gold"):
        """
        Initialize BigQuery client.

        Args:
            project_id: GCP project ID
            dataset: BigQuery dataset name (default: gold)
        """
        self.project_id = project_id
        self.dataset = dataset
        self._client = None

    @property
    def client(self):
        """Lazy load BigQuery client."""
        if self._client is None:
            try:
                from google.cloud import bigquery

                self._client = bigquery.Client(project=self.project_id)
            except ImportError as e:
                raise ImportError(
                    "google-cloud-bigquery is required for BigQuery support. "
                    "Install with: pip install google-cloud-bigquery"
                ) from e
        return self._client

    def get_offers_by_ids(self, offer_ids: list[str]) -> dict[str, OfferDetails]:
        """Get offer details from BigQuery."""
        if not offer_ids:
            return {}

        try:
            # Build query with parameterized values
            query = f"""
                SELECT
                    o.id,
                    o.intitule,
                    o.description,
                    e.nom as entreprise
                FROM `{self.project_id}.{self.dataset}.offers` o
                LEFT JOIN `{self.project_id}.{self.dataset}.offers_entreprise` e
                    ON o.id = e.offer_id
                WHERE o.id IN UNNEST(@offer_ids)
            """

            job_config = self.client.QueryJobConfig(
                query_parameters=[self.client.ArrayQueryParameter("offer_ids", "STRING", offer_ids)]
            )

            results = {}
            for row in self.client.query(query, job_config=job_config):
                results[row.id] = OfferDetails(
                    id=row.id,
                    intitule=row.intitule or "Sans titre",
                    entreprise=row.entreprise,
                    description=row.description,
                )

            return results

        except Exception as e:
            logger.error(f"BigQuery error getting offers: {e}")
            return {}

    def get_offer_full_details(self, offer_id: str) -> OfferFullDetails | None:
        """Get complete offer details from BigQuery."""
        try:
            # Main query with all details
            query = f"""
                SELECT
                    o.id,
                    o.intitule,
                    o.description,
                    o.typeContratLibelle,
                    o.experienceLibelle,
                    o.dureeTravailLibelleConverti,
                    o.dateCreation,
                    o.romeLibelle,
                    o.secteurActiviteLibelle,
                    e.nom as entreprise,
                    l.libelle as lieu,
                    s.libelle as salaire
                FROM `{self.project_id}.{self.dataset}.offers` o
                LEFT JOIN `{self.project_id}.{self.dataset}.offers_entreprise` e ON o.id = e.offer_id
                LEFT JOIN `{self.project_id}.{self.dataset}.offers_lieu_travail` l ON o.id = l.offer_id
                LEFT JOIN `{self.project_id}.{self.dataset}.offers_salaire` s ON o.id = s.offer_id
                WHERE o.id = @offer_id
            """

            from google.cloud import bigquery

            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("offer_id", "STRING", offer_id)]
            )

            rows = list(self.client.query(query, job_config=job_config))
            if not rows:
                return None

            row = rows[0]

            # Get competences
            comp_query = f"""
                SELECT libelle FROM `{self.project_id}.{self.dataset}.offers_competences`
                WHERE offer_id = @offer_id AND libelle IS NOT NULL
            """
            competences = [r.libelle for r in self.client.query(comp_query, job_config=job_config)]

            # Get qualites
            qual_query = f"""
                SELECT libelle FROM `{self.project_id}.{self.dataset}.offers_qualites_professionnelles`
                WHERE offer_id = @offer_id AND libelle IS NOT NULL
            """
            qualites = [r.libelle for r in self.client.query(qual_query, job_config=job_config)]

            return OfferFullDetails(
                id=row.id,
                intitule=row.intitule or "Sans titre",
                description=row.description,
                entreprise=row.entreprise,
                type_contrat=row.typeContratLibelle,
                experience=row.experienceLibelle,
                duree_travail=row.dureeTravailLibelleConverti,
                lieu=row.lieu,
                salaire=row.salaire,
                date_creation=row.dateCreation,
                rome_libelle=row.romeLibelle,
                secteur_activite=row.secteurActiviteLibelle,
                competences=competences if competences else None,
                qualites=qualites if qualites else None,
            )

        except Exception as e:
            logger.error(f"BigQuery error getting full offer details: {e}")
            return None


class OffersDBError(Exception):
    """Exception raised when offers database fails."""

    pass


def get_offers_db() -> OffersDB:
    """
    Factory function to get the appropriate offers database implementation.

    Uses USE_SQLITE_OFFERS environment variable to determine which implementation.
    - USE_SQLITE_OFFERS=true -> SQLiteOffersDB (uses Silver DB)
    - USE_SQLITE_OFFERS=false (or not set) -> BigQueryOffersDB

    Returns:
        OffersDB implementation
    """
    use_sqlite = os.environ.get("USE_SQLITE_OFFERS", "true").lower() == "true"

    if use_sqlite:
        # Use Silver DB for development/testing
        silver_db_path = Path(__file__).parent.parent / "temp_BQ" / "Silver" / "offers.db"
        logger.info(f"Using SQLiteOffersDB with: {silver_db_path}")
        return SQLiteOffersDB(silver_db_path)
    else:
        project_id = os.environ.get("GCP_PROJECT_ID", "job-match-v0")
        dataset = os.environ.get("BIGQUERY_GOLD_DATASET", "gold")
        logger.info(f"Using BigQueryOffersDB: {project_id}.{dataset}")
        return BigQueryOffersDB(project_id, dataset)
