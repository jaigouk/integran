"""Integration tests for the complete dataset building pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.answer_engine import AnswerEngine
from src.core.data_builder import BuildStatus, DataBuilder
from src.core.image_processor import ImageProcessor


class TestDatasetBuildingIntegration:
    """Integration tests for the dataset building pipeline."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    def create_mock_extraction_checkpoint(self) -> Path:
        """Create a mock extraction checkpoint for testing."""
        checkpoint_data = {
            "questions": [
                {
                    "id": 1,
                    "question": "Test question 1",
                    "options": {"A": "Option A", "B": "Option B", "C": "Option C"},
                    "correct": "A",
                    "category": "Test Category",
                    "page": 1,
                },
                {
                    "id": 21,  # Image question
                    "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
                    "options": {"A": "Bild 1", "B": "Bild 2", "C": "Bild 3"},
                    "correct": "A",
                    "category": "Symbols",
                    "page": 9,
                },
            ]
        }

        checkpoint_path = self.test_dir / "extraction_checkpoint.json"
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f)

        return checkpoint_path

    @patch("src.core.data_builder.RAGEngine")
    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.image_processor.GeminiClient")
    def test_complete_pipeline_integration(
        self, mock_image_gemini, mock_answer_gemini, mock_rag_engine
    ):
        """Test the complete dataset building pipeline integration."""
        # Create mock extraction checkpoint
        checkpoint_path = self.create_mock_extraction_checkpoint()

        # Mock image processing
        mock_image_client = Mock()
        mock_image_gemini.return_value = mock_image_client
        mock_image_client.describe_image.return_value = {
            "description": "German federal eagle on yellow background",
            "visual_elements": ["eagle", "yellow", "heraldic"],
            "context": "Official coat of arms of Germany",
            "question_relevance": "Represents German state symbols",
        }

        # Mock answer generation
        mock_answer_client = Mock()
        mock_answer_gemini.return_value = mock_answer_client
        mock_answer_client.generate_multilingual_answer.return_value = {
            "en": {
                "explanation": "This is the official German federal eagle...",
                "why_others_wrong": {"B": "Wrong symbol", "C": "Not official"},
                "key_concept": "German state symbols",
                "mnemonic": "Eagle = Germany",
            },
            "de": {
                "explanation": "Das ist der offizielle deutsche Bundesadler...",
                "why_others_wrong": {"B": "Falsches Symbol", "C": "Nicht offiziell"},
                "key_concept": "Deutsche Staatssymbole",
                "mnemonic": "Adler = Deutschland",
            },
        }

        # Mock RAG engine
        mock_rag = Mock()
        mock_rag_engine.return_value = mock_rag
        mock_rag.search_knowledge_base.return_value = []

        # Mock image files
        with (
            patch("src.core.image_processor.Path.glob") as mock_glob,
            patch("builtins.open", create=True),
            patch("json.dump"),
        ):
            # Mock finding image files
            mock_glob.return_value = [Path("data/images/page_9_img_1.png")]

            # Initialize components
            image_processor = ImageProcessor()
            answer_engine = AnswerEngine()

            # Test image processing workflow
            image_result = image_processor.process_images_workflow(checkpoint_path)

            # Verify image processing results
            assert "page_info" in image_result
            assert "image_descriptions" in image_result
            assert "question_image_mapping" in image_result

            # Test answer generation
            test_question = {
                "id": 21,
                "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
                "options": {"A": "Bild 1", "B": "Bild 2", "C": "Bild 3"},
                "correct": "A",
                "category": "Symbols",
            }

            answer_result = answer_engine.generate_answer_with_explanation(
                test_question
            )

            # Verify answer generation results
            assert answer_result.question_id == 21
            assert answer_result.correct_answer == "A"
            assert "en" in answer_result.explanations
            assert "de" in answer_result.explanations

    @patch("src.core.data_builder.RAGEngine")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.ImageProcessor")
    def test_data_builder_workflow_integration(
        self, mock_image_processor, mock_answer_engine, mock_rag_engine
    ):
        """Test DataBuilder workflow integration."""
        # Create mock extraction checkpoint
        checkpoint_path = self.create_mock_extraction_checkpoint()

        # Mock ImageProcessor
        mock_processor = Mock()
        mock_image_processor.return_value = mock_processor
        mock_processor.process_images_workflow.return_value = {
            "page_info": {},
            "image_descriptions": {},
            "question_image_mapping": {21: ["page_9_img_1.png"]},
        }

        # Mock AnswerEngine
        mock_engine = Mock()
        mock_answer_engine.return_value = mock_engine
        mock_engine.generate_answer_with_explanation.return_value = Mock(
            question_id=1,
            correct_answer="A",
            explanations={"en": "Test explanation"},
            why_others_wrong={"en": {"B": "Wrong", "C": "Wrong"}},
            key_concept={"en": "Test concept"},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        # Mock RAGEngine
        mock_rag = Mock()
        mock_rag_engine.return_value = mock_rag

        # Test DataBuilder
        with (
            patch("src.core.data_builder.Path") as mock_path,
            patch("builtins.open", create=True),
            patch("json.load") as mock_json_load,
            patch("json.dump") as mock_json_dump,
        ):
            # Mock file operations
            mock_path.return_value.exists.return_value = True
            mock_json_load.return_value = {
                "questions": [
                    {
                        "id": 1,
                        "question": "Test question",
                        "options": {"A": "Option A", "B": "Option B"},
                        "correct": "A",
                        "category": "Test",
                        "page": 1,
                    }
                ]
            }

            # Initialize DataBuilder
            builder = DataBuilder()

            # Mock checkpoint directory
            builder.checkpoint_path = self.test_dir / "dataset_checkpoint.json"
            builder.output_path = self.test_dir / "questions.json"
            builder.extraction_checkpoint_path = checkpoint_path

            # Test build process
            result = builder.build_complete_dataset()

            # Verify successful build
            assert result is True
            mock_json_dump.assert_called()  # Should save final dataset

    @patch("src.core.data_builder.RAGEngine")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.ImageProcessor")
    def test_error_recovery_integration(
        self, mock_image_processor, mock_answer_engine, mock_rag_engine
    ):
        """Test error recovery and checkpoint functionality."""
        # Create mock extraction checkpoint
        checkpoint_path = self.create_mock_extraction_checkpoint()

        # Mock ImageProcessor to fail initially
        mock_processor = Mock()
        mock_image_processor.return_value = mock_processor
        mock_processor.process_images_workflow.side_effect = [
            Exception("Image processing failed"),
            {  # Second call succeeds
                "page_info": {},
                "image_descriptions": {},
                "question_image_mapping": {},
            },
        ]

        # Mock AnswerEngine
        mock_engine = Mock()
        mock_answer_engine.return_value = mock_engine
        mock_engine.generate_answer_with_explanation.return_value = Mock(
            question_id=1,
            correct_answer="A",
            explanations={"en": "Test explanation"},
            why_others_wrong={"en": {"B": "Wrong"}},
            key_concept={"en": "Test concept"},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        # Mock RAGEngine
        mock_rag = Mock()
        mock_rag_engine.return_value = mock_rag

        with (
            patch("src.core.data_builder.Path") as mock_path,
            patch("builtins.open", create=True),
            patch("json.load"),
            patch("json.dump"),
        ):
            mock_path.return_value.exists.return_value = True

            # Initialize DataBuilder
            builder = DataBuilder()
            builder.checkpoint_path = self.test_dir / "dataset_checkpoint.json"
            builder.extraction_checkpoint_path = checkpoint_path

            # First attempt should fail
            result1 = builder.build_complete_dataset()
            assert result1 is False

            # Check that error checkpoint was saved
            status = builder.get_build_status()
            assert status.status == BuildStatus.FAILED

            # Second attempt should succeed
            result2 = builder.build_complete_dataset()
            assert result2 is True

    def test_checkpoint_persistence_integration(self):
        """Test checkpoint persistence across DataBuilder instances."""
        checkpoint_data = {
            "status": "IN_PROGRESS",
            "total_questions": 460,
            "processed_questions": 150,
            "processed_images": 25,
            "current_step": "generating_answers",
            "error_message": None,
            "started_at": "2025-01-09T12:00:00",
            "updated_at": "2025-01-09T12:30:00",
        }

        checkpoint_path = self.test_dir / "dataset_checkpoint.json"
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f)

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            # Create first DataBuilder instance
            builder1 = DataBuilder()
            builder1.checkpoint_path = checkpoint_path

            # Load status from first instance
            status1 = builder1.get_build_status()
            assert status1.status == BuildStatus.IN_PROGRESS
            assert status1.processed_questions == 150

            # Create second DataBuilder instance
            builder2 = DataBuilder()
            builder2.checkpoint_path = checkpoint_path

            # Load status from second instance
            status2 = builder2.get_build_status()
            assert status2.status == BuildStatus.IN_PROGRESS
            assert status2.processed_questions == 150

            # Status should be identical
            assert status1.status == status2.status
            assert status1.processed_questions == status2.processed_questions

    @pytest.mark.slow
    def test_performance_with_large_dataset(self):
        """Test performance considerations with larger datasets."""
        # Create larger mock dataset
        questions = []
        for i in range(100):  # Simulate 100 questions
            questions.append(
                {
                    "id": i + 1,
                    "question": f"Test question {i + 1}",
                    "options": {"A": "Option A", "B": "Option B", "C": "Option C"},
                    "correct": "A",
                    "category": "Test",
                    "page": (i // 10) + 1,  # Distribute across pages
                }
            )

        checkpoint_data = {"questions": questions}
        checkpoint_path = self.test_dir / "large_checkpoint.json"
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f)

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
            patch("builtins.open", create=True),
            patch("json.dump"),
        ):
            # Test with smaller batch size for performance
            builder = DataBuilder(batch_size=10)
            builder.extraction_checkpoint_path = checkpoint_path

            # Verify batch processing
            questions_loaded = builder._load_extraction_checkpoint()
            assert len(questions_loaded) == 100

            # Test batch creation
            batches = list(builder._create_batches(questions_loaded))
            assert len(batches) == 10  # 100 questions / 10 batch_size
            assert all(len(batch) == 10 for batch in batches)


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.slow
    def test_placeholder_for_e2e_tests(self):
        """Placeholder for future end-to-end tests.

        Future tests might include:
        - Complete pipeline with real PDF extraction
        - Integration with actual AI models (when API keys available)
        - Performance testing with full 460-question dataset
        - Memory usage and optimization testing
        """
        assert True, "Structure ready for E2E tests"
