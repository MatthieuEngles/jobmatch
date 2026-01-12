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
        max_tokens: int | None = None,
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
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS

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
            max_tokens=self._max_tokens,
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
            max_tokens=self._max_tokens,
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
        max_tokens: int | None = None,
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
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS

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
            max_tokens=self._max_tokens,
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
            max_tokens=self._max_tokens,
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
        max_tokens: int | None = None,
    ):
        from openai import OpenAI

        # Use provided values or fall back to settings
        actual_endpoint = endpoint or settings.LLM_ENDPOINT or "http://localhost:11434/v1"
        actual_model = model or settings.LLM_MODEL
        # Use provided API key, or settings, or default "ollama" for local instances
        actual_key = api_key or settings.LLM_API_KEY or "ollama"

        self.client = OpenAI(
            api_key=actual_key,
            base_url=actual_endpoint if actual_endpoint.endswith("/v1") else f"{actual_endpoint}/v1",
        )
        self._model = actual_model
        self._endpoint = actual_endpoint if actual_endpoint.endswith("/v1") else f"{actual_endpoint}/v1"
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS

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


class GeminiProvider(LLMProvider):
    """Google Gemini via Vertex AI provider (uses service account authentication)."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        import vertexai
        from vertexai.generative_models import GenerativeModel

        # Use provided values or fall back to settings
        actual_model = model or settings.LLM_MODEL or "gemini-1.5-flash-002"

        # Get project and location from settings or environment
        project_id = getattr(settings, "GCP_PROJECT_ID", None)
        location = getattr(settings, "GCP_LOCATION", "europe-west1")

        # Initialize Vertex AI (uses ADC - Application Default Credentials)
        vertexai.init(project=project_id, location=location)

        self._model_name = actual_model
        self._model = GenerativeModel(actual_model)
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        logger.info(f"Initialized Vertex AI Gemini: project={project_id}, location={location}, model={actual_model}")

    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to Gemini and return response."""
        from vertexai.generative_models import Content, GenerationConfig, Part

        # Build conversation history
        history = []
        for msg in messages[:-1]:  # All but last message
            role = "user" if msg["role"] == "user" else "model"
            history.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

        # Start chat with history
        chat = self._model.start_chat(history=history)

        # Get last user message
        last_message = messages[-1]["content"] if messages else ""

        # Add system prompt to the message
        full_message = f"{system_prompt}\n\n{last_message}"

        logger.info("=== LLM CALL (Vertex AI Gemini) ===")
        logger.info(f"Model: {self._model_name}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        generation_config = GenerationConfig(
            temperature=0.7,
            max_output_tokens=self._max_tokens,
        )

        response = chat.send_message(full_message, generation_config=generation_config)
        return response.text

    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to Gemini and yield response tokens."""
        from vertexai.generative_models import Content, GenerationConfig, Part

        # Build conversation history
        history = []
        for msg in messages[:-1]:  # All but last message
            role = "user" if msg["role"] == "user" else "model"
            history.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

        # Start chat with history
        chat = self._model.start_chat(history=history)

        # Get last user message
        last_message = messages[-1]["content"] if messages else ""

        # Add system prompt to the message
        full_message = f"{system_prompt}\n\n{last_message}"

        logger.info("=== LLM STREAM (Vertex AI Gemini) ===")
        logger.info(f"Model: {self._model_name}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        generation_config = GenerationConfig(
            temperature=0.7,
            max_output_tokens=self._max_tokens,
        )

        response = chat.send_message(full_message, generation_config=generation_config, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text


class OllamaNativeProvider(LLMProvider):
    """Ollama provider using native /api/chat endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        import httpx

        # Use provided values or fall back to settings
        actual_endpoint = endpoint or settings.LLM_ENDPOINT or "http://localhost:11434"
        actual_model = model or settings.LLM_MODEL
        actual_key = api_key or settings.LLM_API_KEY

        # Remove /v1 suffix if present (we use native API)
        if actual_endpoint.endswith("/v1"):
            actual_endpoint = actual_endpoint[:-3]

        self._endpoint = actual_endpoint.rstrip("/")
        self._model = actual_model
        self._api_key = actual_key
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        # Build headers
        self._headers = {"Content-Type": "application/json"}
        if actual_key:
            self._headers["Authorization"] = f"Bearer {actual_key}"

        self._client = httpx.Client(timeout=120.0)

    def chat(self, messages: list[dict], system_prompt: str) -> str:
        """Send messages to Ollama native API and return response."""
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        url = f"{self._endpoint}/api/chat"
        payload = {
            "model": self._model,
            "messages": all_messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_ctx": self._max_tokens},
        }

        logger.info("=== LLM CALL (Ollama Native) ===")
        logger.info(f"Endpoint: {url}")
        logger.info(f"Model: {self._model}")
        logger.info(f"Context size (num_ctx): {self._max_tokens}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        response = self._client.post(url, json=payload, headers=self._headers)
        response.raise_for_status()

        data = response.json()
        content = data.get("message", {}).get("content", "")

        logger.info(f"Response ({len(content)} chars): {content[:300]}...")
        return content

    def chat_stream(self, messages: list[dict], system_prompt: str) -> Iterator[str]:
        """Send messages to Ollama native API and yield response tokens."""
        import httpx

        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(messages)

        url = f"{self._endpoint}/api/chat"
        payload = {
            "model": self._model,
            "messages": all_messages,
            "stream": True,
            "options": {"temperature": 0.7, "num_ctx": self._max_tokens},
        }

        logger.info("=== LLM STREAM (Ollama Native) ===")
        logger.info(f"Endpoint: {url}")
        logger.info(f"Model: {self._model}")
        logger.info(f"Context size (num_ctx): {self._max_tokens}")
        logger.info(f"System prompt ({len(system_prompt)} chars): {system_prompt[:500]}...")
        for msg in messages:
            logger.info(f"Message [{msg['role']}]: {msg['content'][:300]}...")

        import json

        with httpx.stream("POST", url, json=payload, headers=self._headers, timeout=120.0) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


class LLMConfig:
    """Configuration for LLM provider, can override environment settings."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        api_mode: str | None = None,
        max_tokens: int | None = None,
    ):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        # api_mode: "openai_compatible" or "ollama_native"
        self.api_mode = api_mode or "openai_compatible"
        self.max_tokens = max_tokens


def get_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Factory function to create the appropriate LLM provider.

    Args:
        config: Optional LLM configuration that overrides environment settings.
                If None, uses settings from environment variables.
    """
    # Extract config values
    api_key = config.api_key if config else None
    endpoint = config.endpoint if config else None
    model = config.model if config else None
    api_mode = config.api_mode if config else "openai_compatible"
    max_tokens = config.max_tokens if config else None

    # Determine which type of provider to use
    # If custom config with endpoint provided, use the api_mode to decide
    if config and config.endpoint:
        if api_mode == "ollama_native":
            logger.info(f"Using Ollama Native API mode for endpoint: {endpoint}")
            return OllamaNativeProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)
        else:
            logger.info(f"Using OpenAI-compatible API mode for endpoint: {endpoint}")
            return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    # Use environment settings
    llm_type = settings.LLM_TYPE.lower()

    if llm_type == "openai":
        actual_key = api_key or settings.LLM_API_KEY
        if not actual_key:
            raise ValueError("LLM_API_KEY is required for OpenAI")
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    elif llm_type == "anthropic":
        actual_key = api_key or settings.LLM_API_KEY
        if not actual_key:
            raise ValueError("LLM_API_KEY is required for Anthropic")
        return AnthropicProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    elif llm_type == "ollama":
        # For Ollama from env, respect api_mode if provided in config
        if api_mode == "ollama_native":
            return OllamaNativeProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)
        return OllamaProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    elif llm_type == "openai_compatible":
        actual_endpoint = endpoint or settings.LLM_ENDPOINT
        if not actual_endpoint:
            raise ValueError("LLM_ENDPOINT is required for openai_compatible")
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    elif llm_type == "gemini" or llm_type == "google":
        # Google Gemini API
        return GeminiProvider(api_key=api_key, endpoint=endpoint, model=model, max_tokens=max_tokens)

    else:
        raise ValueError(f"Unknown LLM_TYPE: {llm_type}")
