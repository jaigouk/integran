"""Application settings and configuration management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    # Look for .env file in the project root
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Also try current working directory
        load_dotenv(".env", verbose=False)
except ImportError:
    # python-dotenv not available, continue without it
    pass


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Gemini API Configuration (optional for PDF extraction)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", alias="GCP_REGION")
    gemini_model: str = Field(default="gemini-1.5-pro", alias="GEMINI_MODEL")
    google_application_credentials: str = Field(
        default="", alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    use_vertex_ai: bool = Field(default=True, alias="USE_VERTEX_AI")

    # Database Configuration
    database_path: str = Field(
        default="data/trainer.db", alias="INTEGRAN_DATABASE_PATH"
    )

    # Questions Data Configuration
    questions_json_path: str = Field(
        default="data/questions.json", alias="INTEGRAN_QUESTIONS_JSON_PATH"
    )
    questions_csv_path: str = Field(
        default="data/questions.csv", alias="INTEGRAN_QUESTIONS_CSV_PATH"
    )
    pdf_path: str = Field(
        default="data/gesamtfragenkatalog-lebenindeutschland.pdf",
        alias="INTEGRAN_PDF_PATH",
    )

    # Application Configuration
    max_daily_questions: int = Field(default=50, alias="INTEGRAN_MAX_DAILY_QUESTIONS")
    show_explanations: bool = Field(default=True, alias="INTEGRAN_SHOW_EXPLANATIONS")
    color_mode: str = Field(default="auto", alias="INTEGRAN_COLOR_MODE")
    terminal_width: str = Field(default="auto", alias="INTEGRAN_TERMINAL_WIDTH")
    question_timeout: int = Field(default=60, alias="INTEGRAN_QUESTION_TIMEOUT")
    auto_save: bool = Field(default=True, alias="INTEGRAN_AUTO_SAVE")
    spaced_repetition: bool = Field(default=True, alias="INTEGRAN_SPACED_REPETITION")
    repetition_interval: int = Field(default=3, alias="INTEGRAN_REPETITION_INTERVAL")

    # Logging Configuration
    log_level: str = Field(default="INFO", alias="INTEGRAN_LOG_LEVEL")
    log_file: str = Field(default="logs/integran.log", alias="INTEGRAN_LOG_FILE")

    # RAG Configuration removed as it was not used in final dataset generation

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


def has_gemini_config() -> bool:
    """Check if Gemini API configuration is available."""
    settings = get_settings()
    if settings.use_vertex_ai:
        # For Vertex AI, we need project ID and either credentials file or default auth
        return bool(
            settings.gcp_project_id
            and (
                settings.google_application_credentials
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )
        )
    else:
        # For API key auth, we need API key and project ID
        return bool(settings.gemini_api_key and settings.gcp_project_id)


# has_rag_config function removed as RAG was not used in final dataset generation


def get_env_var(key: str, default: Any = None) -> Any:
    """Get environment variable with fallback to default."""
    return os.getenv(key, default)


# Global settings instance
settings = get_settings()
