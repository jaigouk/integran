"""Command for submitting answers with FSRS rating following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.learning.services.submit_answer import (
    SubmitAnswer,
    SubmitAnswerRequest,
)
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
    user_id: int = 1
    session_id: int | None = None
    response_time_ms: int = 1000


@dataclass
class SubmitAnswerWithRatingResult:
    """Result of submitting an answer with rating."""

    success: bool
    is_correct: bool
    next_review_date: float | None = None
    error_message: str | None = None


class SubmitAnswerWithRatingCommandHandler:
    """Handler for submitting answers with FSRS rating following CQRS pattern."""

    def __init__(
        self,
        learning_repository: LearningRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with learning repository and event bus."""
        self.learning_repository = learning_repository
        self.event_bus = event_bus
        self.submit_answer_service = SubmitAnswer(
            learning_repository=learning_repository,
            event_bus=event_bus,
        )

    async def handle(
        self, command: SubmitAnswerWithRatingCommand
    ) -> SubmitAnswerWithRatingResult:
        """Handle the command to submit answer with rating."""
        try:
            # Validate command
            if not self._validate_command(command):
                return SubmitAnswerWithRatingResult(
                    success=False,
                    is_correct=False,
                    error_message="Invalid command parameters",
                )

            # Map command to domain request
            request = self._map_to_domain_request(command)

            # Call domain service
            result = await self.submit_answer_service.call(request)

            # Map domain result to command result
            return SubmitAnswerWithRatingResult(
                success=result.success,
                is_correct=result.is_correct,
                next_review_date=result.next_review_date,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error handling submit answer command: {e}")
            return SubmitAnswerWithRatingResult(
                success=False,
                is_correct=False,
                error_message=f"Failed to submit answer: {e}",
            )

    def _validate_command(self, command: SubmitAnswerWithRatingCommand) -> bool:
        """Validate the command parameters."""
        if not command.question_id or command.question_id <= 0:
            return False
        if not command.selected_answer or not command.correct_answer:
            return False
        return command.fsrs_rating in [1, 2, 3, 4]

    def _map_to_domain_request(
        self, command: SubmitAnswerWithRatingCommand
    ) -> SubmitAnswerRequest:
        """Map command to domain request."""
        return SubmitAnswerRequest(
            question_id=command.question_id,
            selected_answer=command.selected_answer,
            correct_answer=command.correct_answer,
            fsrs_rating=command.fsrs_rating,
            user_id=command.user_id,
            session_id=command.session_id,
            response_time_ms=command.response_time_ms,
        )


# DEPRECATED: Legacy command pattern - use SubmitAnswerWithRatingCommandHandler instead
@dataclass
class SubmitAnswerWithRatingCommandLegacy:
    """DEPRECATED: Legacy command pattern."""

    question_id: int
    selected_answer: str
    correct_answer: str
    fsrs_rating: int
    learning_repository: LearningRepository
    event_bus: EventBusInterface
    user_id: int = 1
    session_id: int | None = None

    async def execute(self) -> SubmitAnswerWithRatingResult:
        """DEPRECATED: Use SubmitAnswerWithRatingCommandHandler.handle() instead."""
        handler = SubmitAnswerWithRatingCommandHandler(
            learning_repository=self.learning_repository,
            event_bus=self.event_bus,
        )

        command = SubmitAnswerWithRatingCommand(
            question_id=self.question_id,
            selected_answer=self.selected_answer,
            correct_answer=self.correct_answer,
            fsrs_rating=self.fsrs_rating,
            user_id=self.user_id,
            session_id=self.session_id,
        )

        return await handler.handle(command)
