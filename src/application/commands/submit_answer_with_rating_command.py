"""Command for submitting answers with FSRS rating following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.learning.events.card_events import CardScheduledEvent
from src.domain.learning.models.learning_models import FSRSCard, ScheduleResult
from src.domain.learning.services.schedule_card import (
    ScheduleCard,
    ScheduleCardRequest,
    ScheduleCardResult,
)
from src.domain.shared.events import QuestionAnsweredEvent
from src.domain.shared.repositories import LearningRepository
from src.domain.shared.services import EventBusInterface

logger = logging.getLogger(__name__)


@dataclass
class SubmitAnswerWithRatingCommand:
    """Command to submit an answer with FSRS rating."""

    question_id: int
    selected_answer: str
    correct_answer: str
    fsrs_rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    learning_repository: LearningRepository
    event_bus: EventBusInterface
    user_id: int = 1
    session_id: int | None = None

    async def execute(self) -> SubmitAnswerWithRatingResult:
        """Execute the command to submit answer with rating."""
        try:
            logger.info(
                f"Submitting answer for question {self.question_id}: "
                f"selected={self.selected_answer}, rating={self.fsrs_rating}"
            )

            # Initialize schedule card service
            schedule_card_service = ScheduleCard(
                learning_repository=self.learning_repository,
                event_bus=self.event_bus,
            )

            # Determine if answer is correct
            is_correct = self.selected_answer == self.correct_answer

            # Publish QuestionAnsweredEvent for cross-context tracking
            await self._publish_question_answered_event(is_correct)

            # Get or create FSRS card for this question
            card = await self._get_or_create_card()

            # Create schedule card request
            from src.domain.shared.models import FSRSRating

            schedule_request = ScheduleCardRequest(
                card_id=int(card.question_id),
                rating=FSRSRating(self.fsrs_rating),
                response_time_ms=1000,  # Default response time
                session_id=self.session_id,
            )

            # Schedule the card using domain service
            schedule_result = await schedule_card_service.call(schedule_request)

            if schedule_result.success:
                # Publish domain event for analytics and cross-context updates
                await self._publish_card_scheduled_event_from_result(
                    schedule_result, is_correct
                )

                return SubmitAnswerWithRatingResult(
                    success=True,
                    is_correct=is_correct,
                    fsrs_result=None,  # We don't have direct access to the internal FSRS result
                    next_review_date=schedule_result.next_review_date,
                )
            else:
                return SubmitAnswerWithRatingResult(
                    success=False,
                    is_correct=is_correct,
                    error_message=schedule_result.error_message
                    or "Failed to schedule card",
                )

        except Exception as e:
            logger.error(f"Error submitting answer with rating: {e}")
            return SubmitAnswerWithRatingResult(
                success=False,
                is_correct=False,
                error_message=f"Failed to submit answer: {e}",
            )

    async def _get_or_create_card(self) -> FSRSCard:
        """Get existing FSRS card or create a new one."""
        try:
            # Try to get existing card
            card = await self.learning_repository.get_fsrs_card(
                user_id=self.user_id, question_id=self.question_id
            )
            if card:
                return card

            # Create new card if none exists
            new_card = FSRSCard(
                user_id=self.user_id,
                question_id=self.question_id,
                next_review_date=datetime.now(UTC).timestamp(),
                stability=2.5,
                difficulty=2.5,
                retrievability=1.0,
                state=1,  # New state
            )

            saved_card = await self.learning_repository.save_fsrs_card(new_card)
            return saved_card

        except Exception as e:
            logger.error(f"Error getting/creating FSRS card: {e}")
            # Return a default card to avoid breaking the flow
            return FSRSCard(
                user_id=self.user_id,
                question_id=self.question_id,
                next_review_date=datetime.now(UTC).timestamp(),
                stability=2.5,
                difficulty=2.5,
                retrievability=1.0,
                state=1,
            )

    async def _publish_question_answered_event(self, is_correct: bool) -> None:
        """Publish QuestionAnsweredEvent for analytics tracking."""
        try:
            event = QuestionAnsweredEvent(
                question_id=self.question_id,
                user_id=self.user_id,
                selected_answer=self.selected_answer,
                correct_answer=self.correct_answer,
                is_correct=is_correct,
                fsrs_rating=self.fsrs_rating,
                response_time_ms=1000,  # Default
                session_id=self.session_id,
                answered_at=datetime.now(UTC),
            )
            await self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish QuestionAnsweredEvent: {e}")

    async def _publish_card_scheduled_event_from_result(
        self, schedule_result: ScheduleCardResult, _is_correct: bool
    ) -> None:
        """Publish CardScheduledEvent from schedule result."""
        try:
            event = CardScheduledEvent(
                card_id=int(self.question_id),
                question_id=self.question_id,
                new_difficulty=2.5,  # Would come from actual result
                new_stability=schedule_result.stability_after or 2.5,
                new_retrievability=1.0,  # Would come from actual result
                next_review_date=schedule_result.next_review_date or datetime.now(UTC),
                rating=self.fsrs_rating,
                response_time_ms=1000,  # Default
                session_id=self.session_id,
            )
            await self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish CardScheduledEvent: {e}")


@dataclass
class SubmitAnswerWithRatingResult:
    """Result of submitting an answer with rating."""

    success: bool
    is_correct: bool
    fsrs_result: ScheduleResult | None = None
    next_review_date: datetime | None = None
    error_message: str | None = None


# Legacy handler class - deprecated in favor of command.execute()
# Kept for backward compatibility during transition
class SubmitAnswerWithRatingCommandHandler:
    """DEPRECATED: Handler for submitting answers with FSRS rating.

    Use SubmitAnswerWithRatingCommand.execute() method instead.
    """

    def __init__(
        self,
        learning_repository: LearningRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with learning repository and event bus."""
        self.learning_repository = learning_repository
        self.event_bus = event_bus

    async def handle(
        self, command: SubmitAnswerWithRatingCommand
    ) -> SubmitAnswerWithRatingResult:
        """Handle the command to submit answer with rating."""
        # Delegate to command's execute method for proper CQRS pattern
        command.learning_repository = self.learning_repository
        command.event_bus = self.event_bus
        return await command.execute()

    async def _get_or_create_card(self, question_id: int, user_id: int) -> FSRSCard:
        """Get existing FSRS card or create a new one."""
        try:
            # Try to get existing card
            card = await self.learning_repository.get_fsrs_card(
                user_id=user_id, question_id=question_id
            )
            if card:
                return card

            # Create new card if none exists
            new_card = FSRSCard(
                user_id=user_id,
                question_id=question_id,
                next_review_date=datetime.now(UTC).timestamp(),
                stability=2.5,
                difficulty=2.5,
                retrievability=1.0,
                state=1,  # New state
            )

            saved_card = await self.learning_repository.save_fsrs_card(new_card)
            return saved_card

        except Exception as e:
            logger.error(f"Error getting/creating FSRS card: {e}")
            # Return default card if database operations fail
            return FSRSCard(
                user_id=user_id,
                question_id=question_id,
                next_review_date=datetime.now(UTC).timestamp(),
                stability=2.5,
                difficulty=2.5,
                retrievability=1.0,
                state=1,
            )

    async def _publish_question_answered_event(
        self,
        command: SubmitAnswerWithRatingCommand,
        is_correct: bool,
    ) -> None:
        """Publish QuestionAnsweredEvent for cross-context tracking."""
        try:
            event = QuestionAnsweredEvent(
                question_id=command.question_id,
                user_id=command.user_id,
                selected_answer=command.selected_answer,
                correct_answer=command.correct_answer,
                is_correct=is_correct,
                fsrs_rating=command.fsrs_rating,
                response_time_ms=1000,  # Default response time
                session_id=command.session_id,
                answered_at=datetime.now(UTC),
            )
            await self.event_bus.publish(event)
            logger.debug(
                f"Published QuestionAnsweredEvent for question {command.question_id}: "
                f"correct={is_correct}, rating={command.fsrs_rating}"
            )

        except Exception as e:
            logger.error(f"Error publishing QuestionAnsweredEvent: {e}")
            # Don't fail the main operation if event publishing fails

    async def _publish_card_scheduled_event_from_result(
        self,
        command: SubmitAnswerWithRatingCommand,
        schedule_result: ScheduleCardResult,
        is_correct: bool,  # noqa: ARG002
    ) -> None:
        """Publish CardScheduledEvent for analytics and cross-context updates."""
        try:
            event = CardScheduledEvent(
                card_id=schedule_result.card_id,
                question_id=command.question_id,
                new_difficulty=schedule_result.difficulty_after,
                new_stability=schedule_result.stability_after,
                new_retrievability=schedule_result.retrievability_after,
                next_review_date=schedule_result.next_review_date,
                rating=command.fsrs_rating,
                response_time_ms=1000,  # Default response time
                session_id=command.session_id,
            )
            await self.event_bus.publish(event)
            logger.debug(
                f"Published CardScheduledEvent for question {command.question_id}"
            )

        except Exception as e:
            logger.error(f"Error publishing CardScheduledEvent: {e}")
            # Don't fail the main operation if event publishing fails
