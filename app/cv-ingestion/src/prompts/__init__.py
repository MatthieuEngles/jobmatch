"""Prompt loader for CV extraction."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt from file.

    Args:
        name: Name of the prompt file (without .txt extension)

    Returns:
        Content of the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    return prompt_path.read_text(encoding="utf-8")


# Pre-load commonly used prompts
def get_cv_text_prompt() -> str:
    """Get the system prompt for text-based CV extraction."""
    return load_prompt("cv_extraction_text")


def get_cv_vision_prompt() -> str:
    """Get the system prompt for vision-based CV extraction."""
    return load_prompt("cv_extraction_vision")


USER_PROMPT_TEMPLATE = """Analyse ce CV et extrais toutes les informations structurées :

---
{cv_text}
---

Retourne le JSON avec toutes les extracted_lines."""

USER_PROMPT_VISION = """Analyse cette image de CV et extrais toutes les informations structurées.

Retourne le JSON avec toutes les extracted_lines."""
