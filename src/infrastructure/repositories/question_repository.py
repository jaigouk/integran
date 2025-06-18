"""Concrete implementation of QuestionRepository interface."""

from __future__ import annotations

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyQuestionRepository(QuestionRepository):
    """SQLAlchemy implementation of QuestionRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def get_question_by_id(self, question_id: int) -> Question | None:
        """Get a single question by ID."""
        return self.db_manager.get_question(question_id)

    async def get_questions_by_category(self, category: str) -> list[Question]:
        """Get all questions in a specific category."""
        return self.db_manager.get_questions_by_category(category)

    async def get_questions_for_review(
        self,
        user_id: int,  # noqa: ARG002
        limit: int = 10,
    ) -> list[Question]:
        """Get questions due for review for a specific user."""
        return self.db_manager.get_questions_for_review(limit)

    async def get_all_questions(self) -> list[Question]:
        """Get all questions in the database."""
        # NOTE: DatabaseManager doesn't have get_all_questions method
        # This would need to be implemented if needed
        raise NotImplementedError(
            "get_all_questions not implemented in DatabaseManager"
        )

    async def save_question(self, question: Question) -> Question:
        """Save or update a question."""
        # NOTE: DatabaseManager doesn't have save_question method
        # This would need to be implemented if needed
        raise NotImplementedError("save_question not implemented in DatabaseManager")
