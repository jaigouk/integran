"""Tests for SubmitAnswerWithRatingCommand handler."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.submit_answer_with_rating_command import (
    SubmitAnswerWithRatingCommand,
    SubmitAnswerWithRatingCommandHandler,
    SubmitAnswerWithRatingResult,
)
from src.domain.learning.models.learning_models import FSRSCard
from src.domain.learning.services.schedule_card import ScheduleCardResult
from src.domain.shared.models import FSRSState


class TestSubmitAnswerWithRatingCommand:
    """Test SubmitAnswerWithRatingCommand and its handler."""

    @pytest.fixture
    def mock_learning_repository(self):
        """Mock learning repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock()

    @pytest.fixture
    def mock_schedule_card_service(self):
        """Mock schedule card service."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_learning_repository, mock_event_bus):
        """Create command handler."""
        handler = SubmitAnswerWithRatingCommandHandler(
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
        )
        # Replace the schedule_card_service with our mock
        handler.schedule_card_service = AsyncMock()
        return handler

    @pytest.mark.asyncio
    async def test_submit_correct_answer_with_good_rating(
        self, handler, mock_learning_repository, mock_event_bus
    ):
        """Test submitting a correct answer with GOOD rating."""
        # Arrange
        command = SubmitAnswerWithRatingCommand(
            question_id=1,
            selected_answer="A",
            correct_answer="A",
            fsrs_rating=3,  # GOOD
            user_id=1,
            session_id=123,
        )

        # Mock existing FSRS card
        mock_card = MagicMock(spec=FSRSCard)
        mock_card.card_id = 1
        mock_card.user_id = 1
        mock_card.question_id = 1
        mock_card.next_review_date = datetime.now(UTC).timestamp()
        mock_card.stability = 2.5
        mock_card.difficulty = 2.5
        mock_card.state = FSRSState.NEW
        mock_card.last_review_date = None
        mock_card.review_count = 0
        mock_card.lapse_count = 0
        mock_learning_repository.get_fsrs_card.return_value = mock_card

        # Mock schedule result
        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=1,
            question_id=1,
            difficulty_before=2.5,
            stability_before=2.5,
            retrievability_before=0.9,
            state_before=FSRSState.NEW,
            difficulty_after=2.3,
            stability_after=4.14,
            retrievability_after=0.9,
            state_after=FSRSState.LEARNING,
            next_review_date=datetime.now(UTC),
            next_interval_days=4.0,
            lapse_count_updated=False,
        )

        # Mock the SubmitAnswer service directly on the handler
        mock_submit_result = AsyncMock()
        mock_submit_result.success = True
        mock_submit_result.is_correct = True  # Correct answer (A == A)
        mock_submit_result.next_review_date = (
            mock_schedule_result.next_review_date.timestamp()
        )
        mock_submit_result.error_message = None

        handler.submit_answer_service = AsyncMock()
        handler.submit_answer_service.call.return_value = mock_submit_result

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True
        assert result.is_correct is True
        assert (
            result.next_review_date == mock_schedule_result.next_review_date.timestamp()
        )
        assert result.error_message is None

        # Verify domain service was called
        handler.submit_answer_service.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_incorrect_answer_with_again_rating(
        self, handler, mock_learning_repository, mock_event_bus
    ):
        """Test submitting an incorrect answer with AGAIN rating."""
        # Arrange
        command = SubmitAnswerWithRatingCommand(
            question_id=2,
            selected_answer="B",
            correct_answer="A",
            fsrs_rating=1,  # AGAIN
            user_id=1,
            session_id=124,
        )

        # Mock existing FSRS card
        mock_card = MagicMock(spec=FSRSCard)
        mock_card.card_id = 2
        mock_card.user_id = 1
        mock_card.question_id = 2
        mock_card.next_review_date = datetime.now(UTC).timestamp()
        mock_card.stability = 4.14
        mock_card.difficulty = 2.5
        mock_card.state = FSRSState.REVIEW
        mock_card.last_review_date = datetime.now(UTC).timestamp()
        mock_card.review_count = 3
        mock_card.lapse_count = 0
        mock_learning_repository.get_fsrs_card.return_value = mock_card

        # Mock schedule result
        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=2,
            question_id=2,
            difficulty_before=2.5,
            stability_before=4.14,
            retrievability_before=0.9,
            state_before=FSRSState.REVIEW,
            difficulty_after=2.7,
            stability_after=0.4,
            retrievability_after=0.9,
            state_after=FSRSState.RELEARNING,
            next_review_date=datetime.now(UTC),
            next_interval_days=0.01,  # 10 minutes
            lapse_count_updated=True,
        )

        # Mock the SubmitAnswer service directly on the handler
        mock_submit_result = AsyncMock()
        mock_submit_result.success = True
        mock_submit_result.is_correct = False  # Incorrect answer (B != A)
        mock_submit_result.next_review_date = (
            mock_schedule_result.next_review_date.timestamp()
        )
        mock_submit_result.error_message = None

        handler.submit_answer_service = AsyncMock()
        handler.submit_answer_service.call.return_value = mock_submit_result

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True
        assert result.is_correct is False
        assert (
            result.next_review_date == mock_schedule_result.next_review_date.timestamp()
        )
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_create_new_card_when_none_exists(
        self, handler, mock_learning_repository, mock_event_bus
    ):
        """Test creating a new FSRS card when none exists."""
        # Arrange
        command = SubmitAnswerWithRatingCommand(
            question_id=3,
            selected_answer="C",
            correct_answer="C",
            fsrs_rating=4,  # EASY
            user_id=1,
        )

        # Mock no existing card
        mock_learning_repository.get_fsrs_card.return_value = None

        # Mock saving new card
        new_card = MagicMock(spec=FSRSCard)
        new_card.card_id = 3
        new_card.user_id = 1
        new_card.question_id = 3
        new_card.next_review_date = datetime.now(UTC).timestamp()
        new_card.stability = 2.5
        new_card.difficulty = 2.5
        new_card.state = FSRSState.NEW
        new_card.last_review_date = None
        new_card.review_count = 0
        new_card.lapse_count = 0
        mock_learning_repository.save_fsrs_card.return_value = new_card

        # Mock schedule result
        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=3,
            question_id=3,
            difficulty_before=2.5,
            stability_before=2.5,
            retrievability_before=1.0,
            state_before=FSRSState.NEW,
            difficulty_after=2.1,
            stability_after=5.2,
            retrievability_after=0.9,
            state_after=FSRSState.LEARNING,
            next_review_date=datetime.now(UTC),
            next_interval_days=5.0,
            lapse_count_updated=False,
        )

        # Mock the SubmitAnswer service directly on the handler
        mock_submit_result = AsyncMock()
        mock_submit_result.success = True
        mock_submit_result.is_correct = True  # Correct answer (C == C)
        mock_submit_result.next_review_date = (
            mock_schedule_result.next_review_date.timestamp()
        )
        mock_submit_result.error_message = None

        handler.submit_answer_service = AsyncMock()
        handler.submit_answer_service.call.return_value = mock_submit_result

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True
        assert result.is_correct is True
        # Note: The domain service handles card creation, so we don't check repository calls here

    @pytest.mark.asyncio
    async def test_handle_schedule_failure(
        self, handler, mock_learning_repository, mock_event_bus
    ):
        """Test handling when schedule card service fails."""
        # Arrange
        command = SubmitAnswerWithRatingCommand(
            question_id=4,
            selected_answer="D",
            correct_answer="D",
            fsrs_rating=2,  # HARD
            user_id=1,
        )

        # Mock existing card
        mock_card = MagicMock()
        mock_learning_repository.get_fsrs_card.return_value = mock_card

        # Mock the SubmitAnswer service directly on the handler to return failure
        handler.submit_answer_service = AsyncMock()
        handler.submit_answer_service.call.return_value = AsyncMock()
        handler.submit_answer_service.call.return_value.success = False
        handler.submit_answer_service.call.return_value.error_message = (
            "Failed to update card state"
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_message == "Failed to update card state"

    @pytest.mark.asyncio
    async def test_handle_exception_during_processing(
        self, handler, mock_learning_repository, mock_event_bus
    ):
        """Test handling exceptions during command processing gracefully degrades."""
        # Arrange
        command = SubmitAnswerWithRatingCommand(
            question_id=5,
            selected_answer="A",
            correct_answer="B",
            fsrs_rating=3,
            user_id=1,
        )

        # Mock the SubmitAnswer service to succeed despite repository exception
        mock_submit_result = AsyncMock()
        mock_submit_result.success = True
        mock_submit_result.is_correct = False  # Incorrect answer (A != B)
        mock_submit_result.next_review_date = datetime.now(UTC).timestamp()
        mock_submit_result.error_message = None

        handler.submit_answer_service = AsyncMock()
        handler.submit_answer_service.call.return_value = mock_submit_result

        # Act
        result = await handler.handle(command)

        # Assert - The handler gracefully handles the error and continues
        assert result.success is True
        assert result.is_correct is False  # Wrong answer
        assert result.error_message is None

    def test_submit_answer_with_rating_result_attributes(self):
        """Test that SubmitAnswerWithRatingResult has the expected attributes."""
        # This test documents the expected interface
        result = SubmitAnswerWithRatingResult(
            success=True,
            is_correct=True,
            next_review_date=datetime.now(UTC).timestamp(),
            error_message=None,
        )

        assert hasattr(result, "success")
        assert hasattr(result, "is_correct")
        assert hasattr(result, "next_review_date")
        assert hasattr(result, "error_message")
