"""Concrete implementation of QuestionRepository interface."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyQuestionRepository(QuestionRepository):
    """SQLAlchemy implementation of QuestionRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

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

        def _get_all_questions() -> list[Question]:
            with self.db_manager.get_session() as session:
                return session.query(Question).all()

        return await self._run_in_executor(_get_all_questions)

    async def get_image_questions(self) -> list[Question]:
        """Get all questions that have images."""

        def _get_image_questions() -> list[Question]:
            with self.db_manager.get_session() as session:
                return session.query(Question).filter(Question.is_image_question).all()

        return await self._run_in_executor(_get_image_questions)

    async def save_question(self, question: Question) -> Question:
        """Save or update a question."""

        def _save_question() -> Question:
            with self.db_manager.get_session() as session:
                # Check if question exists (has ID)
                if hasattr(question, "id") and question.id:
                    # Update existing question
                    existing = session.query(Question).filter_by(id=question.id).first()
                    if existing:
                        # Update fields
                        for field in [
                            "question",
                            "options",
                            "correct",
                            "category",
                            "difficulty",
                            "image_paths",
                            "image_mapping",
                            "multilingual_answers",
                            "rag_sources",
                        ]:
                            if hasattr(question, field):
                                setattr(existing, field, getattr(question, field))
                        session.commit()
                        return existing
                    else:
                        # Add as new question
                        session.add(question)
                        session.commit()
                        return question
                else:
                    # Add as new question
                    session.add(question)
                    session.commit()
                    return question

        return await self._run_in_executor(_save_question)
