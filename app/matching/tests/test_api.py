# tests/test_api.py
import numpy as np
from fastapi.testclient import TestClient
from matcher.main import app

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
        "title_embedded": title_embedded.tolist(),
        "description_embedded": description_embedded.tolist(),
        "job_offers_sqlite": SAMPLE_SQLITE_DB,
    }

    response = client.post("/api/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], list)
    if data["result"]:
        item = data["result"][0]
        assert "id" in item
        assert "similarity" in item
        assert isinstance(item["similarity"], float)
        print(pretty_print_response(data))
