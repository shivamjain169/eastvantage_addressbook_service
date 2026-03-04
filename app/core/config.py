# Centralised application settings — reads all config from environment variables or .env file.

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolves to the project root regardless of the working directory at runtime
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "sqlite:///./addressbook.db"
    LOG_LEVEL: str = "INFO"


# Module-level singleton — imported directly wherever config values are needed
settings = Settings()
