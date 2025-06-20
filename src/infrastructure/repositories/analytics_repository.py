"""Concrete implementation of AnalyticsRepository interface."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from src.domain.shared.repositories import AnalyticsRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyAnalyticsRepository(AnalyticsRepository):
    """SQLAlchemy implementation of AnalyticsRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def get_learning_stats(self, user_id: int) -> dict[str, Any]:  # noqa: ARG002
        """Get comprehensive learning statistics for a user."""
        # DatabaseManager method is get_learning_stats() - takes no parameters
        # Convert LearningStats to dict
        stats = self.db_manager.get_learning_stats()
        return stats.__dict__ if hasattr(stats, "__dict__") else {}

    async def get_session_progress(self, user_id: int) -> dict[str, Any]:
        """Get session progress data for a user."""
        # Use the new session statistics method from DatabaseManager
        session_stats = self.db_manager.get_session_statistics(user_id)

        # Get additional learning stats for current streak
        learning_stats = self.db_manager.get_learning_stats()

        return {
            "total_sessions": session_stats["total_sessions"],
            "avg_duration": session_stats["avg_duration"],
            "total_time": session_stats["total_time"],
            "total_questions": session_stats["total_questions"],
            "total_correct": session_stats["total_correct"],
            "current_streak": getattr(learning_stats, "current_streak", 0),
            "longest_streak": getattr(learning_stats, "longest_streak", 0),
        }

    async def save_user_progress(
        self, user_id: int, progress_data: dict[str, Any]
    ) -> None:
        """Save user progress data."""

        def _save_user_progress() -> None:
            with self.db_manager.get_session() as session:
                from src.domain.analytics.models.analytics_models import UserProgress

                # Check if user progress exists
                existing = (
                    session.query(UserProgress).filter_by(user_id=user_id).first()
                )
                if existing:
                    # Update existing progress (updated_at will be set automatically)
                    for key, value in progress_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # Create new progress record
                    progress = UserProgress(user_id=user_id, **progress_data)
                    session.add(progress)

                session.commit()

        await self._run_in_executor(_save_user_progress)

    async def delete_user_analytics(self, user_id: int) -> dict[str, int]:
        """Delete all analytics data for a user and return counts."""

        def _delete_user_analytics() -> dict[str, int]:
            with self.db_manager.get_session() as session:
                from src.domain.analytics.models.analytics_models import (
                    UserProgress,
                )

                # Count items before deletion
                user_progress_count = (
                    session.query(UserProgress).filter_by(user_id=user_id).count()
                )
                # Note: CategoryProgress is global and QuestionAttempt deletion handled by session management

                # Delete user-specific analytics data
                session.query(UserProgress).filter_by(user_id=user_id).delete()
                # Note: CategoryProgress is global and typically not deleted per user
                # QuestionAttempt deletion should be handled carefully - depends on session management

                session.commit()

                return {
                    "user_progress": user_progress_count,
                    "category_progress": 0,  # Not deleted
                    "question_attempts": 0,  # Not deleted to preserve session data integrity
                }

        return await self._run_in_executor(_delete_user_analytics)

    async def get_category_progress(self, user_id: int) -> dict[str, Any]:  # noqa: ARG002
        """Get progress by category for a user."""

        def _get_category_progress() -> dict[str, Any]:
            with self.db_manager.get_session() as session:
                from src.domain.analytics.models.analytics_models import (
                    CategoryProgress,
                )

                # Get all category progress data
                categories = session.query(CategoryProgress).all()

                progress_by_category: dict[str, Any] = {}
                for category in categories:
                    progress_by_category[str(category.category)] = {
                        "total_questions": int(category.total_questions),
                        "questions_seen": int(category.questions_seen),
                        "correct_answers": int(category.correct_answers),
                        "accuracy": float(
                            category.correct_answers / category.questions_seen
                        )
                        if category.questions_seen > 0
                        else 0.0,
                        "average_time": float(category.average_time or 0.0),
                        "last_practiced": category.last_practiced.isoformat()
                        if category.last_practiced
                        else None,
                    }

                return progress_by_category

        return await self._run_in_executor(_get_category_progress)

    async def record_question_attempt(
        self,
        user_id: int,  # noqa: ARG002
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
        session_id: int | None = None,
    ) -> None:
        """Record a question attempt."""
        if session_id is None:
            # Cannot record attempt without session_id
            return

        # Use DatabaseManager's record_attempt method with appropriate AnswerStatus
        from src.domain.shared.models import AnswerStatus

        status = AnswerStatus.CORRECT if is_correct else AnswerStatus.INCORRECT
        time_taken = response_time_ms / 1000.0  # Convert to seconds

        self.db_manager.record_attempt(
            session_id=session_id,
            question_id=question_id,
            status=status,
            user_answer=None,  # Not provided in this interface
            time_taken=time_taken,
        )
