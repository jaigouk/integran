"""Tests for the data building pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.data_builder import (
    BuildCheckpoint,
    BuildStatus,
    DataBuilder,
)


class TestBuildStatus:
    """Tests for BuildStatus enum."""

    def test_build_status_values(self):
        """Test BuildStatus enum values."""
        assert BuildStatus.NOT_STARTED.value == "NOT_STARTED"
        assert BuildStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert BuildStatus.COMPLETED.value == "COMPLETED"
        assert BuildStatus.FAILED.value == "FAILED"


class TestBuildCheckpoint:
    """Tests for BuildCheckpoint dataclass."""

    def test_build_checkpoint_creation(self):
        """Test creating a BuildCheckpoint."""
        checkpoint = BuildCheckpoint(
            status=BuildStatus.IN_PROGRESS,
            total_questions=460,
            processed_questions=100,
            processed_images=20,
            current_step="processing_questions",
            error_message=None,
        )

        assert checkpoint.status == BuildStatus.IN_PROGRESS
        assert checkpoint.total_questions == 460
        assert checkpoint.processed_questions == 100
        assert checkpoint.processed_images == 20
        assert checkpoint.current_step == "processing_questions"
        assert checkpoint.error_message is None

    def test_build_checkpoint_with_error(self):
        """Test creating a BuildCheckpoint with error."""
        checkpoint = BuildCheckpoint(
            status=BuildStatus.FAILED,
            total_questions=460,
            processed_questions=50,
            processed_images=0,
            current_step="image_processing",
            error_message="Image processing failed",
        )

        assert checkpoint.status == BuildStatus.FAILED
        assert checkpoint.error_message == "Image processing failed"


class TestDataBuilder:
    """Tests for DataBuilder class."""

    def setup_method(self):
        """Setup for each test method."""
        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            self.builder = DataBuilder()

    @patch("src.core.data_builder.ImageProcessor")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.RAGEngine")
    def test_initialization(
        self, mock_rag_engine, mock_answer_engine, mock_image_processor
    ):
        """Test DataBuilder initialization."""
        builder = DataBuilder()

        # Verify components are initialized
        mock_image_processor.assert_called_once()
        mock_answer_engine.assert_called_once()
        mock_rag_engine.assert_called_once()

    @patch("builtins.open")
    @patch("src.core.data_builder.Path.exists")
    @patch("json.load")
    def test_load_extraction_checkpoint(self, mock_json_load, mock_exists, mock_open):
        """Test loading extraction checkpoint."""
        mock_exists.return_value = True
        mock_checkpoint_data = {
            "questions": [
                {"id": 1, "question": "Test question 1", "page": 1},
                {"id": 2, "question": "Test question 2", "page": 2},
            ]
        }
        mock_json_load.return_value = mock_checkpoint_data

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        result = builder._load_extraction_checkpoint()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    @patch("src.core.data_builder.Path.exists")
    def test_load_extraction_checkpoint_missing_file(self, mock_exists):
        """Test loading extraction checkpoint when file is missing."""
        mock_exists.return_value = False

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with pytest.raises(FileNotFoundError):
            builder._load_extraction_checkpoint()

    @patch("builtins.open")
    @patch("src.core.data_builder.Path.exists")
    @patch("json.load")
    @patch("json.dump")
    def test_save_checkpoint(
        self, mock_json_dump, mock_json_load, mock_exists, mock_open
    ):
        """Test saving build checkpoint."""
        mock_exists.return_value = False  # No existing checkpoint

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        checkpoint = BuildCheckpoint(
            status=BuildStatus.IN_PROGRESS,
            total_questions=460,
            processed_questions=100,
            processed_images=20,
            current_step="processing_questions",
        )

        builder._save_checkpoint(checkpoint)

        # Verify JSON was written
        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        saved_data = args[0]

        assert saved_data["status"] == "IN_PROGRESS"
        assert saved_data["total_questions"] == 460
        assert saved_data["processed_questions"] == 100

    @patch("builtins.open")
    @patch("src.core.data_builder.Path.exists")
    @patch("json.load")
    def test_load_checkpoint(self, mock_json_load, mock_exists, mock_open):
        """Test loading build checkpoint."""
        mock_exists.return_value = True
        mock_checkpoint_data = {
            "status": "IN_PROGRESS",
            "total_questions": 460,
            "processed_questions": 100,
            "processed_images": 20,
            "current_step": "processing_questions",
            "error_message": None,
            "started_at": "2025-01-09T12:00:00",
            "updated_at": "2025-01-09T12:30:00",
        }
        mock_json_load.return_value = mock_checkpoint_data

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        checkpoint = builder._load_checkpoint()

        assert checkpoint.status == BuildStatus.IN_PROGRESS
        assert checkpoint.total_questions == 460
        assert checkpoint.processed_questions == 100

    def test_get_build_status_no_checkpoint(self):
        """Test getting build status when no checkpoint exists."""
        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with patch.object(builder, "_load_checkpoint", return_value=None):
            status = builder.get_build_status()

        assert status.status == BuildStatus.NOT_STARTED
        assert status.total_questions == 0
        assert status.processed_questions == 0

    def test_get_build_status_with_checkpoint(self):
        """Test getting build status when checkpoint exists."""
        checkpoint = BuildCheckpoint(
            status=BuildStatus.IN_PROGRESS,
            total_questions=460,
            processed_questions=100,
            processed_images=20,
            current_step="processing_questions",
        )

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with patch.object(builder, "_load_checkpoint", return_value=checkpoint):
            status = builder.get_build_status()

        assert status.status == BuildStatus.IN_PROGRESS
        assert status.total_questions == 460
        assert status.processed_questions == 100

    @patch("src.core.data_builder.DataBuilder._load_extraction_checkpoint")
    @patch("src.core.data_builder.DataBuilder._process_images")
    @patch("src.core.data_builder.DataBuilder._generate_multilingual_answers")
    @patch("src.core.data_builder.DataBuilder._save_final_dataset")
    def test_build_complete_dataset_success(
        self,
        mock_save_dataset,
        mock_generate_answers,
        mock_process_images,
        mock_load_checkpoint,
    ):
        """Test successful complete dataset building."""
        # Mock the workflow steps
        mock_questions = [{"id": 1, "question": "Test question", "page": 1}]
        mock_load_checkpoint.return_value = mock_questions

        mock_image_data = {"image_descriptions": {}, "question_image_mapping": {}}
        mock_process_images.return_value = mock_image_data

        mock_enhanced_questions = [
            {
                "id": 1,
                "question": "Test question",
                "answers": {"en": {"explanation": "Test explanation"}},
            }
        ]
        mock_generate_answers.return_value = mock_enhanced_questions

        mock_save_dataset.return_value = True

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        # Mock checkpoint operations
        with patch.object(builder, "_save_checkpoint") as mock_save_checkpoint:
            result = builder.build_complete_dataset()

        assert result is True
        mock_load_checkpoint.assert_called_once()
        mock_process_images.assert_called_once()
        mock_generate_answers.assert_called_once()
        mock_save_dataset.assert_called_once()

        # Verify checkpoints were saved
        assert mock_save_checkpoint.call_count >= 2  # At least start and completion

    @patch("src.core.data_builder.DataBuilder._load_extraction_checkpoint")
    def test_build_complete_dataset_failure(self, mock_load_checkpoint):
        """Test dataset building with failure."""
        # Mock failure in loading checkpoint
        mock_load_checkpoint.side_effect = Exception("Load failed")

        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with patch.object(builder, "_save_checkpoint") as mock_save_checkpoint:
            result = builder.build_complete_dataset()

        assert result is False

        # Should save error checkpoint
        mock_save_checkpoint.assert_called()
        args, kwargs = mock_save_checkpoint.call_args
        error_checkpoint = args[0]
        assert error_checkpoint.status == BuildStatus.FAILED
        assert "Load failed" in error_checkpoint.error_message

    def test_force_rebuild_clears_checkpoint(self):
        """Test that force rebuild clears existing checkpoint."""
        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with (
            patch.object(builder, "_clear_checkpoint") as mock_clear,
            patch.object(builder, "_load_extraction_checkpoint", return_value=[]),
            patch.object(builder, "_process_images", return_value={}),
            patch.object(builder, "_generate_multilingual_answers", return_value=[]),
            patch.object(builder, "_save_final_dataset", return_value=True),
            patch.object(builder, "_save_checkpoint"),
        ):
            builder.build_complete_dataset(force_rebuild=True)

        mock_clear.assert_called_once()

    @patch("src.core.data_builder.logger")
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder()

        with patch.object(
            builder, "_load_extraction_checkpoint", side_effect=Exception("Test error")
        ):
            builder.build_complete_dataset()

        # Should log the error
        mock_logger.error.assert_called()

    def test_batch_processing(self):
        """Test batch processing configuration."""
        with (
            patch("src.core.data_builder.ImageProcessor"),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.RAGEngine"),
        ):
            builder = DataBuilder(batch_size=5)

        assert builder.batch_size == 5

        # Test with different batch sizes
        questions = list(range(12))  # 12 questions
        batches = list(builder._create_batches(questions))

        assert len(batches) == 3  # 12/5 = 2.4, so 3 batches
        assert len(batches[0]) == 5
        assert len(batches[1]) == 5
        assert len(batches[2]) == 2


class TestDataBuilderIntegration:
    """Integration tests for DataBuilder."""

    @pytest.mark.slow
    def test_placeholder_for_integration_tests(self):
        """Placeholder for future integration tests.

        Future tests might include:
        - End-to-end dataset building with real data
        - Performance testing with large datasets
        - Checkpoint recovery after interruption
        """
        assert True, "Structure ready for integration tests"
