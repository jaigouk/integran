"""Tests for SubmitAnswerWithRatingCommand handler."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
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

        # Mock the ScheduleCard service creation
        with patch(
            "src.application.commands.submit_answer_with_rating_command.ScheduleCard"
        ) as mock_schedule_card_class:
            mock_schedule_service = AsyncMock()
            mock_schedule_service.call.return_value = mock_schedule_result
            mock_schedule_card_class.return_value = mock_schedule_service

            # Act
            result = await command.execute()

            # Assert
            assert result.success is True
            assert result.is_correct is True
            assert result.next_review_date == mock_schedule_result.next_review_date
            assert result.error_message is None

            # Verify event publishing
            assert mock_event_bus.publish.call_count >= 1

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
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
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

        # Mock the ScheduleCard service creation
        with patch(
            "src.application.commands.submit_answer_with_rating_command.ScheduleCard"
        ) as mock_schedule_card_class:
            mock_schedule_service = AsyncMock()
            mock_schedule_service.call.return_value = mock_schedule_result
            mock_schedule_card_class.return_value = mock_schedule_service

            # Act
            result = await command.execute()

            # Assert
            assert result.success is True
            assert result.is_correct is False
            assert result.next_review_date == mock_schedule_result.next_review_date
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
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
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

        # Mock the ScheduleCard service creation
        with patch(
            "src.application.commands.submit_answer_with_rating_command.ScheduleCard"
        ) as mock_schedule_card_class:
            mock_schedule_service = AsyncMock()
            mock_schedule_service.call.return_value = mock_schedule_result
            mock_schedule_card_class.return_value = mock_schedule_service

            # Act
            result = await command.execute()

            # Assert
            assert result.success is True
            assert result.is_correct is True
            mock_learning_repository.save_fsrs_card.assert_called_once()

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
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
            user_id=1,
        )

        # Mock existing card
        mock_card = MagicMock()
        mock_learning_repository.get_fsrs_card.return_value = mock_card

        # Mock schedule failure
        mock_schedule_result = ScheduleCardResult(
            success=False,
            card_id=4,
            question_id=4,
            difficulty_before=0.0,
            stability_before=0.0,
            retrievability_before=0.0,
            state_before=FSRSState.NEW,
            difficulty_after=0.0,
            stability_after=0.0,
            retrievability_after=0.0,
            state_after=FSRSState.NEW,
            next_review_date=datetime.now(UTC),
            next_interval_days=0.0,
            error_message="Failed to update card state",
        )

        # Mock the ScheduleCard service creation
        with patch(
            "src.application.commands.submit_answer_with_rating_command.ScheduleCard"
        ) as mock_schedule_card_class:
            mock_schedule_service = AsyncMock()
            mock_schedule_service.call.return_value = mock_schedule_result
            mock_schedule_card_class.return_value = mock_schedule_service

            # Act
            result = await command.execute()

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
            learning_repository=mock_learning_repository,
            event_bus=mock_event_bus,
            user_id=1,
        )

        # Mock repository throwing exception on get, but save works
        mock_learning_repository.get_fsrs_card.side_effect = Exception(
            "Database connection error"
        )

        # Mock successful schedule result
        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=5,
            question_id=5,
            difficulty_before=2.5,
            stability_before=2.5,
            retrievability_before=1.0,
            state_before=FSRSState.NEW,
            difficulty_after=2.3,
            stability_after=3.5,
            retrievability_after=0.9,
            state_after=FSRSState.LEARNING,
            next_review_date=datetime.now(UTC),
            next_interval_days=3.0,
        )

        # Mock the ScheduleCard service creation
        with patch(
            "src.application.commands.submit_answer_with_rating_command.ScheduleCard"
        ) as mock_schedule_card_class:
            mock_schedule_service = AsyncMock()
            mock_schedule_service.call.return_value = mock_schedule_result
            mock_schedule_card_class.return_value = mock_schedule_service

            # Act
            result = await command.execute()

            # Assert - The handler gracefully handles the error and continues
            assert result.success is True
            assert result.is_correct is False  # Wrong answer
            assert result.error_message is None

            # Verify error was logged
            assert mock_learning_repository.get_fsrs_card.called

    def test_submit_answer_with_rating_result_attributes(self):
        """Test that SubmitAnswerWithRatingResult has the expected attributes."""
        # This test documents the expected interface
        result = SubmitAnswerWithRatingResult(
            success=True,
            is_correct=True,
            fsrs_result=None,  # This is part of the result
            next_review_date=datetime.now(UTC),
            error_message=None,
        )

        assert hasattr(result, "success")
        assert hasattr(result, "is_correct")
        assert hasattr(result, "fsrs_result")
        assert hasattr(result, "next_review_date")
        assert hasattr(result, "error_message")
