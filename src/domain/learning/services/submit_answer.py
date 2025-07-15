"""SubmitAnswer domain service for handling answer submission with FSRS scheduling.

This domain service encapsulates the business logic for submitting answers,
including FSRS card management, scheduling, and event publishing.
"""

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
from src.domain.shared.models import FSRSRating
from src.domain.shared.repositories import LearningRepository
from src.domain.shared.services import (
    DomainService,
    EventBusInterface,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class SubmitAnswerRequest:
    """Request to submit an answer with FSRS rating."""

    question_id: int
    selected_answer: str
    correct_answer: str
    fsrs_rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    user_id: int = 1
    session_id: int | None = None
    response_time_ms: int = 1000


@dataclass
class SubmitAnswerResult:
    """Result of submitting an answer."""

    success: bool
    is_correct: bool
    next_review_date: float | None = None
    fsrs_result: ScheduleResult | None = None
    error_message: str | None = None


class SubmitAnswer(DomainService[SubmitAnswerRequest, SubmitAnswerResult]):
    """Domain service to handle answer submission with FSRS scheduling."""

    def __init__(
        self,
        learning_repository: LearningRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with learning repository and event bus."""
        super().__init__(event_bus)
        self.learning_repository = learning_repository
        self.schedule_card_service = ScheduleCard(
            learning_repository=learning_repository,
            event_bus=event_bus,
        )

    async def call(self, request: SubmitAnswerRequest) -> SubmitAnswerResult:
        """Submit answer with FSRS rating and scheduling."""
        try:
            # Validate input
            if not self._validate_request(request):
                raise ValidationError("Invalid submit answer request")

            # Determine if answer is correct
            is_correct = request.selected_answer == request.correct_answer

            # Publish QuestionAnsweredEvent for cross-context tracking
            await self._publish_question_answered_event(request, is_correct)

            # Get or create FSRS card for this question
            card = await self._get_or_create_card(request)

            # Schedule the card using domain service
            schedule_result = await self._schedule_card(request, card)

            if schedule_result.success:
                # Publish domain event for analytics and cross-context updates
                await self._publish_card_scheduled_event(schedule_result, request, card)

                return SubmitAnswerResult(
                    success=True,
                    is_correct=is_correct,
                    next_review_date=schedule_result.next_review_date,
                    fsrs_result=schedule_result.fsrs_result,
                )
            else:
                return SubmitAnswerResult(
                    success=False,
                    is_correct=is_correct,
                    error_message=schedule_result.error_message
                    or "Failed to schedule card",
                )

        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return SubmitAnswerResult(
                success=False,
                is_correct=False,
                error_message=f"Failed to submit answer: {e}",
            )

    def _validate_request(self, request: SubmitAnswerRequest) -> bool:
        """Validate the submit answer request."""
        if not request.question_id or request.question_id <= 0:
            return False
        if not request.selected_answer or not request.correct_answer:
            return False
        return request.fsrs_rating in [1, 2, 3, 4]

    async def _get_or_create_card(self, request: SubmitAnswerRequest) -> FSRSCard:
        """Get existing FSRS card or create a new one."""
        try:
            # Try to get existing card
            card = await self.learning_repository.get_fsrs_card(
                user_id=request.user_id, question_id=request.question_id
            )
            if card:
                return card

            # Create new card if none exists
            new_card = FSRSCard.create_new(
                question_id=request.question_id,
                user_id=request.user_id,
            )

            # Save the new card
            saved_card = await self.learning_repository.save_fsrs_card(new_card)
            logger.info(
                f"Created new FSRS card {saved_card.card_id} for question {request.question_id}"
            )
            return saved_card

        except Exception as e:
            logger.error(f"Error getting/creating FSRS card: {e}")
            raise

    async def _schedule_card(
        self, request: SubmitAnswerRequest, card: FSRSCard
    ) -> ScheduleCardResult:
        """Schedule the FSRS card based on the rating."""
        schedule_request = ScheduleCardRequest(
            card_id=int(card.card_id),
            rating=FSRSRating(request.fsrs_rating),
            response_time_ms=request.response_time_ms,
            session_id=request.session_id,
        )

        return await self.schedule_card_service.call(schedule_request)

    async def _publish_question_answered_event(
        self, request: SubmitAnswerRequest, is_correct: bool
    ) -> None:
        """Publish QuestionAnsweredEvent for cross-context tracking."""
        event = QuestionAnsweredEvent(
            question_id=request.question_id,
            user_id=request.user_id,
            selected_answer=request.selected_answer,
            correct_answer=request.correct_answer,
            is_correct=is_correct,
            fsrs_rating=request.fsrs_rating,
            response_time_ms=request.response_time_ms,
            session_id=request.session_id,
        )
        await self.event_bus.publish(event)

    async def _publish_card_scheduled_event(
        self,
        schedule_result: ScheduleCardResult,
        request: SubmitAnswerRequest,
        card: FSRSCard,
    ) -> None:
        """Publish CardScheduledEvent for analytics and cross-context updates."""

        # Use the FSRS result data from schedule_result
        fsrs_result = schedule_result.fsrs_result
        event = CardScheduledEvent(
            card_id=int(card.card_id),
            question_id=request.question_id,
            new_difficulty=fsrs_result.difficulty if fsrs_result else card.difficulty,
            new_stability=fsrs_result.stability if fsrs_result else card.stability,
            new_retrievability=fsrs_result.retrievability
            if fsrs_result
            else card.retrievability,
            next_review_date=datetime.fromtimestamp(
                schedule_result.next_review_date, UTC
            )
            if schedule_result.next_review_date
            else datetime.now(UTC),
            rating=request.fsrs_rating,
            response_time_ms=request.response_time_ms,
            session_id=request.session_id,
        )
        await self.event_bus.publish(event)
