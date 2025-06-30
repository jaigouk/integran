"""Query handler for getting questions by federal state following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository

logger = logging.getLogger(__name__)


@dataclass
class GetQuestionsByStateQuery:
    """Query for getting questions by federal state."""

    state: str | None
    question_repository: QuestionRepository

    async def handle(self) -> GetQuestionsByStateResult:
        """Handle the query to get questions by federal state."""
        try:
            questions = await self.question_repository.get_questions_by_state(
                state=self.state
            )

            if questions:
                return GetQuestionsByStateResult(success=True, questions=questions)
            else:
                state_name = self.state or "general questions"
                return GetQuestionsByStateResult(
                    success=False, error_message=f"No questions found for {state_name}"
                )

        except Exception as e:
            state_name = self.state or "general questions"
            logger.error(f"Error getting questions for state '{state_name}': {e}")
            return GetQuestionsByStateResult(
                success=False, error_message=f"Failed to get questions: {e}"
            )


@dataclass
class GetQuestionsByStateResult:
    """Result of getting questions by federal state."""

    success: bool
    questions: list[Question] | None = None
    error_message: str | None = None
