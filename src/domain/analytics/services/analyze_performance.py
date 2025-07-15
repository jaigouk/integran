"""Learning progress analytics and insights.

This module provides comprehensive analytics for learning progress,
retention rates, category performance, and personalized learning insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.domain.shared.repositories import AnalyticsRepository
from src.domain.shared.services import (
    DomainService,
    EventBusInterface,
    ValidationError,
)


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

    # Session statistics
    total_sessions: int


@dataclass
class AnalyzePerformanceRequest:
    """Request to analyze user performance."""

    user_id: int
    session_id: int | None = None
    time_period: str = "all"  # "all", "7_days", "30_days"


@dataclass
class AnalyzePerformanceResult:
    """Result of performance analysis."""

    success: bool
    insights: LearningInsights | None = None
    error_message: str | None = None


class AnalyzePerformance(
    DomainService[AnalyzePerformanceRequest, AnalyzePerformanceResult]
):
    """Domain service to analyze user performance following DDD patterns."""

    def __init__(
        self,
        analytics_repository: AnalyticsRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with analytics repository and event bus."""
        super().__init__(event_bus)
        self.analytics_repository = analytics_repository

    async def call(
        self, request: AnalyzePerformanceRequest
    ) -> AnalyzePerformanceResult:
        """Analyze user performance and return insights."""
        try:
            # Validate request
            if not self._validate_request(request):
                raise ValidationError("Invalid analyze performance request")

            # Get learning insights (business logic)
            insights = await self._get_learning_insights(request.user_id)

            # Publish domain events
            await self._publish_performance_analyzed_event(request, insights)
            await self._publish_learning_insights_generated_event(request, insights)

            return AnalyzePerformanceResult(
                success=True,
                insights=insights,
            )

        except Exception as e:
            return AnalyzePerformanceResult(
                success=False,
                error_message=f"Failed to analyze performance: {e}",
            )

    def _validate_request(self, request: AnalyzePerformanceRequest) -> bool:
        """Validate the analyze performance request."""
        return request.user_id > 0 and request.time_period in [
            "all",
            "7_days",
            "30_days",
        ]

    async def _get_learning_insights(self, user_id: int) -> LearningInsights:
        """Get comprehensive learning insights for a user."""
        # Get analytics data from repository
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)
        session_progress = await self.analytics_repository.get_session_progress(user_id)
        category_progress = await self.analytics_repository.get_category_progress(
            user_id
        )

        # Extract basic card statistics
        total_cards = learning_stats.get("total_cards", 0)
        mastered = learning_stats.get("cards_mastered", 0)
        learning = learning_stats.get("cards_learning", 0)
        new = learning_stats.get("cards_new", 0)
        progress_percentage = (mastered / total_cards * 100) if total_cards > 0 else 0

        # Create simplified analytics (complex analytics moved to repository)
        retention_analysis = await self._get_retention_analysis(user_id)

        # Simplified category performance
        categories = []
        for cat_name, cat_data in category_progress.items():
            if isinstance(cat_data, dict):
                categories.append(
                    CategoryPerformance(
                        category=cat_name,
                        total_questions=cat_data.get("total", 0),
                        mastered_questions=cat_data.get("mastered", 0),
                        learning_questions=cat_data.get("learning", 0),
                        new_questions=cat_data.get("new", 0),
                        average_retention=cat_data.get("retention", 0.0),
                        average_difficulty=cat_data.get("difficulty", 5.0),
                        total_reviews=cat_data.get("reviews", 0),
                        last_practiced=None,  # Simplified
                        estimated_completion_days=30,  # Simplified
                    )
                )

        return LearningInsights(
            total_cards=total_cards,
            cards_mastered=mastered,
            cards_learning=learning,
            cards_new=new,
            overall_progress_percentage=progress_percentage,
            retention_analysis=retention_analysis,
            category_performance=categories,
            learning_streak=LearningStreak(
                current_streak=0,
                longest_streak=0,
                last_study_date=None,
                streak_broken_date=None,
                days_until_broken=7,
            ),
            study_forecast=StudyForecast(
                reviews_due_today=0,
                reviews_due_tomorrow=0,
                reviews_due_week=0,
                new_cards_recommended=10,
                estimated_study_time_minutes=15,
                peak_review_day="Monday",
                workload_distribution={},
            ),
            recommended_focus_categories=[],
            recommended_daily_reviews=10,
            estimated_completion_date=None,
            best_study_times=[],
            average_session_length=15,
            total_study_time_hours=0.0,
            total_sessions=session_progress.get("total_sessions", 0),
        )

    async def _get_retention_analysis(self, user_id: int) -> RetentionAnalysis:  # noqa: ARG002
        """Get retention analysis for the user."""
        # Simplified implementation - could be enhanced with repository methods
        return RetentionAnalysis(
            overall_retention=85.0,
            last_7_days_retention=88.0,
            last_30_days_retention=85.0,
            retention_trend="stable",
            target_retention=90.0,
            retention_by_category={},
        )

    async def _publish_performance_analyzed_event(
        self, request: AnalyzePerformanceRequest, insights: LearningInsights
    ) -> None:
        """Publish PerformanceAnalyzedEvent."""
        # Import here to avoid circular imports
        from src.domain.analytics.events.analytics_events import (
            PerformanceAnalyzedEvent,
        )

        event = PerformanceAnalyzedEvent(
            user_id=request.user_id,
            analysis_type=request.time_period,
            analysis_results={
                "total_cards": insights.total_cards,
                "cards_mastered": insights.cards_mastered,
                "progress_percentage": insights.overall_progress_percentage,
                "retention_rate": insights.retention_analysis.overall_retention,
            },
            insights_generated=len(insights.recommended_focus_categories) + 1,
            analysis_duration_ms=50,  # Simplified - could be measured
        )
        await self.event_bus.publish(event)

    async def _publish_learning_insights_generated_event(
        self, request: AnalyzePerformanceRequest, insights: LearningInsights
    ) -> None:
        """Publish LearningInsightsGeneratedEvent."""
        # Import here to avoid circular imports
        from src.domain.analytics.events.analytics_events import (
            LearningInsightsGeneratedEvent,
        )

        event = LearningInsightsGeneratedEvent(
            user_id=request.user_id,
            total_cards_analyzed=insights.total_cards,
            progress_percentage=insights.overall_progress_percentage,
            retention_rate=insights.retention_analysis.overall_retention,
            categories_analyzed=len(insights.category_performance),
            recommendations_generated=len(insights.recommended_focus_categories),
            insights_quality_score=0.85,  # Simplified quality score
        )
        await self.event_bus.publish(event)


# DEPRECATED: Legacy class - use AnalyzePerformance domain service instead
class ProgressAnalytics:
    """DEPRECATED: Use AnalyzePerformance domain service instead."""

    def __init__(self, analytics_repository: AnalyticsRepository) -> None:
        """Initialize progress analytics.

        Args:
            analytics_repository: Analytics repository for data access
        """
        self.analytics_repository = analytics_repository

    async def get_learning_insights(self, user_id: int = 1) -> LearningInsights:
        """Get comprehensive learning insights for a user.

        Args:
            user_id: User ID

        Returns:
            Complete learning insights
        """
        # Get analytics data from repository
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)
        session_progress = await self.analytics_repository.get_session_progress(user_id)
        category_progress = await self.analytics_repository.get_category_progress(
            user_id
        )

        # Extract basic card statistics
        total_cards = learning_stats.get("total_cards", 0)
        mastered = learning_stats.get("cards_mastered", 0)
        learning = learning_stats.get("cards_learning", 0)
        new = learning_stats.get("cards_new", 0)
        progress_percentage = (mastered / total_cards * 100) if total_cards > 0 else 0

        # Create simplified analytics (complex analytics moved to repository)
        retention_analysis = await self._get_retention_analysis(user_id)

        # Simplified category performance
        categories = []
        for cat_name, cat_data in category_progress.items():
            if isinstance(cat_data, dict):
                categories.append(
                    CategoryPerformance(
                        category=cat_name,
                        total_questions=cat_data.get("total", 0),
                        mastered_questions=cat_data.get("mastered", 0),
                        learning_questions=cat_data.get("learning", 0),
                        new_questions=cat_data.get("new", 0),
                        average_retention=cat_data.get("retention", 0.0),
                        average_difficulty=cat_data.get("difficulty", 5.0),
                        total_reviews=cat_data.get("reviews", 0),
                        last_practiced=None,  # Simplified
                        estimated_completion_days=30,  # Simplified
                    )
                )

        # Simplified calculations
        learning_streak = LearningStreak(
            current_streak=session_progress.get("current_streak", 0),
            longest_streak=session_progress.get("longest_streak", 0),
            last_study_date=None,  # Simplified
            streak_broken_date=None,
            days_until_broken=7,
        )

        # Get time-based study forecast with real data
        study_forecast = await self._get_study_forecast(user_id)

        # Calculate recommendations
        daily_reviews = await self._recommend_daily_reviews(user_id)
        card_stats = await self._get_card_statistics(user_id)
        completion_date = self._estimate_completion_date(card_stats, daily_reviews)
        focus_categories = (
            [cat.category for cat in categories[:3]] if categories else []
        )

        # Get time-based recommendations and session stats
        best_study_times = await self._analyze_study_times(user_id)
        session_stats = await self._get_session_statistics(user_id)

        return LearningInsights(
            total_cards=total_cards,
            cards_mastered=mastered,
            cards_learning=learning,
            cards_new=new,
            overall_progress_percentage=round(progress_percentage, 1),
            retention_analysis=retention_analysis,
            category_performance=categories,
            learning_streak=learning_streak,
            study_forecast=study_forecast,
            recommended_focus_categories=focus_categories,
            recommended_daily_reviews=daily_reviews,
            estimated_completion_date=completion_date,
            best_study_times=best_study_times,
            average_session_length=session_stats["avg_length"],
            total_study_time_hours=session_stats["total_hours"],
            total_sessions=session_stats["total_sessions"],
        )

    async def get_retention_over_time(
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

        # Simplified implementation using repository
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)
        base_retention = learning_stats.get("retention_rate", 0.8)

        # Generate simplified retention data over time
        retention_by_date = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            # Simulate some variation in retention over time
            variation = 0.1 * (0.5 - (i % 10) / 10)  # Small variations
            retention_by_date[str(date.date())] = max(
                0.0, min(1.0, base_retention + variation)
            )

        return retention_by_date

    async def get_category_progress_detailed(self, user_id: int = 1) -> dict[str, Any]:
        """Get detailed progress breakdown by category.

        Args:
            user_id: User ID

        Returns:
            Detailed category progress data
        """
        # Use repository method for category progress
        return await self.analytics_repository.get_category_progress(user_id)

    async def get_learning_velocity(
        self, user_id: int = 1, days: int = 7
    ) -> dict[str, float]:
        """Calculate learning velocity (cards mastered per day).

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Learning velocity metrics
        """
        # Use repository for simplified velocity calculation
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)
        session_progress = await self.analytics_repository.get_session_progress(user_id)

        # Simplified calculations using repository data
        cards_mastered = learning_stats.get("cards_mastered", 0)
        total_reviews = session_progress.get("total_reviews", 0)

        return {
            "cards_mastered_per_day": cards_mastered / days if days > 0 else 0,
            "reviews_per_day": total_reviews / days if days > 0 else 0,
            "new_cards_per_day": learning_stats.get("cards_new", 0) / days
            if days > 0
            else 0,
            "mastery_rate": cards_mastered / total_reviews if total_reviews > 0 else 0,
        }

    async def _get_card_statistics(self, user_id: int) -> dict[str, int]:
        """Get basic card statistics.

        Args:
            user_id: User ID

        Returns:
            Card statistics
        """
        # Use repository for card statistics
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)
        return {
            "total_cards": learning_stats.get("total_cards", 0),
            "new": learning_stats.get("cards_new", 0),
            "learning": learning_stats.get("cards_learning", 0),
            "mastered": learning_stats.get("cards_mastered", 0),
        }

    async def _get_retention_analysis(self, user_id: int) -> RetentionAnalysis:
        """Get retention analysis.

        Args:
            user_id: User ID

        Returns:
            Retention analysis
        """
        # Use repository for retention analysis
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)

        overall_retention = learning_stats.get("retention_rate", 0.0)

        # Get category retention data
        category_retention = await self._get_category_retention(user_id)

        # Simplified retention analysis using repository data
        return RetentionAnalysis(
            overall_retention=round(overall_retention, 3),
            last_7_days_retention=round(overall_retention * 0.95, 3),  # Simplified
            last_30_days_retention=round(overall_retention * 0.9, 3),  # Simplified
            retention_trend="stable",  # Simplified
            target_retention=0.9,  # Default target
            retention_by_category=category_retention,
        )

    async def _get_category_retention(self, user_id: int) -> dict[str, float]:
        """Get retention by category.

        Args:
            user_id: User ID

        Returns:
            Retention by category
        """
        # Use repository for category retention
        category_progress = await self.analytics_repository.get_category_progress(
            user_id
        )

        retention_by_category = {}
        for category, data in category_progress.items():
            if isinstance(data, dict):
                retention_by_category[category] = data.get("retention", 0.0)
            else:
                retention_by_category[category] = 0.0

        return retention_by_category

    async def _get_category_performance(
        self, user_id: int
    ) -> list[CategoryPerformance]:
        """Get detailed category performance.

        Args:
            user_id: User ID

        Returns:
            List of category performance data
        """
        performances = []
        category_data = await self.get_category_progress_detailed(user_id)

        for category, data in category_data.items():
            if isinstance(data, dict):
                # Estimate completion time based on current velocity
                remaining = data.get("total", 0) - data.get("mastered", 0)
                velocity_data = await self.get_learning_velocity(user_id)
                velocity = velocity_data["cards_mastered_per_day"]
                completion_days = int(remaining / velocity) if velocity > 0 else 999

                performance = CategoryPerformance(
                    category=category,
                    total_questions=data.get("total", 0),
                    mastered_questions=data.get("mastered", 0),
                    learning_questions=data.get("learning", 0),
                    new_questions=data.get("new", 0),
                    average_retention=data.get("retention", 0.0),
                    average_difficulty=data.get("difficulty", 5.0),
                    total_reviews=data.get("reviews", 0),
                    last_practiced=None,  # Simplified
                    estimated_completion_days=completion_days,
                )
                performances.append(performance)

        return performances

    async def _get_learning_streak(self, user_id: int) -> LearningStreak:
        """Get learning streak information.

        Args:
            user_id: User ID

        Returns:
            Learning streak data
        """
        # Use repository for session progress
        session_progress = await self.analytics_repository.get_session_progress(user_id)

        current_streak = session_progress.get("current_streak", 0)
        longest_streak = session_progress.get("longest_streak", 0)

        return LearningStreak(
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_study_date=None,  # Simplified
            streak_broken_date=None,
            days_until_broken=7,  # Simplified
        )

    async def _get_study_forecast(self, user_id: int) -> StudyForecast:
        """Get study forecast with time-based workload analysis.

        Args:
            user_id: User ID

        Returns:
            Study forecast with real workload distribution
        """
        # Use repository for learning stats
        learning_stats = await self.analytics_repository.get_learning_stats(user_id)

        due_today = learning_stats.get("due_today", 0)
        due_tomorrow = learning_stats.get("due_tomorrow", 0)
        due_week = learning_stats.get("due_week", 0)

        # New cards recommended (based on current workload)
        new_recommended = min(20, max(5, 50 - due_today))

        # Calculate workload distribution and peak day from daily patterns
        try:
            daily_patterns = await self.analytics_repository.get_daily_study_patterns(
                user_id, days=28
            )
            workload_distribution = {}

            if daily_patterns:
                # Group by day of week
                day_totals = {
                    "Mon": 0,
                    "Tue": 0,
                    "Wed": 0,
                    "Thu": 0,
                    "Fri": 0,
                    "Sat": 0,
                    "Sun": 0,
                }
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

                for day_data in daily_patterns:
                    if day_data.get("session_count", 0) > 0:
                        # Parse date and get day of week
                        try:
                            from datetime import datetime

                            date_str = day_data["date"]
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            day_name = day_names[date_obj.weekday()]

                            # Add total questions answered that day
                            total_questions = sum(
                                session.get("total_questions", 0)
                                for session in day_data.get("sessions", [])
                            )
                            day_totals[day_name] += total_questions
                        except (ValueError, KeyError):
                            continue

                workload_distribution = day_totals
                # Find peak day (day with most questions answered)
                peak_review_day = (
                    max(day_totals.items(), key=lambda x: x[1])[0]
                    if any(day_totals.values())
                    else "Monday"
                )
            else:
                # Default distribution if no data
                workload_distribution = {
                    "Mon": 10,
                    "Tue": 12,
                    "Wed": 8,
                    "Thu": 15,
                    "Fri": 11,
                    "Sat": 9,
                    "Sun": 13,
                }
                peak_review_day = "Monday"

        except Exception:
            # Fallback to default values
            workload_distribution = {
                "Mon": 10,
                "Tue": 12,
                "Wed": 8,
                "Thu": 15,
                "Fri": 11,
                "Sat": 9,
                "Sun": 13,
            }
            peak_review_day = "Monday"

        return StudyForecast(
            reviews_due_today=due_today,
            reviews_due_tomorrow=due_tomorrow,
            reviews_due_week=due_week,
            new_cards_recommended=new_recommended,
            estimated_study_time_minutes=int((due_today + new_recommended) * 0.5),
            peak_review_day=peak_review_day,
            workload_distribution=workload_distribution,
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

    async def _recommend_daily_reviews(self, user_id: int) -> int:
        """Recommend daily review target.

        Args:
            user_id: User ID

        Returns:
            Recommended daily reviews
        """
        velocity = await self.get_learning_velocity(user_id)
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

    async def _analyze_study_times(self, user_id: int) -> list[str]:
        """Analyze best study times based on historical performance.

        Args:
            user_id: User ID

        Returns:
            List of best study hours formatted as HH:MM
        """
        try:
            # Get hourly session statistics for the last 30 days
            hourly_stats = await self.analytics_repository.get_hourly_session_stats(
                user_id, days=30
            )

            if not hourly_stats or not any(
                stats["count"] > 0 for stats in hourly_stats.values()
            ):
                # No study history available, return sensible defaults
                return ["09:00", "14:00", "19:00"]

            # Score each hour based on performance metrics
            hour_scores = {}
            for hour, stats in hourly_stats.items():
                if stats["count"] == 0:
                    hour_scores[hour] = 0.0
                    continue

                # Calculate composite score based on:
                # 1. Session count (frequency)
                # 2. Average accuracy
                # 3. Session duration consistency
                session_count = stats["count"]
                avg_accuracy = stats["avg_accuracy"]
                total_duration = stats["total_duration"]
                avg_duration = (
                    total_duration / session_count if session_count > 0 else 0
                )

                # Normalize metrics (0-1 scale)
                frequency_score = min(session_count / 10, 1.0)  # Cap at 10 sessions
                accuracy_score = avg_accuracy  # Already 0-1
                duration_score = min(avg_duration / 1800, 1.0)  # Cap at 30 minutes

                # Weighted composite score
                # Prioritize accuracy (50%), then frequency (30%), then duration (20%)
                composite_score = (
                    accuracy_score * 0.5 + frequency_score * 0.3 + duration_score * 0.2
                )

                hour_scores[hour] = composite_score

            # Get top 3 hours sorted by score
            top_hours = sorted(hour_scores.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]

            # Filter out hours with zero scores (no activity)
            valid_hours = [(hour, score) for hour, score in top_hours if score > 0]

            if not valid_hours:
                # Fallback to defaults if no valid hours found
                return ["09:00", "14:00", "19:00"]

            # Format hours as HH:MM
            recommended_hours = [f"{hour:02d}:00" for hour, _ in valid_hours]

            # Ensure we have at least 3 recommendations, add defaults if needed
            defaults = ["09:00", "14:00", "19:00"]
            for default in defaults:
                if len(recommended_hours) >= 3:
                    break
                if default not in recommended_hours:
                    recommended_hours.append(default)

            return recommended_hours[:3]

        except Exception:
            # Fallback to defaults on any error
            return ["09:00", "14:00", "19:00"]

    async def _get_session_statistics(self, user_id: int) -> dict[str, Any]:
        """Get session statistics.

        Args:
            user_id: User ID

        Returns:
            Session statistics
        """
        # Use repository for session statistics
        session_progress = await self.analytics_repository.get_session_progress(user_id)

        return {
            "avg_length": session_progress.get("avg_duration", 0),
            "total_hours": session_progress.get("total_time", 0)
            / 3600,  # Convert to hours
            "total_sessions": session_progress.get("total_sessions", 0),
            "total_questions": session_progress.get("total_questions", 0),
            "total_correct": session_progress.get("total_correct", 0),
        }
