"""Lightweight package stub to enable running demos and tests without installing.

This file extends the package search path so that the actual package code
under `shared/src/shared` is discoverable when importing `shared` from the
repository root (e.g., `python -m shared.scripts.embeddings_demo`).

Note: this is intentionally minimal and only mutates `__path__` and
`sys.path` to point at the `src` layout. It avoids importing heavy modules.
"""
from __future__ import annotations

from pathlib import Path
import sys

__all__ = []

_here = Path(__file__).resolve().parent
_src_dir = str(_here / "src")
_src_shared_pkg = str(_here / "src" / "shared")

# Ensure that import machinery can find modules under src/ and src/shared
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Also extend package __path__ so submodules can be loaded from src/shared
if _src_shared_pkg not in __path__:
    __path__.insert(0, _src_shared_pkg)
