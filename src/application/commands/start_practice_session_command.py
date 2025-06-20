"""Command for starting a practice session following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.application.queries.get_questions_by_mode_query import (
    GetQuestionsByModeQuery,
    GetQuestionsByModeQueryHandler,
)
from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository

logger = logging.getLogger(__name__)


@dataclass
class StartPracticeSessionCommand:
    """Command to start a practice session with specified mode."""

    practice_mode: str  # "random", "sequential", "review", "category"
    user_id: int = 1
    limit: int = 1
    # State for cycling through questions
    category_index: int = 0
    question_indices: dict[str, int] | None = None
    last_question_id: int = 0


@dataclass
class StartPracticeSessionResult:
    """Result of starting a practice session."""

    success: bool
    question: Question | None = None
    session_state: dict[str, Any] | None = None  # State for UI to maintain
    practice_mode: str | None = None
    error_message: str | None = None


class StartPracticeSessionCommandHandler:
    """Handler for starting practice sessions using CQRS pattern."""

    def __init__(self, question_repository: QuestionRepository):
        """Initialize with question repository."""
        self.question_repository = question_repository
        self.questions_query_handler = GetQuestionsByModeQueryHandler(
            question_repository=question_repository
        )

    async def handle(
        self, command: StartPracticeSessionCommand
    ) -> StartPracticeSessionResult:
        """Handle the command to start a practice session."""
        try:
            logger.info(
                f"Starting practice session: mode={command.practice_mode}, user_id={command.user_id}"
            )

            # Use the existing query handler to get the first question
            query = GetQuestionsByModeQuery(
                practice_mode=command.practice_mode,
                user_id=command.user_id,
                limit=command.limit,
                category_index=command.category_index,
                question_indices=command.question_indices,
                last_question_id=command.last_question_id,
            )

            result = await self.questions_query_handler.handle(query)

            if result.success and result.question:
                return StartPracticeSessionResult(
                    success=True,
                    question=result.question,
                    session_state=result.next_state,
                    practice_mode=command.practice_mode,
                )
            else:
                return StartPracticeSessionResult(
                    success=False,
                    practice_mode=command.practice_mode,
                    error_message=result.error_message
                    or f"No questions available for {command.practice_mode} mode",
                )

        except Exception as e:
            logger.error(f"Error starting practice session: {e}")
            return StartPracticeSessionResult(
                success=False,
                practice_mode=command.practice_mode,
                error_message=f"Failed to start practice session: {e}",
            )
