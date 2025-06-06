"""Tests for PDF extraction functionality."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.pdf_extractor import (
    GeminiPDFExtractor,
    ensure_questions_available,
    extract_questions_to_csv,
)


class TestGeminiPDFExtractor:
    """Test the Gemini PDF extractor."""

    def test_init_genai_not_available(self):
        """Test initialization fails when google-genai not available."""
        with (
            patch("src.utils.pdf_extractor.GENAI_AVAILABLE", False),
            pytest.raises(ImportError, match="google-genai package is required"),
        ):
            GeminiPDFExtractor()

    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch("src.utils.pdf_extractor.get_settings")
    def test_init_missing_project_id_vertex_ai(self, mock_get_settings):
        """Test initialization fails without project ID for Vertex AI."""
        # Mock settings to return empty project ID with Vertex AI enabled
        mock_settings = MagicMock()
        mock_settings.gemini_api_key = ""
        mock_settings.gcp_project_id = ""
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro-preview-06-05"
        mock_settings.use_vertex_ai = True
        mock_settings.google_application_credentials = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(
            ValueError, match="GCP_PROJECT_ID is required for Vertex AI"
        ):
            GeminiPDFExtractor()

    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch("src.utils.pdf_extractor.get_settings")
    def test_init_missing_api_key_legacy(self, mock_get_settings):
        """Test initialization fails without API key for legacy auth."""
        # Mock settings to return empty API key with legacy auth
        mock_settings = MagicMock()
        mock_settings.gemini_api_key = ""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro-preview-06-05"
        mock_settings.use_vertex_ai = False
        mock_settings.google_application_credentials = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            GeminiPDFExtractor()

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch("src.utils.pdf_extractor.get_settings")
    def test_init_success_vertex_ai(self, mock_get_settings, mock_genai):
        """Test successful initialization with Vertex AI."""
        # Mock settings for Vertex AI
        mock_settings = MagicMock()
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro-preview-06-05"
        mock_settings.use_vertex_ai = True
        mock_settings.google_application_credentials = "/path/to/credentials.json"
        mock_get_settings.return_value = mock_settings

        extractor = GeminiPDFExtractor()
        assert extractor.project_id == "test-project"
        assert extractor.model_id == "gemini-2.5-pro-preview-06-05"
        assert extractor.use_vertex_ai is True
        mock_genai.Client.assert_called_once_with(
            vertexai=True, project="test-project", location="global"
        )

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch("src.utils.pdf_extractor.get_settings")
    def test_init_success_api_key(self, mock_get_settings, mock_genai):
        """Test successful initialization with API key."""
        # Mock settings for API key auth
        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-api-key"
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro-preview-06-05"
        mock_settings.use_vertex_ai = False
        mock_settings.google_application_credentials = ""
        mock_get_settings.return_value = mock_settings

        extractor = GeminiPDFExtractor()
        assert extractor.project_id == "test-project"
        assert extractor.model_id == "gemini-2.5-pro-preview-06-05"
        assert extractor.use_vertex_ai is False
        mock_genai.Client.assert_called_once_with(api_key="test-api-key")

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_extract_questions_pdf_not_found(self, _mock_genai):
        """Test extraction fails when PDF doesn't exist."""
        extractor = GeminiPDFExtractor()

        with pytest.raises(FileNotFoundError):
            extractor.extract_questions_from_pdf("nonexistent.pdf")

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_extract_questions_success(self, mock_genai):
        """Test successful question extraction."""
        # Mock the Gemini client response
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "questions": [
                    {
                        "id": 1,
                        "question": "Test question?",
                        "option_a": "Option A",
                        "option_b": "Option B",
                        "option_c": "Option C",
                        "option_d": "Option D",
                        "correct_answer": "A",
                        "category": "Test",
                        "difficulty": "easy",
                    }
                ]
            }
        )

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        extractor = GeminiPDFExtractor()

        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"dummy pdf content")
            tmp_path = tmp_file.name

        try:
            questions = extractor.extract_questions_from_pdf(tmp_path)

            assert len(questions) == 1
            assert questions[0]["id"] == 1
            assert questions[0]["question"] == "Test question?"
            assert questions[0]["category"] == "Test"

        finally:
            Path(tmp_path).unlink()

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_save_questions_to_csv(self, _mock_genai):
        """Test saving questions to CSV."""
        extractor = GeminiPDFExtractor()

        questions = [
            {
                "id": 1,
                "question": "Test question?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_answer": "A",
                "category": "Test",
                "difficulty": "easy",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test.csv"
            extractor.save_questions_to_csv(questions, csv_path)

            assert csv_path.exists()

            # Verify CSV content
            import csv

            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["id"] == "1"
            assert rows[0]["question"] == "Test question?"
            assert rows[0]["correct"] == "Option A"

    @patch("src.utils.pdf_extractor.genai")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_convert_csv_to_json(self, _mock_genai):
        """Test converting CSV to JSON."""
        extractor = GeminiPDFExtractor()

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test.csv"
            json_path = Path(tmp_dir) / "test.json"

            # Create test CSV
            import csv

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "id",
                        "question",
                        "options",
                        "correct",
                        "category",
                        "difficulty",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "1",
                        "question": "Test question?",
                        "options": '["A", "B", "C", "D"]',
                        "correct": "A",
                        "category": "Test",
                        "difficulty": "easy",
                    }
                )

            count = extractor.convert_csv_to_json(csv_path, json_path)

            assert count == 1
            assert json_path.exists()

            # Verify JSON content
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["id"] == 1
            assert data[0]["question"] == "Test question?"
            assert data[0]["options"] == ["A", "B", "C", "D"]


class TestEnsureQuestionsAvailable:
    """Test the ensure_questions_available function."""

    def test_json_exists(self):
        """Test when JSON file already exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "data" / "questions.json"
            json_path.parent.mkdir(parents=True)
            json_path.write_text("[]")

            with patch("src.utils.pdf_extractor.Path") as mock_path:
                mock_path.return_value = json_path

                result = ensure_questions_available()
                assert result == json_path

    def test_csv_exists_converts_to_json(self):
        """Test when CSV exists and gets converted to JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "docs" / "questions.csv"
            json_path = Path(tmp_dir) / "data" / "questions.json"

            csv_path.parent.mkdir(parents=True)
            json_path.parent.mkdir(parents=True)

            # Create test CSV
            import csv

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "id",
                        "question",
                        "options",
                        "correct",
                        "category",
                        "difficulty",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "1",
                        "question": "Test?",
                        "options": '["A", "B", "C", "D"]',
                        "correct": "A",
                        "category": "Test",
                        "difficulty": "easy",
                    }
                )

            with patch("src.utils.pdf_extractor.Path") as mock_path:

                def path_side_effect(path_str):
                    if "questions.json" in str(path_str):
                        return json_path
                    elif "questions.csv" in str(path_str):
                        return csv_path
                    else:
                        return Path(tmp_dir) / str(path_str)

                mock_path.side_effect = path_side_effect

                with (
                    patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
                    patch("src.utils.pdf_extractor.genai"),
                    patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True),
                ):
                    result = ensure_questions_available()
                    assert json_path.exists()
                    assert result == json_path

    def test_no_files_available(self):
        """Test when no files are available."""
        with patch("src.utils.pdf_extractor.Path") as mock_path:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_path.return_value = mock_file

            with pytest.raises(FileNotFoundError, match="Questions file not found"):
                ensure_questions_available()


class TestExtractQuestionsToCSV:
    """Test the extract_questions_to_csv function."""

    @patch("src.utils.pdf_extractor.has_gemini_config")
    def test_missing_environment_variables(self, mock_has_config):
        """Test extraction skipped when environment variables missing."""
        mock_has_config.return_value = False
        result = extract_questions_to_csv()
        assert result is False

    def test_genai_not_available(self):
        """Test extraction skipped when google-genai not available."""
        with patch("src.utils.pdf_extractor.GENAI_AVAILABLE", False):
            result = extract_questions_to_csv()
            assert result is False

    @patch("src.utils.pdf_extractor.GeminiPDFExtractor")
    @patch("src.utils.pdf_extractor.GENAI_AVAILABLE", True)
    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-key",
            "GCP_PROJECT_ID": "test-project",
            "GCP_REGION": "test-region",
        },
    )
    def test_successful_extraction(self, mock_extractor_class):
        """Test successful question extraction."""
        mock_extractor = Mock()
        mock_extractor.extract_questions_from_pdf.return_value = [{"id": 1}]
        mock_extractor_class.return_value = mock_extractor

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "test.pdf"
            csv_path = Path(tmp_dir) / "test.csv"
            pdf_path.write_bytes(b"dummy pdf")

            result = extract_questions_to_csv(pdf_path, csv_path)

            assert result is True
            mock_extractor.extract_questions_from_pdf.assert_called_once_with(pdf_path)
            mock_extractor.save_questions_to_csv.assert_called_once()
