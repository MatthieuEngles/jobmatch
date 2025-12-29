"""LLM providers for chat - simplified version for conversational use."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to LLM and return response text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt for the conversation.

        Returns:
            Assistant's response text.
        """
        pass

    @abstractmethod
    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to LLM and yield response tokens as they arrive.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt for the conversation.

        Yields:
            Response text chunks as they are generated.
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (also compatible with OpenAI-like APIs)."""

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
        self._endpoint = actual_endpoint or "https://api.openai.com/v1"

    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to OpenAI and return response."""
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        # Log LLM call details
        logger.info("=== LLM CALL (OpenAI) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        response = self.client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=0.7,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content

    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to OpenAI and yield response tokens."""
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        # Log LLM call details
        logger.info("=== LLM STREAM (OpenAI) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        stream = self.client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=0.7,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

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
        self._endpoint = actual_endpoint or "https://api.anthropic.com"

    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to Anthropic and return response."""
        # Log LLM call details
        logger.info("=== LLM CALL (Anthropic) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        response = self.client.messages.create(
            model=self._model,
            max_tokens=settings.LLM_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text

    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to Anthropic and yield response tokens."""
        # Log LLM call details
        logger.info("=== LLM STREAM (Anthropic) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        with self.client.messages.stream(
            model=self._model,
            max_tokens=settings.LLM_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        ) as stream:
            yield from stream.text_stream


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (uses OpenAI-compatible API)."""

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
        self._endpoint = actual_endpoint

    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to Ollama and return response."""
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        # Log LLM call details
        logger.info("=== LLM CALL (Ollama) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        response = self.client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to Ollama and yield response tokens."""
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        # Log LLM call details
        logger.info("=== LLM STREAM (Ollama) ===")
        logger.info(f"Endpoint: {self._endpoint}")
        logger.info(f"Model: {self._model}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        stream = self.client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


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
        actual_endpoint = endpoint or settings.LLM_ENDPOINT
        if not actual_endpoint:
            raise ValueError("LLM_ENDPOINT is required for openai_compatible")
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model)

    else:
        raise ValueError(f"Unknown LLM_TYPE: {llm_type}")
