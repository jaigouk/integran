"""Simplified tests for application workflow coordinators focused on coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.workflows.build_dataset_workflow import DatasetBuildWorkflow
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow


class TestDatasetBuildWorkflowSimple:
    """Test DatasetBuildWorkflow thin coordinator - simplified for coverage."""

    @pytest.fixture
    def mock_build_dataset_service(self):
        """Mock BuildDataset domain service."""
        return AsyncMock()

    @pytest.fixture
    def workflow(self, mock_build_dataset_service):
        """Create DatasetBuildWorkflow instance."""
        return DatasetBuildWorkflow(build_dataset_service=mock_build_dataset_service)

    @pytest.mark.asyncio
    async def test_build_complete_dataset_basic(
        self, workflow, mock_build_dataset_service
    ):
        """Test basic dataset building workflow."""
        # Arrange
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_dataset_path = "/test/path"
        mock_result.statistics = {"test": "stats"}
        mock_result.build_progress = "progress"
        mock_result.error_message = None
        mock_build_dataset_service.call.return_value = mock_result

        # Act
        result = await workflow.build_complete_dataset()

        # Assert
        mock_build_dataset_service.call.assert_called_once()
        assert result["success"] is True
        assert result["dataset_path"] == "/test/path"

    @pytest.mark.asyncio
    async def test_build_complete_dataset_with_params(
        self, workflow, mock_build_dataset_service
    ):
        """Test dataset building with custom parameters."""
        # Arrange
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_dataset_path = "/test/path"
        mock_result.statistics = {}
        mock_result.build_progress = "progress"
        mock_result.error_message = None
        mock_build_dataset_service.call.return_value = mock_result

        # Act
        await workflow.build_complete_dataset(
            force_rebuild=True,
            multilingual=False,
            batch_size=5,
        )

        # Assert
        mock_build_dataset_service.call.assert_called_once()
        call_args = mock_build_dataset_service.call.call_args[0][0]
        assert call_args.force_rebuild is True
        assert call_args.multilingual is False
        assert call_args.batch_size == 5

    @pytest.mark.asyncio
    async def test_get_build_status(self, workflow, mock_build_dataset_service):
        """Test getting build status."""
        # Arrange
        mock_result = MagicMock()
        mock_result.build_progress = "test_progress"
        mock_result.statistics = {"status": "test"}
        mock_build_dataset_service.call.return_value = mock_result

        # Act
        result = await workflow.get_build_status()

        # Assert
        mock_build_dataset_service.call.assert_called_once()
        assert result["progress"] == "test_progress"
        assert result["statistics"]["status"] == "test"


class TestSessionWorkflowSimple:
    """Test SessionWorkflow thin coordinator - simplified for coverage."""

    @pytest.fixture
    def mock_complete_learning_session(self):
        """Mock CompleteLearningSession domain service."""
        return AsyncMock()

    @pytest.fixture
    def workflow(self, mock_complete_learning_session):
        """Create SessionWorkflow instance."""
        return SessionWorkflow(complete_learning_session=mock_complete_learning_session)

    @pytest.mark.asyncio
    async def test_start_session_basic(self, workflow, mock_complete_learning_session):
        """Test basic session start."""
        # Arrange
        from src.domain.learning.services.complete_learning_session import (
            SessionConfig,
            SessionType,
        )

        mock_config = SessionConfig(session_type=SessionType.REVIEW)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.session_id = 123
        mock_result.questions = ["Q1", "Q2"]
        mock_complete_learning_session.call.return_value = mock_result

        # Act
        result = await workflow.start_session(mock_config)

        # Assert
        mock_complete_learning_session.call.assert_called_once()
        call_args = mock_complete_learning_session.call.call_args[0][0]
        assert call_args.config == mock_config
        assert call_args.user_id == 1  # Default value
        assert result["session_id"] == 123
        assert result["questions"] == ["Q1", "Q2"]
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_start_session_with_user_id(
        self, workflow, mock_complete_learning_session
    ):
        """Test session start with custom user ID."""
        # Arrange
        from src.domain.learning.services.complete_learning_session import (
            SessionConfig,
            SessionType,
        )

        mock_config = SessionConfig(session_type=SessionType.LEARN)
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.session_id = 456
        mock_result.questions = []
        mock_complete_learning_session.call.return_value = mock_result

        # Act
        await workflow.start_session(mock_config, user_id=42)

        # Assert
        call_args = mock_complete_learning_session.call.call_args[0][0]
        assert call_args.user_id == 42

    @pytest.mark.asyncio
    async def test_submit_answer_basic(self, workflow, mock_complete_learning_session):
        """Test basic answer submission."""
        # Arrange
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.is_correct = True
        mock_result.schedule_result = "schedule_data"
        mock_result.updated_progress = "progress_data"
        mock_complete_learning_session.call.return_value = mock_result

        # Act
        result = await workflow.submit_answer(
            session_id=123,
            card_id=456,
            user_answer="A",
            response_time_ms=2000,
        )

        # Assert
        mock_complete_learning_session.call.assert_called_once()
        call_args = mock_complete_learning_session.call.call_args[0][0]
        assert call_args.session_id == 123
        assert call_args.card_id == 456
        assert call_args.user_answer == "A"
        assert call_args.response_time_ms == 2000
        assert call_args.rating is None  # Default
        assert result["success"] is True
        assert result["is_correct"] is True
        assert "schedule_result" in result
        assert "progress" in result

    @pytest.mark.asyncio
    async def test_submit_answer_with_rating(
        self, workflow, mock_complete_learning_session
    ):
        """Test answer submission with FSRS rating."""
        # Arrange
        from src.domain.shared.models import FSRSRating

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.is_correct = False
        mock_result.schedule_result = "schedule_data"
        mock_result.updated_progress = "progress_data"
        mock_complete_learning_session.call.return_value = mock_result

        # Act
        await workflow.submit_answer(
            session_id=123,
            card_id=456,
            user_answer="B",
            response_time_ms=3000,
            rating=FSRSRating.HARD,
        )

        # Assert
        call_args = mock_complete_learning_session.call.call_args[0][0]
        assert call_args.rating == FSRSRating.HARD

    @pytest.mark.asyncio
    async def test_complete_session_basic(
        self, workflow, mock_complete_learning_session
    ):
        """Test basic session completion."""
        # Arrange
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.session_summary = {
            "total_questions": 10,
            "correct_answers": 8,
            "session_duration_seconds": 600,
            "average_response_time_ms": 2500.0,
        }
        mock_complete_learning_session.call.return_value = mock_result

        # Act
        result = await workflow.complete_session(session_id=123)

        # Assert
        mock_complete_learning_session.call.assert_called_once()
        call_args = mock_complete_learning_session.call.call_args[0][0]
        assert call_args.session_id == 123
        assert result["success"] is True
        assert result["summary"]["total_questions"] == 10
        assert result["summary"]["correct_answers"] == 8
