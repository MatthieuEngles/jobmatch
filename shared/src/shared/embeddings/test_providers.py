import sys
import types

import numpy as np
import pytest

from .embeddings import TextSimilarity
from . import providers


def test_sentence_transformers_embedder_mock(monkeypatch):
    # Create a fake sentence_transformers module with SentenceTransformer
    class FakeModel:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, texts, batch_size=None, device=None, convert_to_numpy=True):
            # Deterministic embedding: [len(text), sum(chars) % 10]
            return np.array([[len(t), sum(ord(c) for c in t) % 10] for t in texts], dtype=np.float64)

    mod = types.ModuleType("sentence_transformers")
    mod.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)

    embedder = providers.create_sentence_transformers_embedder(model="fake", batch_size=2, device="cpu", normalize=True)
    arr = embedder(["a", "bb"])

    assert arr.shape == (2, 2)
    # Check rows are normalized
    norms = np.linalg.norm(arr, axis=1)
    assert np.allclose(norms, np.ones_like(norms))

    # Use with TextSimilarity
    sim = TextSimilarity(embedder)
    assert pytest.approx(sim.similarity("abc", "abc")) == 1.0


def test_vec2vec_embedder_module_function(monkeypatch):
    # Fake vec2vec module exposing `embed`
    def _fake_embed(texts, batch_size=None):
        return np.vstack([[len(t)] for t in texts]).astype(np.float64)

    mod = types.ModuleType("vec2vec")
    mod.embed = _fake_embed

    monkeypatch.setitem(sys.modules, "vec2vec", mod)

    embedder = providers.create_vec2vec_embedder()
    arr = embedder(["x", "yy", "zzz"])

    assert arr.shape == (3, 1)
    assert arr.dtype == np.float64

    sim = TextSimilarity(embedder)
    assert pytest.approx(sim.similarity("a", "a")) == 1.0


def test_create_embedder_dispatch(monkeypatch):
    # Ensure dispatch uses the correct factory
    st_mod = types.ModuleType("sentence_transformers")

    class FakeModel:
        def __init__(self, model_name):
            pass

        def encode(self, texts, **kwargs):
            return np.vstack([[len(t)] for t in texts]).astype(np.float64)

    st_mod.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", st_mod)

    v2v_mod = types.ModuleType("vec2vec")

    def _embed(texts):
        return np.vstack([[len(t)] for t in texts]).astype(np.float64)

    v2v_mod.embed = _embed
    monkeypatch.setitem(sys.modules, "vec2vec", v2v_mod)

    e1 = providers.create_embedder("sentence-transformers")
    e2 = providers.create_embedder("vec2vec")

    assert callable(e1) and callable(e2)

    with pytest.raises(ValueError):
        providers.create_embedder("nonexistent")
