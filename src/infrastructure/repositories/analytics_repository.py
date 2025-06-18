"""Concrete implementation of AnalyticsRepository interface."""

from __future__ import annotations

from typing import Any

from src.domain.shared.repositories import AnalyticsRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyAnalyticsRepository(AnalyticsRepository):
    """SQLAlchemy implementation of AnalyticsRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def get_learning_stats(self, user_id: int) -> dict[str, Any]:  # noqa: ARG002
        """Get comprehensive learning statistics for a user."""
        # DatabaseManager method is get_learning_stats() - takes no parameters
        # Convert LearningStats to dict
        stats = self.db_manager.get_learning_stats()
        return stats.__dict__ if hasattr(stats, "__dict__") else {}

    async def get_session_progress(self, user_id: int) -> dict[str, Any]:
        """Get session progress data for a user."""
        # NOTE: DatabaseManager doesn't have get_session_progress method
        raise NotImplementedError(
            "get_session_progress not implemented in DatabaseManager"
        )

    async def save_user_progress(
        self, user_id: int, progress_data: dict[str, Any]
    ) -> None:
        """Save user progress data."""
        # NOTE: DatabaseManager doesn't have save_user_progress method
        raise NotImplementedError(
            "save_user_progress not implemented in DatabaseManager"
        )

    async def delete_user_analytics(self, user_id: int) -> dict[str, int]:
        """Delete all analytics data for a user and return counts."""
        # NOTE: DatabaseManager doesn't have delete_user_analytics method
        raise NotImplementedError(
            "delete_user_analytics not implemented in DatabaseManager"
        )

    async def get_category_progress(self, user_id: int) -> dict[str, Any]:
        """Get progress by category for a user."""
        # NOTE: DatabaseManager doesn't have get_category_progress method
        raise NotImplementedError(
            "get_category_progress not implemented in DatabaseManager"
        )

    async def record_question_attempt(
        self,
        user_id: int,
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
        session_id: int | None = None,
    ) -> None:
        """Record a question attempt."""
        # NOTE: DatabaseManager doesn't have record_question_attempt method
        # It has record_attempt which takes different parameters
        raise NotImplementedError(
            "record_question_attempt not implemented in DatabaseManager"
        )
