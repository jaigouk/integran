"""Simplified tests for Gemini client functionality."""

import json
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.external.gemini_client import GeminiClient


class TestGeminiClient:
    """Test Gemini AI client - simplified version."""

    @patch("src.infrastructure.external.gemini_client.GENAI_AVAILABLE", True)
    @patch("src.infrastructure.external.gemini_client.get_settings")
    @patch("src.infrastructure.external.gemini_client.genai")
    def test_init_vertex_ai(self, mock_genai, mock_get_settings):
        """Test initialization with Vertex AI."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.use_vertex_ai = True
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_get_settings.return_value = mock_settings

        # Mock genai client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        client = GeminiClient()

        assert client.project_id == "test-project"
        assert client.use_vertex_ai is True
        mock_genai.Client.assert_called_once_with(
            vertexai=True, project="test-project", location="global"
        )

    def test_init_genai_not_available(self):
        """Test initialization fails when genai is not available."""
        with (
            patch("src.infrastructure.external.gemini_client.GENAI_AVAILABLE", False),
            pytest.raises(ImportError, match="google-genai package is required"),
        ):
            GeminiClient()

    @patch("src.infrastructure.external.gemini_client.GENAI_AVAILABLE", True)
    @patch("src.infrastructure.external.gemini_client.time.sleep")
    @patch("src.infrastructure.external.gemini_client.get_settings")
    @patch("src.infrastructure.external.gemini_client.genai")
    @patch("src.infrastructure.external.gemini_client.types")
    def test_generate_text_success(
        self, mock_types, mock_genai, mock_get_settings, mock_sleep
    ):
        """Test successful text generation."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.use_vertex_ai = True
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_get_settings.return_value = mock_settings

        # Mock response
        mock_response = Mock()
        mock_response.text = "Generated response"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        mock_part = Mock()
        mock_content = Mock()
        mock_config = Mock()
        mock_types.Part.from_text.return_value = mock_part
        mock_types.Content.return_value = mock_content
        mock_types.GenerateContentConfig.return_value = mock_config

        client = GeminiClient()
        result = client.generate_text("Test prompt")

        assert result == "Generated response"
        mock_client.models.generate_content.assert_called_once()
        mock_sleep.assert_not_called()  # No retries needed

    @patch("src.infrastructure.external.gemini_client.GENAI_AVAILABLE", True)
    @patch("src.infrastructure.external.gemini_client.time.sleep")
    @patch("src.infrastructure.external.gemini_client.json.loads")
    @patch("src.infrastructure.external.gemini_client.get_settings")
    @patch("src.infrastructure.external.gemini_client.genai")
    @patch("src.infrastructure.external.gemini_client.types")
    def test_generate_json_response(
        self, mock_types, mock_genai, mock_get_settings, mock_json_loads, mock_sleep
    ):
        """Test JSON response generation."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.use_vertex_ai = True
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_get_settings.return_value = mock_settings

        # Mock response with JSON
        test_json = {"key": "value", "number": 42}
        json_str = json.dumps(test_json)
        mock_response = Mock()
        mock_response.text = json_str

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        mock_part = Mock()
        mock_content = Mock()
        mock_config = Mock()
        mock_types.Part.from_text.return_value = mock_part
        mock_types.Content.return_value = mock_content
        mock_types.GenerateContentConfig.return_value = mock_config

        # Mock json.loads
        mock_json_loads.return_value = test_json

        client = GeminiClient()
        result = client.generate_json_response("Test prompt")

        assert result == test_json
        mock_sleep.assert_not_called()  # No retries needed
        mock_json_loads.assert_called_once()
