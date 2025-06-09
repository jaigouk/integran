"""Comprehensive tests for image-to-question mapping validation.

This module focuses specifically on testing the critical image mapping logic
that was the root cause of the original data quality issues.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.image_processor import ImageProcessor, PageInfo


class TestImageQuestionMapping:
    """Tests for the core image-to-question mapping logic."""

    def create_mock_extraction_checkpoint(self, questions: list[dict]) -> Path:
        """Create a mock extraction checkpoint with specific questions."""
        checkpoint_data = {"state": "completed", "questions": questions}

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(checkpoint_data, temp_file)
        temp_file.close()

        return Path(temp_file.name)

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_image_question_detection_patterns(self, mock_settings, mock_client):
        """Test that image questions are correctly identified by various patterns."""
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Test cases for image question detection
        test_cases = [
            # Positive cases - should be identified as image questions
            {
                "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
                "expected": True,
                "reason": "Four 'Bild X' options",
            },
            {
                "question": "Welche Flagge zeigt die deutschen Farben?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": True,
                "reason": "Contains 'Flagge' keyword",
            },
            {
                "question": "Was zeigt dieses Symbol?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": True,
                "reason": "Contains 'Symbol' keyword",
            },
            {
                "question": "Welches Wappen gehört zu Berlin?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": True,
                "reason": "Contains 'Wappen' keyword",
            },
            {
                "question": "Was zeigt die Abbildung?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": True,
                "reason": "Contains 'Abbildung' keyword",
            },
            # Negative cases - should NOT be identified as image questions
            {
                "question": "Wann wurde die BRD gegründet?",
                "option_a": "1945",
                "option_b": "1949",
                "option_c": "1950",
                "option_d": "1951",
                "expected": False,
                "reason": "No image indicators",
            },
            {
                "question": "Wie viele Bundesländer hat Deutschland?",
                "option_a": "14",
                "option_b": "15",
                "option_c": "16",
                "option_d": "17",
                "expected": False,
                "reason": "No image indicators",
            },
            # Edge cases
            {
                "question": "Welches Bild ist richtig?",  # Contains 'Bild' but only once
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": True,
                "reason": "Contains 'Bild' keyword in question",
            },
            {
                "question": "Regular question",
                "option_a": "Bild 1",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "expected": False,
                "reason": "Only one 'Bild' option, needs >= 2",
            },
        ]

        for i, case in enumerate(test_cases):
            result = processor._is_image_question(case)
            assert result == case["expected"], (
                f"Test case {i + 1} failed: {case['reason']}. "
                f"Expected {case['expected']}, got {result}. "
                f"Question: '{case['question']}'"
            )

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_page_to_question_mapping_accuracy(self, mock_settings, mock_client):
        """Test that questions are correctly mapped to their source pages."""
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        # Create test questions from known image pages (based on real exam structure)
        test_questions = [
            {
                "id": 21,
                "question": "Welches ist das Wappen der BRD?",
                "page_number": 9,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },
            {
                "id": 22,
                "question": "Welche Flagge zeigt deutsche Farben?",
                "page_number": 9,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },
            {
                "id": 89,
                "question": "Welches Wappen gehört zu Bayern?",
                "page_number": 78,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },
            {
                "id": 150,
                "question": "Regular text question",
                "page_number": 120,
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
            },
        ]

        checkpoint_path = self.create_mock_extraction_checkpoint(test_questions)

        with patch("src.core.image_processor.Path.glob") as mock_glob:
            # Mock finding images for pages 9 and 78, but not 120
            def mock_glob_func(pattern):
                if "page_9_img_" in pattern:
                    return [
                        Path("data/images/page_9_img_1.png"),
                        Path("data/images/page_9_img_2.png"),
                    ]
                elif "page_78_img_" in pattern:
                    return [Path("data/images/page_78_img_1.png")]
                else:
                    return []

            mock_glob.side_effect = mock_glob_func

            processor = ImageProcessor()
            page_info = processor.analyze_pdf_structure(checkpoint_path)

            # Verify page mapping accuracy
            assert len(page_info) == 3, "Should have 3 pages mapped"

            # Page 9 should have 2 questions, both image questions
            assert 9 in page_info
            page_9 = page_info[9]
            assert page_9.has_images is True
            assert len(page_9.question_ids) == 2
            assert 21 in page_9.question_ids
            assert 22 in page_9.question_ids
            assert len(page_9.image_paths) == 2

            # Page 78 should have 1 question, image question
            assert 78 in page_info
            page_78 = page_info[78]
            assert page_78.has_images is True
            assert len(page_78.question_ids) == 1
            assert 89 in page_78.question_ids
            assert len(page_78.image_paths) == 1

            # Page 120 should have 1 question, not an image question
            assert 120 in page_info
            page_120 = page_info[120]
            assert page_120.has_images is False
            assert len(page_120.question_ids) == 1
            assert 150 in page_120.question_ids
            assert len(page_120.image_paths) == 0

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_question_image_mapping_creation(self, mock_settings, mock_client):
        """Test the final question-to-image mapping creation."""
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Create realistic page info based on actual exam structure
        page_info = {
            9: PageInfo(
                page_number=9,
                has_images=True,
                image_paths=[
                    "data/images/page_9_img_1.png",
                    "data/images/page_9_img_2.png",
                ],
                question_pattern="Aufgabe 21-22",
                question_ids=[21, 22],
            ),
            78: PageInfo(
                page_number=78,
                has_images=True,
                image_paths=["data/images/page_78_img_1.png"],
                question_pattern="Aufgabe 89",
                question_ids=[89],
            ),
            120: PageInfo(  # Non-image page
                page_number=120,
                has_images=False,
                image_paths=[],
                question_pattern="Aufgabe 150",
                question_ids=[150],
            ),
        }

        # Create mock image descriptions (content doesn't matter for mapping test)
        image_descriptions = {}

        mapping = processor.create_question_image_mapping(page_info, image_descriptions)

        # Verify mapping accuracy
        assert len(mapping) == 2, (
            "Should map exactly 2 questions (only image questions)"
        )

        # Question 21 should map to both images on page 9
        assert 21 in mapping
        assert len(mapping[21]) == 2
        assert "data/images/page_9_img_1.png" in mapping[21]
        assert "data/images/page_9_img_2.png" in mapping[21]

        # Question 22 should also map to both images on page 9 (same page)
        assert 22 in mapping
        assert len(mapping[22]) == 2
        assert mapping[22] == mapping[21], (
            "Questions on same page should have same images"
        )

        # Question 89 should map to single image on page 78
        assert 89 in mapping
        assert len(mapping[89]) == 1
        assert "data/images/page_78_img_1.png" in mapping[89]

        # Question 150 should NOT be in mapping (not an image question)
        assert 150 not in mapping

    @patch("src.core.image_processor.GENAI_AVAILABLE", True)
    @patch("src.core.image_processor.genai.Client")
    @patch("src.core.image_processor.get_settings")
    def test_edge_cases_and_error_handling(self, mock_settings, mock_client):
        """Test edge cases and error handling in mapping logic."""
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        processor = ImageProcessor()

        # Test 1: Question without page_number
        test_questions = [
            {
                "id": 1,
                "question": "Test",
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },  # Missing page_number
        ]

        checkpoint_path = self.create_mock_extraction_checkpoint(test_questions)

        with patch("src.core.image_processor.Path.glob", return_value=[]):
            page_info = processor.analyze_pdf_structure(checkpoint_path)
            assert len(page_info) == 0, (
                "Questions without page_number should be skipped"
            )

        # Test 2: Question without ID
        test_questions = [
            {
                "question": "Test",
                "page_number": 9,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },  # Missing id
        ]

        checkpoint_path = self.create_mock_extraction_checkpoint(test_questions)

        with patch("src.core.image_processor.Path.glob", return_value=[]):
            page_info = processor.analyze_pdf_structure(checkpoint_path)
            assert len(page_info) == 0, "Questions without id should be skipped"

        # Test 3: Image question but no images found on disk
        test_questions = [
            {
                "id": 21,
                "question": "Test",
                "page_number": 9,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
            },
        ]

        checkpoint_path = self.create_mock_extraction_checkpoint(test_questions)

        with patch(
            "src.core.image_processor.Path.glob", return_value=[]
        ):  # No images found
            page_info = processor.analyze_pdf_structure(checkpoint_path)
            assert len(page_info) == 1
            assert page_info[9].has_images is True  # Still marked as image question
            assert len(page_info[9].image_paths) == 0  # But no images found

    def test_known_image_question_validation(self):
        """Test validation against known problematic image questions from the original issue."""
        # These are actual question IDs that were known to have image mapping issues
        # Based on the original problem: 25 out of 42 image questions missing image paths

        known_image_questions = [
            # These should all be detected as image questions
            {
                "id": 21,
                "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
            },
            {"id": 22, "question": "Welche Flagge zeigt schwarz-rot-gold?"},
            {"id": 209, "question": "Welches Wappen gehört zum Freistaat Sachsen?"},
            {"id": 226, "question": "Welches ist das Wappen von Brandenburg?"},
            {"id": 275, "question": "Welches ist das Wappen des Freistaates Bayern?"},
            {"id": 294, "question": "Welches ist das Wappen von Nordrhein-Westfalen?"},
            {"id": 319, "question": "Welches ist das Wappen von Berlin?"},
            {"id": 344, "question": "Welches ist das Wappen von Sachsen-Anhalt?"},
            {"id": 369, "question": "Welches ist das Wappen des Landes Hessen?"},
            {"id": 394, "question": "Welches ist das Wappen von Rheinland-Pfalz?"},
        ]

        with (
            patch("src.core.image_processor.GENAI_AVAILABLE", True),
            patch("src.core.image_processor.genai.Client"),
            patch("src.core.image_processor.get_settings") as mock_settings,
        ):
            mock_settings.return_value = Mock(
                use_vertex_ai=True,
                gcp_project_id="test",
                gcp_region="us-central1",
                gemini_model="test",
                gemini_api_key=None,
            )

            processor = ImageProcessor()

            for question_data in known_image_questions:
                # Add typical Bild options to simulate real structure
                question_data.update(
                    {
                        "option_a": "Bild 1",
                        "option_b": "Bild 2",
                        "option_c": "Bild 3",
                        "option_d": "Bild 4",
                    }
                )

                is_image_q = processor._is_image_question(question_data)
                assert is_image_q, (
                    f"Question {question_data['id']} should be detected as image question: {question_data['question']}"
                )

    def test_mapping_consistency_validation(self):
        """Test that mapping is consistent and deterministic."""
        with (
            patch("src.core.image_processor.GENAI_AVAILABLE", True),
            patch("src.core.image_processor.genai.Client"),
            patch("src.core.image_processor.get_settings") as mock_settings,
        ):
            mock_settings.return_value = Mock(
                use_vertex_ai=True,
                gcp_project_id="test",
                gcp_region="us-central1",
                gemini_model="test",
                gemini_api_key=None,
            )

            processor = ImageProcessor()

            # Create consistent test data
            page_info = {
                9: PageInfo(
                    page_number=9,
                    has_images=True,
                    image_paths=[
                        "data/images/page_9_img_1.png",
                        "data/images/page_9_img_2.png",
                    ],
                    question_pattern="Aufgabe 21-22",
                    question_ids=[21, 22],
                )
            }

            # Run mapping multiple times to ensure consistency
            mapping1 = processor.create_question_image_mapping(page_info, {})
            mapping2 = processor.create_question_image_mapping(page_info, {})
            mapping3 = processor.create_question_image_mapping(page_info, {})

            assert mapping1 == mapping2 == mapping3, (
                "Mapping should be deterministic and consistent"
            )

            # Verify specific expectations
            assert len(mapping1) == 2  # Two questions
            assert set(mapping1.keys()) == {21, 22}  # Correct question IDs
            assert mapping1[21] == mapping1[22]  # Same page = same images
            assert len(mapping1[21]) == 2  # Both images mapped


class TestImageMappingIntegration:
    """Integration tests for the complete image mapping pipeline."""

    @pytest.mark.slow
    def test_placeholder_for_full_pipeline_tests(self):
        """Placeholder for future full pipeline integration tests.

        These would test:
        - Complete workflow from extraction_checkpoint.json to final questions.json
        - Validation that all known image questions get proper image mappings
        - Cross-validation with actual extracted images in data/images/
        - Performance testing with realistic dataset sizes
        """
        assert True, "Structure ready for full pipeline tests"
