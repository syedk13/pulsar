from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API settings, read from the environment or the repo-root .env file."""

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    supabase_url: str = ""
    # Server-side only. Never expose to the browser.
    supabase_secret_key: str = Field(default="", repr=False)
    cors_allowed_origins: str = "http://localhost:5173"
    demo_mode: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
