# tests/test_api.py
import os

import numpy as np
from fastapi.testclient import TestClient
from matcher.main import app

# Set the database path environment variable for tests
os.environ["JOB_OFFERS_DB_PATH"] = "tests/data/top10.db"

client = TestClient(app)

# SAMPLE_SQLITE_DB = "tests/data/job_offers_gold.db"
SAMPLE_SQLITE_DB = "tests/data/top10.db"
SAMPLE_TITLE_EMBEDDED_ARCHIVE = "tests/data/title_embedded.npy"
SAMPLE_DESCRIPTION_EMBEDDED_ARCHIVE = "tests/data/desc_embedded.npy"


def pretty_print_response(response_data):
    import json

    return json.dumps(response_data, indent=4, ensure_ascii=False)


def load_test_embeddings():
    title_embedded = np.load(SAMPLE_TITLE_EMBEDDED_ARCHIVE)
    description_embedded = np.load(SAMPLE_DESCRIPTION_EMBEDDED_ARCHIVE)
    return title_embedded, description_embedded


def test_match_endpoint():
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
        assert isinstance(item["score"], float)
        print(pretty_print_response(data))
