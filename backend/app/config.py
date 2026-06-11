"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./regloop.db"
    sqlite_database_url: str = "sqlite+aiosqlite:///./regloop.db"

    # Storage
    upload_dir: str = "./storage/uploads"

    # LLM
    llm_provider: str = "open" + "ai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
