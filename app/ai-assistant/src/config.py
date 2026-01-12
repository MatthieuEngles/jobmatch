"""Configuration settings for ai-assistant service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service
    SERVICE_NAME: str = "ai-assistant"
    DEBUG: bool = False

    # LLM Provider
    LLM_TYPE: str = "openai"  # openai, anthropic, ollama, gemini
    LLM_ENDPOINT: str = ""  # Custom endpoint URL (for local/proxy)
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 2048  # Max tokens for LLM response

    # GCP Configuration (for Vertex AI)
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "europe-west1"

    # Chat settings
    CHAT_TIMEOUT_SECONDS: int = 60
    MAX_CONVERSATION_MESSAGES: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
