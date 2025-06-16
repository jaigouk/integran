"""Question display component with FSRS rating support."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Static

from src.domain.content.models.question_models import Question
from src.infrastructure.messaging.event_bus import EventBus
from src.presentation.terminal.base import EventAwareWidget

logger = logging.getLogger(__name__)


class QuestionWidget(EventAwareWidget):
    """Widget for displaying a single question with answer options."""

    def __init__(self, question: Question, event_bus: EventBus, **kwargs: Any):
        super().__init__(event_bus=event_bus, **kwargs)
        self.question = question
        self.selected_answer: str | None = None
        self.answer_revealed = False

    def compose(self) -> ComposeResult:
        """Compose the question widget."""
        with Container(classes="question-container"):
            yield Static(f"Question {self.question.id}", classes="question-number")
            yield Static(self.question.question, classes="question-text")

            with Vertical(classes="answer-options"):
                for i, option in enumerate(self.question.options, 1):
                    yield Button(
                        f"{i}. {option}",
                        id=f"option_{i}",
                        variant="default",
                        classes="answer-option",
                    )

            # Initially hidden - shown after answer selection
            yield Container(
                Static("", id="result-text", classes="result-text"),
                Static("", id="correct-answer", classes="correct-answer"),
                Static("", id="explanation", classes="explanation"),
                classes="answer-result hidden",
            )

            # FSRS rating buttons - shown after answer reveal
            yield Container(
                Static("How well did you know this?", classes="rating-prompt"),
                Horizontal(
                    Button(
                        "1. Again", id="rating_1", variant="error", classes="rating-btn"
                    ),
                    Button(
                        "2. Hard",
                        id="rating_2",
                        variant="warning",
                        classes="rating-btn",
                    ),
                    Button(
                        "3. Good",
                        id="rating_3",
                        variant="success",
                        classes="rating-btn",
                    ),
                    Button(
                        "4. Easy",
                        id="rating_4",
                        variant="primary",
                        classes="rating-btn",
                    ),
                    classes="rating-buttons",
                ),
                classes="fsrs-rating hidden",
            )

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        # No domain event subscriptions needed for this widget
        pass

    @on(Button.Pressed, ".answer-option")
    async def on_answer_selected(self, event: Button.Pressed) -> None:
        """Handle answer option selection."""
        if self.answer_revealed:
            return

        # Extract option number from button ID
        option_num = int(event.button.id.split("_")[1])
        self.selected_answer = self.question.options[option_num - 1]

        # Highlight selected option
        for i in range(1, 5):
            btn = self.query_one(f"#option_{i}", Button)
            if i == option_num:
                btn.variant = "primary"
                btn.add_class("selected")
            else:
                btn.disabled = True

        # Reveal the answer
        await self.reveal_answer()

    @on(Button.Pressed, ".rating-btn")
    async def on_rating_selected(self, event: Button.Pressed) -> None:
        """Handle FSRS rating selection."""
        rating = int(event.button.id.split("_")[1])

        # Publish answer submission event
        await self.submit_answer_with_rating(rating)

        # Notify parent that we're ready for next question
        self.post_message(self.QuestionCompleted(rating))

    async def reveal_answer(self) -> None:
        """Reveal the correct answer and explanation."""
        self.answer_revealed = True

        # Show result
        result_container = self.query_one(".answer-result")
        result_container.remove_class("hidden")

        # Update result text
        is_correct = self.selected_answer == self.question.correct
        result_text = self.query_one("#result-text", Static)
        if is_correct:
            result_text.update("[green]✓ Correct![/green]")
        else:
            result_text.update("[red]✗ Incorrect[/red]")

        # Show correct answer
        correct_answer = self.query_one("#correct-answer", Static)
        correct_answer.update(f"Correct answer: [bold]{self.question.correct}[/bold]")

        # Show explanation if available
        if hasattr(self.question, "explanation") and self.question.explanation:
            explanation = self.query_one("#explanation", Static)
            explanation.update(f"Explanation: {self.question.explanation}")

        # Show FSRS rating buttons
        rating_container = self.query_one(".fsrs-rating")
        rating_container.remove_class("hidden")

    async def submit_answer_with_rating(self, rating: int) -> None:
        """Submit the answer with FSRS rating to the domain."""
        # TODO: Create and publish AnswerSubmittedEvent
        logger.info(
            f"Answer submitted: Q{self.question.id}, "
            f"Selected: {self.selected_answer}, "
            f"Correct: {self.question.correct}, "
            f"Rating: {rating}"
        )

    class QuestionCompleted(Message):
        """Message sent when question is completed with rating."""

        def __init__(self, rating: int):
            super().__init__()
            self.rating = rating


class PracticeScreen(Screen):
    """Screen for practicing questions."""

    CSS = """
    .question-container {
        align: center middle;
        width: 80%;
        max-width: 100;
        background: $surface;
        border: solid $primary;
        padding: 2;
        margin: 1;
    }

    .question-number {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }

    .question-text {
        text-align: left;
        margin-bottom: 2;
        word-wrap: break-word;
    }

    .answer-options {
        spacing: 1;
        margin-bottom: 2;
    }

    .answer-option {
        width: 100%;
        height: 3;
        text-align: left;
    }

    .answer-option.selected {
        border: solid $primary;
        text-style: bold;
    }

    .answer-result {
        margin: 2 0;
        padding: 1;
        background: $background;
        border: solid $muted;
    }

    .result-text {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .correct-answer {
        text-align: center;
        margin-bottom: 1;
    }

    .explanation {
        text-align: left;
        color: $text-muted;
    }

    .fsrs-rating {
        margin-top: 2;
        padding: 1;
        background: $accent-alpha;
        border: solid $accent;
    }

    .rating-prompt {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .rating-buttons {
        align: center middle;
        width: 100%;
        spacing: 1;
    }

    .rating-btn {
        width: 1fr;
        height: 3;
    }

    .hidden {
        display: none;
    }
    """

    BINDINGS = [
        ("1", "select_option_1", "Option 1"),
        ("2", "select_option_2", "Option 2"),
        ("3", "select_option_3", "Option 3"),
        ("4", "select_option_4", "Option 4"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(self, practice_mode: str = "random", **kwargs: Any):
        super().__init__(**kwargs)
        self.practice_mode = practice_mode
        self.current_question: Question | None = None
        self.questions_answered = 0
        self.correct_answers = 0

    def compose(self) -> ComposeResult:
        """Compose the practice screen."""
        yield Container(
            Static(
                f"Practice Mode: {self.practice_mode.title()}", classes="mode-title"
            ),
            Static("Loading question...", id="question-container"),
            classes="practice-container",
        )

    async def on_mount(self) -> None:
        """Load first question when screen mounts."""
        await self.load_next_question()

    async def load_next_question(self) -> None:
        """Load the next question for practice."""
        # TODO: Get question from session workflow
        # For now, create a dummy question
        self.current_question = Question(
            id=1,
            question="Was ist die Hauptstadt von Deutschland?",
            options=["Berlin", "München", "Hamburg", "Köln"],
            correct="Berlin",
            category="Geschichte",
            difficulty="easy",
        )

        # Create question widget
        question_widget = QuestionWidget(
            question=self.current_question,
            event_bus=self.app.event_bus,
        )

        # Replace the loading text with the question widget
        container = self.query_one("#question-container")
        await container.remove()
        await self.mount(question_widget)

    def action_select_option_1(self) -> None:
        """Select option 1 via keyboard."""
        self._select_option(1)

    def action_select_option_2(self) -> None:
        """Select option 2 via keyboard."""
        self._select_option(2)

    def action_select_option_3(self) -> None:
        """Select option 3 via keyboard."""
        self._select_option(3)

    def action_select_option_4(self) -> None:
        """Select option 4 via keyboard."""
        self._select_option(4)

    def _select_option(self, option_num: int) -> None:
        """Select an option by number."""
        try:
            btn = self.query_one(f"#option_{option_num}", Button)
            btn.press()
        except Exception as e:
            # Button not found or not available
            logger.debug(f"Could not select option {option_num}: {e}")

    def action_back_to_menu(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    @on(QuestionWidget.QuestionCompleted)
    async def on_question_completed(
        self, event: QuestionWidget.QuestionCompleted
    ) -> None:
        """Handle question completion."""
        self.questions_answered += 1

        if self.current_question and event.rating in [3, 4]:  # Good or Easy
            self.correct_answers += 1

        # TODO: Load next question or end session
        logger.info(f"Question completed with rating {event.rating}")
