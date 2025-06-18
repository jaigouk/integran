"""Main Textual application for the Integran terminal trainer."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.domain.analytics.services.analyze_performance import ProgressAnalytics
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.presentation.terminal.base import EventAwareApp
from src.presentation.terminal.progress_view import ProgressScreen
from src.presentation.terminal.question_view import PracticeScreen
from src.presentation.terminal.session_view import SessionScreen
from src.presentation.terminal.settings_view import SettingsScreen
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class ConfirmQuitScreen(Screen[bool]):
    """Confirmation dialog for quitting the application."""

    BINDINGS = [
        ("y", "confirm_yes", "Yes"),
        ("n", "confirm_no", "No"),
        ("escape", "confirm_no", "No"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the quit confirmation dialog."""
        yield Container(
            Static("Are you sure you want to exit Integran?", classes="confirm-title"),
            Static(
                "Press Y for Yes, N for No, or Escape to cancel", classes="confirm-help"
            ),
            Horizontal(
                Button("Yes (Y) - Exit App", id="yes", variant="error"),
                Button("No (N) - Stay in App", id="no", variant="primary"),
                classes="confirm-buttons",
            ),
            classes="confirm-dialog",
        )

    @on(Button.Pressed, "#yes")
    def on_yes_button(self) -> None:
        """User confirmed quit."""
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def on_no_button(self) -> None:
        """User cancelled quit."""
        self.dismiss(False)

    def action_confirm_yes(self) -> None:
        """Confirm quit (Y key)."""
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        """Cancel quit (N or Escape key)."""
        self.dismiss(False)


class MainMenuScreen(Screen):
    """Main menu screen with practice mode options."""

    BINDINGS = [
        ("1", "random_practice", "Random Practice"),
        ("2", "sequential_practice", "Sequential Practice"),
        ("3", "category_practice", "Category Practice"),
        ("4", "review_practice", "Review Failed"),
        ("s", "show_stats", "Statistics"),
        ("t", "show_settings", "Settings"),
        ("q", "quit", "Quit"),
        ("escape", "confirm_quit", "Exit App"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main menu screen."""
        yield Header(show_clock=True)
        yield Container(
            Static(
                "🇩🇪 Integran - German Integration Exam Trainer", classes="text-title"
            ),
            Static("Choose your practice mode:", classes="text-subtitle"),
            Vertical(
                Button("1. Random Practice", id="random", variant="primary"),
                Button("2. Sequential Practice", id="sequential", variant="success"),
                Button("3. Category Practice", id="category", variant="warning"),
                Button("4. Review Failed Questions", id="review", variant="error"),
                Button("Statistics & Progress", id="stats", variant="default"),
                Button("Settings", id="settings", variant="default"),
                classes="buttons-vertical",
            ),
            Static("Press number keys or click buttons to select", classes="text-help"),
            classes="container-centered",
        )
        yield Footer()

    @on(Button.Pressed, "#random")
    def action_random_practice(self) -> None:
        """Start random practice session."""
        self.app.push_screen("practice", {"mode": "random"})

    @on(Button.Pressed, "#sequential")
    def action_sequential_practice(self) -> None:
        """Start sequential practice session."""
        self.app.push_screen("practice", {"mode": "sequential"})

    @on(Button.Pressed, "#category")
    def action_category_practice(self) -> None:
        """Start category-based practice session."""
        self.app.push_screen("practice", {"mode": "category"})

    @on(Button.Pressed, "#review")
    def action_review_practice(self) -> None:
        """Review failed questions."""
        self.app.push_screen("practice", {"mode": "review"})

    @on(Button.Pressed, "#stats")
    def action_show_stats(self) -> None:
        """Show statistics screen."""
        stats_screen = ProgressScreen(
            query_service=self.app.query_service,
            analytics_service=self.app.analytics_service,
        )
        self.app.push_screen(stats_screen)

    @on(Button.Pressed, "#settings")
    def on_settings_button(self) -> None:
        """Handle settings button press."""
        self.action_show_settings()

    def action_show_settings(self) -> None:
        """Show settings screen (keyboard shortcut 't')."""
        settings_screen = SettingsScreen(
            event_bus=self.app.event_bus, user_repository=self.app.user_repository
        )
        self.app.push_screen(settings_screen)

    def action_confirm_quit(self) -> None:
        """Show exit confirmation dialog (Escape key)."""
        self.app.action_quit()


class TrainerApp(EventAwareApp):
    """Main Integran trainer application."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Main menu specific styling */
    .container-centered {
        max-width: 100;
        min-height: 25;
        max-height: 90vh;
    }

    /* Confirm dialog specific styling */
    .confirm-dialog {
        align: center middle;
        width: 60;
        height: 12;
        background: $surface;
        border: solid white;
        padding: 2;
    }

    .confirm-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    .confirm-help {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .confirm-buttons {
        align: center middle;
        width: 100%;
    }

    .confirm-buttons Button {
        width: 1fr;
        height: 3;
        margin: 0 1;
        text-style: bold;
    }
    """
    )

    SCREENS = {
        "main": MainMenuScreen,
        "practice": PracticeScreen,
        "session": SessionScreen,
        "stats": ProgressScreen,
        "settings": SettingsScreen,
    }

    def __init__(
        self,
        event_bus: EventBus,
        session_workflow: SessionWorkflow,
        query_service: GetSessionProgressQueryHandler,
        analytics_service: ProgressAnalytics,
        user_repository=None,
        **kwargs: Any,
    ):
        """Initialize the trainer app."""
        super().__init__(
            event_bus=event_bus,
            **kwargs,
        )

        self.session_workflow = session_workflow
        self.query_service = query_service
        self.analytics_service = analytics_service
        self.user_repository = user_repository

        # Set app title
        self.title = "Integran - German Integration Exam Trainer"
        self.sub_title = "Terminal-based spaced repetition learning"

    async def setup_event_handlers(self) -> None:
        """Setup global event handlers for the app."""
        # TODO: Add event handlers for domain events
        logger.info("Event handlers setup complete")

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Start with the main menu
        self.push_screen("main")
        logger.info("Integran trainer app started")

    def action_quit(self) -> None:
        """Quit the application with confirmation."""
        self.push_screen(ConfirmQuitScreen(), callback=self._quit_callback)

    def _quit_callback(self, quit_confirmed: bool) -> None:
        """Handle quit confirmation result."""
        if quit_confirmed:
            logger.info("User confirmed quit")
            self.exit()
        else:
            logger.info("User cancelled quit")
