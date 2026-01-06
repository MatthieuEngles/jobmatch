"""Configuration settings for cv-ingestion service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service
    SERVICE_NAME: str = "cv-ingestion"
    DEBUG: bool = False

    # LLM Provider
    LLM_TYPE: str = "openai"  # openai, anthropic, ollama, gemini
    LLM_ENDPOINT: str = ""  # Custom endpoint URL (for local/proxy)
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 8192  # Max tokens for LLM response

    # GCP Configuration (for Vertex AI)
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "europe-west1"

    # Processing limits
    MAX_FILE_SIZE_MB: int = 10
    SUPPORTED_FORMATS: str = "pdf,docx"
    EXTRACTION_TIMEOUT_SECONDS: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
