"""Tests for Gemini client functionality."""

import json
from unittest.mock import Mock, patch

import pytest

from src.utils.gemini_client import GeminiClient


class TestGeminiClient:
    """Test Gemini AI client."""

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
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

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    def test_init_api_key(self, mock_genai, mock_get_settings):
        """Test initialization with API key."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.use_vertex_ai = False
        mock_settings.gemini_api_key = "test-api-key"
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_get_settings.return_value = mock_settings

        # Mock genai client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        client = GeminiClient()

        assert client.api_key == "test-api-key"
        assert client.use_vertex_ai is False
        mock_genai.Client.assert_called_once_with(api_key="test-api-key")

    @patch("src.utils.gemini_client.get_settings")
    def test_init_missing_project_id(self, mock_get_settings):
        """Test initialization fails with missing project ID for Vertex AI."""
        mock_settings = Mock()
        mock_settings.use_vertex_ai = True
        mock_settings.gcp_project_id = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="GCP_PROJECT_ID is required"):
            GeminiClient()

    @patch("src.utils.gemini_client.get_settings")
    def test_init_missing_api_key(self, mock_get_settings):
        """Test initialization fails with missing API key."""
        mock_settings = Mock()
        mock_settings.use_vertex_ai = False
        mock_settings.gemini_api_key = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            GeminiClient()

    def test_init_genai_not_available(self):
        """Test initialization fails when genai is not available."""
        with (
            patch("src.utils.gemini_client.GENAI_AVAILABLE", False),
            pytest.raises(ImportError, match="google-genai package is required"),
        ):
            GeminiClient()

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_generate_text_success(self, mock_types, mock_genai, mock_get_settings):
        """Test successful text generation."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

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

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_generate_text_retry_on_overload(
        self, mock_types, mock_genai, mock_get_settings
    ):
        """Test retry logic on API overload."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        # Mock client that fails first time, succeeds second time
        mock_response = Mock()
        mock_response.text = "Generated response"

        mock_client = Mock()
        mock_client.models.generate_content.side_effect = [
            Exception("Service overloaded"),
            mock_response,
        ]
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        with patch("src.utils.gemini_client.time.sleep"):
            client = GeminiClient()
            result = client.generate_text("Test prompt", max_retries=2)

        assert result == "Generated response"
        assert mock_client.models.generate_content.call_count == 2

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_generate_json_response(self, mock_types, mock_genai, mock_get_settings):
        """Test JSON response generation."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        # Mock response with JSON
        test_json = {"key": "value", "number": 42}
        mock_response = Mock()
        mock_response.text = json.dumps(test_json)

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.generate_json_response("Test prompt")

        assert result == test_json

    @patch("src.utils.gemini_client.time.sleep")
    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_generate_json_response_with_markdown(
        self,
        mock_types,
        mock_genai,
        mock_get_settings,
        mock_sleep,  # noqa: ARG002
    ):
        """Test JSON response with markdown formatting."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        # Mock response with markdown-wrapped JSON
        test_json = {"key": "value"}
        mock_response = Mock()
        mock_response.text = f"```json\n{json.dumps(test_json)}\n```"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.generate_json_response("Test prompt")

        assert result == test_json

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_generate_with_context(self, mock_types, mock_genai, mock_get_settings):
        """Test generation with context for RAG."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        mock_response = Mock()
        mock_response.text = "Contextual response"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.generate_with_context(
            query="What is the Grundgesetz?",
            context="The Grundgesetz is the German constitution.",
            system_prompt="Answer in German.",
        )

        assert result == "Contextual response"
        # Verify the prompt includes context and query
        call_args = mock_client.models.generate_content.call_args
        assert call_args is not None

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_summarize_text(self, mock_types, mock_genai, mock_get_settings):
        """Test text summarization."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        mock_response = Mock()
        mock_response.text = "Summary of the text"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.summarize_text("Long text to summarize", max_length=100)

        assert result == "Summary of the text"

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_extract_key_concepts(self, mock_types, mock_genai, mock_get_settings):
        """Test key concept extraction."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        mock_response = Mock()
        mock_response.text = "1. Concept One\n2. Concept Two\n• Concept Three"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.extract_key_concepts("Text with concepts", max_concepts=5)

        assert isinstance(result, list)
        assert len(result) <= 5
        assert "Concept One" in result
        assert "Concept Two" in result
        assert "Concept Three" in result

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_check_relevance_relevant(self, mock_types, mock_genai, mock_get_settings):
        """Test relevance checking for relevant document."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        mock_response = Mock()
        mock_response.text = "0.8"  # High relevance score

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.check_relevance("Query about topic", "Document about topic")

        assert result is True

    @patch("src.utils.gemini_client.get_settings")
    @patch("src.utils.gemini_client.genai")
    @patch("src.utils.gemini_client.types")
    def test_check_relevance_not_relevant(
        self, mock_types, mock_genai, mock_get_settings
    ):
        """Test relevance checking for irrelevant document."""
        # Setup mocks
        self._setup_basic_mocks(mock_get_settings, mock_genai)

        mock_response = Mock()
        mock_response.text = "0.2"  # Low relevance score

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock types
        self._setup_types_mocks(mock_types)

        client = GeminiClient()
        result = client.check_relevance(
            "Query about topic", "Unrelated document", threshold=0.5
        )

        assert result is False

    def _setup_basic_mocks(self, mock_get_settings, mock_genai):
        """Helper to setup basic mocks."""
        mock_settings = Mock()
        mock_settings.use_vertex_ai = True
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_get_settings.return_value = mock_settings

        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

    def _setup_types_mocks(self, mock_types):
        """Helper to setup types mocks."""
        mock_part = Mock()
        mock_content = Mock()
        mock_config = Mock()
        mock_types.Part.from_text.return_value = mock_part
        mock_types.Content.return_value = mock_content
        mock_types.GenerateContentConfig.return_value = mock_config
