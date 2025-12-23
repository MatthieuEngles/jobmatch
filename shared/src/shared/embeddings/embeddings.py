from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

# ---- Type aliases ---------------------------------------------------------

Embedding = np.ndarray
Embedder = Callable[[Sequence[str]], Embedding]


# ---- Core implementation --------------------------------------------------


class TextSimilarity:
    """
    Utility class for computing embeddings, cosine similarities,
    and joint similarity scores between strings or sets of strings.
    """

    def __init__(self, embedder: Embedder) -> None:
        """
        Parameters
        ----------
        embedder:
            Callable taking a sequence of strings and returning a 2D numpy array
            of shape (n_texts, embedding_dim).
        """
        self._embedder = embedder

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(self, texts: Sequence[str]) -> Embedding:
        """
        Compute embeddings for a list of strings.
        """
        if not texts:
            raise ValueError("Input texts must not be empty")

        embeddings = self._embedder(texts)

        if not isinstance(embeddings, np.ndarray):
            raise TypeError("Embedder must return a numpy.ndarray")

        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2D array")

        return embeddings

    # ------------------------------------------------------------------
    # Cosine similarity (low level)
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: Embedding, b: Embedding) -> float:
        """
        Cosine similarity between two single embeddings.
        """
        if a.ndim != 1 or b.ndim != 1:
            raise ValueError("Inputs must be 1D embeddings")

        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0.0:
            return 0.0

        return float(np.dot(a, b) / denom)

    @staticmethod
    def cosine_similarity_matrix(a: Embedding, b: Embedding) -> np.ndarray:
        """
        Compute cosine similarity matrix between two embedding sets.

        Returns
        -------
        np.ndarray of shape (len(a), len(b))
        """
        if a.ndim != 2 or b.ndim != 2:
            raise ValueError("Inputs must be 2D embedding matrices")

        a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
        b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)

        return a_norm @ b_norm.T

    # ------------------------------------------------------------------
    # String-level similarity
    # ------------------------------------------------------------------

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Cosine similarity between two strings.
        """
        embeddings = self.embed([text_a, text_b])
        return self.cosine_similarity(embeddings[0], embeddings[1])

    # ------------------------------------------------------------------
    # Set-level similarity
    # ------------------------------------------------------------------

    def joint_similarity(
        self,
        texts_a: Sequence[str],
        texts_b: Sequence[str],
    ) -> float:
        """
        Compute a joint similarity score between two sets of strings.

        Strategy:
        - symmetric best-match average
        """
        if not texts_a or not texts_b:
            raise ValueError("Input text sets must not be empty")

        emb_a = self.embed(texts_a)
        emb_b = self.embed(texts_b)

        sim_matrix = self.cosine_similarity_matrix(emb_a, emb_b)

        # Best match for each direction
        best_a_to_b = sim_matrix.max(axis=1)
        best_b_to_a = sim_matrix.max(axis=0)

        return float((best_a_to_b.mean() + best_b_to_a.mean()) / 2.0)


if __name__ == "__main__":
    # Simple demo
    def simple_embedder(texts: Sequence[str]) -> Embedding:
        return np.array([[len(t)] for t in texts], dtype=np.float64)

    similarity = TextSimilarity(simple_embedder)

    text1 = "hello world"
    text2 = "hello"

    sim_score = similarity.similarity(text1, text2)
    print(f"Similarity between '{text1}' and '{text2}': {sim_score}")

    set1 = ["hello world", "foo bar"]
    set2 = ["hello", "bar baz"]

    joint_score = similarity.joint_similarity(set1, set2)
    print(f"Joint similarity between sets {set1} and {set2}: {joint_score}")
