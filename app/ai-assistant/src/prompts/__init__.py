"""Prompts for STAR coaching."""

from pathlib import Path


def get_star_coaching_prompt() -> str:
    """Load the STAR coaching system prompt from file."""
    prompt_file = Path(__file__).parent / "star_coaching.txt"
    return prompt_file.read_text(encoding="utf-8")


__all__ = ["get_star_coaching_prompt"]
