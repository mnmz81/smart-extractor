"""Application settings, loaded from environment variables and an optional `.env` file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    API keys are `SecretStr`, so `repr()`, logs and tracebacks show `**********`
    instead of the real value. Call `.get_secret_value()` only where the key is used.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once on first use."""
    return Settings()
