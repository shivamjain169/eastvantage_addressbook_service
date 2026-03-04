from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolves to the project root (two levels up from app/core/config.py)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "sqlite:///./addressbook.db"
    LOG_LEVEL: str = "INFO"


settings = Settings()
