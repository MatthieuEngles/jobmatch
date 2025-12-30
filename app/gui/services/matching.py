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

            return [MatchResult(offer_id=m["offer_id"], score=m["score"]) for m in data.get("matches", [])]

        except requests.RequestException as e:
            logger.error(f"Matching service error: {e}")
            raise MatchingServiceError(f"Failed to get matches: {e}") from e


class MockMatchingService(MatchingService):
    """Mock implementation for testing without the real matching service."""

    def __init__(self, silver_db_path: str | Path):
        """
        Initialize mock service with path to Silver DB for random offer selection.

        Args:
            silver_db_path: Path to the SQLite Silver database
        """
        self.silver_db_path = Path(silver_db_path)

    def get_matches(
        self,
        title_embedding: list[float],
        cv_embedding: list[float],
        top_k: int = 20,
    ) -> list[MatchResult]:
        """
        Return random offers with simulated scores for testing.

        Selects random offers from the Silver DB and assigns random scores.
        """
        if not self.silver_db_path.exists():
            logger.warning(f"Silver DB not found at {self.silver_db_path}")
            return []

        try:
            conn = sqlite3.connect(str(self.silver_db_path))
            cursor = conn.cursor()

            # Get random offer IDs from the database
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

            # Generate random scores and sort descending
            results = [
                MatchResult(
                    offer_id=offer_id,
                    score=round(random.uniform(0.5, 0.98), 3),
                )
                for offer_id in offer_ids
            ]

            return sorted(results, key=lambda x: x.score, reverse=True)

        except sqlite3.Error as e:
            logger.error(f"SQLite error in mock matching: {e}")
            return []


class MatchingServiceError(Exception):
    """Exception raised when matching service fails."""

    pass


def get_matching_service() -> MatchingService:
    """
    Factory function to get the appropriate matching service implementation.

    Uses USE_MOCK_MATCHING environment variable to determine which implementation.
    - USE_MOCK_MATCHING=true -> MockMatchingService
    - USE_MOCK_MATCHING=false (or not set) -> RealMatchingService

    Returns:
        MatchingService implementation
    """
    use_mock = os.environ.get("USE_MOCK_MATCHING", "false").lower() == "true"

    if use_mock:
        # Use Silver DB for mock data
        silver_db_path = Path(__file__).parent.parent / "temp_BQ" / "Silver" / "offers.db"
        logger.info(f"Using MockMatchingService with DB: {silver_db_path}")
        return MockMatchingService(silver_db_path)
    else:
        matching_url = os.environ.get("MATCHING_SERVICE_URL", "http://matching:8086")
        logger.info(f"Using RealMatchingService at: {matching_url}")
        return RealMatchingService(matching_url)
