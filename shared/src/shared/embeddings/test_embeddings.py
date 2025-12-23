import numpy as np
import pytest

from .embeddings import TextSimilarity

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def fake_embedder():
    """
    Deterministic embedder for testing.
    Maps strings to simple numeric vectors based on character ordinals.
    """

    def _embed(texts: list[str]) -> np.ndarray:
        embeddings = []
        for text in texts:
            vec = np.array(
                [
                    sum(ord(c) for c in text) % 101,
                    len(text),
                    sum(c.isalpha() for c in text),
                ],
                dtype=np.float64,
            )
            embeddings.append(vec)
        return np.vstack(embeddings)

    return _embed


@pytest.fixture
def similarity(fake_embedder):
    return TextSimilarity(fake_embedder)


# ---------------------------------------------------------------------
# Embedding tests
# ---------------------------------------------------------------------


def test_embed_shape(similarity):
    embeddings = similarity.embed(["hello", "world"])
    assert embeddings.shape == (2, 3)


def test_embed_empty_input_raises(similarity):
    with pytest.raises(ValueError):
        similarity.embed([])


def test_embed_returns_numpy_array(similarity):
    embeddings = similarity.embed(["test"])
    assert isinstance(embeddings, np.ndarray)


# ---------------------------------------------------------------------
# Cosine similarity (low-level)
# ---------------------------------------------------------------------


def test_cosine_similarity_identical_vectors():
    vec = np.array([1.0, 2.0, 3.0])
    score = TextSimilarity.cosine_similarity(vec, vec)
    assert pytest.approx(score) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    score = TextSimilarity.cosine_similarity(a, b)
    assert pytest.approx(score) == 0.0


def test_cosine_similarity_zero_vector():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 2.0])
    score = TextSimilarity.cosine_similarity(a, b)
    assert score == 0.0


def test_cosine_similarity_invalid_shape():
    with pytest.raises(ValueError):
        TextSimilarity.cosine_similarity(
            np.array([[1, 2]]),
            np.array([1, 2]),
        )


# ---------------------------------------------------------------------
# Cosine similarity matrix
# ---------------------------------------------------------------------


def test_cosine_similarity_matrix_shape(similarity):
    a = similarity.embed(["a", "b", "c"])
    b = similarity.embed(["x", "y"])
    matrix = similarity.cosine_similarity_matrix(a, b)
    assert matrix.shape == (3, 2)


def test_cosine_similarity_matrix_values(similarity):
    a = similarity.embed(["same"])
    b = similarity.embed(["same"])
    matrix = similarity.cosine_similarity_matrix(a, b)
    assert pytest.approx(matrix[0, 0]) == 1.0


# ---------------------------------------------------------------------
# String-level similarity
# ---------------------------------------------------------------------


def test_string_similarity_identity(similarity):
    score = similarity.similarity("hello", "hello")
    assert pytest.approx(score) == 1.0


def test_string_similarity_symmetry(similarity):
    score1 = similarity.similarity("abc", "xyz")
    score2 = similarity.similarity("xyz", "abc")
    assert pytest.approx(score1) == score2


# ---------------------------------------------------------------------
# Joint similarity
# ---------------------------------------------------------------------


def test_joint_similarity_identity(similarity):
    texts = ["machine learning", "deep learning"]
    score = similarity.joint_similarity(texts, texts)
    assert pytest.approx(score) == 1.0


def test_joint_similarity_partial_overlap(similarity):
    a = ["apple", "banana"]
    b = ["apple", "car"]
    score = similarity.joint_similarity(a, b)
    assert 0.0 < score <= 1.0


def test_joint_similarity_symmetry(similarity):
    a = ["a", "b", "c"]
    b = ["x", "y"]
    score1 = similarity.joint_similarity(a, b)
    score2 = similarity.joint_similarity(b, a)
    assert pytest.approx(score1) == score2


def test_joint_similarity_empty_input_raises(similarity):
    with pytest.raises(ValueError):
        similarity.joint_similarity([], ["test"])

    with pytest.raises(ValueError):
        similarity.joint_similarity(["test"], [])
