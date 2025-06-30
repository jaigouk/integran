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

    async def get_questions_by_state(self, state: str | None = None) -> list[Question]:
        """Get questions filtered by federal state.

        Args:
            state: Federal state name (e.g., "Baden-Württemberg").
                  If None, returns general questions (no state restriction).

        Returns:
            List of questions for the specified state or general questions.
        """

        def _get_questions_by_state() -> list[Question]:
            with self.db_manager.get_session() as session:
                if state is None:
                    # Return general questions (where state is null or question_type is 'general')
                    return (
                        session.query(Question)
                        .filter(
                            (Question.state.is_(None))
                            | (Question.question_type == "general")
                        )
                        .all()
                    )
                else:
                    # Return questions for specific state
                    return session.query(Question).filter(Question.state == state).all()

        return await self._run_in_executor(_get_questions_by_state)

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

    async def get_questions_for_active_learning(
        self,
        user_id: int = 1,
        desired_retention: float = 0.90,  # noqa: ARG002
        stability_threshold: int = 30,
        retrievability_threshold: float = 0.9,
        include_leeches: bool = True,
        limit: int = 100,
    ) -> list[Question]:
        """Get questions that need active learning (excludes well-mastered questions)."""

        def _get_questions_for_active_learning() -> list[Question]:
            with self.db_manager.get_session() as session:
                import math
                from datetime import UTC, datetime

                from src.domain.learning.models.learning_models import FSRSCard
                from src.domain.shared.models import FSRSState

                now = datetime.now(UTC).timestamp()
                results = []

                # Get all questions
                all_questions = session.query(Question).all()

                for question in all_questions:
                    # Look up FSRS card for this question
                    fsrs_card = (
                        session.query(FSRSCard)
                        .filter(
                            FSRSCard.question_id == question.id,
                            FSRSCard.user_id == user_id,
                        )
                        .first()
                    )

                    # If no FSRS card exists, this is a NEW question - include it
                    if fsrs_card is None:
                        results.append((question, 0))  # Priority 0 = highest (NEW)
                        continue

                    # Calculate current retrievability
                    if fsrs_card.last_review_date and fsrs_card.stability > 0:
                        elapsed_days = (now - fsrs_card.last_review_date) / 86400
                        retrievability = math.exp(-elapsed_days / fsrs_card.stability)
                    else:
                        retrievability = 1.0

                    # Check if question should be excluded (well-mastered)
                    if (
                        fsrs_card.stability > stability_threshold
                        and retrievability > retrievability_threshold
                        and fsrs_card.state == FSRSState.REVIEW.value
                    ):
                        continue  # Skip well-mastered questions

                    # Include leeches if enabled
                    if include_leeches and fsrs_card.lapse_count >= 8:
                        results.append((question, 1))  # Priority 1 = high (LEECHES)
                        continue

                    # Include questions in learning states
                    if fsrs_card.state in [
                        FSRSState.NEW.value,
                        FSRSState.LEARNING.value,
                    ]:
                        results.append((question, 1))  # Priority 1 = high
                        continue

                    # Include relearning questions
                    if fsrs_card.state == FSRSState.RELEARNING.value:
                        results.append((question, 2))  # Priority 2 = medium
                        continue

                    # Include due review questions
                    if fsrs_card.next_review_date <= now:
                        results.append((question, 3))  # Priority 3 = low
                        continue

                # Sort by priority (lower number = higher priority) and limit
                results.sort(key=lambda x: x[1])
                return [question for question, _ in results[:limit]]

        return await self._run_in_executor(_get_questions_for_active_learning)
