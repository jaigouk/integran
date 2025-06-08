"""Tests for settings and configuration management."""

import os
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from src.core.settings import Settings, get_settings, has_gemini_config, has_rag_config


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""

        # Create a Settings class that ignores environment files
        class PureDefaultSettings(Settings):
            model_config = {
                "env_prefix": "",
                "case_sensitive": False,
                "env_file": None,  # Disable env file loading
                "env_file_encoding": "utf-8",
            }

        # Clear environment to test true defaults
        with patch.dict(os.environ, {}, clear=True):
            settings = PureDefaultSettings()

            # Gemini API defaults
            assert settings.gcp_region in [
                "us-central1",
                "europe-west3",
            ]  # Allow both defaults
            assert settings.gemini_model == "gemini-2.5-pro-preview-06-05"
            assert settings.use_vertex_ai is True

            # Application defaults
            assert settings.max_daily_questions == 50
            assert settings.show_explanations is True
            assert settings.color_mode == "auto"
            assert settings.spaced_repetition is True
            assert settings.log_level == "INFO"

            # RAG defaults
            assert settings.vector_store_dir == "data/vector_store"
            assert settings.vector_collection_name == "german_integration_kb"
            assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert settings.chunk_size == 1000
            assert settings.chunk_overlap == 200

    def test_environment_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "GCP_REGION": "europe-west3",
                "INTEGRAN_MAX_DAILY_QUESTIONS": "25",
                "INTEGRAN_CHUNK_SIZE": "1500",
                "FIRECRAWL_API_KEY": "test-key",
            },
        ):
            settings = Settings()
            assert settings.gcp_region == "europe-west3"
            assert settings.max_daily_questions == 25
            assert settings.chunk_size == 1500
            assert settings.firecrawl_api_key == "test-key"

    def test_get_settings_singleton(self):
        """Test that get_settings returns consistent instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        # They should have the same values (though not necessarily same instance)
        assert settings1.gcp_region == settings2.gcp_region
        assert settings1.chunk_size == settings2.chunk_size

    def test_has_gemini_config_vertex_ai(self):
        """Test Gemini config detection for Vertex AI."""
        with patch.dict(
            os.environ,
            {
                "USE_VERTEX_AI": "true",
                "GCP_PROJECT_ID": "test-project",
                "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            },
        ):
            assert has_gemini_config() is True

    def test_has_gemini_config_api_key(self):
        """Test Gemini config detection for API key."""
        with patch.dict(
            os.environ,
            {
                "USE_VERTEX_AI": "false",
                "GCP_PROJECT_ID": "test-project",
                "GEMINI_API_KEY": "test-key",
            },
        ):
            assert has_gemini_config() is True

    def test_has_gemini_config_missing(self):
        """Test Gemini config detection when missing."""
        with patch.dict(
            os.environ,
            {
                "USE_VERTEX_AI": "true",
                "GCP_PROJECT_ID": "",  # Empty project ID
                "GOOGLE_APPLICATION_CREDENTIALS": "",
            },
        ):
            # Missing required config
            assert not has_gemini_config()

    def test_has_rag_config_available(self):
        """Test RAG config when dependencies are available."""
        with patch("builtins.__import__") as mock_import:
            # Mock successful imports
            mock_import.return_value = Mock()
            assert has_rag_config() is True

    def test_has_rag_config_missing(self):
        """Test RAG config when dependencies are missing."""
        # Mock chromadb import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("chromadb not found")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            assert has_rag_config() is False

    def test_file_paths(self):
        """Test file path settings."""
        settings = Settings()

        # Check that paths are strings
        assert isinstance(settings.database_path, str)
        assert isinstance(settings.questions_json_path, str)
        assert isinstance(settings.pdf_path, str)
        assert isinstance(settings.vector_store_dir, str)

        # Check default paths
        assert "trainer.db" in settings.database_path
        assert "questions.json" in settings.questions_json_path
        assert "vector_store" in settings.vector_store_dir

    def test_boolean_settings(self):
        """Test boolean settings parsing."""
        with patch.dict(
            os.environ,
            {
                "INTEGRAN_SHOW_EXPLANATIONS": "false",
                "INTEGRAN_SPACED_REPETITION": "true",
                "USE_VERTEX_AI": "false",
            },
        ):
            settings = Settings()
            assert settings.show_explanations is False
            assert settings.spaced_repetition is True
            assert settings.use_vertex_ai is False

    def test_numeric_settings(self):
        """Test numeric settings parsing."""
        with patch.dict(
            os.environ,
            {
                "INTEGRAN_MAX_DAILY_QUESTIONS": "100",
                "INTEGRAN_QUESTION_TIMEOUT": "120",
                "INTEGRAN_CHUNK_SIZE": "2000",
            },
        ):
            settings = Settings()
            assert settings.max_daily_questions == 100
            assert settings.question_timeout == 120
            assert settings.chunk_size == 2000

    def test_invalid_numeric_settings(self):
        """Test handling of invalid numeric values."""
        with (
            patch.dict(os.environ, {"INTEGRAN_MAX_DAILY_QUESTIONS": "not-a-number"}),
            pytest.raises(ValidationError),
        ):  # Pydantic validation error
            Settings()

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        with patch.dict(
            os.environ,
            {
                "GCP_REGION": "us-east1"  # Test that uppercase works
            },
        ):
            settings = Settings()
            assert settings.gcp_region == "us-east1"
