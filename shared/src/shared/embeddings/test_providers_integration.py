import os

import pytest

from .embeddings import TextSimilarity


@pytest.mark.skipif(
    os.getenv("JOBMATCH_RUN_EMBEDDING_INTEGRATION") != "1",
    reason=(
        "Integration test disabled by default. Set JOBMATCH_RUN_EMBEDDING_INTEGRATION=1 "
        "and install sentence-transformers to run this test."
    ),
)
def test_sentence_transformers_integration_real_model():
    # Skip early if the package is missing
    pytest.importorskip("sentence_transformers")

    from .providers import create_sentence_transformers_embedder

    # Use a small model by default to keep resource usage low
    embedder = create_sentence_transformers_embedder(model="all-MiniLM-L6-v2", normalize=True)

    arr = embedder(["hello world", "hello"])

    assert arr.shape == (2, arr.shape[1])
    assert arr.dtype == float or str(arr.dtype).startswith("float")

    sim = TextSimilarity(embedder)

    # Identical strings should be ~1.0
    assert pytest.approx(sim.similarity("same text", "same text")) == 1.0

    # Joint similarity should return a float in (0, 1]
    score = sim.joint_similarity(["a", "b"], ["a"])
    assert 0.0 < score <= 1.0
