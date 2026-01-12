"""
Matching service abstraction for job offer recommendations.

Provides interface to get matching offers based on user profile embeddings.
Supports both real matching API and mock implementation for testing.
"""

import logging
import os
import random
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """A single match result from the matching service."""

    offer_id: str
    score: float
    ingestion_date: str | None = None  # For BigQuery partition pruning


class MatchingService(ABC):
    """Abstract base class for matching service implementations."""

    @abstractmethod
    def get_matches(
        self,
        title_embedding: list[float],
        cv_embedding: list[float],
        top_k: int = 20,
    ) -> list[MatchResult]:
        """
        Get matching offers based on profile embeddings.

        Args:
            title_embedding: Embedding vector for the profile title/description
            cv_embedding: Embedding vector for the CV content
            top_k: Number of top matches to return

        Returns:
            List of MatchResult with offer_id and score, sorted by score descending
        """
        pass


class RealMatchingService(MatchingService):
    """Real implementation calling the matching microservice API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get_matches(
        self,
        title_embedding: list[float],
        cv_embedding: list[float],
        top_k: int = 20,
    ) -> list[MatchResult]:
        """Call the matching API to get real matches."""
        url = f"{self.base_url}/api/match"

        payload = {
            "title_embedding": title_embedding,
            "cv_embedding": cv_embedding,
            "top_k": top_k,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            return [
                MatchResult(
                    offer_id=m["offer_id"],
                    score=m["score"],
                    ingestion_date=m.get("ingestion_date"),
                )
                for m in data.get("matches", [])
            ]

        except requests.RequestException as e:
            logger.error(f"Matching service error: {e}")
            raise MatchingServiceError(f"Failed to get matches: {e}") from e


class MockMatchingService(MatchingService):
    """Mock implementation for testing without the real matching service."""

    def __init__(
        self,
        silver_db_path: str | Path | None = None,
        use_bigquery: bool = False,
        bigquery_project: str | None = None,
        bigquery_dataset: str | None = None,
    ):
        """
        Initialize mock service with data source for random offer selection.

        Args:
            silver_db_path: Path to the SQLite Silver database (for SQLite mode)
            use_bigquery: If True, use BigQuery Gold for offer IDs
            bigquery_project: GCP project ID for BigQuery Gold
            bigquery_dataset: BigQuery dataset name
        """
        self.silver_db_path = Path(silver_db_path) if silver_db_path else None
        self.use_bigquery = use_bigquery
        self.bigquery_project = bigquery_project
        self.bigquery_dataset = bigquery_dataset
        self._bq_client = None

    def _get_bigquery_offer_ids(self, top_k: int) -> list[str]:
        """Get random offer IDs from BigQuery Gold."""
        try:
            from google.cloud import bigquery

            if self._bq_client is None:
                self._bq_client = bigquery.Client(project=self.bigquery_project)

            # Get random offer IDs using RAND() function
            query = f"""
                SELECT id FROM `{self.bigquery_project}.{self.bigquery_dataset}.offers`
                WHERE ingestion_date = "2025-10-01"
                ORDER BY RAND()
                LIMIT {top_k}
            """  # nosec B608 - project/dataset from config, top_k is int
            rows = list(self._bq_client.query(query))
            return [row.id for row in rows]

        except Exception as e:
            logger.error(f"BigQuery error in mock matching: {e}")
            return []

    def _get_sqlite_offer_ids(self, top_k: int) -> list[str]:
        """Get random offer IDs from SQLite Silver DB."""
        if not self.silver_db_path or not self.silver_db_path.exists():
            logger.warning(f"Silver DB not found at {self.silver_db_path}")
            return []

        try:
            conn = sqlite3.connect(str(self.silver_db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM offers
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (top_k,),
            )
            offer_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return offer_ids

        except sqlite3.Error as e:
            logger.error(f"SQLite error in mock matching: {e}")
            return []

    def get_matches(
        self,
        title_embedding: list[float],
        cv_embedding: list[float],
        top_k: int = 20,
    ) -> list[MatchResult]:
        """
        Return random offers with simulated scores for testing.

        Selects random offers from BigQuery Gold or SQLite Silver DB depending on config.
        """
        # Get offer IDs from the appropriate source
        offer_ids = self._get_bigquery_offer_ids(top_k) if self.use_bigquery else self._get_sqlite_offer_ids(top_k)

        if not offer_ids:
            return []

        # Generate random scores and sort descending
        results = [
            MatchResult(
                offer_id=offer_id,
                score=round(random.uniform(0.5, 0.98), 3),
            )
            for offer_id in offer_ids
        ]

        return sorted(results, key=lambda x: x.score, reverse=True)


class MatchingServiceError(Exception):
    """Exception raised when matching service fails."""

    pass


def get_matching_service() -> MatchingService:
    """
    Factory function to get the appropriate matching service implementation.

    Uses USE_MOCK_MATCHING environment variable to determine which implementation.
    - USE_MOCK_MATCHING=true -> MockMatchingService
    - USE_MOCK_MATCHING=false (or not set) -> RealMatchingService

    When using MockMatchingService, the data source aligns with USE_SQLITE_OFFERS:
    - USE_SQLITE_OFFERS=true -> Mock uses SQLite Silver DB
    - USE_SQLITE_OFFERS=false -> Mock uses BigQuery Gold (same as offers_db)

    Returns:
        MatchingService implementation
    """
    use_mock = os.environ.get("USE_MOCK_MATCHING", "false").lower() == "true"

    if use_mock:
        # Align mock data source with offers_db source
        use_sqlite = os.environ.get("USE_SQLITE_OFFERS", "true").lower() == "true"

        if use_sqlite:
            # Use SQLite Silver DB for mock data
            silver_db_path = Path(__file__).parent.parent / "temp_BQ" / "Silver" / "offers.db"
            logger.info(f"Using MockMatchingService with SQLite: {silver_db_path}")
            return MockMatchingService(silver_db_path=silver_db_path)
        else:
            # Use BigQuery Gold for mock data (same source as offers_db)
            project_id = os.environ.get("BIGQUERY_GOLD_PROJECT_ID", "jobmatch-482415")
            dataset = os.environ.get("BIGQUERY_GOLD_CROSS_PROJECT_DATASET", "jobmatch_gold")
            logger.info(f"Using MockMatchingService with BigQuery: {project_id}.{dataset}")
            return MockMatchingService(
                use_bigquery=True,
                bigquery_project=project_id,
                bigquery_dataset=dataset,
            )
    else:
        matching_url = os.environ.get("MATCHING_SERVICE_URL", "http://matching:8086")
        logger.info(f"Using RealMatchingService at: {matching_url}")
        return RealMatchingService(matching_url)
