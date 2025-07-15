"""Session management view for learning sessions."""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, ProgressBar, Static

from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.domain.shared.services import EventBusInterface
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class SessionProgressWidget(EventAwareWidget):
    """Widget for displaying rich session progress and analytics."""

    def __init__(self, event_bus: EventBusInterface, **kwargs: Any):
        super().__init__(event_bus=event_bus, **kwargs)
        self.questions_answered = 0
        self.total_questions = 0
        self.correct_answers = 0
        self.session_time = 0

        # Enhanced analytics tracking
        self.new_cards_learned = 0
        self.review_cards_completed = 0
        self.response_times = []
        self.difficulty_distribution = {"New": 0, "Learning": 0, "Review": 0, "Hard": 0}
        self.category_performance = {}
        self.predicted_retention = 0.0
        self.learning_velocity = 0.0

    def compose(self) -> ComposeResult:
        """Compose the enhanced session progress widget with rich analytics."""
        with Container(classes="session-progress"):
            yield Static("Session Progress & Analytics", classes="text-section-header")

            # Primary progress stats
            with Horizontal(classes="progress-stats"):
                yield Static("0/0", id="question-counter", classes="stat-item")
                yield Static("0%", id="accuracy", classes="stat-item")
                yield Static("00:00", id="session-time", classes="stat-item")
                yield Static("0.0s avg", id="avg-response-time", classes="stat-item")

            yield ProgressBar(
                total=100,
                show_eta=False,
                show_percentage=True,
                id="progress-bar",
                classes="session-progress-bar",
            )

            # Rich analytics panel
            with Container(classes="analytics-panel"):
                yield Static("Session Analytics", classes="analytics-header")

                with Horizontal(classes="analytics-row"):
                    with Vertical(classes="analytics-column"):
                        yield Static("Card Distribution", classes="analytics-label")
                        yield Static(
                            "New: 0 | Learning: 0 | Review: 0 | Hard: 0",
                            id="difficulty-distribution",
                            classes="analytics-value",
                        )

                        yield Static("Learning Progress", classes="analytics-label")
                        yield Static(
                            "New Cards: 0 | Reviews: 0",
                            id="card-progress",
                            classes="analytics-value",
                        )

                    with Vertical(classes="analytics-column"):
                        yield Static("Performance Insights", classes="analytics-label")
                        yield Static(
                            "Retention: 0% | Velocity: Normal",
                            id="performance-insights",
                            classes="analytics-value",
                        )

                        yield Static("Recommendations", classes="analytics-label")
                        yield Static(
                            "Starting session...",
                            id="session-recommendations",
                            classes="analytics-value",
                        )

            with Vertical(classes="session-controls"):
                yield Button("Pause Session", id="pause", variant="warning")
                yield Button("End Session", id="end", variant="error")

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        # Domain events are part of the shared kernel and can be imported
        from src.domain.shared.events import (
            CardScheduledEvent,
            SessionCompletedEvent,
            SessionPausedEvent,
            SessionStartedEvent,
        )

        # Subscribe to session-related events for real-time progress updates
        self.subscribe_to_event(SessionStartedEvent, self._handle_session_started)
        self.subscribe_to_event(SessionCompletedEvent, self._handle_session_completed)
        self.subscribe_to_event(SessionPausedEvent, self._handle_session_paused)
        self.subscribe_to_event(CardScheduledEvent, self._handle_card_scheduled)

        logger.debug(f"{self.__class__.__name__} subscribed to session progress events")

    def update_progress(
        self,
        answered: int,
        total: int,
        correct: int,
        time_elapsed: int,
        response_time_ms: int = 0,
        difficulty_rating: str = "",
        is_new_card: bool = False,
        category: str = "",
    ) -> None:
        """Update enhanced session progress display with rich analytics."""
        self.questions_answered = answered
        self.total_questions = total
        self.correct_answers = correct
        self.session_time = time_elapsed

        # Track analytics data
        if response_time_ms > 0:
            self.response_times.append(response_time_ms)

        if difficulty_rating and difficulty_rating in self.difficulty_distribution:
            self.difficulty_distribution[difficulty_rating] += 1

        if is_new_card:
            self.new_cards_learned += 1
        else:
            self.review_cards_completed += 1

        if category:
            if category not in self.category_performance:
                self.category_performance[category] = {"correct": 0, "total": 0}
            self.category_performance[category]["total"] += 1
            if correct > 0:  # If this question was correct
                self.category_performance[category]["correct"] += 1

        # Update primary stats
        counter = self.query_one("#question-counter", Static)
        counter.update(f"{answered}/{total}")

        accuracy = (correct / answered * 100) if answered > 0 else 0
        accuracy_widget = self.query_one("#accuracy", Static)
        accuracy_widget.update(f"{accuracy:.1f}%")

        minutes, seconds = divmod(time_elapsed, 60)
        time_widget = self.query_one("#session-time", Static)
        time_widget.update(f"{minutes:02d}:{seconds:02d}")

        # Update average response time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )
        avg_time_widget = self.query_one("#avg-response-time", Static)
        avg_time_widget.update(f"{avg_response_time / 1000:.1f}s avg")

        # Update progress bar
        progress = (answered / total * 100) if total > 0 else 0
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)

        # Update analytics displays
        self._update_analytics_display()

    def _update_analytics_display(self) -> None:
        """Update the rich analytics display panels."""
        try:
            # Update difficulty distribution
            dist_widget = self.query_one("#difficulty-distribution", Static)
            dist_text = " | ".join(
                [
                    f"{difficulty}: {count}"
                    for difficulty, count in self.difficulty_distribution.items()
                ]
            )
            dist_widget.update(dist_text)

            # Update card progress
            progress_widget = self.query_one("#card-progress", Static)
            progress_widget.update(
                f"New Cards: {self.new_cards_learned} | Reviews: {self.review_cards_completed}"
            )

            # Calculate and update performance insights
            current_accuracy = (
                (self.correct_answers / self.questions_answered * 100)
                if self.questions_answered > 0
                else 0
            )

            # Calculate learning velocity (questions per minute)
            if self.session_time > 0:
                velocity = self.questions_answered / (self.session_time / 60)
                velocity_label = (
                    "Fast" if velocity > 2.0 else "Normal" if velocity > 1.0 else "Slow"
                )
            else:
                velocity_label = "Normal"

            insights_widget = self.query_one("#performance-insights", Static)
            insights_widget.update(
                f"Retention: {current_accuracy:.0f}% | Velocity: {velocity_label}"
            )

            # Generate adaptive recommendations
            recommendations = self._generate_recommendations()
            recommendations_widget = self.query_one("#session-recommendations", Static)
            recommendations_widget.update(recommendations)

        except Exception as e:
            logger.debug(f"Error updating analytics display: {e}")

    def _generate_recommendations(self) -> str:
        """Generate adaptive recommendations based on session performance."""
        if self.questions_answered == 0:
            return "Starting session..."

        current_accuracy = (
            (self.correct_answers / self.questions_answered * 100)
            if self.questions_answered > 0
            else 0
        )
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )

        recommendations = []

        # Accuracy-based recommendations
        if current_accuracy < 70:
            recommendations.append("Focus on comprehension")
        elif current_accuracy > 90:
            recommendations.append("Excellent performance!")

        # Response time recommendations
        if avg_response_time > 15000:  # > 15 seconds
            recommendations.append("Take your time")
        elif avg_response_time < 3000:  # < 3 seconds
            recommendations.append("Great speed!")

        # Session length recommendations
        if self.questions_answered > 15:
            recommendations.append("Consider a break soon")

        # Category-based recommendations
        if self.category_performance:
            weak_categories = [
                cat
                for cat, perf in self.category_performance.items()
                if perf["total"] > 1 and (perf["correct"] / perf["total"]) < 0.7
            ]
            if weak_categories:
                recommendations.append(f"Review {weak_categories[0]} category")

        return (
            " | ".join(recommendations) if recommendations else "Keep up the good work!"
        )

    async def _handle_session_started(self, event) -> None:
        """Handle SessionStartedEvent to initialize session progress."""
        try:
            # Reset progress counters
            self.questions_answered = 0
            self.total_questions = event.max_reviews
            self.correct_answers = 0
            self.session_time = 0

            # Update UI components
            self.update_progress(0, event.max_reviews, 0, 0)
            logger.debug(
                f"Session started: {event.session_id} with {event.max_reviews} max reviews"
            )
        except Exception as e:
            logger.error(f"Error handling session started event: {e}")

    async def _handle_session_completed(self, event) -> None:
        """Handle SessionCompletedEvent to finalize session display."""
        try:
            # Update final session statistics
            self.questions_answered = event.questions_reviewed
            self.correct_answers = event.questions_correct
            self.session_time = event.duration_seconds

            # Update UI with final stats
            self.update_progress(
                event.questions_reviewed,
                event.questions_reviewed,  # Total equals answered for completed session
                event.questions_correct,
                event.duration_seconds,
            )
            logger.debug(
                f"Session completed: {event.session_id} - {event.questions_correct}/{event.questions_reviewed} correct"
            )
        except Exception as e:
            logger.error(f"Error handling session completed event: {e}")

    async def _handle_session_paused(self, event) -> None:
        """Handle SessionPausedEvent to update pause/resume state."""
        try:
            # Update session time if pausing
            if event.is_paused and event.pause_duration_seconds:
                self.session_time += event.pause_duration_seconds

            # Update button states (could be implemented in UI)
            pause_button = self.query_one("#pause", Button)
            if event.is_paused:
                pause_button.label = "Resume Session"
                pause_button.variant = "success"
            else:
                pause_button.label = "Pause Session"
                pause_button.variant = "warning"

            logger.debug(
                f"Session {'paused' if event.is_paused else 'resumed'}: {event.session_id}"
            )
        except Exception as e:
            logger.error(f"Error handling session paused event: {e}")

    async def _handle_card_scheduled(self, event) -> None:
        """Handle CardScheduledEvent to update progress after each question."""
        try:
            # Increment questions answered
            self.questions_answered += 1

            # Update correct answers if rating indicates success (Good=3, Easy=4)
            if event.rating >= 3:
                self.correct_answers += 1

            # Update UI with new progress
            self.update_progress(
                self.questions_answered,
                self.total_questions,
                self.correct_answers,
                self.session_time,
            )
            logger.debug(
                f"Card scheduled: Q{event.question_id} with rating {event.rating}"
            )
        except Exception as e:
            logger.error(f"Error handling card scheduled event: {e}")


class SessionScreen(Screen):
    """Screen for managing learning sessions."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Session view specific styling */
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

    /* Enhanced analytics styling */
    .analytics-panel {
        width: 100%;
        background: $surface;
        border: solid white;
        padding: 2;
        margin: 2 0;
    }

    .analytics-header {
        text-style: bold;
        color: $secondary;
        text-align: center;
        margin-bottom: 1;
    }

    .analytics-row {
        width: 100%;
        margin: 1 0;
    }

    .analytics-column {
        width: 1fr;
        padding: 0 1;
    }

    .analytics-label {
        text-style: bold;
        color: $accent;
        margin: 1 0;
        font-size: 90%;
    }

    .analytics-value {
        color: $text;
        background: $background;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
        word-wrap: break-word;
    }

    .progress-stats .stat-item {
        min-width: 12;
    }
    """
    )

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
                classes="text-title",
            ),
            SessionProgressWidget(
                event_bus=self.app.event_bus,
                id="session-progress",
            ),
            Static(
                "Session controls and question display will appear here",
                classes="text-help",
            ),
            Horizontal(
                Button("Start Session", id="start", variant="success"),
                Button("Configure", id="configure", variant="default"),
                Button("Back to Menu", id="back", variant="default"),
                classes="buttons-horizontal",
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
            # Create session through application layer command
            # The practice mode will be handled by the session workflow

            # For now, we'll use the workflow directly since it handles the session creation
            # In a full CQRS implementation, this would go through a command handler
            result = await self.session_workflow.start_session(
                practice_mode=self.practice_mode, max_questions=20, user_id=1
            )

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
                    f"Started {self.practice_mode} session with {len(self.session_questions)} questions"
                )
            else:
                self.notify("Failed to start session", severity="error")
                logger.error("Failed to start session through workflow")

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.notify("Error starting session - check logs", severity="error")

    async def pause_session(self) -> None:
        """Pause or resume the current session."""
        if not self.session_active or self.current_session_id is None:
            return

        try:
            # Get command handler from container
            pause_command_handler = (
                self.app.container.get_pause_session_command_handler()
            )

            # Create command
            from src.application.commands.pause_session_command import (
                PauseSessionCommand,
            )

            command = PauseSessionCommand(
                session_id=self.current_session_id,
                is_pause=not self.session_paused,  # Toggle current state
                user_id=1,
            )

            # Execute command through domain service
            result = await pause_command_handler.handle(command)

            if result.success:
                # Update UI state based on result
                self.session_paused = result.is_paused

                pause_button = self.query_one("#pause", Button)
                if result.is_paused:
                    pause_button.label = "Resume Session"
                    pause_button.variant = "success"
                    self.notify("Session paused")
                    logger.info(f"Session {self.current_session_id} paused")
                else:
                    pause_button.label = "Pause Session"
                    pause_button.variant = "warning"
                    pause_message = "Session resumed"
                    if result.pause_duration_seconds:
                        duration_min = result.pause_duration_seconds // 60
                        pause_message += f" (paused for {duration_min} minutes)"
                    self.notify(pause_message)
                    logger.info(f"Session {self.current_session_id} resumed")
            else:
                self.notify(
                    f"Failed to {'pause' if not self.session_paused else 'resume'} session: {result.error_message}",
                    severity="error",
                )
                logger.error(
                    f"Failed to {'pause' if not self.session_paused else 'resume'} session: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Error during session pause/resume: {e}")
            self.notify("Error pausing/resuming session - check logs", severity="error")

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

                    # Get session analytics from progress widget
                    progress_widget = self.query_one(
                        "#session-progress", SessionProgressWidget
                    )

                    # Show comprehensive session summary
                    accuracy = (
                        session_summary.get("correct_answers", 0)
                        / max(session_summary.get("total_questions", 1), 1)
                    ) * 100

                    # Calculate session insights
                    avg_response_time = (
                        sum(progress_widget.response_times)
                        / len(progress_widget.response_times)
                        if progress_widget.response_times
                        else 0
                    )

                    # Generate comprehensive summary
                    summary_lines = [
                        "📊 Session Complete!",
                        f"Questions: {session_summary.get('total_questions', 0)}",
                        f"Correct: {session_summary.get('correct_answers', 0)}",
                        f"Accuracy: {accuracy:.1f}%",
                        f"Avg Response: {avg_response_time / 1000:.1f}s",
                        "",
                        "📈 Learning Progress:",
                        f"New Cards Learned: {progress_widget.new_cards_learned}",
                        f"Review Cards: {progress_widget.review_cards_completed}",
                        "",
                        "🎯 Performance Analysis:",
                    ]

                    # Add performance insights
                    if accuracy >= 90:
                        summary_lines.append("⭐ Excellent mastery!")
                    elif accuracy >= 80:
                        summary_lines.append("✅ Good performance")
                    elif accuracy >= 70:
                        summary_lines.append("⚠️ Needs improvement")
                    else:
                        summary_lines.append("🔄 Review recommended")

                    # Add category insights if available
                    if progress_widget.category_performance:
                        weak_categories = [
                            cat
                            for cat, perf in progress_widget.category_performance.items()
                            if perf["total"] > 1
                            and (perf["correct"] / perf["total"]) < 0.7
                        ]
                        if weak_categories:
                            summary_lines.append(
                                f"Focus areas: {', '.join(weak_categories[:2])}"
                            )

                    # Add next session recommendation
                    summary_lines.append("")
                    summary_lines.append("🔮 Next Session:")
                    if accuracy > 85:
                        summary_lines.append("Ready for new content!")
                    else:
                        summary_lines.append("Review difficult cards")

                    summary_text = "\n".join(summary_lines)
                    self.notify(summary_text, title="Comprehensive Session Analysis")
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
