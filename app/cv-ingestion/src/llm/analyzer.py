"""LLM-based CV analysis - provider agnostic with Vision support."""

import base64
import json
import logging
import re
from abc import ABC, abstractmethod

from ..config import settings
from ..prompts import (
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_VISION,
    get_cv_text_prompt,
    get_cv_vision_prompt,
)
from ..schemas import ContentType, ExtractedLine

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        """Send prompts to LLM and return raw response text."""
        pass

    def supports_vision(self) -> bool:
        """Check if this provider supports vision/image analysis.

        Override in subclasses that support vision.
        """
        return False

    def analyze_images(self, system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
        """Analyze images using vision LLM.

        Args:
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt for the LLM.
            images: List of image bytes (PNG/JPEG).

        Returns:
            Raw response text from LLM.

        Raises:
            NotImplementedError: If provider doesn't support vision.
        """
        raise NotImplementedError("This provider does not support vision")


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (also compatible with OpenAI-like APIs)."""

    # Models known to support vision
    VISION_MODELS = {"gpt-4-vision-preview", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"}

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
    ):
        from openai import OpenAI

        # Use provided values or fall back to settings
        actual_key = api_key or settings.LLM_API_KEY
        actual_endpoint = endpoint or settings.LLM_ENDPOINT
        actual_model = model or settings.LLM_MODEL

        self.client = OpenAI(
            api_key=actual_key,
            base_url=actual_endpoint if actual_endpoint else None,
        )
        self._model = actual_model

    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        # Check if model name contains vision indicators or is in known list
        model_lower = self._model.lower()
        if self._model in self.VISION_MODELS:
            return True
        if "vision" in model_lower or "gpt-4o" in model_lower:
            return True
        # For custom endpoints, check config flag
        return getattr(settings, "LLM_SUPPORTS_VISION", False)

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def analyze_images(self, system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
        """Analyze images using OpenAI Vision API."""
        # Build content with images
        content = [{"type": "text", "text": user_prompt}]

        for img_bytes in images:
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high",
                    },
                }
            )

        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    # Claude models with vision support
    VISION_MODELS = {
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-sonnet-20241022",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
    }

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
    ):
        from anthropic import Anthropic

        # Use provided values or fall back to settings
        actual_key = api_key or settings.LLM_API_KEY
        actual_endpoint = endpoint or settings.LLM_ENDPOINT
        actual_model = model or settings.LLM_MODEL

        base_url = actual_endpoint if actual_endpoint else None
        self.client = Anthropic(api_key=actual_key, base_url=base_url)
        self._model = actual_model

    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        # All Claude 3+ models support vision
        model_lower = self._model.lower()
        if self._model in self.VISION_MODELS:
            return True
        if "claude-3" in model_lower or "claude-sonnet-4" in model_lower or "claude-opus-4" in model_lower:
            return True
        return getattr(settings, "LLM_SUPPORTS_VISION", False)

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def analyze_images(self, system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
        """Analyze images using Anthropic Vision API."""
        # Build content with images
        content = []

        for img_bytes in images:
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64_image,
                    },
                }
            )

        content.append({"type": "text", "text": user_prompt})

        response = self.client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (uses OpenAI-compatible API)."""

    # Ollama models with vision support
    VISION_MODELS = {"llava", "llava:7b", "llava:13b", "bakllava", "llava-llama3"}

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
    ):
        from openai import OpenAI

        # Use provided values or fall back to settings
        actual_endpoint = endpoint or settings.LLM_ENDPOINT or "http://localhost:11434/v1"
        actual_model = model or settings.LLM_MODEL

        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't need a real key
            base_url=actual_endpoint,
        )
        self._model = actual_model

    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        model_lower = self._model.lower()
        if self._model in self.VISION_MODELS:
            return True
        if "llava" in model_lower or "bakllava" in model_lower:
            return True
        return getattr(settings, "LLM_SUPPORTS_VISION", False)

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        # Ollama may not support response_format, so we add JSON instruction
        enhanced_user_prompt = f"{user_prompt}\n\nIMPORTANT: Return ONLY valid JSON, no other text."

        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_user_prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content

    def analyze_images(self, system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
        """Analyze images using Ollama Vision (LLaVA)."""
        enhanced_user_prompt = f"{user_prompt}\n\nIMPORTANT: Return ONLY valid JSON, no other text."

        # Build content with images (OpenAI-compatible format)
        content = [{"type": "text", "text": enhanced_user_prompt}]

        for img_bytes in images:
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                }
            )

        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content


class LLMConfig:
    """Configuration for LLM provider, can override environment settings."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key


def get_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Factory function to create the appropriate LLM provider.

    Args:
        config: Optional LLM configuration that overrides environment settings.
                If None, uses settings from environment variables.
    """
    # Determine which type of provider to use
    # If custom config with endpoint provided, use openai_compatible type
    if config and config.endpoint:
        llm_type = "openai_compatible"
        api_key = config.api_key
        endpoint = config.endpoint
        model = config.model
    else:
        llm_type = settings.LLM_TYPE.lower()
        api_key = config.api_key if config else None
        endpoint = config.endpoint if config else None
        model = config.model if config else None

    if llm_type == "openai":
        actual_key = api_key or settings.LLM_API_KEY
        if not actual_key:
            raise ValueError("LLM_API_KEY is required for OpenAI")
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model)

    elif llm_type == "anthropic":
        actual_key = api_key or settings.LLM_API_KEY
        if not actual_key:
            raise ValueError("LLM_API_KEY is required for Anthropic")
        return AnthropicProvider(api_key=api_key, endpoint=endpoint, model=model)

    elif llm_type == "ollama":
        return OllamaProvider(endpoint=endpoint, model=model)

    elif llm_type == "openai_compatible":
        # Generic OpenAI-compatible endpoint (vLLM, LocalAI, user custom, etc.)
        actual_endpoint = endpoint or settings.LLM_ENDPOINT
        if not actual_endpoint:
            raise ValueError("LLM_ENDPOINT is required for openai_compatible")
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model)

    else:
        raise ValueError(f"Unknown LLM_TYPE: {llm_type}")


def analyze_cv_text(cv_text: str, llm_config: LLMConfig | None = None) -> list[ExtractedLine]:
    """
    Analyze CV text using LLM and extract structured information.

    Args:
        cv_text: Raw text extracted from the CV.
        llm_config: Optional LLM configuration that overrides environment settings.

    Returns:
        List of ExtractedLine objects.

    Raises:
        ValueError: If LLM analysis fails or returns invalid response.
    """
    provider = get_llm_provider(llm_config)
    system_prompt = get_cv_text_prompt()
    user_prompt = USER_PROMPT_TEMPLATE.format(cv_text=cv_text)

    if llm_config and llm_config.endpoint:
        logger.info(f"Using custom LLM endpoint: {llm_config.endpoint}, model: {llm_config.model}")
    else:
        logger.info(f"Using LLM type: {settings.LLM_TYPE}, model: {settings.LLM_MODEL}")
        if settings.LLM_ENDPOINT:
            logger.info(f"Custom endpoint: {settings.LLM_ENDPOINT}")

    try:
        logger.info(f"Sending {len(cv_text)} chars to LLM for analysis")
        response_text = provider.analyze(system_prompt, user_prompt)
        logger.debug(f"LLM response: {response_text[:500]}...")

        return parse_llm_response(response_text)

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        raise ValueError(f"LLM analysis failed: {e}") from e


def analyze_cv_images(images: list[bytes], llm_config: LLMConfig | None = None) -> list[ExtractedLine]:
    """
    Analyze CV images using Vision LLM and extract structured information.

    Args:
        images: List of image bytes (PNG format recommended).
        llm_config: Optional LLM configuration that overrides environment settings.

    Returns:
        List of ExtractedLine objects.

    Raises:
        ValueError: If LLM analysis fails, returns invalid response,
                   or provider doesn't support vision.
    """
    provider = get_llm_provider(llm_config)

    if not provider.supports_vision():
        model_info = llm_config.model if llm_config else settings.LLM_MODEL
        raise ValueError(
            f"LLM model {model_info} does not support vision. Use a vision-capable model or enable OCR fallback."
        )

    system_prompt = get_cv_vision_prompt()
    user_prompt = USER_PROMPT_VISION

    if llm_config and llm_config.endpoint:
        logger.info(f"Using custom Vision LLM: {llm_config.endpoint}, model: {llm_config.model}")
    else:
        logger.info(f"Using Vision LLM type: {settings.LLM_TYPE}, model: {settings.LLM_MODEL}")
    logger.info(f"Processing {len(images)} image(s)")

    try:
        response_text = provider.analyze_images(system_prompt, user_prompt, images)
        logger.debug(f"Vision LLM response: {response_text[:500]}...")

        return parse_llm_response(response_text)

    except Exception as e:
        logger.error(f"Vision LLM analysis failed: {e}")
        raise ValueError(f"Vision LLM analysis failed: {e}") from e


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
