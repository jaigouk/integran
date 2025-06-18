"""Session management view for learning sessions."""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, ProgressBar, Static

from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.presentation.terminal.base import EventAwareWidget

logger = logging.getLogger(__name__)


class SessionProgressWidget(EventAwareWidget):
    """Widget for displaying session progress and statistics."""

    def __init__(self, event_bus: EventBus, **kwargs: Any):
        super().__init__(event_bus=event_bus, **kwargs)
        self.questions_answered = 0
        self.total_questions = 0
        self.correct_answers = 0
        self.session_time = 0

    def compose(self) -> ComposeResult:
        """Compose the session progress widget."""
        with Container(classes="session-progress"):
            yield Static("Session Progress", classes="progress-title")

            with Horizontal(classes="progress-stats"):
                yield Static("0/0", id="question-counter", classes="stat-item")
                yield Static("0%", id="accuracy", classes="stat-item")
                yield Static("00:00", id="session-time", classes="stat-item")

            yield ProgressBar(
                total=100,
                show_eta=False,
                show_percentage=True,
                id="progress-bar",
                classes="session-progress-bar",
            )

            with Vertical(classes="session-controls"):
                yield Button("Pause Session", id="pause", variant="warning")
                yield Button("End Session", id="end", variant="error")

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        # TODO: Subscribe to session progress events
        pass

    def update_progress(
        self,
        answered: int,
        total: int,
        correct: int,
        time_elapsed: int,
    ) -> None:
        """Update session progress display."""
        self.questions_answered = answered
        self.total_questions = total
        self.correct_answers = correct
        self.session_time = time_elapsed

        # Update question counter
        counter = self.query_one("#question-counter", Static)
        counter.update(f"{answered}/{total}")

        # Update accuracy
        accuracy = (correct / answered * 100) if answered > 0 else 0
        accuracy_widget = self.query_one("#accuracy", Static)
        accuracy_widget.update(f"{accuracy:.1f}%")

        # Update time
        minutes, seconds = divmod(time_elapsed, 60)
        time_widget = self.query_one("#session-time", Static)
        time_widget.update(f"{minutes:02d}:{seconds:02d}")

        # Update progress bar
        progress = (answered / total * 100) if total > 0 else 0
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)


class SessionScreen(Screen):
    """Screen for managing learning sessions."""

    CSS = """
    .session-container {
        align: center middle;
        width: 80%;
        max-width: 100;
        background: $surface;
        border: solid white;
        padding: 2;
        margin: 1;
    }

    .session-progress {
        width: 100%;
        background: $background;
        border: solid white;
        padding: 2;
        margin-bottom: 2;
    }

    .progress-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }

    .progress-stats {
        align: center middle;
        width: 100%;
        margin: 2;
        margin-bottom: 2;
    }

    .stat-item {
        text-align: center;
        width: 1fr;
        background: $accent 20%;
        padding: 1;
        border: solid white;
    }

    .session-progress-bar {
        width: 100%;
        margin-bottom: 2;
    }

    .session-controls {
        align: center middle;
        width: 100%;
        margin: 1;
    }

    .session-controls Button {
        width: 1fr;
        height: 3;
    }

    .session-info {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .session-actions {
        align: center middle;
        width: 100%;
        margin: 1;
    }

    .session-actions Button {
        width: 1fr;
        height: 3;
    }
    """

    BINDINGS = [
        ("p", "pause_session", "Pause"),
        ("e", "end_session", "End Session"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(
        self,
        session_workflow: SessionWorkflow,
        practice_mode: str = "random",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.session_workflow = session_workflow
        self.practice_mode = practice_mode
        self.session_active = False
        self.session_paused = False
        self.current_session_id: int | None = None
        self.session_questions: list = []

    def compose(self) -> ComposeResult:
        """Compose the session screen."""
        yield Container(
            Static(
                f"Learning Session - {self.practice_mode.title()}",
                classes="session-info",
            ),
            SessionProgressWidget(
                event_bus=self.app.event_bus,
                id="session-progress",
            ),
            Static(
                "Session controls and question display will appear here",
                classes="session-info",
            ),
            Horizontal(
                Button("Start Session", id="start", variant="success"),
                Button("Configure", id="configure", variant="default"),
                Button("Back to Menu", id="back", variant="default"),
                classes="session-actions",
            ),
            classes="session-container",
        )

    async def on_mount(self) -> None:
        """Initialize session when screen mounts."""
        logger.info(f"Session screen mounted for {self.practice_mode} mode")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "start":
            await self.start_session()
        elif button_id == "pause":
            await self.pause_session()
        elif button_id == "end":
            await self.end_session()
        elif button_id == "configure":
            await self.configure_session()
        elif button_id == "back":
            self.app.pop_screen()

    async def start_session(self) -> None:
        """Start a new learning session."""
        if self.session_active:
            return

        logger.info(f"Starting {self.practice_mode} session")

        try:
            # Create session configuration based on practice mode
            from src.domain.learning.services.complete_learning_session import (
                SessionConfig,
                SessionType,
            )

            # Map practice mode to session type
            session_type_map = {
                "review": SessionType.REVIEW,
                "learn": SessionType.LEARN,
                "random": SessionType.MIXED,
                "quiz": SessionType.QUIZ,
                "weak": SessionType.WEAK_FOCUS,
            }

            session_type = session_type_map.get(self.practice_mode, SessionType.MIXED)

            # Create session configuration
            config = SessionConfig(
                session_type=session_type,
                max_reviews=20,  # Reasonable session size
                max_new_cards=10,
                target_retention=0.9,
                time_limit_minutes=30,  # 30 minute sessions
                categories=None,  # Use all categories
                shuffle_questions=True,
            )

            # Start session using workflow
            result = await self.session_workflow.start_session(config, user_id=1)

            if result["success"]:
                self.session_active = True
                self.session_paused = False
                self.current_session_id = result["session_id"]
                self.session_questions = result["questions"]

                logger.info(
                    f"Successfully started session {self.current_session_id} with {len(self.session_questions)} questions"
                )

                # Update progress display with real data
                progress_widget = self.query_one(
                    "#session-progress", SessionProgressWidget
                )
                progress_widget.update_progress(0, len(self.session_questions), 0, 0)

                # Update button
                start_button = self.query_one("#start", Button)
                start_button.label = "Session Running"
                start_button.variant = "primary"
                start_button.disabled = True

                self.notify(
                    f"Started {session_type.value} session with {len(self.session_questions)} questions"
                )
            else:
                self.notify("Failed to start session", severity="error")
                logger.error("Failed to start session through workflow")

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.notify("Error starting session - check logs", severity="error")

    async def pause_session(self) -> None:
        """Pause or resume the current session."""
        if not self.session_active:
            return

        if self.session_paused:
            # Resume session
            logger.info("Resuming session")
            self.session_paused = False

            pause_button = self.query_one("#pause", Button)
            pause_button.label = "Pause Session"
            pause_button.variant = "warning"

            self.notify("Session resumed")
        else:
            # Pause session
            logger.info("Pausing session")
            self.session_paused = True

            pause_button = self.query_one("#pause", Button)
            pause_button.label = "Resume Session"
            pause_button.variant = "success"

            self.notify("Session paused")

    async def end_session(self) -> None:
        """End the current session."""
        if not self.session_active:
            return

        logger.info("Ending session")

        try:
            # Complete session using workflow if we have a session ID
            if self.current_session_id is not None:
                result = await self.session_workflow.complete_session(
                    self.current_session_id
                )

                if result["success"]:
                    session_summary = result["summary"]
                    logger.info(
                        f"Successfully completed session {self.current_session_id}"
                    )

                    # Show session summary
                    accuracy = (
                        session_summary.get("correct_answers", 0)
                        / max(session_summary.get("total_questions", 1), 1)
                    ) * 100

                    summary_text = (
                        f"Session Complete!\n"
                        f"Questions: {session_summary.get('total_questions', 0)}\n"
                        f"Correct: {session_summary.get('correct_answers', 0)}\n"
                        f"Accuracy: {accuracy:.1f}%"
                    )

                    self.notify(summary_text, title="Session Summary")
                else:
                    logger.error("Failed to complete session through workflow")
                    self.notify(
                        "Session ended but summary unavailable", severity="warning"
                    )

            # Reset session state
            self.session_active = False
            self.session_paused = False
            self.current_session_id = None
            self.session_questions = []

            # Reset UI
            start_button = self.query_one("#start", Button)
            start_button.label = "Start Session"
            start_button.variant = "success"
            start_button.disabled = False

            # Reset pause button
            pause_button = self.query_one("#pause", Button)
            pause_button.label = "Pause Session"
            pause_button.variant = "warning"

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            self.notify("Error ending session - check logs", severity="error")

    async def configure_session(self) -> None:
        """Configure session settings."""
        logger.info("Opening session configuration")

        # For now, show available configuration options as a notification
        # In a full implementation, this would open a configuration screen/modal
        config_options = [
            f"Current mode: {self.practice_mode}",
            "Available modes: review, learn, random, quiz, weak",
            "Session settings: 20 reviews, 10 new cards, 30 min limit",
            "Use Settings screen to modify preferences",
        ]

        config_text = "\n".join(config_options)
        self.notify(config_text, title="Session Configuration")

    def action_pause_session(self) -> None:
        """Pause session via keyboard."""
        self.run_action("pause_session")

    def action_end_session(self) -> None:
        """End session via keyboard."""
        self.run_action("end_session")

    def action_back_to_menu(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
