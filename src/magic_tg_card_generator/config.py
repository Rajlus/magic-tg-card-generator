"""Configuration management for the application."""

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Magic TG Card Generator"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # API Settings
    api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    api_timeout: int = Field(default=30)

    # Database settings
    database_url: str = Field(default="sqlite:///./data/app.db")

    # Paths
    data_dir: Path = Field(default=Path("data"))
    output_dir: Path = Field(default=Path("output"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize settings and create directories."""
        super().__init__(**kwargs)
        self.data_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
