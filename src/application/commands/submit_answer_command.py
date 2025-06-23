"""Command for submitting an answer during a learning session - thin coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.commands import Command, CommandHandler, CommandResult
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
    SubmitAnswerRequest,
)
from src.domain.shared.models import FSRSRating


@dataclass
class SubmitAnswerCommand(Command):
    """Command to submit an answer for a question."""

    session_id: int
    card_id: int
    user_answer: str | None  # A, B, C, D or None for skipped
    response_time_ms: int
    rating: int | None = None  # Optional manual rating (1-4)

    def validate(self) -> bool:
        return (
            (self.user_answer is None or self.user_answer in ["A", "B", "C", "D"])
            and self.response_time_ms >= 0
            and (self.rating is None or 1 <= self.rating <= 4)
        )


@dataclass
class SubmitAnswerResult(CommandResult):
    """Result of submitting an answer."""

    success: bool = False
    error_message: str | None = None
    is_correct: bool = False
    next_review_date: str | None = None

    def get_result_data(self) -> dict[str, Any]:
        return {"is_correct": self.is_correct, "next_review": self.next_review_date}


class SubmitAnswerCommandHandler(
    CommandHandler[SubmitAnswerCommand, SubmitAnswerResult]
):
    """Handler for submitting answers - thin coordinator only."""

    def __init__(self, learning_service: CompleteLearningSession):
        self.learning_service = learning_service

    async def handle(self, command: SubmitAnswerCommand) -> SubmitAnswerResult:
        """Validate input and delegate to domain service."""
        if not command.validate():
            return SubmitAnswerResult(error_message="Invalid answer or rating")
        # Convert int rating to FSRSRating enum if provided
        fsrs_rating = None
        if command.rating is not None:
            rating_map = {
                1: FSRSRating.AGAIN,
                2: FSRSRating.HARD,
                3: FSRSRating.GOOD,
                4: FSRSRating.EASY,
            }
            fsrs_rating = rating_map.get(command.rating)
        request = SubmitAnswerRequest(
            session_id=command.session_id,
            card_id=command.card_id,
            user_answer=command.user_answer,
            response_time_ms=command.response_time_ms,
            rating=fsrs_rating,
        )
        result = await self.learning_service.call(request)
        return SubmitAnswerResult(
            success=result.success,
            is_correct=result.is_correct,
            next_review_date=result.next_review_date.isoformat()
            if result.next_review_date
            else None,
            error_message=result.error_message,
        )
