"""Enhanced question display component with rich multilingual content support."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Static, TabbedContent, TabPane

from src.domain.content.models.question_models import Question
from src.domain.content.services.enhanced_question_display import (
    EnhancedQuestionData,
    EnhancedQuestionDisplay,
    EnhancedQuestionDisplayRequest,
)
from src.domain.user.models.user_models import Language
from src.domain.user.services.load_user_settings import (
    LoadUserSettings,
    LoadUserSettingsRequest,
)
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class QuestionWidget(EventAwareWidget):
    """Widget for displaying a single question with enhanced multilingual content."""

    def __init__(
        self,
        question: Question,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
        submit_answer_command_handler=None,
        preferred_language: Language = Language.ENGLISH,
        session_id: int | None = None,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.question = question
        self.user_repository = user_repository
        self.submit_answer_command_handler = submit_answer_command_handler
        self.preferred_language = preferred_language
        self.session_id = session_id
        self.selected_answer: str | None = None
        self.answer_revealed = False
        self.enhanced_data: EnhancedQuestionData | None = None
        self.enhanced_service = EnhancedQuestionDisplay(event_bus)
        self.load_user_settings_service = LoadUserSettings(event_bus, user_repository)
        self.user_preferences = None  # Will be loaded from user settings

    def compose(self) -> ComposeResult:
        """Compose the enhanced question widget with tab-based navigation."""
        # Tab-based content organization
        with TabbedContent(initial="question-tab", classes="question-tabs"):
            # Tab 1: Question and Answer
            with TabPane("Question", id="question-tab", classes="question-pane"):  # noqa: SIM117
                with VerticalScroll(classes="question-container"):  # noqa: SIM117
                    # Question header
                    yield Static(f"Question {self.question.id}", classes="text-title")
                    yield Static(
                        f"Category: {self.question.category}",
                        classes="text-subtitle",
                    )
                    yield Static(self.question.question, classes="question-text")

                    # Answer options
                    with Vertical(classes="answer-options"):
                        for i, option in enumerate(self.question.options_list, 1):
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
                        classes="answer-result hidden",
                    )

            # Tab 2: Learning Content
            with TabPane("Learn More", id="learn-tab", classes="learn-pane"):  # noqa: SIM117
                with VerticalScroll(classes="learn-container"):  # noqa: SIM117
                    # Enhanced content - shown after answer reveal
                    yield Container(
                        # Rich explanation with multilingual support
                        Collapsible(
                            Static(
                                "",
                                id="detailed-explanation",
                                classes="rich-explanation",
                            ),
                            title="📝 Detailed Explanation",
                            collapsed=False,
                            classes="content-section",
                        ),
                        # Key concept for educational understanding
                        Collapsible(
                            Static("", id="key-concept", classes="key-concept"),
                            title="🎯 Key Concept",
                            collapsed=False,
                            classes="content-section",
                        ),
                        # Memory technique
                        Collapsible(
                            Static("", id="mnemonic", classes="mnemonic"),
                            title="🧠 Memory Technique",
                            collapsed=True,
                            classes="content-section",
                        ),
                        # Wrong answer analysis
                        Collapsible(
                            Container(id="wrong-analysis", classes="wrong-analysis"),
                            title="❌ Why Other Options Are Wrong",
                            collapsed=True,
                            classes="content-section",
                        ),
                        # Image descriptions (for image questions)
                        Collapsible(
                            Container(
                                id="image-descriptions", classes="image-descriptions"
                            ),
                            title="🖼️ Image Descriptions",
                            collapsed=True,
                            classes="content-section hidden",
                        ),
                        classes="enhanced-content hidden",
                    )

        # Fixed FSRS rating buttons - always visible at bottom
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
        # Load user preferred language on startup
        await self._load_user_preferred_language()

    async def _load_user_preferred_language(self) -> None:
        """Load user's preferred language and progressive disclosure settings."""
        try:
            request = LoadUserSettingsRequest(user_id=1)
            result = await self.load_user_settings_service.call(request)

            if result.success and result.user_settings:
                # Update preferred language from user settings
                self.preferred_language = result.user_settings.language

                # Load progressive disclosure preferences from custom settings
                self.user_preferences = result.user_settings.preferences
                logger.info(
                    f"Loaded user preferred language: {self.preferred_language.value}"
                )
            else:
                logger.warning(
                    f"Could not load user settings, using default language: {self.preferred_language.value}"
                )

        except Exception as e:
            logger.error(f"Error loading user preferred language: {e}")
            # Keep default language

    def _should_expand_explanation(self) -> bool:
        """Determine if explanation section should be expanded by default."""
        if self.user_preferences:
            # Check if user wants explanations shown
            if not self.user_preferences.show_explanations:
                return False
            # Check custom setting for auto-expansion
            return self.user_preferences.custom_settings.get(
                "auto_expand_explanation", True
            )
        return True  # Default: expanded

    def _should_expand_key_concepts(self) -> bool:
        """Determine if key concepts section should be expanded by default."""
        if self.user_preferences:
            return self.user_preferences.custom_settings.get(
                "auto_expand_key_concepts", True
            )
        return True  # Default: expanded

    def _should_expand_mnemonics(self) -> bool:
        """Determine if mnemonics section should be expanded by default."""
        if self.user_preferences:
            return self.user_preferences.custom_settings.get(
                "auto_expand_mnemonics", False
            )
        return False  # Default: collapsed

    def _should_expand_wrong_analysis(self) -> bool:
        """Determine if wrong answer analysis should be expanded by default."""
        if self.user_preferences:
            return self.user_preferences.custom_settings.get(
                "auto_expand_wrong_analysis", False
            )
        return False  # Default: collapsed

    def _should_expand_image_descriptions(self) -> bool:
        """Determine if image descriptions should be expanded by default."""
        if self.user_preferences:
            return self.user_preferences.custom_settings.get(
                "auto_expand_images", False
            )
        return False  # Default: collapsed

    @on(Button.Pressed, ".answer-option")
    async def on_answer_selected(self, event: Button.Pressed) -> None:
        """Handle answer option selection."""
        if self.answer_revealed:
            return

        # Extract option number from button ID
        option_num = int(event.button.id.split("_")[1])
        self.selected_answer = self.question.options_list[option_num - 1]

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
        """Reveal the correct answer and enhanced multilingual content."""
        self.answer_revealed = True

        # Load enhanced content
        await self._load_enhanced_content()

        # Show basic result
        result_container = self.query_one(".answer-result")
        result_container.remove_class("hidden")

        # Update result text
        is_correct = self.selected_answer == self.question.correct
        result_text = self.query_one("#result-text", Static)
        if is_correct:
            result_text.update("[green]✓ Correct![/green]")
        else:
            result_text.update("[red]✗ Incorrect[/red]")

        # Show correct answer with enhanced info
        correct_answer = self.query_one("#correct-answer", Static)
        if self.enhanced_data:
            correct_answer.update(
                f"Correct answer: [bold]{self.enhanced_data.correct_answer_letter}. {self.enhanced_data.correct_answer}[/bold]"
            )
        else:
            correct_answer.update(
                f"Correct answer: [bold]{self.question.correct}[/bold]"
            )

        # Show enhanced content
        await self._display_enhanced_content()

        # Enable Learn More tab by showing enhanced content
        enhanced_container = self.query_one(".enhanced-content")
        enhanced_container.remove_class("hidden")

        # Show FSRS rating buttons
        rating_container = self.query_one(".fsrs-rating")
        rating_container.remove_class("hidden")

    async def _load_enhanced_content(self) -> None:
        """Load enhanced content from the enhanced question display service."""
        try:
            request = EnhancedQuestionDisplayRequest(
                question_id=self.question.id,
                preferred_language=self.preferred_language,
                include_wrong_analysis=True,
                include_key_concepts=True,
                include_mnemonics=True,
                include_image_descriptions=True,
            )

            result = await self.enhanced_service.call(request)

            if result.success and result.question_data:
                self.enhanced_data = result.question_data
                logger.info(f"Loaded enhanced content for question {self.question.id}")
            else:
                logger.warning(
                    f"Failed to load enhanced content: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Error loading enhanced content: {e}")

    async def _display_enhanced_content(self) -> None:
        """Display the enhanced multilingual content."""
        if not self.enhanced_data:
            return

        # Show enhanced content container
        enhanced_container = self.query_one(".enhanced-content")
        enhanced_container.remove_class("hidden")

        # Apply progressive disclosure preferences
        await self._apply_progressive_disclosure()

        # Display detailed explanation
        explanation_widget = self.query_one("#detailed-explanation", Static)
        explanation_widget.update(self.enhanced_data.multilingual_content.explanation)

        # Display key concept
        key_concept_widget = self.query_one("#key-concept", Static)
        key_concept_widget.update(self.enhanced_data.multilingual_content.key_concept)

        # Display mnemonic (if available)
        if self.enhanced_data.multilingual_content.mnemonic:
            mnemonic_widget = self.query_one("#mnemonic", Static)
            mnemonic_widget.update(self.enhanced_data.multilingual_content.mnemonic)
        else:
            # Hide mnemonic section if not available
            try:
                # Find the Collapsible that contains the mnemonic
                for collapsible in self.query("Collapsible").results():
                    if collapsible.query_one("#mnemonic", Static, fallback=None):
                        collapsible.add_class("hidden")
                        break
            except Exception as e:
                logger.debug(f"Could not hide mnemonic section: {e}")

        # Display wrong answer analysis
        await self._display_wrong_answer_analysis()

        # Display image descriptions (if image question)
        if self.enhanced_data.is_image_question and self.enhanced_data.images:
            await self._display_image_descriptions()
        else:
            # Hide image section for non-image questions
            try:
                # Find the Collapsible that contains the image descriptions
                for collapsible in self.query("Collapsible").results():
                    if collapsible.query_one(
                        "#image-descriptions", Container, fallback=None
                    ):
                        collapsible.add_class("hidden")
                        break
            except Exception as e:
                logger.debug(f"Could not hide image descriptions: {e}")

    async def _apply_progressive_disclosure(self) -> None:
        """Apply progressive disclosure preferences to collapsible sections."""
        try:
            # Get all collapsible sections
            collapsibles = self.query("Collapsible")

            for collapsible in collapsibles:
                section_id = None
                # Determine which section this is based on its content
                if collapsible.query_one(
                    "#detailed-explanation", Static, fallback=None
                ):
                    section_id = "explanation"
                elif collapsible.query_one("#key-concept", Static, fallback=None):
                    section_id = "key_concepts"
                elif collapsible.query_one("#mnemonic", Static, fallback=None):
                    section_id = "mnemonics"
                elif collapsible.query_one("#wrong-analysis", fallback=None):
                    section_id = "wrong_analysis"
                elif collapsible.query_one("#image-descriptions", fallback=None):
                    section_id = "image_descriptions"

                # Apply preference based on section
                if section_id == "explanation":
                    collapsible.collapsed = not self._should_expand_explanation()
                elif section_id == "key_concepts":
                    collapsible.collapsed = not self._should_expand_key_concepts()
                elif section_id == "mnemonics":
                    collapsible.collapsed = not self._should_expand_mnemonics()
                elif section_id == "wrong_analysis":
                    collapsible.collapsed = not self._should_expand_wrong_analysis()
                elif section_id == "image_descriptions":
                    collapsible.collapsed = not self._should_expand_image_descriptions()

        except Exception as e:
            logger.warning(f"Error applying progressive disclosure: {e}")
            # Continue with default behavior

    async def _display_wrong_answer_analysis(self) -> None:
        """Display analysis of why wrong answers are incorrect."""
        if not self.enhanced_data or not self.enhanced_data.wrong_answer_analysis:
            return

        wrong_analysis_container = self.query_one("#wrong-analysis")

        # Clear existing content
        await wrong_analysis_container.remove_children()

        # Add analysis for each wrong option
        for analysis in self.enhanced_data.wrong_answer_analysis:
            wrong_item = Static(
                f"[bold red]{analysis.option_letter}. {analysis.option_text}[/bold red]\n{analysis.explanation}",
                classes="wrong-item",
            )
            await wrong_analysis_container.mount(wrong_item)

    async def _display_image_descriptions(self) -> None:
        """Display descriptions for image-based questions."""
        if not self.enhanced_data or not self.enhanced_data.images:
            return

        # Show image descriptions section
        try:
            # Find the Collapsible that contains the image descriptions
            for collapsible in self.query("Collapsible").results():
                if collapsible.query_one(
                    "#image-descriptions", Container, fallback=None
                ):
                    collapsible.remove_class("hidden")
                    break
        except Exception as e:
            logger.debug(f"Could not show image descriptions: {e}")

        image_container = self.query_one("#image-descriptions")

        # Clear existing content
        await image_container.remove_children()

        # Add description for each image
        for i, image in enumerate(self.enhanced_data.images, 1):
            image_item = Container(
                Static(
                    f"[bold]Image {i}: {image.context}[/bold]", classes="image-title"
                ),
                Static(image.description, classes="image-description"),
                Static(f"[dim]Path: {image.path}[/dim]", classes="image-path"),
                classes="image-item",
            )
            await image_container.mount(image_item)

    async def submit_answer_with_rating(self, rating: int) -> None:
        """Submit the answer with FSRS rating using CQRS command handler."""
        try:
            if not self.submit_answer_command_handler:
                logger.warning("No submit answer command handler available")
                return

            # Create submit answer command
            from src.application.commands.submit_answer_with_rating_command import (
                SubmitAnswerWithRatingCommand,
            )

            command = SubmitAnswerWithRatingCommand(
                question_id=self.question.id,
                selected_answer=self.selected_answer or "",
                correct_answer=self.question.correct,
                fsrs_rating=rating,
                user_id=1,  # Default user
                session_id=self.session_id,  # Pass session ID for progress tracking
            )

            # Execute command through CQRS handler
            result = await self.submit_answer_command_handler.handle(command)

            if result.success:
                logger.info(
                    f"Answer submitted successfully: Q{self.question.id}, "
                    f"Selected: {self.selected_answer}, "
                    f"Correct: {self.question.correct}, "
                    f"Rating: {rating}, "
                    f"Next review: {result.next_review_date if result.next_review_date else 'N/A'}"
                )
            else:
                logger.warning(
                    f"Answer submission had issues: Q{self.question.id}, "
                    f"Error: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Failed to submit answer with rating: {e}")
            # Continue execution even if scheduling fails

    class QuestionCompleted(Message):
        """Message sent when question is completed with rating."""

        def __init__(self, rating: int):
            super().__init__()
            self.rating = rating


class PracticeScreen(Screen):
    """Screen for practicing questions."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Question view specific styling */
    .question-tabs {
        width: 95vw;
        max-width: 120;
        height: auto;
        max-height: 88vh;
        background: $surface;
        border: solid white;
        margin: 1;
    }

    .question-pane {
        height: auto;
        overflow: hidden;
    }

    .learn-pane {
        height: auto;
        overflow: hidden;
    }

    .question-container {
        width: 100%;
        height: auto;
        max-height: 75vh;
        padding: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    .learn-container {
        width: 100%;
        height: auto;
        max-height: 75vh;
        padding: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    .question-text {
        text-align: left;
        margin-bottom: 1;
        padding: 1;
        height: auto;
        min-height: 3;
        background: $panel;
        border-left: solid white;
    }

    .answer-options {
        margin: 1;
        margin-bottom: 1;
        height: auto;
    }

    .answer-option {
        width: 100%;
        height: auto;
        min-height: 3;
        text-align: left;
        margin-bottom: 1;
    }

    .answer-option.selected {
        border: solid white;
        text-style: bold;
    }

    .answer-result {
        margin: 1 0;
        padding: 1;
        height: auto;
        background: $background;
        border: solid white;
    }

    .result-text {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        height: auto;
    }

    .correct-answer {
        text-align: center;
        margin-bottom: 1;
        height: auto;
    }

    /* Enhanced content styles */
    .enhanced-content {
        margin-top: 1;
        margin: 1;
        height: auto;
        overflow: auto;
    }

    /* Specific styling for content sections */
    .content-section Collapsible {
        height: auto;
        min-height: 0;
    }

    .content-section > Contents {
        height: auto;
        min-height: 0;
        padding: 0;
    }

    .rich-explanation {
        padding: 1;
        color: $text;
    }

    .key-concept {
        padding: 1;
        color: $warning;
        text-style: italic;
        background: $warning 20%;
        border-left: solid white;
    }

    .mnemonic {
        padding: 1;
        color: $success;
        text-style: bold;
        background: $success 20%;
        border-left: solid white;
    }

    .wrong-analysis {
        padding: 0;
        margin: 0;
        height: auto;
        min-height: 0;
    }

    .wrong-item {
        margin-bottom: 0;
        padding: 1;
        background: $error 20%;
        border-left: solid white;
        height: auto;
        color: $text;
    }

    .image-descriptions {
        padding: 1;
        margin: 1;
    }

    .image-item {
        margin-bottom: 1;
        padding: 1;
        background: $primary 20%;
        border-left: solid white;
    }

    .image-title {
        color: $primary;
        margin-bottom: 1;
    }

    .image-description {
        color: $text;
        margin-bottom: 1;
    }

    .image-path {
        color: $text-muted;
        text-style: italic;
    }

    /* FSRS rating buttons - ensure visibility and consistency */
    .fsrs-rating {
        dock: bottom;
        width: 100%;
        height: auto;
        min-height: 6;
        max-height: 10;
        padding: 1;
        background: $accent 20%;
        border: solid white;
        margin: 0;
    }

    .rating-prompt {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        height: auto;
        color: white;
    }

    .rating-buttons {
        align: center middle;
        width: 100%;
        height: auto;
        margin: 1;
    }

    .rating-btn {
        width: 1fr;
        min-width: 8;
        height: 3;
    }
    """
    )

    BINDINGS = [
        ("1", "select_option_1", "Option 1"),
        ("2", "select_option_2", "Option 2"),
        ("3", "select_option_3", "Option 3"),
        ("4", "select_option_4", "Option 4"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(
        self,
        practice_mode: str = "random",
        user_repository: UserSettingsRepository | None = None,
        submit_answer_command_handler=None,
        start_practice_command_handler=None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.practice_mode = practice_mode
        self.user_repository = user_repository
        self.submit_answer_command_handler = submit_answer_command_handler
        self.start_practice_command_handler = start_practice_command_handler
        self.current_question: Question | None = None
        self.questions_answered = 0
        self.correct_answers = 0
        self.session_id: int | None = None

        # State for question cycling
        self._question_state = {
            "category_index": 0,
            "question_indices": {},
            "last_question_id": 0,
        }

    def compose(self) -> ComposeResult:
        """Compose the practice screen."""
        yield Container(
            Static(
                f"Practice Mode: {self.practice_mode.title()}", classes="text-title"
            ),
            Static("Loading question...", id="question-container"),
            classes="container-centered",
        )

    async def on_mount(self) -> None:
        """Load first question when screen mounts."""
        try:
            logger.info(f"PracticeScreen mounting with mode: {self.practice_mode}")

            # Create a practice session for progress tracking
            await self._create_practice_session()

            await self.load_next_question()
            logger.info("PracticeScreen mounted successfully")
        except Exception as e:
            logger.error(f"Critical error during PracticeScreen mount: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't re-raise, just show an error message to user
            self.mount(
                Static(
                    f"[red]Error loading practice session:[/red]\n{str(e)}\n\nPress Escape to return to menu.",
                    classes="error-message",
                )
            )

    async def load_next_question(self) -> None:
        """Load the next question for practice using CQRS command handler."""
        try:
            # Get command handler or fallback to app container
            command_handler = self.start_practice_command_handler
            if not command_handler:
                if hasattr(self.app, "container") and self.app.container:
                    command_handler = (
                        self.app.container.get_start_practice_session_command_handler()
                    )
                else:
                    # Fallback: create temporary handler
                    from src.infrastructure.containers.main_container import (
                        MainContainer,
                    )

                    container = MainContainer()
                    command_handler = (
                        container.get_start_practice_session_command_handler()
                    )

            # Create command with current state
            from src.application.commands.start_practice_session_command import (
                StartPracticeSessionCommand,
            )

            command = StartPracticeSessionCommand(
                practice_mode=self.practice_mode,
                user_id=1,
                limit=1,
                category_index=self._question_state["category_index"],
                question_indices=self._question_state["question_indices"],
                last_question_id=self._question_state["last_question_id"],
            )

            # Execute command
            result = await command_handler.handle(command)

            if result.success and result.question:
                self.current_question = result.question

                # Update state for next question
                if result.session_state:
                    self._question_state.update(result.session_state)

                logger.info(
                    f"Loaded question {self.current_question.id} for {self.practice_mode} mode"
                )
            else:
                logger.error(f"Failed to load question: {result.error_message}")
                raise Exception(result.error_message or "Unknown error")

        except Exception as e:
            logger.error(f"Error loading question: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't raise - return with error display instead
            error_container = Container(
                Static("[red]Failed to load question:[/red]", classes="text-title"),
                Static(f"{str(e)}", classes="error-text"),
                Static("Press Escape to return to menu", classes="text-help"),
                classes="container-centered",
            )
            await self.mount(error_container)
            return

        # Get submit answer command handler or fallback
        submit_handler = self.submit_answer_command_handler
        if not submit_handler and hasattr(self.app, "container") and self.app.container:
            submit_handler = self.app.container.get_submit_answer_command_handler()

        # Create enhanced question widget with command handler support
        if self.user_repository:
            question_widget = QuestionWidget(
                question=self.current_question,
                event_bus=self.app.event_bus,
                user_repository=self.user_repository,
                submit_answer_command_handler=submit_handler,
                preferred_language=Language.ENGLISH,  # Will be updated from user settings
                session_id=self.session_id,  # Pass session ID for progress tracking
            )
        else:
            # Fallback: create a temporary repository
            from src.infrastructure.database.database import DatabaseManager

            temp_db_manager = DatabaseManager()
            temp_repository = UserSettingsRepository(temp_db_manager)

            question_widget = QuestionWidget(
                question=self.current_question,
                event_bus=self.app.event_bus,
                user_repository=temp_repository,
                submit_answer_command_handler=submit_handler,
                preferred_language=Language.ENGLISH,
                session_id=self.session_id,  # Pass session ID for progress tracking
            )

        # Remove all children except header and footer, then mount the question widget
        try:
            # Get all direct children of the screen
            children = list(self.children)
            for child in children:
                # Keep header and footer, remove everything else
                if not (hasattr(child, "id") and child.id in ["header", "footer"]):
                    await child.remove()
        except Exception as e:
            logger.debug(f"Could not remove existing widgets: {e}")

        # Mount the new question widget
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
        # First check if we should be selecting a rating button instead
        try:
            # Check if the rating container is visible
            rating_container = self.query_one(".fsrs-rating", fallback=None)
            if rating_container and not rating_container.has_class("hidden"):
                # Select rating button instead
                rating_btn = self.query_one(f"#rating_{option_num}", Button)
                rating_btn.press()
                return
        except Exception as e:
            logger.debug(f"Could not press rating button: {e}")

        # Otherwise select answer option
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

        # Load next question
        logger.info(f"Question completed with rating {event.rating}")
        await self.load_next_question()

    async def _create_practice_session(self) -> None:
        """Create a practice session for progress tracking."""
        try:
            # Get session repository from app container
            if hasattr(self.app, "container") and self.app.container:
                session_repository = self.app.container.get_session_repository()
                # Create session with practice mode type
                session_id = await session_repository.create_session(
                    user_id=1,
                    session_type=self.practice_mode,
                    configuration={"mode": self.practice_mode},
                )
                # Store session ID for tracking answers
                self.session_id = session_id
                logger.info(
                    f"Created practice session {session_id} for mode {self.practice_mode}"
                )
            else:
                # Fallback: create session directly with DatabaseManager
                from src.infrastructure.database.database import DatabaseManager

                db_manager = DatabaseManager()
                session_id = db_manager.create_session(self.practice_mode, user_id=1)
                self.session_id = session_id
                logger.info(
                    f"Created practice session {session_id} (fallback) for mode {self.practice_mode}"
                )
        except Exception as e:
            logger.warning(f"Failed to create practice session: {e}")
            # Continue without session tracking
            self.session_id = None
