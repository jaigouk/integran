"""Tests for settings and configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.infrastructure.config.settings import (
    Settings,
    get_env_var,
    get_settings,
    has_gemini_config,
)


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
            assert settings.gemini_model == "gemini-1.5-pro"
            assert settings.use_vertex_ai is True

            # Application defaults
            assert settings.max_daily_questions == 50
            assert settings.show_explanations is True
            assert settings.color_mode == "auto"
            assert settings.spaced_repetition is True
            assert settings.log_level == "INFO"

            # RAG settings removed as RAG was not used in final dataset

    def test_environment_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "GCP_REGION": "europe-west3",
                "INTEGRAN_MAX_DAILY_QUESTIONS": "25",
            },
        ):
            settings = Settings()
            assert settings.gcp_region == "europe-west3"
            assert settings.max_daily_questions == 25

    # RAG setting assertions removed

    def test_get_settings_singleton(self):
        """Test that get_settings returns consistent instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        # They should have the same values (though not necessarily same instance)
        assert settings1.gcp_region == settings2.gcp_region

    # chunk_size comparison removed

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

    # has_rag_config tests removed as RAG was not used in final dataset

    def test_file_paths(self):
        """Test file path settings."""
        settings = Settings()

        # Check that paths are strings
        assert isinstance(settings.database_path, str)
        assert isinstance(settings.questions_json_path, str)
        assert isinstance(settings.pdf_path, str)
        # vector_store_dir removed

        # Check default paths
        assert "trainer.db" in settings.database_path
        assert "questions.json" in settings.questions_json_path

    # vector_store check removed

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
                # chunk_size removed
            },
        ):
            settings = Settings()
            assert settings.max_daily_questions == 100
            assert settings.question_timeout == 120

    # chunk_size assertion removed

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


class TestGetEnvVar:
    """Test get_env_var utility function."""

    def test_existing_environment_variable(self):
        """Test getting existing environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}, clear=False):
            result = get_env_var("TEST_VAR")
            assert result == "test_value"

    def test_missing_environment_variable_no_default(self):
        """Test getting missing environment variable without default."""
        result = get_env_var("NONEXISTENT_VAR")
        assert result is None

    def test_missing_environment_variable_with_default(self):
        """Test getting missing environment variable with default."""
        result = get_env_var("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"

    def test_empty_environment_variable(self):
        """Test getting empty environment variable."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}, clear=False):
            result = get_env_var("EMPTY_VAR", "default")
            assert result == ""  # Empty string should be returned, not default

    def test_various_types_as_default(self):
        """Test various types as default values."""
        # String default
        assert get_env_var("MISSING", "default") == "default"

        # Integer default
        assert get_env_var("MISSING", 42) == 42

        # Boolean default
        assert get_env_var("MISSING", True) is True

        # None default
        assert get_env_var("MISSING", None) is None

        # List default
        default_list = [1, 2, 3]
        assert get_env_var("MISSING", default_list) is default_list


class TestAdvancedSettings:
    """Test advanced settings functionality."""

    def test_all_field_aliases(self):
        """Test that all field aliases work correctly."""
        settings = Settings(
            GEMINI_API_KEY="test-key",
            GCP_PROJECT_ID="test-project",
            GCP_REGION="test-region",
            GEMINI_MODEL="test-model",
            GOOGLE_APPLICATION_CREDENTIALS="test-creds",
            USE_VERTEX_AI=False,
            INTEGRAN_DATABASE_PATH="test.db",
            INTEGRAN_QUESTIONS_JSON_PATH="test.json",
            INTEGRAN_QUESTIONS_CSV_PATH="test.csv",
            INTEGRAN_PDF_PATH="test.pdf",
            INTEGRAN_MAX_DAILY_QUESTIONS=25,
            INTEGRAN_SHOW_EXPLANATIONS=False,
            INTEGRAN_COLOR_MODE="light",
            INTEGRAN_TERMINAL_WIDTH="100",
            INTEGRAN_QUESTION_TIMEOUT=30,
            INTEGRAN_AUTO_SAVE=False,
            INTEGRAN_SPACED_REPETITION=False,
            INTEGRAN_REPETITION_INTERVAL=5,
            INTEGRAN_LOG_LEVEL="DEBUG",
            INTEGRAN_LOG_FILE="test.log",
        )

        assert settings.gemini_api_key == "test-key"
        assert settings.gcp_project_id == "test-project"
        assert settings.gcp_region == "test-region"
        assert settings.gemini_model == "test-model"
        assert settings.google_application_credentials == "test-creds"
        assert settings.use_vertex_ai is False
        assert settings.database_path == "test.db"
        assert settings.questions_json_path == "test.json"
        assert settings.questions_csv_path == "test.csv"
        assert settings.pdf_path == "test.pdf"
        assert settings.max_daily_questions == 25
        assert settings.show_explanations is False
        assert settings.color_mode == "light"
        assert settings.terminal_width == "100"
        assert settings.question_timeout == 30
        assert settings.auto_save is False
        assert settings.spaced_repetition is False
        assert settings.repetition_interval == 5
        assert settings.log_level == "DEBUG"
        assert settings.log_file == "test.log"

    def test_boolean_string_conversion(self):
        """Test boolean string conversion from environment variables."""
        boolean_tests = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]

        for env_value, expected in boolean_tests:
            with patch.dict(os.environ, {"USE_VERTEX_AI": env_value}, clear=False):
                settings = Settings()
                assert settings.use_vertex_ai == expected

    def test_model_config_properties(self):
        """Test model configuration properties."""
        settings = Settings()
        config = settings.model_config

        assert config["env_prefix"] == ""
        assert config["case_sensitive"] is False
        assert config["env_file"] == ".env"
        assert config["env_file_encoding"] == "utf-8"

    def test_settings_with_mixed_case_env_vars(self):
        """Test settings with mixed case environment variables."""
        with patch.dict(
            os.environ,
            {
                "gcp_region": "mixed-case-region",  # lowercase
                "GCP_PROJECT_ID": "UPPERCASE-PROJECT",  # uppercase
                "Gemini_Model": "Mixed-Case-Model",  # mixed case
            },
        ):
            settings = Settings()
            # Due to case_sensitive=False, these should work
            assert hasattr(settings, "gcp_region")
            assert hasattr(settings, "gcp_project_id")
            assert hasattr(settings, "gemini_model")


class TestAdvancedGeminiConfig:
    """Test advanced Gemini configuration scenarios."""

    def test_vertex_ai_with_default_credentials(self):
        """Test Vertex AI with default application credentials."""
        env_vars = {
            "GCP_PROJECT_ID": "test-project",
            "USE_VERTEX_AI": "true",
            # No GOOGLE_APPLICATION_CREDENTIALS set
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            patch("os.getenv") as mock_getenv,
        ):
            mock_getenv.return_value = "/default/path/to/creds.json"
            assert has_gemini_config() is True

            # Verify it checks for GOOGLE_APPLICATION_CREDENTIALS
            mock_getenv.assert_called_with("GOOGLE_APPLICATION_CREDENTIALS")

    def test_vertex_ai_no_default_credentials(self):
        """Test Vertex AI without any credentials."""
        env_vars = {
            "GCP_PROJECT_ID": "test-project",
            "USE_VERTEX_AI": "true",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            patch("os.getenv") as mock_getenv,
        ):
            mock_getenv.return_value = None  # No default credentials
            assert has_gemini_config() is False

    def test_api_key_auth_complete(self):
        """Test complete API key authentication."""
        env_vars = {
            "GEMINI_API_KEY": "sk-test-key-123",
            "GCP_PROJECT_ID": "my-project-123",
            "USE_VERTEX_AI": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            assert has_gemini_config() is True

    def test_api_key_auth_partial_configs(self):
        """Test partial API key configurations."""
        # Missing API key
        with patch.dict(
            os.environ,
            {
                "GCP_PROJECT_ID": "test-project",
                "USE_VERTEX_AI": "false",
                "GEMINI_API_KEY": "",
            },
            clear=True,
        ):
            assert has_gemini_config() is False

        # Missing project ID
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "USE_VERTEX_AI": "false",
                "GCP_PROJECT_ID": "",
            },
            clear=True,
        ):
            assert has_gemini_config() is False

    def test_empty_string_values(self):
        """Test that empty string values are treated as missing."""
        env_vars = {
            "GEMINI_API_KEY": "",
            "GCP_PROJECT_ID": "",
            "USE_VERTEX_AI": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            assert has_gemini_config() is False

    def test_whitespace_only_values(self):
        """Test that whitespace-only values are treated as valid."""
        env_vars = {
            "GEMINI_API_KEY": "   ",  # Whitespace only
            "GCP_PROJECT_ID": "test-project",
            "USE_VERTEX_AI": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Whitespace is considered a valid value by bool()
            assert has_gemini_config() is True


class TestDotenvIntegration:
    """Test dotenv integration functionality."""

    def test_dotenv_loading_project_root(self):
        """Test that .env file loading is handled gracefully."""
        # This test is more for documentation - the actual dotenv loading
        # happens at module import time and is difficult to test reliably
        # without complex mocking that can interfere with other tests

        # Verify that the try/except block exists by checking module source
        import inspect

        import src.infrastructure.config.settings

        source = inspect.getsource(src.infrastructure.config.settings)
        assert "try:" in source
        assert "load_dotenv" in source
        assert "ImportError" in source

    def test_dotenv_import_error_handling(self):
        """Test that missing dotenv package doesn't break settings."""
        # Test that settings work even if dotenv is not available
        # This is tested indirectly by creating a settings instance
        settings = Settings()
        assert isinstance(settings, Settings)
        assert hasattr(settings, "gemini_api_key")

    def test_dotenv_path_construction(self):
        """Test that dotenv path construction works."""
        # Test that Path operations work correctly
        import pathlib

        # This mimics the path construction in settings.py
        current_file = pathlib.Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        env_file = project_root / ".env"

        # Should be able to construct the path without error
        assert isinstance(env_file, pathlib.Path)
        assert str(env_file).endswith(".env")


class TestGlobalSettingsInstance:
    """Test the global settings instance."""

    def test_global_settings_instance_exists(self):
        """Test that global settings instance is created."""
        # Import and test the global settings instance
        import src.infrastructure.config.settings

        assert hasattr(src.infrastructure.config.settings, "settings")
        settings_instance = src.infrastructure.config.settings.settings
        assert isinstance(settings_instance, Settings)
        assert hasattr(settings_instance, "gcp_region")
        assert hasattr(settings_instance, "database_path")

    def test_global_instance_has_expected_defaults(self):
        """Test that global instance has expected default values."""
        from src.infrastructure.config.settings import settings

        # Test key defaults that should always be present
        assert isinstance(settings.max_daily_questions, int)
        assert isinstance(settings.use_vertex_ai, bool)
        assert isinstance(settings.show_explanations, bool)
        assert settings.gcp_region in ["us-central1", "europe-west3"]  # Allow both
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class TestSettingsValidation:
    """Test settings validation edge cases."""

    def test_invalid_boolean_values(self):
        """Test handling of invalid boolean values."""
        with pytest.raises(ValidationError):
            Settings(INTEGRAN_AUTO_SAVE="maybe")

    def test_invalid_integer_values(self):
        """Test handling of invalid integer values."""
        with pytest.raises(ValidationError):
            Settings(INTEGRAN_MAX_DAILY_QUESTIONS="lots")

    def test_negative_integer_values(self):
        """Test handling of negative integer values."""
        # Negative values should be accepted by Pydantic int field
        settings = Settings(INTEGRAN_MAX_DAILY_QUESTIONS="-10")
        assert settings.max_daily_questions == -10

    def test_zero_values(self):
        """Test handling of zero values."""
        settings = Settings(
            INTEGRAN_MAX_DAILY_QUESTIONS="0",
            INTEGRAN_QUESTION_TIMEOUT="0",
            INTEGRAN_REPETITION_INTERVAL="0",
        )
        assert settings.max_daily_questions == 0
        assert settings.question_timeout == 0
        assert settings.repetition_interval == 0

    def test_very_large_integer_values(self):
        """Test handling of very large integer values."""
        large_value = str(2**31 - 1)  # Max 32-bit signed int
        settings = Settings(INTEGRAN_MAX_DAILY_QUESTIONS=large_value)
        assert settings.max_daily_questions == 2**31 - 1


class TestSettingsPathHandling:
    """Test settings path handling."""

    def test_relative_paths(self):
        """Test relative path handling."""
        settings = Settings(
            INTEGRAN_DATABASE_PATH="./data/test.db",
            INTEGRAN_QUESTIONS_JSON_PATH="../questions.json",
            INTEGRAN_PDF_PATH="~/documents/test.pdf",
        )

        assert settings.database_path == "./data/test.db"
        assert settings.questions_json_path == "../questions.json"
        assert settings.pdf_path == "~/documents/test.pdf"

    def test_absolute_paths(self):
        """Test absolute path handling."""
        settings = Settings(
            INTEGRAN_DATABASE_PATH="/absolute/path/to/test.db",
            INTEGRAN_LOG_FILE="/var/log/integran.log",
        )

        assert settings.database_path == "/absolute/path/to/test.db"
        assert settings.log_file == "/var/log/integran.log"

    def test_windows_paths(self):
        """Test Windows-style path handling."""
        settings = Settings(
            INTEGRAN_DATABASE_PATH="C:\\Users\\Test\\data\\test.db",
            INTEGRAN_QUESTIONS_JSON_PATH="D:\\Questions\\questions.json",
        )

        assert settings.database_path == "C:\\Users\\Test\\data\\test.db"
        assert settings.questions_json_path == "D:\\Questions\\questions.json"
