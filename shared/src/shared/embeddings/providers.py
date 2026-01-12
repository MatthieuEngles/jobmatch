from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence

import numpy as np

# Local simple type alias to avoid circular imports
Embedding = np.ndarray
Embedder = Callable[[Sequence[str]], Embedding]


# -------------------- Utilities ------------------------------------------


def _validate_embeddings(arr: np.ndarray) -> np.ndarray:
    if not isinstance(arr, np.ndarray):
        raise TypeError("Embedder must return a numpy.ndarray")
    if arr.ndim != 2:
        raise ValueError("Embeddings must be a 2D array")
    return arr


def _l2_normalize_rows(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    # avoid division by zero
    norms = np.where(norms == 0.0, 1.0, norms)
    return arr / norms


# -------------------- SentenceTransformers provider -----------------------


def create_sentence_transformers_embedder(
    model: str = "all-MiniLM-L6-v2",
    device: str = "cpu",
    batch_size: int = 64,
    normalize: bool = False,
) -> Embedder:
    """Create an embedder backed by the sentence-transformers library.

    Notes
    -----
    - Imports are lazy to avoid pulling heavy deps into test runs.
    - Returns a callable of signature (Sequence[str]) -> np.ndarray of shape (n, d).
    """

    try:
        st_mod = importlib.import_module("sentence_transformers")
    except Exception as exc:  # ImportError or other import-time errors
        raise ImportError(
            "Optional dependency 'sentence-transformers' is not installed. "
            "Install with `pip install .[embeddings]` or `pip install sentence-transformers`."
        ) from exc

    if not hasattr(st_mod, "SentenceTransformer"):
        raise RuntimeError("`sentence_transformers` does not expose `SentenceTransformer`")

    SentenceTransformer = st_mod.SentenceTransformer

    model_obj = SentenceTransformer(model)

    def _embed(texts: Sequence[str]) -> np.ndarray:
        if not texts:
            raise ValueError("Input texts must not be empty")

        # Encode; many versions accept device and convert_to_numpy
        encode_kwargs = {"batch_size": batch_size, "convert_to_numpy": True}
        # Some versions accept device in encode; we'll try to pass it but tolerate failure
        try:
            embeddings = model_obj.encode(list(texts), device=device, **encode_kwargs)
        except TypeError:
            embeddings = model_obj.encode(list(texts), **encode_kwargs)

        arr = np.asarray(embeddings, dtype=np.float64)
        arr = _validate_embeddings(arr)
        if normalize:
            arr = _l2_normalize_rows(arr)
        return arr

    return _embed


# -------------------- vec2vec provider -----------------------------------


def create_vec2vec_embedder(
    model_or_endpoint: str | None = None,
    api_key: str | None = None,
    batch_size: int = 64,
    normalize: bool = False,
) -> Embedder:
    """Create an embedder using a `vec2vec`-compatible client.

    This function tries a few common import patterns so it can interoperate with
    different `vec2vec` client libraries. The library is expected to provide
    either a module-level `embed`/`encode` function taking a list of strings and
    returning a 2D numpy array or a client class with an `.encode` method.
    """

    try:
        v2v = importlib.import_module("vec2vec")
    except Exception as exc:
        raise ImportError(
            "Optional dependency 'vec2vec' is not installed. "
            "Install with `pip install .[embeddings]` or your preferred vec2vec client."
        ) from exc

    # Resolve an embedding callable on the module/object
    embed_fn = None

    if hasattr(v2v, "embed") and callable(v2v.embed):
        embed_fn = v2v.embed
    elif hasattr(v2v, "encode") and callable(v2v.encode):
        embed_fn = v2v.encode
    else:
        # Look for a client class with encode
        client_cls = getattr(v2v, "Vec2Vec", None) or getattr(v2v, "Client", None)
        if client_cls is not None:
            client = client_cls(model_or_endpoint) if model_or_endpoint is not None else client_cls()

            if hasattr(client, "encode") and callable(client.encode):
                embed_fn = client.encode

    if embed_fn is None:
        raise RuntimeError("Could not find an 'embed' or 'encode' callable in the 'vec2vec' module/client.")

    def _embed(texts: Sequence[str]) -> np.ndarray:
        if not texts:
            raise ValueError("Input texts must not be empty")

        # Try to call with a batch_size arg, but tolerate if signature differs
        try:
            embeddings = embed_fn(list(texts), batch_size=batch_size)
        except TypeError:
            embeddings = embed_fn(list(texts))

        arr = np.asarray(embeddings, dtype=np.float64)
        arr = _validate_embeddings(arr)
        if normalize:
            arr = _l2_normalize_rows(arr)
        return arr

    return _embed


# -------------------- Generic factory -----------------------------------


def create_embedder(provider: str, **config) -> Embedder:
    provider = provider.replace("-", "_").lower()

    if provider in ("sentence_transformers", "sentence_transformers", "st"):
        return create_sentence_transformers_embedder(**config)
    if provider in ("vec2vec", "vec_2_vec", "v2v"):
        return create_vec2vec_embedder(**config)

    raise ValueError(f"Unknown embedding provider: {provider}")


__all__ = [
    "create_sentence_transformers_embedder",
    "create_vec2vec_embedder",
    "create_embedder",
]
