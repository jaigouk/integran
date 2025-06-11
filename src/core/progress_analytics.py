"""Learning progress analytics and insights.

This module provides comprehensive analytics for learning progress,
retention rates, category performance, and personalized learning insights.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import DatabaseManager
from src.core.models import FSRSCard, LearningSession, ReviewHistory


@dataclass
class CategoryPerformance:
    """Performance statistics for a category."""

    category: str
    total_questions: int
    mastered_questions: int
    learning_questions: int
    new_questions: int
    average_retention: float
    average_difficulty: float
    total_reviews: int
    last_practiced: datetime | None
    estimated_completion_days: int


@dataclass
class LearningStreak:
    """Learning streak information."""

    current_streak: int
    longest_streak: int
    last_study_date: datetime | None
    streak_broken_date: datetime | None
    days_until_broken: int  # Days until streak breaks if no practice


@dataclass
class RetentionAnalysis:
    """Retention rate analysis over time."""

    overall_retention: float
    last_7_days_retention: float
    last_30_days_retention: float
    retention_trend: str  # "improving", "stable", "declining"
    target_retention: float
    retention_by_category: dict[str, float]


@dataclass
class StudyForecast:
    """Forecast of upcoming study requirements."""

    reviews_due_today: int
    reviews_due_tomorrow: int
    reviews_due_week: int
    new_cards_recommended: int
    estimated_study_time_minutes: int
    peak_review_day: str  # Day of week with most reviews
    workload_distribution: dict[str, int]  # Next 7 days


@dataclass
class LearningInsights:
    """Comprehensive learning insights and recommendations."""

    total_cards: int
    cards_mastered: int
    cards_learning: int
    cards_new: int
    overall_progress_percentage: float

    retention_analysis: RetentionAnalysis
    category_performance: list[CategoryPerformance]
    learning_streak: LearningStreak
    study_forecast: StudyForecast

    # Personalized recommendations
    recommended_focus_categories: list[str]
    recommended_daily_reviews: int
    estimated_completion_date: datetime | None

    # Time-based insights
    best_study_times: list[str]  # Hours of day with best performance
    average_session_length: int  # Minutes
    total_study_time_hours: float


class ProgressAnalytics:
    """Comprehensive learning progress analytics engine."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize progress analytics.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def get_learning_insights(self, user_id: int = 1) -> LearningInsights:
        """Get comprehensive learning insights for a user.

        Args:
            user_id: User ID

        Returns:
            Complete learning insights
        """
        # Get basic card statistics
        card_stats = self._get_card_statistics(user_id)

        # Calculate overall progress
        total_cards = card_stats["total_cards"]
        mastered = card_stats["mastered"]
        progress_percentage = (mastered / total_cards * 100) if total_cards > 0 else 0

        # Get detailed analytics
        retention_analysis = self._get_retention_analysis(user_id)
        category_performance = self._get_category_performance(user_id)
        learning_streak = self._get_learning_streak(user_id)
        study_forecast = self._get_study_forecast(user_id)

        # Generate recommendations
        focus_categories = self._recommend_focus_categories(category_performance)
        daily_reviews = self._recommend_daily_reviews(user_id)
        completion_date = self._estimate_completion_date(card_stats, daily_reviews)

        # Get time-based insights
        study_times = self._analyze_study_times(user_id)
        session_stats = self._get_session_statistics(user_id)

        return LearningInsights(
            total_cards=total_cards,
            cards_mastered=mastered,
            cards_learning=card_stats["learning"],
            cards_new=card_stats["new"],
            overall_progress_percentage=round(progress_percentage, 1),
            retention_analysis=retention_analysis,
            category_performance=category_performance,
            learning_streak=learning_streak,
            study_forecast=study_forecast,
            recommended_focus_categories=focus_categories,
            recommended_daily_reviews=daily_reviews,
            estimated_completion_date=completion_date,
            best_study_times=study_times,
            average_session_length=session_stats["avg_length"],
            total_study_time_hours=session_stats["total_hours"],
        )

    def get_retention_over_time(
        self, user_id: int = 1, days: int = 30
    ) -> dict[str, float]:
        """Get retention rate over time.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Dictionary of date -> retention rate
        """
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        retention_by_date = {}

        with self.db_manager.get_session() as session:
            # Get reviews in date range
            reviews = (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    ReviewHistory.review_date >= start_date.timestamp(),
                    ReviewHistory.review_date <= end_date.timestamp(),
                )
                .all()
            )

            # Group by date
            reviews_by_date = defaultdict(list)
            for review in reviews:
                review_date = datetime.fromtimestamp(review.review_date, UTC).date()
                reviews_by_date[str(review_date)].append(review)

            # Calculate daily retention
            for date_str, day_reviews in reviews_by_date.items():
                if day_reviews:
                    successful = sum(1 for r in day_reviews if r.rating >= 3)
                    retention_by_date[date_str] = successful / len(day_reviews)
                else:
                    retention_by_date[date_str] = 0.0

        return retention_by_date

    def get_category_progress_detailed(self, user_id: int = 1) -> dict[str, Any]:
        """Get detailed progress breakdown by category.

        Args:
            user_id: User ID

        Returns:
            Detailed category progress data
        """
        category_data = {}

        with self.db_manager.get_session() as session:
            # Get all categories
            from src.core.models import Question

            categories = session.query(Question.category).distinct().all()

            for (category,) in categories:
                # Get cards for this category
                cards = (
                    session.query(FSRSCard)
                    .join(Question)
                    .filter(FSRSCard.user_id == user_id, Question.category == category)
                    .all()
                )

                if not cards:
                    continue

                # Calculate statistics
                total = len(cards)
                new = sum(1 for c in cards if c.review_count == 0)
                learning = sum(1 for c in cards if 0 < c.review_count < 5)
                mastered = sum(1 for c in cards if c.review_count >= 5)

                avg_difficulty = sum(c.difficulty for c in cards) / total
                avg_stability = sum(c.stability for c in cards) / total

                # Get recent reviews for retention
                recent_reviews = (
                    session.query(ReviewHistory)
                    .join(FSRSCard)
                    .join(Question)
                    .filter(
                        FSRSCard.user_id == user_id,
                        Question.category == category,
                        ReviewHistory.review_date
                        >= (datetime.now(UTC) - timedelta(days=30)).timestamp(),
                    )
                    .all()
                )

                retention = 0.0
                if recent_reviews:
                    successful = sum(1 for r in recent_reviews if r.rating >= 3)
                    retention = successful / len(recent_reviews)

                category_data[category] = {
                    "total_cards": total,
                    "new": new,
                    "learning": learning,
                    "mastered": mastered,
                    "progress_percentage": round(mastered / total * 100, 1),
                    "average_difficulty": round(avg_difficulty, 1),
                    "average_stability": round(avg_stability, 1),
                    "retention_rate": round(retention, 3),
                    "recent_reviews": len(recent_reviews),
                }

        return category_data

    def get_learning_velocity(
        self, user_id: int = 1, days: int = 7
    ) -> dict[str, float]:
        """Calculate learning velocity (cards mastered per day).

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Learning velocity metrics
        """
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        with self.db_manager.get_session() as session:
            # Get cards that became mastered in the period
            cards_mastered = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.review_count >= 5,
                    FSRSCard.updated_at >= start_date.timestamp(),
                )
                .count()
            )

            # Get total reviews in period
            total_reviews = (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    ReviewHistory.review_date >= start_date.timestamp(),
                )
                .count()
            )

            # Get new cards started
            new_cards_started = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.review_count > 0,
                    FSRSCard.created_at >= start_date.timestamp(),
                )
                .count()
            )

        return {
            "cards_mastered_per_day": cards_mastered / days,
            "reviews_per_day": total_reviews / days,
            "new_cards_per_day": new_cards_started / days,
            "mastery_rate": cards_mastered / total_reviews if total_reviews > 0 else 0,
        }

    def _get_card_statistics(self, user_id: int) -> dict[str, int]:
        """Get basic card statistics.

        Args:
            user_id: User ID

        Returns:
            Card statistics
        """
        with self.db_manager.get_session() as session:
            cards = session.query(FSRSCard).filter_by(user_id=user_id).all()

            total = len(cards)
            new = sum(1 for c in cards if c.review_count == 0)
            learning = sum(1 for c in cards if 0 < c.review_count < 5)
            mastered = sum(1 for c in cards if c.review_count >= 5)

            return {
                "total_cards": total,
                "new": new,
                "learning": learning,
                "mastered": mastered,
            }

    def _get_retention_analysis(self, user_id: int) -> RetentionAnalysis:
        """Get retention analysis.

        Args:
            user_id: User ID

        Returns:
            Retention analysis
        """
        now = datetime.now(UTC)

        with self.db_manager.get_session() as session:
            # Overall retention
            all_reviews = (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(FSRSCard.user_id == user_id)
                .all()
            )

            overall_retention = 0.0
            if all_reviews:
                successful = sum(1 for r in all_reviews if r.rating >= 3)
                overall_retention = successful / len(all_reviews)

            # Last 7 days
            week_ago = now - timedelta(days=7)
            week_reviews = [
                r for r in all_reviews if r.review_date >= week_ago.timestamp()
            ]
            week_retention = 0.0
            if week_reviews:
                successful = sum(1 for r in week_reviews if r.rating >= 3)
                week_retention = successful / len(week_reviews)

            # Last 30 days
            month_ago = now - timedelta(days=30)
            month_reviews = [
                r for r in all_reviews if r.review_date >= month_ago.timestamp()
            ]
            month_retention = 0.0
            if month_reviews:
                successful = sum(1 for r in month_reviews if r.rating >= 3)
                month_retention = successful / len(month_reviews)

            # Determine trend
            trend = "stable"
            if week_retention > month_retention + 0.05:
                trend = "improving"
            elif week_retention < month_retention - 0.05:
                trend = "declining"

            # Get target retention from config
            config = self.db_manager.get_algorithm_config(user_id)
            target = config.target_retention if config else 0.9

            return RetentionAnalysis(
                overall_retention=round(overall_retention, 3),
                last_7_days_retention=round(week_retention, 3),
                last_30_days_retention=round(month_retention, 3),
                retention_trend=trend,
                target_retention=target,
                retention_by_category=self._get_category_retention(user_id),
            )

    def _get_category_retention(self, user_id: int) -> dict[str, float]:
        """Get retention by category.

        Args:
            user_id: User ID

        Returns:
            Retention by category
        """
        retention_by_category = {}

        with self.db_manager.get_session() as session:
            from src.core.models import Question

            categories = session.query(Question.category).distinct().all()

            for (category,) in categories:
                reviews = (
                    session.query(ReviewHistory)
                    .join(FSRSCard)
                    .join(Question)
                    .filter(
                        FSRSCard.user_id == user_id,
                        Question.category == category,
                    )
                    .all()
                )

                if reviews:
                    successful = sum(1 for r in reviews if r.rating >= 3)
                    retention_by_category[category] = round(
                        successful / len(reviews), 3
                    )
                else:
                    retention_by_category[category] = 0.0

        return retention_by_category

    def _get_category_performance(self, user_id: int) -> list[CategoryPerformance]:
        """Get detailed category performance.

        Args:
            user_id: User ID

        Returns:
            List of category performance data
        """
        performances = []
        category_data = self.get_category_progress_detailed(user_id)

        for category, data in category_data.items():
            # Estimate completion time based on current velocity
            remaining = data["total_cards"] - data["mastered"]
            velocity = self.get_learning_velocity(user_id)["cards_mastered_per_day"]
            completion_days = int(remaining / velocity) if velocity > 0 else 999

            performance = CategoryPerformance(
                category=category,
                total_questions=data["total_cards"],
                mastered_questions=data["mastered"],
                learning_questions=data["learning"],
                new_questions=data["new"],
                average_retention=data["retention_rate"],
                average_difficulty=data["average_difficulty"],
                total_reviews=data["recent_reviews"],
                last_practiced=None,  # TODO: Implement
                estimated_completion_days=completion_days,
            )
            performances.append(performance)

        return performances

    def _get_learning_streak(self, user_id: int) -> LearningStreak:
        """Get learning streak information.

        Args:
            user_id: User ID

        Returns:
            Learning streak data
        """
        with self.db_manager.get_session() as session:
            # Get all learning sessions ordered by date
            sessions = (
                session.query(LearningSession)
                .filter_by(user_id=user_id)
                .order_by(LearningSession.start_time.desc())
                .all()
            )

            if not sessions:
                return LearningStreak(
                    current_streak=0,
                    longest_streak=0,
                    last_study_date=None,
                    streak_broken_date=None,
                    days_until_broken=1,
                )

            # Calculate current streak
            current_streak = 0
            today = datetime.now(UTC).date()

            for session in sessions:
                session_date = datetime.fromtimestamp(session.start_time, UTC).date()
                day_diff = (today - session_date).days

                if day_diff <= current_streak + 1:
                    current_streak = max(current_streak, day_diff)
                else:
                    break

            # For now, use simple logic
            last_study = (
                datetime.fromtimestamp(sessions[0].start_time, UTC)
                if sessions
                else None
            )

            return LearningStreak(
                current_streak=current_streak,
                longest_streak=current_streak,  # TODO: Calculate actual longest
                last_study_date=last_study,
                streak_broken_date=None,
                days_until_broken=1,
            )

    def _get_study_forecast(self, user_id: int) -> StudyForecast:
        """Get study forecast.

        Args:
            user_id: User ID

        Returns:
            Study forecast
        """
        now = datetime.now(UTC)
        today_end = now.replace(hour=23, minute=59, second=59)
        tomorrow_end = today_end + timedelta(days=1)
        week_end = today_end + timedelta(days=7)

        with self.db_manager.get_session() as session:
            # Due today
            due_today = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.next_review_date <= today_end.timestamp(),
                )
                .count()
            )

            # Due tomorrow
            due_tomorrow = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.next_review_date > today_end.timestamp(),
                    FSRSCard.next_review_date <= tomorrow_end.timestamp(),
                )
                .count()
            )

            # Due this week
            due_week = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.next_review_date <= week_end.timestamp(),
                )
                .count()
            )

            # New cards recommended (based on current workload)
            new_recommended = min(20, max(5, 50 - due_today))

            return StudyForecast(
                reviews_due_today=due_today,
                reviews_due_tomorrow=due_tomorrow,
                reviews_due_week=due_week,
                new_cards_recommended=new_recommended,
                estimated_study_time_minutes=int((due_today + new_recommended) * 0.5),
                peak_review_day="Monday",  # TODO: Calculate from data
                workload_distribution={},  # TODO: Calculate 7-day distribution
            )

    def _recommend_focus_categories(
        self, performances: list[CategoryPerformance]
    ) -> list[str]:
        """Recommend categories to focus on.

        Args:
            performances: Category performance data

        Returns:
            List of recommended focus categories
        """
        # Sort by retention rate (lowest first) and filter those below target
        focus_categories = [
            p.category
            for p in performances
            if p.average_retention < 0.8 and p.learning_questions > 0
        ]

        return sorted(
            focus_categories,
            key=lambda c: next(
                p.average_retention for p in performances if p.category == c
            ),
        )[:3]  # Top 3 categories needing attention

    def _recommend_daily_reviews(self, user_id: int) -> int:
        """Recommend daily review target.

        Args:
            user_id: User ID

        Returns:
            Recommended daily reviews
        """
        velocity = self.get_learning_velocity(user_id)
        current_rate = velocity["reviews_per_day"]

        # Aim for 50% more than current rate, but cap at reasonable limits
        target = int(current_rate * 1.5)
        return max(20, min(100, target))

    def _estimate_completion_date(
        self, card_stats: dict[str, int], daily_reviews: int
    ) -> datetime | None:
        """Estimate completion date.

        Args:
            card_stats: Card statistics
            daily_reviews: Daily review target

        Returns:
            Estimated completion date
        """
        remaining_cards = card_stats["new"] + card_stats["learning"]
        if remaining_cards == 0 or daily_reviews == 0:
            return None

        # Rough estimate: each card needs ~3 reviews to master
        total_reviews_needed = remaining_cards * 3
        days_needed = total_reviews_needed / daily_reviews

        return datetime.now(UTC) + timedelta(days=int(days_needed))

    def _analyze_study_times(self, user_id: int) -> list[str]:  # noqa: ARG002
        """Analyze best study times.

        Args:
            user_id: User ID

        Returns:
            List of best study hours
        """
        # TODO: Implement time-based performance analysis
        return ["09:00", "14:00", "19:00"]  # Default recommendations

    def _get_session_statistics(self, user_id: int) -> dict[str, Any]:
        """Get session statistics.

        Args:
            user_id: User ID

        Returns:
            Session statistics
        """
        with self.db_manager.get_session() as session:
            sessions = (
                session.query(LearningSession)
                .filter_by(user_id=user_id)
                .filter(LearningSession.duration_seconds.isnot(None))
                .all()
            )

            if not sessions:
                return {"avg_length": 0, "total_hours": 0.0}

            total_time = sum(s.duration_seconds for s in sessions)
            avg_length = total_time / len(sessions) / 60  # Minutes
            total_hours = total_time / 3600  # Hours

            return {
                "avg_length": int(avg_length),
                "total_hours": round(total_hours, 1),
            }
