"""Tests for settings configuration module."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

from src.infrastructure.config.settings import (
    Settings,
    get_env_var,
    get_settings,
    has_gemini_config,
)


class TestSettings:
    """Test Settings configuration class."""

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_default_values(self) -> None:
        """Test default values are set correctly."""
        # Create settings without env file loading
        settings = Settings(_env_file=None)

        # Check key defaults
        assert settings.gcp_region == "us-central1"
        assert settings.gemini_model == "gemini-1.5-pro"
        assert settings.use_vertex_ai is True
        assert settings.database_path == "data/trainer.db"
        assert settings.questions_json_path == "data/questions.json"
        assert settings.max_daily_questions == 50
        assert settings.show_explanations is True
        assert settings.log_level == "INFO"

    @patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "test-api-key",
            "GCP_PROJECT_ID": "test-project",
            "GCP_REGION": "us-west1",
            "INTEGRAN_MAX_DAILY_QUESTIONS": "25",
            "INTEGRAN_SHOW_EXPLANATIONS": "false",
        },
    )
    def test_settings_from_environment(self) -> None:
        """Test settings loaded from environment variables."""
        settings = Settings()

        assert settings.gemini_api_key == "test-api-key"
        assert settings.gcp_project_id == "test-project"
        assert settings.gcp_region == "us-west1"
        assert settings.max_daily_questions == 25
        assert settings.show_explanations is False

    def test_get_settings_returns_instance(self) -> None:
        """Test get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    @patch.dict(
        os.environ,
        {
            "GCP_PROJECT_ID": "test-project",
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "USE_VERTEX_AI": "true",
        },
    )
    def test_has_gemini_config_vertex_ai_with_credentials(self) -> None:
        """Test has_gemini_config with Vertex AI and credentials."""
        assert has_gemini_config() is True

    @patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project", "USE_VERTEX_AI": "true"})
    def test_has_gemini_config_vertex_ai_no_credentials(self) -> None:
        """Test has_gemini_config with Vertex AI but no credentials."""
        # Clear any existing credentials
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

        # Mock settings to not have credentials
        with patch("src.infrastructure.config.settings.get_settings") as mock_get:
            mock_settings = Mock()
            mock_settings.gcp_project_id = "test-project"
            mock_settings.google_application_credentials = ""
            mock_settings.use_vertex_ai = True
            mock_get.return_value = mock_settings

            assert has_gemini_config() is False

    @patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "test-key",
            "GCP_PROJECT_ID": "test-project",
            "USE_VERTEX_AI": "false",
        },
    )
    def test_has_gemini_config_api_key_mode(self) -> None:
        """Test has_gemini_config with API key mode."""
        assert has_gemini_config() is True

    @patch.dict(
        os.environ, {"GCP_PROJECT_ID": "test-project", "USE_VERTEX_AI": "false"}
    )
    def test_has_gemini_config_api_key_mode_no_key(self) -> None:
        """Test has_gemini_config with API key mode but no key."""
        # Clear any existing API key
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        with patch("src.infrastructure.config.settings.get_settings") as mock_get:
            mock_settings = Mock()
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gemini_api_key = ""
            mock_settings.use_vertex_ai = False
            mock_get.return_value = mock_settings

            assert has_gemini_config() is False

    def test_get_env_var_with_value(self) -> None:
        """Test get_env_var with existing environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_env_var("TEST_VAR")
            assert result == "test_value"

    def test_get_env_var_with_default(self) -> None:
        """Test get_env_var with default value."""
        result = get_env_var("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"

    def test_get_env_var_no_default(self) -> None:
        """Test get_env_var without default returns None."""
        result = get_env_var("NONEXISTENT_VAR")
        assert result is None

    def test_boolean_field_parsing(self) -> None:
        """Test boolean field parsing from environment."""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_val, expected in test_cases:
            with patch.dict(os.environ, {"INTEGRAN_SHOW_EXPLANATIONS": env_val}):
                settings = Settings()
                assert settings.show_explanations == expected

    def test_integer_field_parsing(self) -> None:
        """Test integer field parsing from environment."""
        with patch.dict(os.environ, {"INTEGRAN_MAX_DAILY_QUESTIONS": "75"}):
            settings = Settings()
            assert settings.max_daily_questions == 75
            assert isinstance(settings.max_daily_questions, int)

    def test_model_config_settings(self) -> None:
        """Test model configuration settings."""
        settings = Settings()
        config = settings.model_config

        assert config["env_prefix"] == ""
        assert config["case_sensitive"] is False
        assert config["env_file"] == ".env"
        assert config["env_file_encoding"] == "utf-8"

    @patch.dict(os.environ, {}, clear=True)
    def test_empty_environment(self) -> None:
        """Test settings with completely empty environment."""
        settings = Settings(_env_file=None)

        # Should still have defaults
        assert settings.gcp_region == "us-central1"
        assert settings.gemini_api_key == ""
        assert settings.gcp_project_id == ""
        assert settings.use_vertex_ai is True
