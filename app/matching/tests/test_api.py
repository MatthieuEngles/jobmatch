# tests/test_api.py
import json
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from matcher.main import app

# Set the database path environment variable for tests
os.environ["JOB_OFFERS_DB_PATH"] = "tests/data/top10.db"
# Set matching method to SQLite for tests (default)
os.environ["MATCHING_METHOD"] = "sqlite"

client = TestClient(app)

# SAMPLE_SQLITE_DB = "tests/data/job_offers_gold.db"
SAMPLE_SQLITE_DB = "tests/data/top10.db"
SAMPLE_TITLE_EMBEDDED_ARCHIVE = "tests/data/title_embedded.npy"
SAMPLE_DESCRIPTION_EMBEDDED_ARCHIVE = "tests/data/desc_embedded.npy"


def pretty_print_response(response_data):
    return json.dumps(response_data, indent=4, ensure_ascii=False)


def load_test_embeddings():
    title_embedded = np.load(SAMPLE_TITLE_EMBEDDED_ARCHIVE)
    description_embedded = np.load(SAMPLE_DESCRIPTION_EMBEDDED_ARCHIVE)
    return title_embedded, description_embedded


def test_match_endpoint_sqlite():
    """Test the match endpoint using SQLite backend."""
    os.environ["MATCHING_METHOD"] = "sqlite"

    title_embedded, description_embedded = load_test_embeddings()
    payload = {
        "title_embedding": title_embedded.tolist(),
        "cv_embedding": description_embedded.tolist(),
        "top_k": 5,
    }

    response = client.post("/api/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)
    if data["matches"]:
        item = data["matches"][0]
        assert "offer_id" in item
        assert "score" in item
        assert "ingestion_date" in item
        assert isinstance(item["score"], float)
        # ingestion_date is None for SQLite backend
        assert item["ingestion_date"] is None
        print("\nSQLite backend results:")
        print(pretty_print_response(data))


def test_match_endpoint_bigquery():
    """
    Test the match endpoint using BigQuery backend.

    NOTE: This test requires valid GCP credentials and BigQuery access.
    It's marked as expensive and skipped by default to avoid BigQuery costs.
    Run with: pytest tests/test_api.py::test_match_endpoint_bigquery -v -s
    """
    # Skip if GCP credentials not available
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GCP credentials not configured - skipping BigQuery test")

    # Check required BigQuery environment variables
    required_vars = ["GCP_PROJECT_ID", "DATASET_ID", "TABLE_DESCRIPTION_EMBEDDINGS_ID"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing BigQuery env vars: {', '.join(missing)} - skipping BigQuery test")

    os.environ["MATCHING_METHOD"] = "bigquery"

    title_embedded, description_embedded = load_test_embeddings()
    payload = {
        "title_embedding": title_embedded.tolist(),
        "cv_embedding": description_embedded.tolist(),
        "top_k": 5,
    }

    try:
        response = client.post("/api/match", json=payload)

        # Check response status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "matches" in data
        assert isinstance(data["matches"], list)

        if data["matches"]:
            item = data["matches"][0]
            assert "offer_id" in item
            assert "score" in item
            assert "ingestion_date" in item
            assert isinstance(item["score"], float)

            # BigQuery backend should return ingestion_date (ISO format string)
            # It may be None for some entries, but if present, should be a string
            if item["ingestion_date"] is not None:
                assert isinstance(item["ingestion_date"], str), "ingestion_date should be ISO format string"
                # Verify ISO format (basic check)
                assert "T" in item["ingestion_date"] or "-" in item["ingestion_date"]

            # Check score is in valid range
            assert 0.0 <= item["score"] <= 1.0, f"Score {item['score']} should be between 0 and 1"

            print("\nBigQuery backend results:")
            print(pretty_print_response(data))

    finally:
        # Reset to sqlite
        os.environ["MATCHING_METHOD"] = "sqlite"


def test_match_endpoint_bigquery_response_format():
    """
    Test that BigQuery backend returns the expected response format.

    Verifies:
    - Response structure matches MatchResponse schema
    - ingestion_date field is present (critical for partition pruning)
    - Results are sorted by score (descending)
    """
    # Skip if GCP credentials not available
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GCP credentials not configured - skipping BigQuery test")

    required_vars = ["GCP_PROJECT_ID", "DATASET_ID", "TABLE_DESCRIPTION_EMBEDDINGS_ID"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing BigQuery env vars: {', '.join(missing)} - skipping BigQuery test")

    os.environ["MATCHING_METHOD"] = "bigquery"

    title_embedded, description_embedded = load_test_embeddings()
    payload = {
        "title_embedding": title_embedded.tolist(),
        "cv_embedding": description_embedded.tolist(),
        "top_k": 10,
    }

    try:
        response = client.post("/api/match", json=payload)
        assert response.status_code == 200

        data = response.json()
        matches = data["matches"]

        # Check we got results
        assert len(matches) > 0, "Should return at least one match"
        assert len(matches) <= 10, "Should return at most top_k matches"

        # Verify all matches have required fields
        for i, match in enumerate(matches):
            assert "offer_id" in match, f"Match {i} missing offer_id"
            assert "score" in match, f"Match {i} missing score"
            assert "ingestion_date" in match, f"Match {i} missing ingestion_date (needed for partition pruning)"

            # Verify types
            assert isinstance(match["offer_id"], str), f"Match {i} offer_id should be string"
            assert isinstance(match["score"], float), f"Match {i} score should be float"
            # ingestion_date can be None or string
            if match["ingestion_date"] is not None:
                assert isinstance(match["ingestion_date"], str), f"Match {i} ingestion_date should be string"

        # Verify results are sorted by score (descending)
        scores = [m["score"] for m in matches]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score (highest first)"

        print(f"\n✓ BigQuery returned {len(matches)} matches with correct format")
        print(f"  Top score: {scores[0]:.4f}")
        print(f"  Lowest score: {scores[-1]:.4f}")

    finally:
        os.environ["MATCHING_METHOD"] = "sqlite"


def test_match_endpoint_invalid_method():
    """Test that invalid matching method returns 500 error."""
    os.environ["MATCHING_METHOD"] = "invalid_method"

    title_embedded, description_embedded = load_test_embeddings()
    payload = {
        "title_embedding": title_embedded.tolist(),
        "cv_embedding": description_embedded.tolist(),
        "top_k": 5,
    }

    response = client.post("/api/match", json=payload)

    assert response.status_code == 500
    assert "Invalid MATCHING_METHOD" in response.json()["detail"]

    # Reset to sqlite
    os.environ["MATCHING_METHOD"] = "sqlite"


# Alias for backward compatibility
def test_match_endpoint():
    """Backward compatibility alias for test_match_endpoint_sqlite."""
    test_match_endpoint_sqlite()
