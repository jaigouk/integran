"""Main Textual application for the Integran terminal trainer."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.presentation.terminal.base import EventAwareApp
from src.presentation.terminal.progress_view import ProgressScreen
from src.presentation.terminal.question_view import PracticeScreen
from src.presentation.terminal.session_view import SessionScreen
from src.presentation.terminal.themes import INTEGRAN_COLOR_SYSTEM

logger = logging.getLogger(__name__)


class MainMenuScreen(Screen):
    """Main menu screen with practice mode options."""

    BINDINGS = [
        ("1", "random_practice", "Random Practice"),
        ("2", "sequential_practice", "Sequential Practice"),
        ("3", "category_practice", "Category Practice"),
        ("4", "review_practice", "Review Failed"),
        ("s", "show_stats", "Statistics"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main menu screen."""
        yield Header(show_clock=True)
        yield Container(
            Static("🇩🇪 Integran - German Integration Exam Trainer", classes="title"),
            Static("Choose your practice mode:", classes="subtitle"),
            Vertical(
                Button("1. Random Practice", id="random", variant="primary"),
                Button("2. Sequential Practice", id="sequential", variant="success"),
                Button("3. Category Practice", id="category", variant="warning"),
                Button("4. Review Failed Questions", id="review", variant="error"),
                Button("Statistics & Progress", id="stats", variant="default"),
                classes="menu-buttons",
            ),
            Static("Press number keys or click buttons to select", classes="help"),
            classes="main-menu",
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
        stats_screen = ProgressScreen(query_service=self.app.query_service)
        self.app.push_screen(stats_screen)


class TrainerApp(EventAwareApp):
    """Main Integran trainer application."""

    CSS = """
    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1;
    }

    .subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .main-menu {
        align: center middle;
        width: 60;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 2;
    }

    .menu-buttons {
        align: center middle;
        width: 100%;
        spacing: 1;
    }

    .menu-buttons Button {
        width: 100%;
        height: 3;
        margin: 1 0;
    }

    .help {
        text-align: center;
        color: $text-muted;
        margin-top: 2;
    }
    """

    SCREENS = {
        "main": MainMenuScreen,
        "practice": PracticeScreen,
        "session": SessionScreen,
        "stats": ProgressScreen,
    }

    def __init__(
        self,
        event_bus: EventBus,
        session_workflow: SessionWorkflow,
        query_service: GetSessionProgressQueryHandler,
        **kwargs: Any,
    ):
        """Initialize the trainer app."""
        super().__init__(
            event_bus=event_bus,
            design=INTEGRAN_COLOR_SYSTEM,
            **kwargs,
        )

        self.session_workflow = session_workflow
        self.query_service = query_service

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
        """Quit the application."""
        logger.info("User requested quit")
        self.exit()
