"""SQLAlchemy implementation of the Analytics repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func

from src.domain.analytics.entities.performance_metrics import (
    DifficultyDistribution,
    PerformanceInsights,
    PerformanceMetrics,
)
from src.domain.shared.repositories import AnalyticsRepository
from src.infrastructure.database.models import (
    LearningProgressDB,
    SessionDB,
    UserDB,
)

if TYPE_CHECKING:
    from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyAnalyticsRepository(AnalyticsRepository):
    """SQLAlchemy implementation of the analytics repository."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the repository with database manager."""
        self._db_manager = db_manager

    async def get_learning_stats(self, user_id: int) -> dict[str, Any]:
        """Get comprehensive learning statistics for a user."""
        metrics = await self.get_performance_metrics(user_id)

        return {
            "total_cards": metrics.total_cards_studied,
            "cards_mastered": int(
                metrics.total_cards_studied * metrics.mastery_percentage / 100
            ),
            "cards_learning": metrics.total_cards_studied
            - int(metrics.total_cards_studied * metrics.mastery_percentage / 100),
            "cards_new": 0,  # TODO: Track new cards separately
            "due_today": metrics.cards_due_today,
            "due_tomorrow": 0,  # TODO: Calculate tomorrow's due cards
            "due_week": 0,  # TODO: Calculate week's due cards
            "average_accuracy": metrics.average_accuracy,
            "study_streak": metrics.study_streak,
            "total_study_time_minutes": metrics.total_study_time_minutes,
        }

    async def get_session_progress(self, user_id: int) -> dict[str, Any]:
        """Get session progress data for a user."""
        with self._db_manager.get_session() as session:
            # Get user's current and longest streak
            user = session.query(UserDB).filter_by(id=user_id).first()
            if not user:
                return {
                    "current_streak": 0,
                    "longest_streak": 0,
                    "total_sessions": 0,
                }

            # Count total sessions
            total_sessions = session.query(SessionDB).filter_by(user_id=user_id).count()

            return {
                "current_streak": user.study_streak,
                "longest_streak": user.study_streak,  # TODO: Track longest separately
                "total_sessions": total_sessions,
            }

    async def save_user_progress(
        self, user_id: int, progress_data: dict[str, Any]
    ) -> None:
        """Save user progress data."""
        # TODO: Implement progress saving
        pass

    async def delete_user_analytics(self, user_id: int) -> dict[str, int]:
        """Delete all analytics data for a user and return counts."""
        with self._db_manager.get_session() as session:
            # Count and delete learning progress
            progress_count = (
                session.query(LearningProgressDB).filter_by(user_id=user_id).count()
            )
            session.query(LearningProgressDB).filter_by(user_id=user_id).delete()

            # Count and delete sessions
            session_count = session.query(SessionDB).filter_by(user_id=user_id).count()
            session.query(SessionDB).filter_by(user_id=user_id).delete()

            session.commit()

            return {
                "learning_progress": progress_count,
                "sessions": session_count,
            }

    async def get_category_progress(self, user_id: int) -> dict[str, Any]:  # noqa: ARG002
        """Get progress by category for a user."""
        # TODO: Implement when categories are added to the schema
        return {}

    async def record_question_attempt(
        self,
        user_id: int,
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
        session_id: int | None = None,
    ) -> None:
        """Record a question attempt."""
        # TODO: Implement question attempt recording
        pass

    async def get_performance_metrics(self, user_id: int) -> PerformanceMetrics:
        """Get performance metrics for a user."""
        with self._db_manager.get_session() as session:
            # Get user stats
            user = session.query(UserDB).filter_by(id=user_id).first()
            if not user:
                # Return default metrics for non-existent user
                return PerformanceMetrics(
                    total_cards_studied=0,
                    average_accuracy=0.0,
                    study_streak=0,
                    total_study_time_minutes=0,
                    cards_due_today=0,
                    mastery_percentage=0.0,
                )

            # Get learning progress stats
            progress_query = session.query(LearningProgressDB).filter_by(
                user_id=user_id
            )
            total_cards = progress_query.count()

            # Calculate mastered cards (stability > 30 days)
            mastered_cards = progress_query.filter(
                LearningProgressDB.stability >= 30.0
            ).count()

            # Calculate average accuracy from recent sessions
            recent_sessions = (
                session.query(SessionDB)
                .filter_by(user_id=user_id)
                .order_by(SessionDB.started_at.desc())
                .limit(10)
                .all()
            )

            total_accuracy = 0.0
            session_count = 0
            for sess in recent_sessions:
                if sess.total_questions > 0:
                    accuracy = (sess.correct_answers / sess.total_questions) * 100
                    total_accuracy += accuracy
                    session_count += 1

            average_accuracy = (
                total_accuracy / session_count if session_count > 0 else 0.0
            )

            # Calculate cards due today
            now = datetime.now(UTC)
            cards_due = progress_query.filter(
                LearningProgressDB.next_review <= now
            ).count()

            # Calculate total study time from sessions
            total_time_result = (
                session.query(func.sum(SessionDB.duration_seconds))
                .filter_by(user_id=user_id)
                .scalar()
            )
            total_study_minutes = (total_time_result or 0) // 60

            return PerformanceMetrics(
                total_cards_studied=total_cards,
                average_accuracy=average_accuracy,
                study_streak=user.study_streak,
                total_study_time_minutes=total_study_minutes,
                cards_due_today=cards_due,
                mastery_percentage=(mastered_cards / total_cards * 100)
                if total_cards > 0
                else 0.0,
            )

    async def get_difficulty_distribution(self, user_id: int) -> DifficultyDistribution:
        """Get distribution of card difficulties for a user."""
        with self._db_manager.get_session() as session:
            # Get difficulty counts
            progress_records = (
                session.query(LearningProgressDB).filter_by(user_id=user_id).all()
            )

            easy_count = sum(1 for p in progress_records if p.difficulty >= 2.5)
            medium_count = sum(1 for p in progress_records if 1.5 <= p.difficulty < 2.5)
            hard_count = sum(1 for p in progress_records if p.difficulty < 1.5)

            total = len(progress_records)

            return DifficultyDistribution(
                easy_count=easy_count,
                medium_count=medium_count,
                hard_count=hard_count,
                easy_percentage=(easy_count / total * 100) if total > 0 else 0.0,
                medium_percentage=(medium_count / total * 100) if total > 0 else 0.0,
                hard_percentage=(hard_count / total * 100) if total > 0 else 0.0,
            )

    async def get_performance_insights(self, user_id: int) -> PerformanceInsights:
        """Get AI-generated performance insights."""
        # For now, return basic insights based on metrics
        metrics = await self.get_performance_metrics(user_id)

        strengths = []
        weaknesses = []
        recommendations = []

        # Analyze performance
        if metrics.average_accuracy >= 80:
            strengths.append("High accuracy rate in recent sessions")
        else:
            weaknesses.append("Accuracy below target level")
            recommendations.append("Review incorrect answers more carefully")

        if metrics.study_streak >= 7:
            strengths.append(
                f"Consistent study habit ({metrics.study_streak} day streak)"
            )
        else:
            weaknesses.append("Irregular study pattern")
            recommendations.append("Try to study daily for better retention")

        if metrics.mastery_percentage >= 50:
            strengths.append(f"{metrics.mastery_percentage:.0f}% of cards mastered")
        else:
            recommendations.append(
                "Focus on mastering more cards through consistent review"
            )

        if metrics.cards_due_today > 20:
            weaknesses.append(f"{metrics.cards_due_today} cards overdue for review")
            recommendations.append("Clear your backlog of due cards")

        # Default recommendations if none generated
        if not recommendations:
            recommendations.append("Keep up the great work!")

        return PerformanceInsights(
            strengths=strengths or ["Building knowledge steadily"],
            weaknesses=weaknesses or ["No major weaknesses identified"],
            recommendations=recommendations,
            focus_areas=[],  # TODO: Implement category-based focus areas
        )

    async def record_study_session(
        self,
        user_id: int,
        duration_minutes: int,
        cards_studied: int,
        accuracy: float,
    ) -> None:
        """Record a study session for analytics."""
        # This is typically handled by the session repository
        # But we can add analytics-specific recording here if needed
        pass

    async def get_learning_velocity(self, user_id: int, days: int = 30) -> float:
        """Calculate learning velocity (cards mastered per day)."""
        with self._db_manager.get_session() as session:
            # Get cards mastered in the last N days
            cutoff_date = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Count cards that reached mastery (stability >= 30) in the period
            mastered_count = (
                session.query(LearningProgressDB)
                .filter(
                    and_(
                        LearningProgressDB.user_id == user_id,
                        LearningProgressDB.stability >= 30.0,
                        LearningProgressDB.last_reviewed >= cutoff_date,
                    )
                )
                .count()
            )

            return mastered_count / days if days > 0 else 0.0

    async def get_category_performance(
        self,
        user_id: int,  # noqa: ARG002
    ) -> dict[str, tuple[int, float]]:
        """Get performance by category."""
        # TODO: Implement when categories are added to the schema
        return {}
