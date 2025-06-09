"""Tests for the image processing module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.image_processor import (
    ImageDescription,
    PageInfo,
)


class TestImageDescription:
    """Tests for ImageDescription dataclass."""

    def test_image_description_creation(self):
        """Test creating an ImageDescription."""
        desc = ImageDescription(
            path="images/test.png",
            description="A test image",
            visual_elements=["red", "circle"],
            context="Test context",
            question_relevance="Test relevance",
        )

        assert desc.path == "images/test.png"
        assert desc.description == "A test image"
        assert desc.visual_elements == ["red", "circle"]
        assert desc.context == "Test context"
        assert desc.question_relevance == "Test relevance"


class TestPageInfo:
    """Tests for PageInfo dataclass."""

    def test_page_info_creation(self):
        """Test creating a PageInfo."""
        page_info = PageInfo(
            page_number=1,
            has_images=True,
            image_paths=["image1.png", "image2.png"],
            question_pattern="Aufgabe 1",
            question_ids=[1, 2],
        )

        assert page_info.page_number == 1
        assert page_info.has_images is True
        assert len(page_info.question_ids) == 2
        assert page_info.image_paths == ["image1.png", "image2.png"]


class TestImageProcessor:
    """Tests for ImageProcessor class."""

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_initialization(self, mock_settings, mock_client):
        """Test ImageProcessor initialization."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Verify components are initialized
        mock_client.assert_called_once()
        assert processor.project_id == "test-project"

    @patch("src.core.image_processor.GENAI_AVAILABLE", False)
    def test_initialization_no_genai(self):
        """Test initialization when GenAI is not available."""
        from src.core.image_processor import ImageProcessor

        with pytest.raises(ImportError, match="google-genai package is required"):
            ImageProcessor()

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    @patch("builtins.open")
    @patch("json.load")
    def test_analyze_pdf_structure(
        self, mock_json_load, mock_open, mock_settings, mock_client
    ):
        """Test analyzing PDF structure from checkpoint."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        # Mock checkpoint data
        mock_checkpoint_data = {
            "state": "completed",
            "questions": [
                {
                    "id": 1,
                    "question": "Test question 1",
                    "page_number": 1,
                    "option_a": "Bild 1",
                    "option_b": "Bild 2",
                    "option_c": "Bild 3",
                },
                {
                    "id": 2,
                    "question": "Regular question",
                    "page_number": 2,
                    "option_a": "Option A",
                    "option_b": "Option B",
                },
            ],
        }
        mock_json_load.return_value = mock_checkpoint_data

        # Mock images directory
        with patch("src.core.image_processor.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("data/images/page_1_img_1.png"),
                Path("data/images/page_1_img_2.png"),
            ]

            processor = ImageProcessor()
            result = processor.analyze_pdf_structure(Path("test_checkpoint.json"))

            # Verify structure
            assert len(result) == 2  # Two pages
            assert 1 in result
            assert 2 in result

            # Check page 1 (has images)
            page_1 = result[1]
            assert page_1.page_number == 1
            assert page_1.has_images is True
            assert len(page_1.image_paths) == 2

            # Check page 2 (no images)
            page_2 = result[2]
            assert page_2.page_number == 2
            assert page_2.has_images is False

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_analyze_pdf_structure_file_not_found(self, mock_settings, mock_client):
        """Test analyze_pdf_structure with missing file."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        with pytest.raises(FileNotFoundError):
            processor.analyze_pdf_structure(Path("nonexistent.json"))

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_is_image_question(self, mock_settings, mock_client):
        """Test detection of image questions."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Test image question with "Bild" options
        image_question = {
            "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
            "option_a": "Bild 1",
            "option_b": "Bild 2",
            "option_c": "Bild 3",
            "option_d": "Bild 4",
        }
        assert processor._is_image_question(image_question) is True

        # Test regular question
        regular_question = {
            "question": "What is the capital of Germany?",
            "option_a": "Berlin",
            "option_b": "Munich",
            "option_c": "Hamburg",
            "option_d": "Frankfurt",
        }
        assert processor._is_image_question(regular_question) is False

        # Test question with image keywords
        keyword_question = {
            "question": "Which flag shows the German colors?",
            "option_a": "Option A",
            "option_b": "Option B",
        }
        assert processor._is_image_question(keyword_question) is True

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    @patch("builtins.open")
    def test_describe_images_with_ai(self, mock_open, mock_settings, mock_client):
        """Test describing images with AI."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        # Mock client response
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(
            text='{"description": "Test description", "visual_elements": ["red", "circle"], "context": "Test context", "question_relevance": "Test relevance"}'
        )

        processor = ImageProcessor()

        # Mock file operations
        with patch("pathlib.Path.exists", return_value=True):
            mock_open.return_value.__enter__.return_value.read.return_value = (
                b"fake_image_data"
            )

            image_paths = [Path("test1.png"), Path("test2.png")]
            result = processor.describe_images_with_ai(image_paths)

            assert len(result) == 2
            assert "test1.png" in result
            assert "test2.png" in result

            # Check description content
            desc = result["test1.png"]
            assert desc.description == "Test description"
            assert desc.visual_elements == ["red", "circle"]

    @patch("src.core.image_processor.logger")
    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_error_handling(self, mock_settings, mock_client, mock_logger):
        """Test error handling in image processing."""
        from src.core.image_processor import ImageProcessor

        # Mock settings
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gemini_model="gemini-2.5-pro",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Test with non-existent image
        with patch("pathlib.Path.exists", return_value=False):
            result = processor.describe_images_with_ai([Path("nonexistent.png")])

            # Should handle missing files gracefully
            assert result == {}
            mock_logger.warning.assert_called()


class TestImageProcessorIntegration:
    """Integration tests for ImageProcessor."""

    @pytest.mark.slow
    def test_placeholder_for_integration_tests(self):
        """Placeholder for future integration tests.

        Future tests might include:
        - End-to-end processing with real checkpoint data
        - Performance testing with large image sets
        - Integration with actual AI image description
        """
        assert True, "Structure ready for integration tests"
