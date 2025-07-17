"""Main Textual application for the Integran terminal trainer."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow

# Analytics is now accessed through application layer queries
from src.domain.shared.services import EventBusInterface
from src.presentation.terminal.base import EventAwareApp
from src.presentation.terminal.bookmark_view import BookmarkScreen
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
            Static(
                "🚪 Are you sure you want to exit Integran?", classes="confirm-title"
            ),
            Static(
                "Press Y for Yes, N for No, or Escape to cancel", classes="confirm-help"
            ),
            Horizontal(
                Button("YES - Exit Application", id="yes", variant="error"),
                Button("NO - Continue Learning", id="no", variant="primary"),
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
        ("4", "failed_practice", "Review Failed"),
        ("5", "images_practice", "Image Questions"),
        ("6", "bookmark_practice", "Bookmark Practice"),
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
            VerticalScroll(
                Vertical(
                    Button("1. Random Practice", id="random", variant="primary"),
                    Button(
                        "2. Sequential Practice", id="sequential", variant="success"
                    ),
                    Button("3. Category Practice", id="category", variant="warning"),
                    Button("4. Review Failed Questions", id="failed", variant="error"),
                    Button("5. Image Questions Only", id="images", variant="primary"),
                    Button("6. Bookmark Practice", id="bookmark", variant="warning"),
                    Button("Statistics & Progress", id="stats", variant="default"),
                    Button("Settings", id="settings", variant="default"),
                    classes="buttons-vertical",
                ),
                classes="buttons-scroll",
            ),
            Static("Press number keys or click buttons to select", classes="text-help"),
            classes="container-centered",
        )
        yield Footer()

    @on(Button.Pressed, "#random")
    def action_random_practice(self) -> None:
        """Start random practice session."""
        practice_screen = PracticeScreen(
            practice_mode="random",
            user_repository=self.app.user_repository,
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#sequential")
    def action_sequential_practice(self) -> None:
        """Start sequential practice session."""
        practice_screen = PracticeScreen(
            practice_mode="sequential",
            user_repository=self.app.user_repository,
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#category")
    def action_category_practice(self) -> None:
        """Start category-based practice session."""
        practice_screen = PracticeScreen(
            practice_mode="category",
            user_repository=self.app.user_repository,
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#failed")
    def action_failed_practice(self) -> None:
        """Review failed questions."""
        practice_screen = PracticeScreen(
            practice_mode="failed",
            user_repository=self.app.user_repository,
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#images")
    def action_images_practice(self) -> None:
        """Practice with image questions only."""
        practice_screen = PracticeScreen(
            practice_mode="images",
            user_repository=self.app.user_repository,
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#bookmark")
    def action_bookmark_practice(self) -> None:
        """Open bookmark management screen."""
        bookmark_screen = BookmarkScreen(
            bookmark_query_handler=self.app.container.get_bookmark_query_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(bookmark_screen)

    @on(Button.Pressed, "#stats")
    def action_show_stats(self) -> None:
        """Show statistics screen."""
        stats_screen = ProgressScreen(
            learning_stats_query_handler=self.app.container.get_learning_stats_query_handler()
            if hasattr(self.app, "container")
            else None,
            fsrs_analytics_query_handler=self.app.container.get_fsrs_analytics_query_handler()
            if hasattr(self.app, "container")
            else None,
            reset_command_handler=self.app.container.get_reset_progress_command_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(stats_screen)

    @on(Button.Pressed, "#settings")
    def on_settings_button(self) -> None:
        """Handle settings button press."""
        self.action_show_settings()

    def action_show_settings(self) -> None:
        """Show settings screen (keyboard shortcut 't')."""
        settings_screen = SettingsScreen(
            event_bus=self.app.event_bus,
            load_user_settings_query_handler=self.app.container.get_load_user_settings_query_handler(),
            save_user_settings_command_handler=self.app.container.get_save_user_settings_command_handler(),
            toggle_developer_mode_command_handler=self.app.container.get_toggle_developer_mode_command_handler(),
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
        align: center middle;
        width: 95vw;
        max-width: 120;
        height: auto;
        max-height: 85vh;
        background: $surface;
        border: solid white;
        padding: 2;
        margin: 1;
    }

    .buttons-scroll {
        width: 100%;
        height: auto;
        max-height: 50vh;
        overflow-y: auto;
        scrollbar-gutter: stable;
        margin: 1 0;
    }

    /* Confirm dialog specific styling */
    .confirm-dialog {
        align: center middle;
        width: 95vw;
        max-width: 100;
        height: auto;
        background: $surface;
        border: solid white;
        padding: 3;
    }

    .confirm-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 2;
        width: 100%;
    }

    .confirm-help {
        text-align: center;
        color: $text-muted;
        margin-bottom: 3;
        width: 100%;
    }

    .confirm-buttons {
        align: center middle;
        width: 100%;
        height: auto;
    }

    .confirm-buttons Button {
        width: 1fr;
        height: 5;
        margin: 0 2;
        text-style: bold;
        min-width: 20;
        padding: 1 2;
    }

    /* Bookmark screen specific styling */
    .bookmark-container {
        align: center middle;
        width: 95vw;
        max-width: 120;
        height: auto;
        max-height: 80vh;
        background: $surface;
        border: solid white;
        padding: 2;
        margin: 1;
    }

    .bookmark-scroll {
        width: 100%;
        height: auto;
        max-height: 50vh;
        overflow-y: auto;
        scrollbar-gutter: stable;
        margin: 1 0;
    }

    .bookmark-list {
        width: 100%;
        height: auto;
    }

    .bookmark-item {
        width: 100%;
        height: auto;
        border: solid $primary;
        margin: 0 0 1 0;
        padding: 1;
        background: $surface;
    }

    .bookmark-text {
        width: 100%;
        color: $text;
        margin-bottom: 1;
    }

    .bookmark-actions {
        align: right middle;
        width: 100%;
        height: auto;
    }

    .bookmark-actions Button {
        width: auto;
        margin: 0 1;
        min-width: 10;
    }

    .bookmark-buttons {
        align: center middle;
        width: 100%;
        height: auto;
        margin-top: 2;
    }

    .bookmark-buttons Button {
        width: 1fr;
        margin: 0 1;
        min-width: 15;
    }

    .loading-container,
    .empty-container,
    .error-container {
        align: center middle;
        width: 100%;
        height: auto;
        padding: 3;
        display: none;
    }

    .text-error {
        color: $error;
        text-align: center;
        width: 100%;
    }

    /* Bookmark toggle button styling */
    .bookmark-toggle {
        width: auto;
        margin: 0 1;
        padding: 0 2;
    }

    .bookmark-toggle.bookmarked {
        background: $warning;
        color: $text;
    }
    """
    )

    SCREENS = {
        "main": MainMenuScreen,
        "practice": PracticeScreen,
        "session": SessionScreen,
        "stats": ProgressScreen,
        "settings": SettingsScreen,
        "bookmarks": BookmarkScreen,
    }

    def __init__(
        self,
        event_bus: EventBusInterface,
        session_workflow: SessionWorkflow,
        query_service: GetSessionProgressQueryHandler,
        user_repository=None,
        container=None,
        **kwargs: Any,
    ):
        """Initialize the trainer app."""
        super().__init__(
            event_bus=event_bus,
            **kwargs,
        )

        self.session_workflow = session_workflow
        self.query_service = query_service
        self.user_repository = user_repository
        self.container = container  # Store the container for service access

        # Set app title
        self.title = "Integran - German Integration Exam Trainer"
        self.sub_title = "Terminal-based spaced repetition learning"

    async def setup_event_handlers(self) -> None:
        """Setup global event handlers for the app."""
        # Domain events are part of the shared kernel and can be imported
        from src.domain.shared.events import CardScheduledEvent, LeechDetectedEvent

        # Subscribe to card scheduled events for UI updates
        self.event_bus.subscribe(CardScheduledEvent, self._handle_card_scheduled)

        # Subscribe to leech detection for notifications
        self.event_bus.subscribe(LeechDetectedEvent, self._handle_leech_detected)

        logger.info("Event handlers setup complete")

    async def _handle_card_scheduled(self, event: Any) -> None:
        """Handle card scheduled events for UI updates."""
        logger.debug(f"Card {event.card_id} scheduled for {event.next_review_date}")
        # Could update UI elements if needed

    async def _handle_leech_detected(self, event: Any) -> None:
        """Handle leech detection events."""
        logger.info(
            f"Leech detected: Card {event.card_id} with {event.lapse_count} lapses"
        )
        # Could show notification to user

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
