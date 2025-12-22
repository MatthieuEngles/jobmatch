"""LLM-based CV analysis - provider agnostic."""

import json
import logging
import re
from abc import ABC, abstractmethod

from ..config import settings
from ..schemas import ContentType, ExtractedLine
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        """Send prompts to LLM and return raw response text."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (also compatible with OpenAI-like APIs)."""

    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_ENDPOINT if settings.LLM_ENDPOINT else None,
        )

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        from anthropic import Anthropic

        base_url = settings.LLM_ENDPOINT if settings.LLM_ENDPOINT else None
        self.client = Anthropic(api_key=settings.LLM_API_KEY, base_url=base_url)

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (uses OpenAI-compatible API)."""

    def __init__(self):
        from openai import OpenAI

        endpoint = settings.LLM_ENDPOINT or "http://localhost:11434/v1"
        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't need a real key
            base_url=endpoint,
        )

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        # Ollama may not support response_format, so we add JSON instruction
        enhanced_user_prompt = f"{user_prompt}\n\nIMPORTANT: Return ONLY valid JSON, no other text."

        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_user_prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content


def get_llm_provider() -> LLMProvider:
    """Factory function to create the appropriate LLM provider."""
    llm_type = settings.LLM_TYPE.lower()

    if llm_type == "openai":
        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is required for OpenAI")
        return OpenAIProvider()

    elif llm_type == "anthropic":
        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is required for Anthropic")
        return AnthropicProvider()

    elif llm_type == "ollama":
        return OllamaProvider()

    elif llm_type == "openai_compatible":
        # Generic OpenAI-compatible endpoint (vLLM, LocalAI, etc.)
        if not settings.LLM_ENDPOINT:
            raise ValueError("LLM_ENDPOINT is required for openai_compatible")
        return OpenAIProvider()

    else:
        raise ValueError(f"Unknown LLM_TYPE: {llm_type}")


def analyze_cv_text(cv_text: str) -> list[ExtractedLine]:
    """
    Analyze CV text using LLM and extract structured information.

    Args:
        cv_text: Raw text extracted from the CV.

    Returns:
        List of ExtractedLine objects.

    Raises:
        ValueError: If LLM analysis fails or returns invalid response.
    """
    provider = get_llm_provider()
    user_prompt = USER_PROMPT_TEMPLATE.format(cv_text=cv_text)

    logger.info(f"Using LLM type: {settings.LLM_TYPE}, model: {settings.LLM_MODEL}")
    if settings.LLM_ENDPOINT:
        logger.info(f"Custom endpoint: {settings.LLM_ENDPOINT}")

    try:
        logger.info(f"Sending {len(cv_text)} chars to LLM for analysis")
        response_text = provider.analyze(SYSTEM_PROMPT, user_prompt)
        logger.debug(f"LLM response: {response_text[:500]}...")

        return parse_llm_response(response_text)

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        raise ValueError(f"LLM analysis failed: {e}") from e


def parse_llm_response(response_text: str) -> list[ExtractedLine]:
    """
    Parse LLM JSON response into ExtractedLine objects.

    Args:
        response_text: Raw JSON string from LLM.

    Returns:
        List of validated ExtractedLine objects.
    """
    # Try to extract JSON from response (some models add text around it)
    json_text = response_text.strip()

    # If response starts with markdown code block, extract JSON
    if json_text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_text)
        if match:
            json_text = match.group(1).strip()

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e

    extracted_lines = data.get("extracted_lines", [])

    if not isinstance(extracted_lines, list):
        raise ValueError("extracted_lines must be a list")

    result = []
    valid_types = {ct.value for ct in ContentType}

    for item in extracted_lines:
        content_type = item.get("content_type", "other")

        # Validate content_type
        if content_type not in valid_types:
            logger.warning(f"Unknown content_type '{content_type}', using 'other'")
            content_type = "other"

        content = item.get("content", "").strip()
        if not content:
            continue

        order = item.get("order", 0)
        if not isinstance(order, int):
            order = 0

        result.append(
            ExtractedLine(
                content_type=ContentType(content_type),
                content=content,
                order=order,
            )
        )

    logger.info(f"Parsed {len(result)} extracted lines from LLM response")
    return result
