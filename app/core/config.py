from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration lives here, read from environment variables / `.env`.

    Field `database_url` is filled from the env var `DATABASE_URL` (matching is
    case-insensitive). Real environment variables win over values in `.env`.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. Required: the app cannot do anything useful without it.
    # SecretStr because the URL contains the password; it prints as '**********'.
    database_url: SecretStr

    # LLM used to write answers. The provider is a setting, not a code decision.
    llm_provider: Literal["groq", "gemini"] = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None

    # Embeddings (see ADR-003).
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # Vector index (see ADR-004): embedded Qdrant at a local path, or a server URL.
    qdrant_path: str = "./qdrant_data"
    qdrant_url: str | None = None

    # Logging.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"


@lru_cache
def get_settings() -> Settings:
    """Build Settings once and reuse it. Also used as a FastAPI dependency."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
