"""Query for getting FSRS-specific analytics following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.domain.shared.repositories import AnalyticsRepository

logger = logging.getLogger(__name__)


@dataclass
class FSRSCardStateDistribution:
    """Distribution of FSRS card states."""

    new_cards: int = 0
    learning_cards: int = 0
    review_cards: int = 0
    relearning_cards: int = 0
    total_cards: int = 0

    @property
    def mastery_percentage(self) -> float:
        """Percentage of cards in review state (mastered)."""
        if self.total_cards == 0:
            return 0.0
        return (self.review_cards / self.total_cards) * 100


@dataclass
class FSRSStabilityAnalysis:
    """Analysis of card stability distribution."""

    cards_below_7_days: int = 0
    cards_7_to_30_days: int = 0
    cards_30_to_90_days: int = 0
    cards_above_90_days: int = 0
    average_stability: float = 0.0
    median_stability: float = 0.0


@dataclass
class FSRSRetrievabilityAnalysis:
    """Analysis of card retrievability distribution."""

    cards_below_80_percent: int = 0
    cards_80_to_90_percent: int = 0
    cards_above_90_percent: int = 0
    average_retrievability: float = 0.0
    due_for_review_today: int = 0


@dataclass
class FSRSLeechAnalysis:
    """Analysis of leech cards (difficult questions)."""

    total_leeches: int = 0
    leeches_by_category: dict[str, int] = field(default_factory=dict)
    average_lapses: float = 0.0
    most_difficult_questions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FSRSPerformanceTrends:
    """FSRS performance trends over time."""

    retention_rate_7_days: float = 0.0
    retention_rate_30_days: float = 0.0
    average_interval_growth: float = 0.0
    cards_graduated_last_week: int = 0
    cards_graduated_last_month: int = 0


@dataclass
class GetFSRSAnalyticsQuery:
    """Query to get FSRS-specific analytics for deep learning insights."""

    user_id: int = 1
    include_stability_analysis: bool = True
    include_retrievability_analysis: bool = True
    include_leech_analysis: bool = True
    include_performance_trends: bool = True
    federal_state_filter: str | None = None


@dataclass
class GetFSRSAnalyticsResult:
    """Result of getting FSRS analytics."""

    success: bool
    card_state_distribution: FSRSCardStateDistribution | None = None
    stability_analysis: FSRSStabilityAnalysis | None = None
    retrievability_analysis: FSRSRetrievabilityAnalysis | None = None
    leech_analysis: FSRSLeechAnalysis | None = None
    performance_trends: FSRSPerformanceTrends | None = None
    error_message: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


class GetFSRSAnalyticsQueryHandler:
    """Query handler for FSRS-specific analytics.

    Follows CQRS pattern with direct repository access for read operations.
    Provides deep insights into FSRS algorithm performance and card states.
    """

    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize with analytics repository."""
        self.analytics_repository = analytics_repository

    async def handle(self, query: GetFSRSAnalyticsQuery) -> GetFSRSAnalyticsResult:
        """Handle the query to get FSRS analytics.

        Args:
            query: GetFSRSAnalyticsQuery with analysis parameters

        Returns:
            GetFSRSAnalyticsResult with FSRS-specific insights
        """
        try:
            logger.info(f"Getting FSRS analytics for user {query.user_id}")

            # Get card state distribution
            card_distribution = await self._get_card_state_distribution(query.user_id)

            # Get detailed analyses based on query parameters
            stability_analysis = None
            if query.include_stability_analysis:
                stability_analysis = await self._get_stability_analysis(query.user_id)

            retrievability_analysis = None
            if query.include_retrievability_analysis:
                retrievability_analysis = await self._get_retrievability_analysis(
                    query.user_id
                )

            leech_analysis = None
            if query.include_leech_analysis:
                leech_analysis = await self._get_leech_analysis(query.user_id)

            performance_trends = None
            if query.include_performance_trends:
                performance_trends = await self._get_performance_trends(query.user_id)

            return GetFSRSAnalyticsResult(
                success=True,
                card_state_distribution=card_distribution,
                stability_analysis=stability_analysis,
                retrievability_analysis=retrievability_analysis,
                leech_analysis=leech_analysis,
                performance_trends=performance_trends,
            )

        except Exception as e:
            logger.error(f"Error getting FSRS analytics: {e}")
            return GetFSRSAnalyticsResult(
                success=False,
                error_message=f"Failed to get FSRS analytics: {e}",
            )

    async def _get_card_state_distribution(
        self, user_id: int
    ) -> FSRSCardStateDistribution:
        """Get distribution of card states."""
        try:
            # Get FSRS statistics from repository
            fsrs_stats = await self.analytics_repository.get_fsrs_card_statistics(
                user_id
            )

            return FSRSCardStateDistribution(
                new_cards=fsrs_stats.get("new_cards", 0),
                learning_cards=fsrs_stats.get("learning_cards", 0),
                review_cards=fsrs_stats.get("review_cards", 0),
                relearning_cards=fsrs_stats.get("relearning_cards", 0),
                total_cards=fsrs_stats.get("total_cards", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to get card state distribution: {e}")
            return FSRSCardStateDistribution()

    async def _get_stability_analysis(self, user_id: int) -> FSRSStabilityAnalysis:
        """Get stability distribution analysis."""
        try:
            stability_data = await self.analytics_repository.get_stability_distribution(
                user_id
            )

            return FSRSStabilityAnalysis(
                cards_below_7_days=stability_data.get("below_7_days", 0),
                cards_7_to_30_days=stability_data.get("7_to_30_days", 0),
                cards_30_to_90_days=stability_data.get("30_to_90_days", 0),
                cards_above_90_days=stability_data.get("above_90_days", 0),
                average_stability=stability_data.get("average_stability", 0.0),
                median_stability=stability_data.get("median_stability", 0.0),
            )
        except Exception as e:
            logger.warning(f"Failed to get stability analysis: {e}")
            return FSRSStabilityAnalysis()

    async def _get_retrievability_analysis(
        self, user_id: int
    ) -> FSRSRetrievabilityAnalysis:
        """Get retrievability distribution analysis."""
        try:
            retrievability_data = (
                await self.analytics_repository.get_retrievability_distribution(user_id)
            )

            return FSRSRetrievabilityAnalysis(
                cards_below_80_percent=retrievability_data.get("below_80_percent", 0),
                cards_80_to_90_percent=retrievability_data.get("80_to_90_percent", 0),
                cards_above_90_percent=retrievability_data.get("above_90_percent", 0),
                average_retrievability=retrievability_data.get(
                    "average_retrievability", 0.0
                ),
                due_for_review_today=retrievability_data.get("due_today", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to get retrievability analysis: {e}")
            return FSRSRetrievabilityAnalysis()

    async def _get_leech_analysis(self, user_id: int) -> FSRSLeechAnalysis:
        """Get leech card analysis."""
        try:
            leech_data = await self.analytics_repository.get_leech_statistics(user_id)

            return FSRSLeechAnalysis(
                total_leeches=leech_data.get("total_leeches", 0),
                leeches_by_category=leech_data.get("leeches_by_category", {}),
                average_lapses=leech_data.get("average_lapses", 0.0),
                most_difficult_questions=leech_data.get("most_difficult", []),
            )
        except Exception as e:
            logger.warning(f"Failed to get leech analysis: {e}")
            return FSRSLeechAnalysis()

    async def _get_performance_trends(self, user_id: int) -> FSRSPerformanceTrends:
        """Get FSRS performance trends."""
        try:
            trends_data = await self.analytics_repository.get_performance_trends(
                user_id
            )

            return FSRSPerformanceTrends(
                retention_rate_7_days=trends_data.get("retention_7_days", 0.0),
                retention_rate_30_days=trends_data.get("retention_30_days", 0.0),
                average_interval_growth=trends_data.get("interval_growth", 0.0),
                cards_graduated_last_week=trends_data.get("graduated_week", 0),
                cards_graduated_last_month=trends_data.get("graduated_month", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to get performance trends: {e}")
            return FSRSPerformanceTrends()
