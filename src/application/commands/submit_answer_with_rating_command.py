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
)
from src.domain.shared.events import QuestionAnsweredEvent
from src.domain.shared.repositories import LearningRepository
from src.infrastructure.messaging.enhanced_event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SubmitAnswerWithRatingCommand:
    """Command to submit an answer with FSRS rating."""

    question_id: int
    selected_answer: str
    correct_answer: str
    fsrs_rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    user_id: int = 1
    session_id: int | None = None


@dataclass
class SubmitAnswerWithRatingResult:
    """Result of submitting an answer with rating."""

    success: bool
    is_correct: bool
    fsrs_result: ScheduleResult | None = None
    next_review_date: datetime | None = None
    error_message: str | None = None


class SubmitAnswerWithRatingCommandHandler:
    """Handler for submitting answers with FSRS rating using CQRS pattern."""

    def __init__(
        self,
        learning_repository: LearningRepository,
        event_bus: EventBus,
    ):
        """Initialize with learning repository and event bus."""
        self.learning_repository = learning_repository
        self.event_bus = event_bus
        self.schedule_card_service = ScheduleCard(
            learning_repository=learning_repository,
            event_bus=event_bus,
        )

    async def handle(
        self, command: SubmitAnswerWithRatingCommand
    ) -> SubmitAnswerWithRatingResult:
        """Handle the command to submit answer with rating."""
        try:
            logger.info(
                f"Submitting answer for question {command.question_id}: "
                f"selected={command.selected_answer}, rating={command.fsrs_rating}"
            )

            # Determine if answer is correct
            is_correct = command.selected_answer == command.correct_answer

            # Publish QuestionAnsweredEvent for cross-context tracking
            await self._publish_question_answered_event(command, is_correct)

            # Get or create FSRS card for this question
            card = await self._get_or_create_card(command.question_id, command.user_id)

            # Create schedule card request
            from src.domain.shared.models import FSRSRating

            schedule_request = ScheduleCardRequest(
                card_id=int(card.question_id),
                rating=FSRSRating(command.fsrs_rating),
                response_time_ms=1000,  # Default response time
                session_id=command.session_id,
            )

            # Schedule the card using domain service
            schedule_result = await self.schedule_card_service.call(schedule_request)

            if schedule_result.success and schedule_result.updated_card:
                # Publish domain event for analytics and cross-context updates
                await self._publish_card_scheduled_event(
                    command, schedule_result.updated_card, is_correct
                )

                return SubmitAnswerWithRatingResult(
                    success=True,
                    is_correct=is_correct,
                    fsrs_result=schedule_result.fsrs_result,
                    next_review_date=schedule_result.updated_card.due_date,
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
                due_date=datetime.now(UTC),
                stability=2.5,
                difficulty=2.5,
                elapsed_days=0,
                scheduled_days=0,
                reps=0,
                lapses=0,
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
                due_date=datetime.now(UTC),
                stability=2.5,
                difficulty=2.5,
                elapsed_days=0,
                scheduled_days=0,
                reps=0,
                lapses=0,
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

    async def _publish_card_scheduled_event(
        self,
        command: SubmitAnswerWithRatingCommand,
        updated_card: FSRSCard,
        is_correct: bool,  # noqa: ARG002
    ) -> None:
        """Publish CardScheduledEvent for analytics and cross-context updates."""
        try:
            # Convert SQLAlchemy attributes to proper types
            from datetime import UTC, datetime

            next_review_timestamp = getattr(updated_card, "next_review_date", None)
            next_review_date = (
                datetime.fromtimestamp(next_review_timestamp, UTC)
                if next_review_timestamp
                else datetime.now(UTC)
            )

            event = CardScheduledEvent(
                card_id=int(updated_card.question_id),
                question_id=command.question_id,
                new_difficulty=float(updated_card.difficulty),
                new_stability=float(updated_card.stability),
                new_retrievability=0.9,  # Default value
                next_review_date=next_review_date,
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
