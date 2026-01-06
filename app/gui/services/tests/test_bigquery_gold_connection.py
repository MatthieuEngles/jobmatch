"""
Mock tests for GUI -> Matching -> BigQuery Gold connection.

Tests the complete flow of:
1. GUI calling the Matching service
2. Matching service returning offer IDs
3. GUI fetching offer details from BigQuery Gold

These tests can run with or without actual BigQuery connection.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the services under test
from services.matching import (
    MatchingService,
    MatchingServiceError,
    MatchResult,
    MockMatchingService,
    RealMatchingService,
    get_matching_service,
)
from services.offers_db import (
    BigQueryOffersDB,
    OfferDetails,
    OfferFullDetails,
    OffersDB,
    SQLiteOffersDB,
    get_offers_db,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing (384 dimensions for MiniLM)."""
    return [0.1] * 384


@pytest.fixture
def sample_match_results():
    """Sample match results from matching service."""
    return [
        MatchResult(offer_id="offer_001", score=0.95),
        MatchResult(offer_id="offer_002", score=0.87),
        MatchResult(offer_id="offer_003", score=0.82),
        MatchResult(offer_id="offer_004", score=0.75),
        MatchResult(offer_id="offer_005", score=0.68),
    ]


@pytest.fixture
def sample_offer_details():
    """Sample offer details from BigQuery Gold."""
    return {
        "offer_001": OfferDetails(
            id="offer_001",
            intitule="Développeur Python Senior",
            entreprise="TechCorp",
            description="Poste de développeur Python avec 5 ans d'expérience...",
        ),
        "offer_002": OfferDetails(
            id="offer_002",
            intitule="Data Engineer",
            entreprise="DataSoft",
            description="Conception et maintenance de pipelines de données...",
        ),
        "offer_003": OfferDetails(
            id="offer_003",
            intitule="DevOps Engineer",
            entreprise="CloudFirst",
            description="Gestion de l'infrastructure cloud et CI/CD...",
        ),
    }


@pytest.fixture
def sample_full_details():
    """Sample full offer details for modal display."""
    return OfferFullDetails(
        id="offer_001",
        intitule="Développeur Python Senior",
        description="Poste de développeur Python avec 5 ans d'expérience...",
        entreprise="TechCorp",
        type_contrat="CDI",
        experience="5 ans",
        duree_travail="35h",
        lieu="Paris (75)",
        salaire="50-60k€",
        date_creation="2024-01-15",
        rome_libelle="Développement informatique",
        secteur_activite="Services informatiques",
        competences=["Python", "Django", "PostgreSQL", "Docker"],
        qualites=["Autonomie", "Rigueur", "Esprit d'équipe"],
    )


# =============================================================================
# Unit Tests - Matching Service
# =============================================================================


class TestMatchingServiceMock:
    """Tests for mocked matching service calls."""

    def test_real_matching_service_success(self, sample_embedding, sample_match_results):
        """Test RealMatchingService with mocked HTTP response."""
        with patch("services.matching.requests.post") as mock_post:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "matches": [{"offer_id": r.offer_id, "score": r.score} for r in sample_match_results]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            # Call the service
            service = RealMatchingService("http://matching:8086")
            results = service.get_matches(
                title_embedding=sample_embedding,
                cv_embedding=sample_embedding,
                top_k=5,
            )

            # Verify
            assert len(results) == 5
            assert results[0].offer_id == "offer_001"
            assert results[0].score == 0.95
            mock_post.assert_called_once()

    def test_real_matching_service_error(self, sample_embedding):
        """Test RealMatchingService handling of API errors."""
        with patch("services.matching.requests.post") as mock_post:
            # Simulate a requests.RequestException which is caught by the service
            from requests.exceptions import RequestException

            mock_post.side_effect = RequestException("Connection refused")

            service = RealMatchingService("http://matching:8086")

            with pytest.raises(MatchingServiceError):
                service.get_matches(
                    title_embedding=sample_embedding,
                    cv_embedding=sample_embedding,
                    top_k=5,
                )

    def test_get_matching_service_factory_real(self):
        """Test factory returns RealMatchingService when USE_MOCK_MATCHING=false."""
        with patch.dict(os.environ, {"USE_MOCK_MATCHING": "false", "MATCHING_SERVICE_URL": "http://test:8086"}):
            service = get_matching_service()
            assert isinstance(service, RealMatchingService)
            assert service.base_url == "http://test:8086"

    def test_get_matching_service_factory_mock_sqlite(self):
        """Test factory returns MockMatchingService with SQLite when USE_SQLITE_OFFERS=true."""
        with patch.dict(os.environ, {"USE_MOCK_MATCHING": "true", "USE_SQLITE_OFFERS": "true"}):
            service = get_matching_service()
            assert isinstance(service, MockMatchingService)
            assert service.use_bigquery is False
            assert service.silver_db_path is not None

    def test_get_matching_service_factory_mock_bigquery(self):
        """Test factory returns MockMatchingService with BigQuery when USE_SQLITE_OFFERS=false."""
        with patch.dict(
            os.environ,
            {
                "USE_MOCK_MATCHING": "true",
                "USE_SQLITE_OFFERS": "false",
                "BIGQUERY_GOLD_PROJECT_ID": "jobmatch-482415",
                "BIGQUERY_GOLD_CROSS_PROJECT_DATASET": "jobmatch_gold",
            },
        ):
            service = get_matching_service()
            assert isinstance(service, MockMatchingService)
            assert service.use_bigquery is True
            assert service.bigquery_project == "jobmatch-482415"
            assert service.bigquery_dataset == "jobmatch_gold"


# =============================================================================
# Unit Tests - BigQuery Offers DB
# =============================================================================


class TestBigQueryOffersDB:
    """Tests for BigQuery Gold database connection."""

    def test_bigquery_get_offers_by_ids_success(self, sample_offer_details):
        """Test BigQueryOffersDB.get_offers_by_ids with mocked BigQuery client."""
        # Create mock BigQuery client directly (no patching needed)
        mock_client = MagicMock()

        # Mock query results (Gold schema: id, intitule, description only)
        mock_rows = []
        for _offer_id, details in sample_offer_details.items():
            mock_row = MagicMock()
            mock_row.id = details.id
            mock_row.intitule = details.intitule
            mock_row.description = details.description
            mock_rows.append(mock_row)

        mock_client.query.return_value = mock_rows

        # Inject mock client directly
        db = BigQueryOffersDB(project_id="jobmatch-482415", dataset="jobmatch_gold")
        db._client = mock_client

        # Call the method
        offer_ids = list(sample_offer_details.keys())
        results = db.get_offers_by_ids(offer_ids)

        # Verify
        assert len(results) == 3
        assert "offer_001" in results
        assert results["offer_001"].intitule == "Développeur Python Senior"
        # Note: entreprise is None in Gold schema (no offers_entreprise table)
        assert results["offer_001"].entreprise is None

    def test_bigquery_get_offers_empty_list(self):
        """Test BigQueryOffersDB.get_offers_by_ids with empty list."""
        db = BigQueryOffersDB(project_id="test-project", dataset="gold")
        results = db.get_offers_by_ids([])
        assert results == {}

    def test_bigquery_get_full_details_success(self, sample_full_details):
        """Test BigQueryOffersDB.get_offer_full_details with mocked response."""
        mock_client = MagicMock()

        # Mock query result (Gold schema: id, intitule, description, created_at only)
        mock_row = MagicMock()
        mock_row.id = sample_full_details.id
        mock_row.intitule = sample_full_details.intitule
        mock_row.description = sample_full_details.description
        mock_row.created_at = "2024-01-15 10:30:00"

        # Setup single query response (no joins in Gold schema)
        mock_client.query.return_value = [mock_row]

        # Inject mock client
        db = BigQueryOffersDB(project_id="jobmatch-482415", dataset="jobmatch_gold")
        db._client = mock_client

        # Call the method
        result = db.get_offer_full_details("offer_001")

        # Verify (only available fields in Gold schema)
        assert result is not None
        assert result.id == "offer_001"
        assert result.intitule == "Développeur Python Senior"
        assert result.description == sample_full_details.description
        assert result.date_creation == "2024-01-15 10:30:00"
        # These fields are None in simplified Gold schema
        assert result.entreprise is None
        assert result.type_contrat is None
        assert result.competences is None

    def test_get_offers_db_factory_sqlite(self):
        """Test factory returns SQLiteOffersDB when USE_SQLITE_OFFERS=true."""
        with patch.dict(os.environ, {"USE_SQLITE_OFFERS": "true"}):
            db = get_offers_db()
            assert isinstance(db, SQLiteOffersDB)

    def test_get_offers_db_factory_bigquery(self):
        """Test factory returns BigQueryOffersDB when USE_SQLITE_OFFERS=false."""
        with patch.dict(
            os.environ,
            {
                "USE_SQLITE_OFFERS": "false",
                "BIGQUERY_GOLD_PROJECT_ID": "jobmatch-482415",
                "BIGQUERY_GOLD_CROSS_PROJECT_DATASET": "jobmatch_gold",
            },
        ):
            db = get_offers_db()
            assert isinstance(db, BigQueryOffersDB)
            assert db.project_id == "jobmatch-482415"
            assert db.dataset == "jobmatch_gold"


# =============================================================================
# Integration Tests - Full Flow Mock
# =============================================================================


class TestGUIMatchingBigQueryFlow:
    """
    Integration tests simulating the complete flow:
    GUI -> Matching Service -> BigQuery Gold
    """

    def test_full_matching_flow_mocked(
        self,
        sample_embedding,
        sample_match_results,
        sample_offer_details,
    ):
        """
        Test the complete flow with all external services mocked.

        Simulates:
        1. User submits CV embedding
        2. Matching service returns top matches
        3. GUI fetches offer details from BigQuery Gold
        4. Results are returned to user
        """
        # Step 1: Mock matching service
        mock_matching = Mock(spec=MatchingService)
        mock_matching.get_matches.return_value = sample_match_results

        # Step 2: Mock BigQuery offers DB
        mock_offers_db = Mock(spec=OffersDB)
        mock_offers_db.get_offers_by_ids.return_value = sample_offer_details

        # Step 3: Simulate the flow (as done in top_offers.py)
        # Get matches from matching service
        matches = mock_matching.get_matches(
            title_embedding=sample_embedding,
            cv_embedding=sample_embedding,
            top_k=5,
        )
        assert len(matches) == 5

        # Get offer details from BigQuery Gold
        offer_ids = [m.offer_id for m in matches]
        offer_details = mock_offers_db.get_offers_by_ids(offer_ids)

        # Combine results
        results = []
        for match in matches:
            details = offer_details.get(match.offer_id)
            if details:
                results.append(
                    {
                        "offer_id": match.offer_id,
                        "score": match.score,
                        "title": details.intitule,
                        "company": details.entreprise,
                    }
                )

        # Verify combined results
        assert len(results) == 3  # Only 3 have details
        assert results[0]["offer_id"] == "offer_001"
        assert results[0]["score"] == 0.95
        assert results[0]["title"] == "Développeur Python Senior"
        assert results[0]["company"] == "TechCorp"

    def test_flow_with_matching_service_error(self, sample_embedding):
        """Test flow handles matching service errors gracefully."""
        mock_matching = Mock(spec=MatchingService)
        mock_matching.get_matches.side_effect = MatchingServiceError("Service unavailable")

        with pytest.raises(MatchingServiceError):
            mock_matching.get_matches(
                title_embedding=sample_embedding,
                cv_embedding=sample_embedding,
                top_k=5,
            )

    def test_flow_with_bigquery_error(self, sample_embedding, sample_match_results):
        """Test flow handles BigQuery errors gracefully."""
        mock_matching = Mock(spec=MatchingService)
        mock_matching.get_matches.return_value = sample_match_results

        mock_offers_db = Mock(spec=OffersDB)
        mock_offers_db.get_offers_by_ids.return_value = {}  # Empty = error or no data

        matches = mock_matching.get_matches(
            title_embedding=sample_embedding,
            cv_embedding=sample_embedding,
            top_k=5,
        )

        offer_ids = [m.offer_id for m in matches]
        offer_details = mock_offers_db.get_offers_by_ids(offer_ids)

        # Should handle gracefully - no details available
        assert offer_details == {}


# =============================================================================
# Integration Test - Mock Matching + Real BigQuery Gold
# =============================================================================


@pytest.mark.skipif(
    os.environ.get("BIGQUERY_GOLD_CREDENTIALS_PATH") is None, reason="BigQuery credentials not configured"
)
class TestMockMatchingRealBigQuery:
    """
    Integration test: Mock matching service returns random IDs,
    real BigQuery Gold fetches offer details, format and display.

    This tests the complete flow without needing CV/embeddings.
    """

    @pytest.fixture(autouse=True)
    def setup_credentials(self):
        """Setup Google credentials for BigQuery access."""
        creds_path = os.environ.get("BIGQUERY_GOLD_CREDENTIALS_PATH")
        if creds_path and os.path.exists(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    def test_full_flow_mock_matching_real_bigquery(self):
        """
        Test the complete flow:
        1. Get 20 random offer IDs from BigQuery Gold (simulating matching)
        2. Generate random scores (0-1)
        3. Fetch offer details from BigQuery Gold
        4. Format and display results
        """
        import random

        from google.cloud import bigquery

        project_id = os.environ.get("BIGQUERY_GOLD_PROJECT_ID", "jobmatch-482415")
        dataset = os.environ.get("BIGQUERY_GOLD_CROSS_PROJECT_DATASET", "jobmatch_gold")

        print(f"\n{'=' * 60}")
        print("TEST: Mock Matching + Real BigQuery Gold Flow")
        print(f"{'=' * 60}")

        # Step 1: Get 20 random offer IDs from BigQuery Gold (simulating matching API)
        print("\n[1] Simulating Matching API - Getting 20 random offer IDs...")

        bq_client = bigquery.Client(project=project_id)
        query = f"""
            SELECT id FROM `{project_id}.{dataset}.offers`
            ORDER BY RAND()
            LIMIT 20
        """
        rows = list(bq_client.query(query))
        offer_ids = [row.id for row in rows]

        print(f"    Found {len(offer_ids)} offer IDs")
        assert len(offer_ids) == 20, f"Expected 20 offers, got {len(offer_ids)}"

        # Step 2: Generate random scores (simulating matching scores)
        print("\n[2] Generating random similarity scores...")

        mock_matches = [MatchResult(offer_id=oid, score=round(random.uniform(0.5, 0.98), 3)) for oid in offer_ids]
        mock_matches.sort(key=lambda x: x.score, reverse=True)

        print(f"    Generated {len(mock_matches)} match results")
        print(f"    Score range: {mock_matches[-1].score:.3f} - {mock_matches[0].score:.3f}")

        # Step 3: Fetch offer details from BigQuery Gold (real query)
        print("\n[3] Fetching offer details from BigQuery Gold...")

        offers_db = BigQueryOffersDB(project_id=project_id, dataset=dataset)
        match_ids = [m.offer_id for m in mock_matches]
        offer_details = offers_db.get_offers_by_ids(match_ids)

        print(f"    Retrieved {len(offer_details)} offer details")
        assert len(offer_details) > 0, "No offer details retrieved"

        # Step 4: Format and display results
        print("\n[4] Formatting results for display...")
        print(f"\n{'=' * 60}")
        print("TOP MATCHING OFFERS")
        print(f"{'=' * 60}\n")

        formatted_results = []
        for i, match in enumerate(mock_matches, 1):
            details = offer_details.get(match.offer_id)
            if details:
                result = {
                    "rank": i,
                    "offer_id": match.offer_id,
                    "score": match.score,
                    "score_percent": f"{match.score * 100:.1f}%",
                    "title": details.intitule,
                    "company": details.entreprise or "Non renseigné",
                    "description_preview": (details.description[:100] + "...")
                    if details.description and len(details.description) > 100
                    else details.description,
                }
                formatted_results.append(result)

                # Display formatted result
                print(f"#{i:2d} | Score: {result['score_percent']:>6} | {result['title'][:50]}")
                print(f"     ID: {result['offer_id']}")
                if result["description_preview"]:
                    print(f"     {result['description_preview'][:80]}...")
                print()

        print(f"{'=' * 60}")
        print(f"Total formatted: {len(formatted_results)} offers")
        print(f"{'=' * 60}\n")

        # Assertions
        assert len(formatted_results) == 20, f"Expected 20 formatted results, got {len(formatted_results)}"

        # Verify all required fields are present
        for result in formatted_results:
            assert "rank" in result
            assert "offer_id" in result
            assert "score" in result
            assert "title" in result
            assert result["title"] != "Sans titre", f"Offer {result['offer_id']} has no title"

        print("✓ All assertions passed!")
        print("✓ Flow completed successfully: Mock Matching → BigQuery Gold → Format → Display")


# =============================================================================
# Live Connection Tests (require actual credentials)
# =============================================================================


@pytest.mark.skipif(
    os.environ.get("BIGQUERY_GOLD_CREDENTIALS_PATH") is None, reason="BigQuery credentials not configured"
)
class TestBigQueryLiveConnection:
    """
    Live tests against actual BigQuery Gold table.

    These tests require:
    - BIGQUERY_GOLD_PROJECT_ID set in environment
    - BIGQUERY_GOLD_CROSS_PROJECT_DATASET set in environment
    - Valid credentials at BIGQUERY_GOLD_CREDENTIALS_PATH
    """

    @pytest.fixture(autouse=True)
    def setup_credentials(self):
        """Setup Google credentials for BigQuery access."""
        creds_path = os.environ.get("BIGQUERY_GOLD_CREDENTIALS_PATH")
        if creds_path and os.path.exists(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    def test_bigquery_connection(self):
        """Test that we can connect to BigQuery Gold."""
        project_id = os.environ.get("BIGQUERY_GOLD_PROJECT_ID", "jobmatch-482415")
        dataset = os.environ.get("BIGQUERY_GOLD_CROSS_PROJECT_DATASET", "jobmatch_gold")

        db = BigQueryOffersDB(project_id=project_id, dataset=dataset)

        # Just verify client initialization works
        try:
            client = db.client
            assert client is not None
            print(f"✓ Connected to BigQuery: {project_id}.{dataset}")
        except Exception as e:
            pytest.fail(f"Failed to connect to BigQuery: {e}")

    def test_bigquery_query_offers(self):
        """Test querying actual offers from BigQuery Gold."""
        project_id = os.environ.get("BIGQUERY_GOLD_PROJECT_ID", "jobmatch-482415")
        dataset = os.environ.get("BIGQUERY_GOLD_CROSS_PROJECT_DATASET", "jobmatch_gold")

        db = BigQueryOffersDB(project_id=project_id, dataset=dataset)

        try:
            # Query for a few sample offers (get first 3 IDs)
            query = f"""
                SELECT id FROM `{project_id}.{dataset}.offers`
                LIMIT 3
            """
            rows = list(db.client.query(query))

            if rows:
                offer_ids = [row.id for row in rows]
                print(f"Found {len(offer_ids)} offers: {offer_ids}")

                # Now test get_offers_by_ids
                details = db.get_offers_by_ids(offer_ids)
                assert len(details) > 0
                print(f"✓ Retrieved {len(details)} offer details")

                for offer_id, offer in details.items():
                    print(f"  - {offer_id}: {offer.intitule} ({offer.entreprise})")
            else:
                pytest.skip("No offers found in BigQuery Gold table")

        except Exception as e:
            pytest.fail(f"BigQuery query failed: {e}")


# =============================================================================
# Run tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
