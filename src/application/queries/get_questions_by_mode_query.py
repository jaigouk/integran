"""Query handler for getting questions by practice mode following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository

logger = logging.getLogger(__name__)


@dataclass
class GetQuestionsByModeQuery:
    """Query for getting questions by practice mode."""

    practice_mode: str
    user_id: int = 1
    limit: int = 1
    # State for cycling through questions
    category_index: int = 0
    question_indices: dict[str, int] | None = None
    last_question_id: int = 0


@dataclass
class GetQuestionsByModeResult:
    """Result of getting questions by practice mode."""

    success: bool
    question: Question | None = None
    next_state: dict[str, Any] | None = None  # State to maintain for cycling
    error_message: str | None = None


class GetQuestionsByModeQueryHandler:
    """Handler for getting questions by practice mode using CQRS pattern."""

    def __init__(self, question_repository: QuestionRepository):
        """Initialize with question repository."""
        self.question_repository = question_repository

    async def handle(self, query: GetQuestionsByModeQuery) -> GetQuestionsByModeResult:
        """Handle the query to get questions by practice mode."""
        try:
            if query.practice_mode == "review":
                return await self._get_review_questions(query)
            elif query.practice_mode == "random":
                return await self._get_random_questions(query)
            elif query.practice_mode == "sequential":
                return await self._get_sequential_questions(query)
            elif query.practice_mode == "category":
                return await self._get_category_questions(query)
            elif query.practice_mode == "images":
                return await self._get_image_questions(query)
            else:
                return await self._get_default_question(query)

        except Exception as e:
            logger.error(
                f"Error getting questions by mode '{query.practice_mode}': {e}"
            )
            return GetQuestionsByModeResult(
                success=False, error_message=f"Failed to get questions: {e}"
            )

    async def _get_review_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions due for review."""
        questions = await self.question_repository.get_questions_for_review(
            user_id=query.user_id, limit=query.limit
        )
        if questions:
            return GetQuestionsByModeResult(success=True, question=questions[0])
        return GetQuestionsByModeResult(
            success=False, error_message="No questions due for review"
        )

    async def _get_random_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get random questions by cycling through categories."""
        categories = ["Geschichte", "Politik", "Recht", "Kultur", "Geographie"]
        current_category_index = query.category_index
        category = categories[current_category_index % len(categories)]

        questions = await self.question_repository.get_questions_by_category(category)
        if questions:
            # Initialize question indices if not provided
            question_indices = query.question_indices or {}
            question_index = question_indices.get(category, 0)

            question = questions[question_index % len(questions)]

            # Update state for next call
            next_question_indices = question_indices.copy()
            next_question_indices[category] = question_index + 1

            next_state = {
                "category_index": (current_category_index + 1) % len(categories),
                "question_indices": next_question_indices,
            }

            return GetQuestionsByModeResult(
                success=True, question=question, next_state=next_state
            )

        return GetQuestionsByModeResult(
            success=False, error_message=f"No questions found in category: {category}"
        )

    async def _get_sequential_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions sequentially by ID."""
        next_question_id = query.last_question_id + 1

        question = await self.question_repository.get_question_by_id(next_question_id)
        if question:
            next_state = {"last_question_id": next_question_id}
            return GetQuestionsByModeResult(
                success=True, question=question, next_state=next_state
            )
        else:
            # Reset to beginning if we've reached the end
            question = await self.question_repository.get_question_by_id(1)
            if question:
                next_state = {"last_question_id": 1}
                return GetQuestionsByModeResult(
                    success=True, question=question, next_state=next_state
                )

        return GetQuestionsByModeResult(
            success=False, error_message="No questions available"
        )

    async def _get_category_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions from a specific category (could be enhanced later)."""
        # For now, delegate to random mode
        return await self._get_random_questions(query)

    async def _get_image_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions that have images."""
        image_questions = await self.question_repository.get_image_questions()
        if image_questions:
            # Cycle through image questions sequentially
            question_index = query.last_question_id % len(image_questions)
            question = image_questions[question_index]

            next_state = {
                "last_question_id": (query.last_question_id + 1) % len(image_questions)
            }
            return GetQuestionsByModeResult(
                success=True, question=question, next_state=next_state
            )

        return GetQuestionsByModeResult(
            success=False, error_message="No image questions available"
        )

    async def _get_default_question(
        self, _query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get default question (first available)."""
        # _query is unused but kept for interface consistency
        question = await self.question_repository.get_question_by_id(1)
        if question:
            return GetQuestionsByModeResult(success=True, question=question)

        return GetQuestionsByModeResult(
            success=False, error_message="No questions available in database"
        )
