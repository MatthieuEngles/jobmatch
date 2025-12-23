"""Simple demo script to show similarity scores using the TextSimilarity utilities.

Run from the repository root like:

    python shared/scripts/embeddings_demo.py

It will run a small demo using a cheap built-in `simple_embedder` and, if
`sentence-transformers` is installed, will also run the same demo using a
real embedding model (`all-MiniLM-L6-v2` by default).
"""
from __future__ import annotations

import sys
from typing import Sequence

# Allow running the script directly or via `python -m shared.scripts.embeddings_demo`
from pathlib import Path
_repo_root = Path(__file__).resolve().parents[2]
_src_path = str(_repo_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import numpy as np

from shared.embeddings import TextSimilarity
from shared.embeddings import Embedding, Embedder
from shared.embeddings import create_sentence_transformers_embedder


def simple_embedder(texts: Sequence[str]) -> Embedding:
    """Toy deterministic embedder based on string length."""
    return np.array([[len(t)] for t in texts], dtype=np.float64)


def print_pairwise(sim: TextSimilarity, texts: Sequence[str]) -> None:
    print("Pairwise similarity:")
    for i, a in enumerate(texts):
        for j, b in enumerate(texts):
            if j <= i:
                continue
            score = sim.similarity(a, b)
            print(f"  '{a}' <-> '{b}': {score:.4f}")


def print_joint(sim: TextSimilarity, a: Sequence[str], b: Sequence[str]) -> None:
    score = sim.joint_similarity(list(a), list(b))
    print(f"Joint similarity between {a} and {b}: {score:.4f}")


def run_demo(embedder: Embedder, title: str) -> None:
    print("""
=====================================
Demo using: {title}
=====================================""".format(title=title))

    sim = TextSimilarity(embedder)

    texts = ["hello world", "hello", "goodbye", "foo bar"]

    print_pairwise(sim, texts)

    print()
    print_joint(sim, ["hello world", "foo bar"], ["hello", "bar baz"])
    print()


def main() -> None:
    print("Simple embedder (length-based):")
    run_demo(simple_embedder, "simple_embedder (len)")

    # Try to run with sentence-transformers if available
    try:
        st_embedder = create_sentence_transformers_embedder(
            model="all-MiniLM-L6-v2", normalize=True
        )
    except Exception as exc:  # ImportError or other config errors
        print("Skipping sentence-transformers demo (not available):", exc)
    else:
        print()
        run_demo(st_embedder, "sentence-transformers (all-MiniLM-L6-v2)")


if __name__ == "__main__":
    main()
