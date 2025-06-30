"""Query for getting comprehensive learning statistics following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.domain.analytics.services.analyze_performance import (
    LearningInsights,
    ProgressAnalytics,
)
from src.domain.shared.repositories import AnalyticsRepository

logger = logging.getLogger(__name__)


@dataclass
class GetLearningStatsQuery:
    """Query to get comprehensive learning statistics for a user."""

    user_id: int = 1
    include_category_breakdown: bool = True
    include_forecasts: bool = True


@dataclass
class GetLearningStatsResult:
    """Result of getting learning statistics."""

    success: bool
    insights: LearningInsights | None = None
    category_progress: dict[str, dict[str, Any]] | None = None
    error_message: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


class GetLearningStatsQueryHandler:
    """Query handler for getting comprehensive learning statistics.

    Follows CQRS pattern with direct repository access for read operations.
    """

    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize with analytics repository."""
        self.analytics_repository = analytics_repository

    async def handle(self, query: GetLearningStatsQuery) -> GetLearningStatsResult:
        """Handle the query to get learning statistics.

        Args:
            query: GetLearningStatsQuery with user parameters

        Returns:
            GetLearningStatsResult with comprehensive analytics data
        """
        try:
            logger.info(f"Getting learning stats for user {query.user_id}")

            # Initialize analytics service with repository
            progress_analytics = ProgressAnalytics(
                analytics_repository=self.analytics_repository
            )

            # Get comprehensive insights using domain analytics service
            insights = await progress_analytics.get_learning_insights(
                user_id=query.user_id
            )

            # Get category progress if requested
            category_progress = None
            if query.include_category_breakdown:
                try:
                    category_progress = (
                        await self.analytics_repository.get_category_progress(
                            user_id=query.user_id
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to get category progress: {e}")
                    category_progress = {}

            return GetLearningStatsResult(
                success=True,
                insights=insights,
                category_progress=category_progress,
            )

        except Exception as e:
            logger.error(f"Error getting learning statistics: {e}")
            return GetLearningStatsResult(
                success=False,
                error_message=f"Failed to get learning statistics: {e}",
            )
