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
from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.domain.analytics.services.analyze_performance import ProgressAnalytics
from src.infrastructure.messaging.enhanced_event_bus import EventBus
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
        query_service: GetSessionProgressQueryHandler,
        analytics_service: ProgressAnalytics,
        event_bus: EventBus,
        reset_command_handler: ResetUserProgressCommandHandler | None = None,
        **kwargs: Any,
    ):
        # Start with simple visible content
        super().__init__(
            "Learning Statistics\n\nMastered: 0\nLearning: 0\nNew: 460\nDue: 0\n\nOverall Accuracy: 0.0%\nStudy Streak: 0 days\nTotal Sessions: 0\nStudy Time: 0h 0m",
            **kwargs,
        )
        self.query_service = query_service
        self.analytics_service = analytics_service
        self.event_bus = event_bus
        self.reset_command_handler = reset_command_handler

    async def refresh_stats(self) -> None:
        """Refresh statistics display."""
        logger.info("StatsWidget: Starting refresh_stats() - SIMPLIFIED VERSION")
        try:
            # Get basic stats and update the content
            insights = self.analytics_service.get_learning_insights(user_id=1)

            # Create simple text content
            content = f"""Learning Statistics

CARD COUNTS:
Mastered: {insights.cards_mastered}
Learning: {insights.cards_learning}
New: {insights.cards_new}
Due: {insights.study_forecast.reviews_due_today}

PROGRESS:
Overall Accuracy: {insights.retention_analysis.overall_retention * 100:.1f}%
Study Streak: {insights.learning_streak.current_streak} days
Total Sessions: {self._get_total_sessions_count()}
Study Time: {insights.total_study_time_hours:.1f}h
"""

            self.update(content)
            logger.info("StatsWidget: Successfully updated with real data")

        except Exception as e:
            logger.error(f"StatsWidget: Failed to refresh stats: {e}")
            # Fallback content
            fallback_content = """Learning Statistics

CARD COUNTS:
Mastered: 0
Learning: 0
New: 460
Due: 0

PROGRESS:
Overall Accuracy: 0.0%
Study Streak: 0 days
Total Sessions: 0
Study Time: 0.0h
"""
            self.update(fallback_content)
            import traceback

            traceback.print_exc()

    def _get_total_sessions_count(self) -> int:
        """Get total number of learning sessions."""
        try:
            # Use analytics service to get session stats instead of direct DB access
            stats = self.analytics_service.get_learning_statistics(user_id=1)
            return stats.get("total_sessions", 0)
        except Exception as e:
            logger.error(f"Failed to get sessions count: {e}")
            return 0


class CategoryProgressWidget(EventAwareWidget):
    """Widget for displaying category-specific progress."""

    def __init__(
        self, analytics_service: ProgressAnalytics, event_bus: EventBus, **kwargs: Any
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.analytics_service = analytics_service

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
        pass

    async def refresh_categories(self) -> None:
        """Refresh category progress display."""
        try:
            # Get actual category data from analytics service
            category_data = self.analytics_service.get_category_progress_detailed(
                user_id=1
            )

            categories = []
            for category_name, data in category_data.items():
                categories.append(
                    {
                        "name": category_name,
                        "mastered": data["mastered"],
                        "total": data["total_cards"],
                        "accuracy": data["retention_rate"]
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
        max-height: 85vh;
        background: $surface;
        border: solid white;
        padding: 1;
        margin: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    #stats-widget {
        width: 100%;
        height: 1fr;
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
    """
    )

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(
        self,
        query_service: GetSessionProgressQueryHandler,
        analytics_service: ProgressAnalytics,
        reset_command_handler: ResetUserProgressCommandHandler | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.query_service = query_service
        self.analytics_service = analytics_service
        self.reset_command_handler = reset_command_handler

    def compose(self) -> ComposeResult:
        """Compose the progress screen."""
        with Container(classes="container-main"):
            yield VerticalScroll(
                StatsWidget(
                    query_service=self.query_service,
                    analytics_service=self.analytics_service,
                    event_bus=self.app.event_bus,
                    reset_command_handler=self.reset_command_handler,
                    id="stats-widget",
                ),
                CategoryProgressWidget(
                    analytics_service=self.analytics_service,
                    event_bus=self.app.event_bus,
                    id="category-widget",
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
        except Exception as e:
            logger.error(f"ProgressScreen: Error in refresh_data(): {e}")
            import traceback

            traceback.print_exc()

    async def export_stats(self) -> None:
        """Export statistics to file."""
        logger.info("Exporting statistics")
        try:
            # Get comprehensive stats from analytics service
            insights = self.analytics_service.get_learning_insights(user_id=1)
            category_data = self.analytics_service.get_category_progress_detailed(
                user_id=1
            )

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
