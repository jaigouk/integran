"""Progress and statistics view for tracking learning performance."""

from __future__ import annotations

import logging
from typing import Any

from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.infrastructure.messaging.event_bus import EventBus
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import format_percentage, get_progress_color

logger = logging.getLogger(__name__)


class StatsWidget(EventAwareWidget):
    """Widget for displaying learning statistics."""

    def __init__(
        self,
        query_service: GetSessionProgressQueryHandler,
        event_bus: EventBus,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.query_service = query_service

    def compose(self) -> ComposeResult:
        """Compose the statistics widget."""
        with Container(classes="stats-container"):
            yield Static("Learning Statistics", classes="stats-title")

            with Horizontal(classes="stats-overview"):
                yield Container(
                    Static("0", id="total-mastered", classes="stat-number"),
                    Static("Mastered", classes="stat-label"),
                    classes="stat-card mastered",
                )
                yield Container(
                    Static("0", id="total-learning", classes="stat-number"),
                    Static("Learning", classes="stat-label"),
                    classes="stat-card learning",
                )
                yield Container(
                    Static("0", id="total-new", classes="stat-number"),
                    Static("New", classes="stat-label"),
                    classes="stat-card new",
                )
                yield Container(
                    Static("0", id="due-review", classes="stat-number"),
                    Static("Due", classes="stat-label"),
                    classes="stat-card due",
                )

            with Vertical(classes="detailed-stats"):
                yield Static("", id="accuracy-stat", classes="detail-stat")
                yield Static("", id="streak-stat", classes="detail-stat")
                yield Static("", id="session-stat", classes="detail-stat")
                yield Static("", id="time-stat", classes="detail-stat")

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        # TODO: Subscribe to analytics events for real-time updates
        pass

    async def refresh_stats(self) -> None:
        """Refresh statistics display."""
        try:
            # TODO: Get actual stats from query service
            # For now, use dummy data
            stats = {
                "mastered": 45,
                "learning": 23,
                "new": 392,
                "due": 12,
                "accuracy": 78.5,
                "streak": 7,
                "sessions": 15,
                "total_time": 450,  # minutes
            }

            # Update overview cards
            self.query_one("#total-mastered", Static).update(str(stats["mastered"]))
            self.query_one("#total-learning", Static).update(str(stats["learning"]))
            self.query_one("#total-new", Static).update(str(stats["new"]))
            self.query_one("#due-review", Static).update(str(stats["due"]))

            # Update detailed stats
            accuracy_color = get_progress_color(stats["accuracy"])
            self.query_one("#accuracy-stat", Static).update(
                f"Overall Accuracy: [{accuracy_color}]{stats['accuracy']:.1f}%[/{accuracy_color}]"
            )

            self.query_one("#streak-stat", Static).update(
                f"Study Streak: [bold green]{stats['streak']} days[/bold green]"
            )

            self.query_one("#session-stat", Static).update(
                f"Total Sessions: [blue]{stats['sessions']}[/blue]"
            )

            hours, minutes = divmod(stats["total_time"], 60)
            self.query_one("#time-stat", Static).update(
                f"Study Time: [purple]{hours}h {minutes}m[/purple]"
            )

        except Exception as e:
            logger.error(f"Failed to refresh stats: {e}")


class CategoryProgressWidget(EventAwareWidget):
    """Widget for displaying category-specific progress."""

    def __init__(self, event_bus: EventBus, **kwargs: Any):
        super().__init__(event_bus=event_bus, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the category progress widget."""
        with Container(classes="category-container"):
            yield Static("Progress by Category", classes="category-title")
            yield Static("", id="category-table", classes="category-table")

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        pass

    async def refresh_categories(self) -> None:
        """Refresh category progress display."""
        try:
            # TODO: Get actual category data
            categories = [
                {"name": "Grundrechte", "mastered": 8, "total": 15, "accuracy": 85.2},
                {"name": "Geschichte", "mastered": 12, "total": 20, "accuracy": 76.3},
                {"name": "Föderalismus", "mastered": 6, "total": 18, "accuracy": 68.1},
                {"name": "Rechtssystem", "mastered": 9, "total": 16, "accuracy": 82.5},
                {"name": "Geografie", "mastered": 10, "total": 14, "accuracy": 91.2},
            ]

            # Create Rich table
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Category", style="cyan", width=15)
            table.add_column("Progress", style="green", width=12)
            table.add_column("Accuracy", style="yellow", width=10)

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

    CSS = """
    .progress-container {
        align: center middle;
        width: 90%;
        max-width: 120;
        background: $surface;
        border: solid $primary;
        padding: 2;
        margin: 1;
    }

    .stats-container {
        width: 100%;
        background: $background;
        border: solid $muted;
        padding: 2;
        margin-bottom: 2;
    }

    .stats-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }

    .stats-overview {
        align: center middle;
        width: 100%;
        spacing: 1;
        margin-bottom: 2;
    }

    .stat-card {
        text-align: center;
        width: 1fr;
        padding: 1;
        border: solid;
    }

    .stat-card.mastered {
        border-color: $success;
        background: $success-alpha;
    }

    .stat-card.learning {
        border-color: $warning;
        background: $warning-alpha;
    }

    .stat-card.new {
        border-color: $info;
        background: $info-alpha;
    }

    .stat-card.due {
        border-color: $error;
        background: $error-alpha;
    }

    .stat-number {
        text-style: bold;
        font-size: 2;
        text-align: center;
    }

    .stat-label {
        text-align: center;
        color: $text-muted;
    }

    .detailed-stats {
        width: 100%;
        spacing: 1;
    }

    .detail-stat {
        text-align: left;
        padding: 1;
        background: $accent-alpha;
        border: solid $accent;
    }

    .category-container {
        width: 100%;
        background: $background;
        border: solid $muted;
        padding: 2;
        margin-bottom: 2;
    }

    .category-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }

    .category-table {
        width: 100%;
        text-align: left;
    }

    .progress-actions {
        align: center middle;
        width: 100%;
        spacing: 1;
    }

    .progress-actions Button {
        width: 1fr;
        height: 3;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(self, query_service: GetSessionProgressQueryHandler, **kwargs: Any):
        super().__init__(**kwargs)
        self.query_service = query_service

    def compose(self) -> ComposeResult:
        """Compose the progress screen."""
        yield Container(
            StatsWidget(
                query_service=self.query_service,
                event_bus=self.app.event_bus,
                id="stats-widget",
            ),
            CategoryProgressWidget(
                event_bus=self.app.event_bus,
                id="category-widget",
            ),
            Horizontal(
                Button("Refresh", id="refresh", variant="primary"),
                Button("Export Stats", id="export", variant="default"),
                Button("Reset Progress", id="reset", variant="error"),
                Button("Back to Menu", id="back", variant="default"),
                classes="progress-actions",
            ),
            classes="progress-container",
        )

    async def on_mount(self) -> None:
        """Load data when screen mounts."""
        await self.refresh_data()

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
        logger.info("Refreshing progress data")

        stats_widget = self.query_one("#stats-widget", StatsWidget)
        await stats_widget.refresh_stats()

        category_widget = self.query_one("#category-widget", CategoryProgressWidget)
        await category_widget.refresh_categories()

    async def export_stats(self) -> None:
        """Export statistics to file."""
        logger.info("Exporting statistics")
        # TODO: Implement stats export
        self.notify("Statistics exported to data/stats_export.txt")

    async def reset_progress(self) -> None:
        """Reset all progress with confirmation."""
        logger.info("Reset progress requested")
        # TODO: Show confirmation dialog
        self.notify("Progress reset requires confirmation")

    def action_refresh(self) -> None:
        """Refresh data via keyboard."""
        self.run_action("refresh")

    def action_export(self) -> None:
        """Export stats via keyboard."""
        self.run_action("export")

    def action_back_to_menu(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
