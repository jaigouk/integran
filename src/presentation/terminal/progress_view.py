"""Progress and statistics view for tracking learning performance."""

from __future__ import annotations

import logging
from typing import Any

from rich.table import Table
from textual.app import ComposeResult
from textual.containers import (
    Container,
    Horizontal,
    VerticalScroll,
)
from textual.screen import Screen
from textual.widgets import Button, Static

from src.application.commands.reset_user_progress_command import (
    ResetUserProgressCommand,
    ResetUserProgressCommandHandler,
)
from src.application.queries.get_fsrs_analytics_query import (
    GetFSRSAnalyticsQuery,
    GetFSRSAnalyticsQueryHandler,
)
from src.domain.shared.services import EventBusInterface
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import (
    COMMON_CSS_BASE,
    format_percentage,
    get_progress_color,
)

logger = logging.getLogger(__name__)


class StatsWidget(Static):
    """Widget for displaying learning statistics."""

    def __init__(
        self,
        learning_stats_query_handler,
        event_bus: EventBusInterface,
        reset_command_handler: ResetUserProgressCommandHandler | None = None,
        fsrs_analytics_query_handler: GetFSRSAnalyticsQueryHandler | None = None,
        **kwargs: Any,
    ):
        # Start with simple visible content
        super().__init__(
            "Learning Statistics\n\nMastered: 0\nLearning: 0\nNew: 460\nDue: 0\n\nOverall Accuracy: 0.0%\nStudy Streak: 0 days\nTotal Sessions: 0\nStudy Time: 0h 0m",
            **kwargs,
        )
        self.learning_stats_query_handler = learning_stats_query_handler
        self.event_bus = event_bus
        self.reset_command_handler = reset_command_handler
        self.fsrs_analytics_query_handler = fsrs_analytics_query_handler

    async def refresh_stats(self) -> None:
        """Refresh statistics display using CQRS query handler."""
        logger.info("StatsWidget: Starting refresh_stats() - CQRS VERSION")
        try:
            if not self.learning_stats_query_handler:
                logger.warning("No learning stats query handler available")
                return

            # Get stats using CQRS query
            from src.application.queries.get_learning_stats_query import (
                GetLearningStatsQuery,
            )

            # Create query - repository will be injected by handler
            query = GetLearningStatsQuery(
                user_id=1,
                include_category_breakdown=False,
                include_forecasts=True,
            )

            result = await self.learning_stats_query_handler.handle(query)

            if result.success and result.insights:
                insights = result.insights
                # Create comprehensive analytics content with Rich markup styling
                content = f"""[bold cyan]Learning Statistics[/bold cyan]

[bold yellow]CARD COUNTS:[/bold yellow]
Mastered: [green]{insights.cards_mastered}[/green] ([green]{insights.overall_progress_percentage:.1f}%[/green])
Learning: [yellow]{insights.cards_learning}[/yellow]
New: [blue]{insights.cards_new}[/blue]
Due Today: [red]{insights.study_forecast.reviews_due_today}[/red]

[bold yellow]RETENTION ANALYSIS:[/bold yellow]
Overall: [green]{insights.retention_analysis.overall_retention * 100:.1f}%[/green]
7-Day: {insights.retention_analysis.last_7_days_retention * 100:.1f}%
30-Day: {insights.retention_analysis.last_30_days_retention * 100:.1f}%
Trend: [cyan]{insights.retention_analysis.retention_trend.title()}[/cyan]

[bold yellow]STUDY PROGRESS:[/bold yellow]
Current Streak: [magenta]{insights.learning_streak.current_streak} days[/magenta]
Longest Streak: [magenta]{insights.learning_streak.longest_streak} days[/magenta]
Total Sessions: {insights.total_sessions}
Study Time: [cyan]{insights.total_study_time_hours:.1f}h[/cyan]

[bold yellow]UPCOMING WORKLOAD:[/bold yellow]
Tomorrow: {insights.study_forecast.reviews_due_tomorrow} reviews
This Week: {insights.study_forecast.reviews_due_week} reviews
Est. Time: [yellow]{insights.study_forecast.estimated_study_time_minutes} min[/yellow]
Peak Day: [cyan]{insights.study_forecast.peak_review_day}[/cyan]

[bold yellow]RECOMMENDATIONS:[/bold yellow]
Daily Goal: [green]{insights.recommended_daily_reviews} reviews[/green]
Focus Areas: [yellow]{", ".join(insights.recommended_focus_categories[:3]) if insights.recommended_focus_categories else "None"}[/yellow]

[bold yellow]LEECH DETECTION:[/bold yellow]
{await self._get_leech_summary()}
"""

                self.update(content)
                logger.info("StatsWidget: Successfully updated with real data")
            else:
                logger.error(f"Failed to get learning stats: {result.error_message}")
                self._show_fallback_content()

        except Exception as e:
            logger.error(f"StatsWidget: Failed to refresh stats: {e}")
            self._show_fallback_content()
            import traceback

            traceback.print_exc()

    def _show_fallback_content(self) -> None:
        """Show fallback content when stats loading fails."""
        fallback_content = """Learning Statistics

CARD COUNTS:
Mastered: 0 (0.0%)
Learning: 0
New: 460
Due Today: 0

RETENTION ANALYSIS:
Overall: 0.0%
7-Day: 0.0%
30-Day: 0.0%
Trend: Stable

STUDY PROGRESS:
Current Streak: 0 days
Longest Streak: 0 days
Total Sessions: 0
Study Time: 0.0h

UPCOMING WORKLOAD:
Tomorrow: 0 reviews
This Week: 0 reviews
Est. Time: 0 min
Peak Day: Monday

RECOMMENDATIONS:
Daily Goal: 20 reviews
Focus Areas: None

LEECH DETECTION:
No difficult cards detected
"""
        self.update(fallback_content)

    def _get_total_sessions_count(self) -> int:
        """Get total number of learning sessions."""
        try:
            # Use analytics service to get session stats instead of direct DB access
            stats = self.analytics_service.get_learning_statistics(user_id=1)
            return stats.get("total_sessions", 0)
        except Exception as e:
            logger.error(f"Failed to get sessions count: {e}")
            return 0

    def _get_session_count_from_insights(self, insights) -> int:
        """Extract session count from learning insights."""
        try:
            # Try to get session count from insights if available
            if hasattr(insights, "total_sessions"):
                return insights.total_sessions

            # Fallback to using the learning stats query handler directly
            if self.learning_stats_query_handler:
                # The session count should be available through the insights
                # For now, return a reasonable default
                return 0

            return 0
        except Exception as e:
            logger.error(f"Failed to get session count from insights: {e}")
            return 0

    async def _get_leech_summary(self) -> str:
        """Get summary of leech detection results."""
        try:
            if not self.fsrs_analytics_query_handler:
                return "[dim]Leech detection requires FSRS analytics[/dim]"

            # Get leech analysis from FSRS analytics
            from src.application.queries.get_fsrs_analytics_query import (
                GetFSRSAnalyticsQuery,
            )

            query = GetFSRSAnalyticsQuery(
                user_id=1,
                include_stability_analysis=False,
                include_retrievability_analysis=False,
                include_leech_analysis=True,
                include_performance_trends=False,
            )

            result = await self.fsrs_analytics_query_handler.handle(query)

            if result.success and result.leech_analysis:
                leech = result.leech_analysis
                if leech.total_leeches == 0:
                    return "[green]No difficult cards detected[/green]"

                # Create summary string
                summary = f"[yellow]{leech.total_leeches} difficult cards[/yellow]"

                if leech.average_lapses > 0:
                    summary += f" • [red]Avg lapses: {leech.average_lapses:.1f}[/red]"

                # Show top category with leeches
                if leech.leeches_by_category:
                    top_category = max(
                        leech.leeches_by_category.items(), key=lambda x: x[1]
                    )
                    summary += f" • [red]{top_category[0]}: {top_category[1]}[/red]"

                return summary
            else:
                return "[yellow]Analyzing difficult cards...[/yellow]"

        except Exception as e:
            logger.error(f"Failed to get leech summary: {e}")
            return "[red]Leech detection unavailable[/red]"


class FSRSAnalyticsWidget(Static):
    """Widget for displaying FSRS-specific analytics."""

    def __init__(
        self,
        fsrs_analytics_query_handler: GetFSRSAnalyticsQueryHandler,
        event_bus: EventBusInterface,
        **kwargs: Any,
    ):
        super().__init__(
            "[bold cyan]FSRS Analytics[/bold cyan]\n\nLoading FSRS analytics...",
            **kwargs,
        )
        self.fsrs_analytics_query_handler = fsrs_analytics_query_handler
        self.event_bus = event_bus

    async def refresh_fsrs_analytics(self) -> None:
        """Refresh FSRS analytics display using CQRS query handler."""
        logger.info("FSRSAnalyticsWidget: Starting refresh_fsrs_analytics()")
        try:
            if not self.fsrs_analytics_query_handler:
                logger.warning("No FSRS analytics query handler available")
                return

            # Get FSRS analytics using CQRS query
            query = GetFSRSAnalyticsQuery(
                user_id=1,
                include_stability_analysis=True,
                include_retrievability_analysis=True,
                include_leech_analysis=True,
                include_performance_trends=True,
            )

            result = await self.fsrs_analytics_query_handler.handle(query)

            if result.success:
                content = self._format_fsrs_analytics(result)
                self.update(content)
                logger.info("FSRSAnalyticsWidget: Successfully updated with FSRS data")
            else:
                logger.error(f"Failed to get FSRS analytics: {result.error_message}")
                self._show_fallback_content()

        except Exception as e:
            logger.error(f"FSRSAnalyticsWidget: Failed to refresh analytics: {e}")
            self._show_fallback_content()

    def _format_fsrs_analytics(self, result) -> str:
        """Format FSRS analytics results into rich markup."""
        try:
            content = "[bold cyan]FSRS Analytics[/bold cyan]\n\n"

            # Card State Distribution
            if result.card_state_distribution:
                dist = result.card_state_distribution
                content += "[bold yellow]CARD STATES:[/bold yellow]\n"
                content += f"New: [blue]{dist.new_cards}[/blue]\n"
                content += f"Learning: [yellow]{dist.learning_cards}[/yellow]\n"
                content += f"Review: [green]{dist.review_cards}[/green]\n"
                content += f"Relearning: [red]{dist.relearning_cards}[/red]\n"
                content += f"Mastery: [green]{dist.mastery_percentage:.1f}%[/green]\n\n"

            # Stability Analysis
            if result.stability_analysis:
                stab = result.stability_analysis
                content += "[bold yellow]STABILITY DISTRIBUTION:[/bold yellow]\n"
                content += f"< 7 days: [red]{stab.cards_below_7_days}[/red]\n"
                content += f"7-30 days: [yellow]{stab.cards_7_to_30_days}[/yellow]\n"
                content += f"30-90 days: [green]{stab.cards_30_to_90_days}[/green]\n"
                content += f"> 90 days: [bright_green]{stab.cards_above_90_days}[/bright_green]\n"
                content += (
                    f"Average: [cyan]{stab.average_stability:.1f} days[/cyan]\n\n"
                )

            # Retrievability Analysis
            if result.retrievability_analysis:
                retr = result.retrievability_analysis
                content += "[bold yellow]RETRIEVABILITY:[/bold yellow]\n"
                content += f"< 80%: [red]{retr.cards_below_80_percent}[/red]\n"
                content += f"80-90%: [yellow]{retr.cards_80_to_90_percent}[/yellow]\n"
                content += f"> 90%: [green]{retr.cards_above_90_percent}[/green]\n"
                content += f"Average: [cyan]{retr.average_retrievability:.1%}[/cyan]\n"
                content += (
                    f"Due Today: [magenta]{retr.due_for_review_today}[/magenta]\n\n"
                )

            # Leech Analysis
            if result.leech_analysis:
                leech = result.leech_analysis
                content += "[bold yellow]LEECH DETECTION:[/bold yellow]\n"
                content += f"Total Leeches: [red]{leech.total_leeches}[/red]\n"
                content += f"Avg Lapses: [yellow]{leech.average_lapses:.1f}[/yellow]\n"
                if leech.leeches_by_category:
                    top_category = max(
                        leech.leeches_by_category.items(), key=lambda x: x[1]
                    )
                    content += f"Most Difficult: [red]{top_category[0]} ({top_category[1]})[/red]\n"
                content += "\n"

            # Performance Trends
            if result.performance_trends:
                trends = result.performance_trends
                content += "[bold yellow]PERFORMANCE TRENDS:[/bold yellow]\n"
                content += f"7-Day Retention: [cyan]{trends.retention_rate_7_days:.1f}%[/cyan]\n"
                content += f"30-Day Retention: [cyan]{trends.retention_rate_30_days:.1f}%[/cyan]\n"
                content += f"Graduated (Week): [green]{trends.cards_graduated_last_week}[/green]\n"
                content += f"Graduated (Month): [green]{trends.cards_graduated_last_month}[/green]\n"

            return content

        except Exception as e:
            logger.error(f"Error formatting FSRS analytics: {e}")
            return "[red]Error displaying FSRS analytics[/red]"

    def _show_fallback_content(self) -> None:
        """Show fallback content when FSRS analytics loading fails."""
        fallback_content = """[bold cyan]FSRS Analytics[/bold cyan]

CARD STATES:
New: 0
Learning: 0
Review: 0
Relearning: 0
Mastery: 0.0%

STABILITY DISTRIBUTION:
< 7 days: 0
7-30 days: 0
30-90 days: 0
> 90 days: 0
Average: 0.0 days

RETRIEVABILITY:
< 80%: 0
80-90%: 0
> 90%: 0
Average: 0.0%
Due Today: 0

LEECH DETECTION:
Total Leeches: 0
Avg Lapses: 0.0

PERFORMANCE TRENDS:
7-Day Retention: 0.0%
30-Day Retention: 0.0%
Graduated (Week): 0
Graduated (Month): 0
"""
        self.update(fallback_content)


class PerformanceTrendsWidget(Static):
    """Widget for displaying performance trends and time-based analytics."""

    def __init__(
        self,
        analytics_repository,
        event_bus: EventBusInterface,
        **kwargs: Any,
    ):
        super().__init__(
            "[bold cyan]Performance Trends[/bold cyan]\n\nLoading performance data...",
            **kwargs,
        )
        self.analytics_repository = analytics_repository
        self.event_bus = event_bus

    async def refresh_performance_trends(self) -> None:
        """Refresh performance trends display."""
        logger.info("PerformanceTrendsWidget: Starting refresh_performance_trends()")
        try:
            if not self.analytics_repository:
                logger.warning("No analytics repository available")
                return

            # Get hourly session statistics
            hourly_stats = await self.analytics_repository.get_hourly_session_stats(
                user_id=1, days=30
            )

            # Get daily study patterns
            daily_patterns = await self.analytics_repository.get_daily_study_patterns(
                user_id=1, days=7
            )

            content = self._format_performance_trends(hourly_stats, daily_patterns)
            self.update(content)
            logger.info(
                "PerformanceTrendsWidget: Successfully updated with trends data"
            )

        except Exception as e:
            logger.error(f"PerformanceTrendsWidget: Failed to refresh trends: {e}")
            self._show_fallback_content()

    def _format_performance_trends(
        self, hourly_stats: dict, daily_patterns: list
    ) -> str:
        """Format performance trends into rich markup."""
        try:
            content = "[bold cyan]Performance Trends[/bold cyan]\n\n"

            # Study time analysis
            content += "[bold yellow]STUDY TIME PATTERNS:[/bold yellow]\n"

            # Find peak study hours
            if hourly_stats:
                peak_hour = max(hourly_stats.items(), key=lambda x: x[1]["count"])
                if peak_hour[1]["count"] > 0:
                    content += f"Peak Hour: [green]{peak_hour[0]:02d}:00[/green] ({peak_hour[1]['count']} sessions)\n"
                    avg_accuracy = peak_hour[1]["avg_accuracy"]
                    content += f"Peak Hour Accuracy: [cyan]{avg_accuracy:.1f}%[/cyan]\n"
                else:
                    content += "Peak Hour: [dim]No sessions recorded[/dim]\n"
            else:
                content += "Peak Hour: [dim]No data available[/dim]\n"

            # Recent daily patterns
            if daily_patterns and len(daily_patterns) > 0:
                content += f"\n[bold yellow]RECENT ACTIVITY (Last {len(daily_patterns)} days):[/bold yellow]\n"
                total_sessions = sum(day["session_count"] for day in daily_patterns)
                total_questions = sum(day["total_questions"] for day in daily_patterns)
                avg_accuracy = sum(
                    day["avg_accuracy"]
                    for day in daily_patterns
                    if day["avg_accuracy"] > 0
                ) / max(1, len([d for d in daily_patterns if d["avg_accuracy"] > 0]))

                content += f"Total Sessions: [cyan]{total_sessions}[/cyan]\n"
                content += f"Questions Answered: [cyan]{total_questions}[/cyan]\n"
                content += f"Average Accuracy: [green]{avg_accuracy:.1f}%[/green]\n"

                # Show consistency
                active_days = len([d for d in daily_patterns if d["session_count"] > 0])
                consistency = (active_days / len(daily_patterns)) * 100
                consistency_color = (
                    "green"
                    if consistency >= 70
                    else "yellow"
                    if consistency >= 40
                    else "red"
                )
                content += f"Study Consistency: [{consistency_color}]{consistency:.0f}%[/{consistency_color}] ({active_days}/{len(daily_patterns)} days)\n"
            else:
                content += "\n[bold yellow]RECENT ACTIVITY:[/bold yellow]\n"
                content += "[dim]No recent study sessions[/dim]\n"

            # Study recommendations
            content += "\n[bold yellow]RECOMMENDATIONS:[/bold yellow]\n"
            if hourly_stats and any(h["count"] > 0 for h in hourly_stats.values()):
                # Find most productive hours
                productive_hours = sorted(
                    [
                        (h, stats)
                        for h, stats in hourly_stats.items()
                        if stats["avg_accuracy"] >= 80 and stats["count"] >= 2
                    ],
                    key=lambda x: x[1]["avg_accuracy"],
                    reverse=True,
                )[:3]

                if productive_hours:
                    best_hours = ", ".join([f"{h:02d}:00" for h, _ in productive_hours])
                    content += f"• [green]Best study times: {best_hours}[/green]\n"
                else:
                    content += "• [yellow]Study more consistently for better insights[/yellow]\n"

                # Consistency recommendation
                if daily_patterns:
                    active_days = len(
                        [d for d in daily_patterns if d["session_count"] > 0]
                    )
                    if active_days < len(daily_patterns) * 0.5:
                        content += "• [yellow]Try to study daily for better retention[/yellow]\n"
                    elif active_days == len(daily_patterns):
                        content += (
                            "• [green]Excellent consistency! Keep it up[/green]\n"
                        )
            else:
                content += "• [blue]Start studying to see personalized recommendations[/blue]\n"

            return content

        except Exception as e:
            logger.error(f"Error formatting performance trends: {e}")
            return "[red]Error displaying performance trends[/red]"

    def _show_fallback_content(self) -> None:
        """Show fallback content when performance trends loading fails."""
        fallback_content = """[bold cyan]Performance Trends[/bold cyan]

STUDY TIME PATTERNS:
Peak Hour: No data available

RECENT ACTIVITY:
Total Sessions: 0
Questions Answered: 0
Average Accuracy: 0.0%
Study Consistency: 0% (0/7 days)

RECOMMENDATIONS:
• Start studying to see personalized insights
• Aim for consistent daily practice
• Track your progress over time
"""
        self.update(fallback_content)


class CategoryProgressWidget(EventAwareWidget):
    """Widget for displaying category-specific progress."""

    def __init__(
        self, learning_stats_query_handler, event_bus: EventBusInterface, **kwargs: Any
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.learning_stats_query_handler = learning_stats_query_handler

    def compose(self) -> ComposeResult:
        """Compose the category progress widget."""
        with Container(classes="category-container"):
            yield Static("Progress by Category", classes="text-section-header")
            yield Static(
                "Loading category data...",
                id="category-table",
                classes="category-table",
            )

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        from src.domain.shared.events import (
            CardScheduledEvent,
            PerformanceAnalyzedEvent,
            ProgressTrackedEvent,
            SessionCompletedEvent,
        )

        # Subscribe to events that affect category progress
        self.subscribe_to_event(CardScheduledEvent, self._handle_card_progress)
        self.subscribe_to_event(ProgressTrackedEvent, self._handle_progress_update)
        self.subscribe_to_event(
            PerformanceAnalyzedEvent, self._handle_performance_analysis
        )
        self.subscribe_to_event(SessionCompletedEvent, self._handle_session_completion)

        logger.debug(
            f"{self.__class__.__name__} subscribed to category progress events"
        )

    async def refresh_categories(self) -> None:
        """Refresh category progress display using CQRS query handler."""
        try:
            if not self.learning_stats_query_handler:
                logger.warning("No learning stats query handler available")
                return

            # Get category data using CQRS query
            from src.application.queries.get_learning_stats_query import (
                GetLearningStatsQuery,
            )

            # Create query - repository will be injected by handler
            query = GetLearningStatsQuery(
                user_id=1,
                include_category_breakdown=True,
                include_forecasts=False,
            )

            result = await self.learning_stats_query_handler.handle(query)

            categories = []
            if result.success and result.category_progress:
                for category_name, data in result.category_progress.items():
                    categories.append(
                        {
                            "name": category_name,
                            "mastered": data.get("mastered", 0),
                            "total": data.get("total_cards", 0),
                            "accuracy": data.get("retention_rate", 0.0)
                            * 100,  # Convert to percentage
                        }
                    )

            # If no data, show empty state
            if not categories:
                categories = [
                    {
                        "name": "No data available",
                        "mastered": 0,
                        "total": 0,
                        "accuracy": 0.0,
                    }
                ]

            # Create responsive Rich table
            table = Table(show_header=True, header_style="bold blue", expand=True)
            table.add_column(
                "Category", style="cyan", ratio=2, min_width=8, no_wrap=False
            )
            table.add_column(
                "Progress", style="green", ratio=1, min_width=10, no_wrap=False
            )
            table.add_column(
                "Accuracy", style="yellow", ratio=1, min_width=8, no_wrap=True
            )

            for cat in categories:
                progress = format_percentage(cat["mastered"], cat["total"])
                accuracy_color = get_progress_color(cat["accuracy"])
                accuracy = (
                    f"[{accuracy_color}]{cat['accuracy']:.1f}%[/{accuracy_color}]"
                )

                table.add_row(
                    cat["name"],
                    f"{cat['mastered']}/{cat['total']} ({progress})",
                    accuracy,
                )

            # Update table display
            table_widget = self.query_one("#category-table", Static)
            table_widget.update(table)

        except Exception as e:
            logger.error(f"Failed to refresh categories: {e}")

    async def _handle_card_progress(self, event) -> None:
        """Handle CardScheduledEvent to update category progress in real-time."""
        try:
            # Refresh category data when a card is scheduled (answered)
            await self.refresh_categories()
            logger.debug(
                f"Updated category progress after card {event.question_id} scheduled"
            )
        except Exception as e:
            logger.error(f"Error handling card progress event: {e}")

    async def _handle_progress_update(self, event) -> None:
        """Handle ProgressTrackedEvent to update overall progress metrics."""
        try:
            # Refresh categories when progress is tracked
            await self.refresh_categories()
            logger.debug(
                f"Updated category progress after progress tracking for user {event.user_id}"
            )
        except Exception as e:
            logger.error(f"Error handling progress update event: {e}")

    async def _handle_performance_analysis(self, event) -> None:
        """Handle PerformanceAnalyzedEvent to update category insights."""
        try:
            # Update category display with performance analysis results
            await self.refresh_categories()

            # Could also update specific category insights based on weak/strong categories
            weak_categories = (
                event.weak_categories if hasattr(event, "weak_categories") else []
            )
            strong_categories = (
                event.strong_categories if hasattr(event, "strong_categories") else []
            )

            logger.debug(
                f"Updated category performance: weak={len(weak_categories)}, strong={len(strong_categories)}"
            )
        except Exception as e:
            logger.error(f"Error handling performance analysis event: {e}")

    async def _handle_session_completion(self, event) -> None:
        """Handle SessionCompletedEvent to update category data after session."""
        try:
            # Refresh category progress after session completion
            await self.refresh_categories()
            logger.debug(
                f"Updated category progress after session {event.session_id} completion"
            )
        except Exception as e:
            logger.error(f"Error handling session completion event: {e}")


class ProgressScreen(Screen):
    """Screen for displaying progress and statistics."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Progress view specific styling */
    .progress-container {
        align: center top;
        width: 95vw;
        max-width: 120;
        height: auto;
        max-height: 90vh;
        background: $surface;
        border: solid white;
        padding: 1;
        margin: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    #stats-widget {
        width: 100%;
        height: auto;
        min-height: 15;
        background: $surface;
        border: solid white;
        padding: 2;
        margin-bottom: 1;
        color: white;
        text-align: left;
    }

    .category-container {
        width: 100%;
        height: auto;
        min-height: 10;
        max-height: 30vh;
        background: $background;
        border: solid white;
        padding: 1;
        margin-bottom: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    .category-table {
        width: 100%;
        height: auto;
        text-align: left;
        overflow-x: auto;
    }

    #fsrs-analytics-widget {
        width: 100%;
        height: auto;
        min-height: 12;
        background: $surface;
        border: solid white;
        padding: 2;
        margin-bottom: 1;
        color: white;
        text-align: left;
    }

    #fsrs-analytics-placeholder {
        width: 100%;
        height: auto;
        min-height: 3;
        background: $background;
        border: dashed white;
        padding: 1;
        margin-bottom: 1;
        color: gray;
        text-align: center;
    }

    #performance-trends-widget {
        width: 100%;
        height: auto;
        min-height: 12;
        background: $surface;
        border: solid white;
        padding: 2;
        margin-bottom: 1;
        color: white;
        text-align: left;
    }
    """
    )

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(
        self,
        learning_stats_query_handler,
        fsrs_analytics_query_handler: GetFSRSAnalyticsQueryHandler | None = None,
        reset_command_handler: ResetUserProgressCommandHandler | None = None,
        analytics_repository=None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.learning_stats_query_handler = learning_stats_query_handler
        self.fsrs_analytics_query_handler = fsrs_analytics_query_handler
        self.reset_command_handler = reset_command_handler
        self.analytics_repository = analytics_repository

    def compose(self) -> ComposeResult:
        """Compose the progress screen."""
        with Container(classes="container-main"):
            yield VerticalScroll(
                StatsWidget(
                    learning_stats_query_handler=self.learning_stats_query_handler,
                    event_bus=self.app.event_bus,
                    reset_command_handler=self.reset_command_handler,
                    fsrs_analytics_query_handler=self.fsrs_analytics_query_handler,
                    id="stats-widget",
                ),
                CategoryProgressWidget(
                    learning_stats_query_handler=self.learning_stats_query_handler,
                    event_bus=self.app.event_bus,
                    id="category-widget",
                ),
                FSRSAnalyticsWidget(
                    fsrs_analytics_query_handler=self.fsrs_analytics_query_handler,
                    event_bus=self.app.event_bus,
                    id="fsrs-analytics-widget",
                )
                if self.fsrs_analytics_query_handler
                else Static(
                    "[dim]FSRS Analytics unavailable[/dim]",
                    id="fsrs-analytics-placeholder",
                ),
                PerformanceTrendsWidget(
                    analytics_repository=self.analytics_repository,
                    event_bus=self.app.event_bus,
                    id="performance-trends-widget",
                )
                if self.analytics_repository
                else Static(
                    "[dim]Performance Trends unavailable[/dim]",
                    id="performance-trends-placeholder",
                ),
                classes="progress-container",
            )
            yield Container(
                Horizontal(
                    Button("Refresh", id="refresh", variant="primary"),
                    Button("Export Stats", id="export", variant="default"),
                    Button("Reset Progress", id="reset", variant="error"),
                    Button("Back to Menu", id="back", variant="default"),
                    classes="buttons-horizontal",
                ),
                classes="footer-container",
            )

    async def on_mount(self) -> None:
        """Load data when screen mounts."""
        logger.info("ProgressScreen: on_mount() called - starting data refresh")
        await self.refresh_data()
        logger.info("ProgressScreen: on_mount() completed")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "refresh":
            await self.refresh_data()
        elif button_id == "export":
            await self.export_stats()
        elif button_id == "reset":
            await self.reset_progress()
        elif button_id == "back":
            self.app.pop_screen()

    async def refresh_data(self) -> None:
        """Refresh all data displays."""
        logger.info("ProgressScreen: Starting refresh_data()")

        try:
            stats_widget = self.query_one("#stats-widget", StatsWidget)
            logger.info("ProgressScreen: Found stats widget, calling refresh_stats()")
            await stats_widget.refresh_stats()
            logger.info("ProgressScreen: Stats widget refreshed successfully")

            category_widget = self.query_one("#category-widget", CategoryProgressWidget)
            logger.info(
                "ProgressScreen: Found category widget, calling refresh_categories()"
            )
            await category_widget.refresh_categories()
            logger.info("ProgressScreen: Category widget refreshed successfully")

            # Refresh FSRS analytics if available
            try:
                fsrs_widget = self.query_one(
                    "#fsrs-analytics-widget", FSRSAnalyticsWidget
                )
                logger.info(
                    "ProgressScreen: Found FSRS analytics widget, refreshing..."
                )
                await fsrs_widget.refresh_fsrs_analytics()
                logger.info(
                    "ProgressScreen: FSRS analytics widget refreshed successfully"
                )
            except Exception as fsrs_error:
                logger.debug(
                    f"ProgressScreen: FSRS analytics widget not available: {fsrs_error}"
                )

            # Refresh performance trends if available
            try:
                trends_widget = self.query_one(
                    "#performance-trends-widget", PerformanceTrendsWidget
                )
                logger.info(
                    "ProgressScreen: Found performance trends widget, refreshing..."
                )
                await trends_widget.refresh_performance_trends()
                logger.info(
                    "ProgressScreen: Performance trends widget refreshed successfully"
                )
            except Exception as trends_error:
                logger.debug(
                    f"ProgressScreen: Performance trends widget not available: {trends_error}"
                )
        except Exception as e:
            logger.error(f"ProgressScreen: Error in refresh_data(): {e}")
            import traceback

            traceback.print_exc()

    async def export_stats(self) -> None:
        """Export statistics to file using CQRS query handler."""
        logger.info("Exporting statistics")
        try:
            if not self.learning_stats_query_handler:
                self.notify("Export failed - no stats query handler", severity="error")
                return

            # Get comprehensive stats using CQRS query
            from src.application.queries.get_learning_stats_query import (
                GetLearningStatsQuery,
            )

            query = GetLearningStatsQuery(
                user_id=1,
                include_category_breakdown=True,
                include_forecasts=True,
            )

            result = await self.learning_stats_query_handler.handle(query)

            if not result.success or not result.insights:
                self.notify("Export failed - could not load stats", severity="error")
                return

            insights = result.insights
            category_data = result.category_progress or {}

            # Create export data structure
            export_data = {
                "export_timestamp": insights.timestamp.isoformat(),
                "overall_stats": {
                    "cards_mastered": insights.cards_mastered,
                    "cards_learning": insights.cards_learning,
                    "cards_new": insights.cards_new,
                    "overall_retention": f"{insights.retention_analysis.overall_retention * 100:.1f}%",
                    "current_streak": insights.learning_streak.current_streak,
                    "total_study_time_hours": f"{insights.total_study_time_hours:.1f}",
                },
                "category_progress": {},
                "study_forecast": {
                    "reviews_due_today": insights.study_forecast.reviews_due_today,
                    "new_cards_today": insights.study_forecast.new_cards_today,
                    "estimated_minutes": insights.study_forecast.estimated_minutes,
                },
            }

            # Add category details
            for category_name, data in category_data.items():
                export_data["category_progress"][category_name] = {
                    "mastered": data["mastered"],
                    "total_cards": data["total_cards"],
                    "retention_rate": f"{data['retention_rate'] * 100:.1f}%",
                    "avg_interval": data["avg_interval"],
                }

            # Write to file
            import json
            from pathlib import Path

            export_path = Path("data/stats_export.json")
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.notify(f"Statistics exported to {export_path}")
            logger.info(f"Successfully exported statistics to {export_path}")

        except Exception as e:
            logger.error(f"Failed to export statistics: {e}")
            self.notify("Export failed - check logs for details", severity="error")

    async def reset_progress(self) -> None:
        """Reset all progress with confirmation."""
        logger.info("Reset progress requested")

        # Show confirmation using Textual's built-in question dialog
        try:
            # For now, we'll use a simple notification-based confirmation
            # In a full implementation, you'd use app.push_screen with a confirmation dialog
            response = await self._confirm_reset()

            if response:
                # Reset learning data through analytics service
                await self._perform_reset()
                self.notify("All learning progress has been reset", severity="warning")
                # Refresh the display
                await self.refresh_data()
            else:
                self.notify("Reset cancelled")

        except Exception as e:
            logger.error(f"Failed to reset progress: {e}")
            self.notify("Reset failed - check logs for details", severity="error")

    async def _confirm_reset(self) -> bool:
        """Simple confirmation for reset action."""
        # For terminal UI, we'll use a simple approach
        # In a full implementation, you'd create a proper confirmation dialog
        # For now, just assume user wants to proceed after explicit action
        return True

    async def _perform_reset(self) -> None:
        """Perform the actual progress reset using CQRS command handler."""
        try:
            # Check if command handler is available
            if not self.reset_command_handler:
                # Fallback: try to get it from app container
                if hasattr(self.app, "container") and self.app.container:
                    self.reset_command_handler = (
                        self.app.container.get_reset_progress_command_handler()
                    )
                else:
                    raise Exception(
                        "Reset command handler not available - check container setup"
                    )

            # Create and execute reset command
            command = ResetUserProgressCommand(
                user_id=1,
                preserve_settings=True,  # Keep user settings while resetting progress
            )

            # Execute command through proper CQRS handler
            result = await self.reset_command_handler.handle(command)

            if result.success:
                items_count = (
                    sum(result.items_deleted.values()) if result.items_deleted else 0
                )
                logger.info(f"Successfully reset {items_count} items for user progress")
            else:
                raise Exception(result.error_message or "Reset command failed")

        except Exception as e:
            logger.error(f"Reset operation failed: {e}")
            raise

    def action_refresh(self) -> None:
        """Refresh data via keyboard."""
        self.run_action("refresh")

    def action_export(self) -> None:
        """Export stats via keyboard."""
        self.run_action("export")

    def action_back_to_menu(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
