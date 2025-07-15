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

from src.application.queries.enhanced_question_content_query import (
    EnhancedQuestionContentQuery,
    EnhancedQuestionContentQueryHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQuery,
    LoadUserSettingsQueryHandler,
)
from src.domain.content.models.question_models import Question
from src.domain.content.services.enhanced_question_display import EnhancedQuestionData
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import Language
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class QuestionWidget(EventAwareWidget):
    """Widget for displaying a single question with enhanced multilingual content."""

    def __init__(
        self,
        question: Question,
        event_bus: EventBusInterface,
        enhanced_question_query_handler: EnhancedQuestionContentQueryHandler,
        load_user_settings_query_handler: LoadUserSettingsQueryHandler,
        learning_repository=None,
        submit_answer_command_handler=None,
        preferred_language: Language = Language.ENGLISH,
        session_id: int | None = None,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.question = question
        self.enhanced_question_query_handler = enhanced_question_query_handler
        self.load_user_settings_query_handler = load_user_settings_query_handler
        self._learning_repository = learning_repository
        self.submit_answer_command_handler = submit_answer_command_handler
        self.preferred_language = preferred_language
        self.session_id = session_id
        self.selected_answer: str | None = None
        self.answer_revealed = False
        self.enhanced_data: EnhancedQuestionData | None = None
        self.user_preferences = None  # Will be loaded from user settings

    async def on_mount(self) -> None:
        """Called when widget is mounted - setup event subscriptions."""
        import time

        self._component_ready_time = time.time()
        await self.setup_event_subscriptions()

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

                    # Answer options - different layout for image questions
                    if self.question.is_image_question:
                        # Always use image layout for image questions, even without enhanced data initially
                        yield from self._compose_image_question_options()
                    else:
                        yield from self._compose_text_question_options()

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
                Button(
                    "Menu",
                    id="back_to_menu",
                    variant="default",
                    classes="menu-btn",
                ),
                classes="rating-buttons",
            ),
            classes="fsrs-rating hidden",
        )

    def _compose_image_question_options(self) -> ComposeResult:
        """Compose image question with appropriate layout based on number of images.

        Yields:
            Layout with images and buttons for each option
        """
        try:
            logger.debug(
                f"_compose_image_question_options called for Q{self.question.id}"
            )

            # Check if textual-image is available
            try:
                from textual_image.widget import Image

                has_textual_image = True
                logger.debug("textual-image library is available")
            except ImportError:
                has_textual_image = False
                logger.debug("textual-image library not available")
                # Provide a dummy Image class to avoid import errors
                Image = None

            # Check how many images exist for this question
            from pathlib import Path

            image_count = 0
            for i in range(1, 5):  # Check for images 1-4
                image_path = f"data/images/q{self.question.id}_{i}.png"
                if Path(image_path).exists():
                    image_count += 1

            logger.debug(f"Question {self.question.id} has {image_count} images")

            # Different layouts based on image count
            if image_count == 1:
                # Single image layout - full width image with text options below
                single_image_path = f"data/images/q{self.question.id}_1.png"

                # Display the single image centered and larger
                with Container(classes="single-image-container"):
                    if has_textual_image and Path(single_image_path).exists():
                        try:
                            # Try to resize image for better terminal display
                            resized_image_path = self._resize_image_for_terminal(
                                single_image_path
                            )
                            image_to_display = resized_image_path or single_image_path

                            # Create image with proper classes for CSS sizing
                            yield Image(
                                image_to_display, classes="single-question-image"
                            )

                            if resized_image_path:
                                logger.debug(
                                    f"Successfully displayed resized single image: {resized_image_path}"
                                )
                            else:
                                logger.debug(
                                    f"Successfully displayed original single image: {single_image_path}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to display image {single_image_path}: {e}"
                            )
                            yield Static(
                                "[yellow]📸 Image\n[dim]Press 'v' to view in external viewer[/dim]",
                                classes="image-fallback-text-large",
                            )
                    else:
                        yield Static(
                            "[yellow]📸 Image\n[dim]Press 'v' to view in external viewer[/dim]",
                            classes="image-fallback-text-large",
                        )

                # Display text options below the image
                yield Static("Answer Options:", classes="options-header")
                with Vertical(classes="answer-options"):
                    for i, option in enumerate(self.question.options_list, 1):
                        option_letter = chr(65 + i - 1)  # A, B, C, D
                        yield Button(
                            f"{option_letter}. {option}",
                            id=f"option_{i}",
                            variant="default",
                            classes="answer-option",  # IMPORTANT: Keep this class for event handler
                        )

            else:
                # Multiple images layout - display all images in a row, then buttons below

                # Row of 4 images
                with Horizontal(classes=f"images-row image-count-{image_count}"):
                    for i in range(1, 5):  # Always show 4 image slots
                        option_letter = chr(65 + i - 1)  # A, B, C, D

                        with Container(classes="image-container"):
                            # Try to display image if available
                            if has_textual_image and self.question.is_image_question:
                                image_path = f"data/images/q{self.question.id}_{i}.png"

                                if Path(image_path).exists():
                                    try:
                                        # Display the image with proper classes
                                        yield Image(
                                            image_path, classes="multi-question-image"
                                        )
                                        logger.debug(
                                            f"Successfully displayed image: {image_path}"
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"Failed to display image {image_path}: {e}"
                                        )
                                        # Show fallback text
                                        yield Static(
                                            f"[yellow]📸 {option_letter}[/yellow]\n[dim]Image viewer needed[/dim]",
                                            classes="image-fallback-text",
                                        )
                                else:
                                    logger.warning(
                                        f"Image file not found: {image_path}"
                                    )
                                    yield Static(
                                        f"[red]❌ Image missing[/red]\n[dim]{option_letter}[/dim]",
                                        classes="image-missing-text",
                                    )
                            else:
                                # Show placeholder for non-textual-image case
                                yield Static(
                                    f"[yellow]📸 {option_letter}[/yellow]\n[dim]Press 'v' to view[/dim]",
                                    classes="image-fallback-text",
                                )

                            # Add option letter label below each image
                            yield Static(
                                f"{option_letter}", classes="image-option-label"
                            )

                # Row of 4 buttons below images
                yield Static("Choose your answer:", classes="options-header")
                with Vertical(classes="answer-buttons-column"):
                    for i, option in enumerate(self.question.options_list, 1):
                        option_letter = chr(65 + i - 1)  # A, B, C, D
                        yield Button(
                            f"{option_letter}. {option}",
                            id=f"option_{i}",
                            variant="default",
                            classes="answer-option multi-image-button",
                            disabled=False,
                        )

        except Exception as e:
            logger.error(f"Error in _compose_image_question_options: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            # Emergency fallback - just show basic buttons
            yield Static(
                "[red]Error loading image options. Using text-only fallback.[/red]",
                classes="error-message",
            )
            with Horizontal(classes="image-options-row"):
                for i, option in enumerate(self.question.options_list, 1):
                    yield Button(
                        f"{i}. {option}",
                        id=f"option_{i}",
                        variant="default",
                        classes="answer-option",
                    )

    def _compose_text_question_options(self) -> ComposeResult:
        """Compose regular text question with vertical button layout.

        Yields:
            Vertical container with answer option buttons
        """
        with Vertical(classes="answer-options"):
            for i, option in enumerate(self.question.options_list, 1):
                yield Button(
                    f"{i}. {option}",
                    id=f"option_{i}",
                    variant="default",
                    classes="answer-option",
                )

    def _create_image_display_info(self) -> Static:
        """Create info message about image display capabilities.

        Returns:
            Static widget with capability information
        """
        # Check terminal support for images
        if self._check_terminal_support():
            return Static(
                "[green]✓ Your terminal supports image display[/green]",
                classes="info-message",
            )
        else:
            return Static(
                "[yellow]Press 'v' to view images in external viewer[/yellow]",
                classes="info-message",
            )

    def _check_terminal_support(self) -> bool:
        """Check if terminal supports image display.

        Returns:
            True if terminal supports images, False otherwise
        """
        import os

        try:
            from textual_image.widget import Image  # noqa: F401

            has_textual_image = True
        except ImportError:
            has_textual_image = False

        if not has_textual_image:
            return False

        term = os.environ.get("TERM", "").lower()
        term_program = os.environ.get("TERM_PROGRAM", "")

        # Modern terminals with native image support
        supported_terminals = [
            "kitty" in term,
            term_program == "iTerm.app",
            "wezterm" in term,
            os.environ.get("WT_SESSION") is not None,  # Windows Terminal
            "konsole" in term,  # KDE Konsole
            "sixel" in term,  # Sixel protocol support
        ]

        return any(supported_terminals)

    def _resize_image_for_terminal(
        self, image_path: str, max_width: int = 100, max_height: int = 40
    ) -> str | None:
        """Resize image for optimal terminal display to prevent cutoff.

        Args:
            image_path: Path to the original image file
            max_width: Maximum width in terminal cells (default: 100 for single images)
            max_height: Maximum height in terminal cells (default: 40 for single images)

        Returns:
            Path to resized image file, or None if processing failed
        """
        # Check if PIL is available
        try:
            from PIL import Image as PILImage
        except ImportError:
            logger.debug("PIL not available for image resizing")
            return None

        import tempfile
        from pathlib import Path

        original_path = Path(image_path)
        if not original_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return None

        try:
            # Open the original image
            with PILImage.open(original_path) as img:
                # Get original dimensions
                orig_width, orig_height = img.size
                logger.debug(f"Original single image size: {orig_width}x{orig_height}")

                # Calculate scaling factor to fit within terminal bounds
                # Terminal cells are roughly 1:2 ratio (height:width), so adjust accordingly
                # For vertical images, we need to be more conservative with height
                width_ratio = max_width / orig_width

                # Adjust height calculation based on image orientation
                if orig_height > orig_width:  # Vertical image
                    # More conservative height scaling for vertical images
                    height_ratio = (max_height * 1.5) / orig_height
                else:  # Horizontal or square image
                    height_ratio = (max_height * 2) / orig_height

                scale_factor = min(width_ratio, height_ratio, 1.0)  # Don't upscale

                # Skip processing if image is already small enough
                if scale_factor >= 0.95:
                    logger.debug("Single image already optimal size, using original")
                    return image_path

                # Calculate new dimensions
                new_width = int(orig_width * scale_factor)
                new_height = int(orig_height * scale_factor)

                logger.debug(
                    f"Resizing single image to: {new_width}x{new_height} (scale: {scale_factor:.2f})"
                )

                # Resize with high quality resampling
                resized_img = img.resize(
                    (new_width, new_height), PILImage.Resampling.LANCZOS
                )

                # Create temporary file for resized image
                temp_dir = Path(tempfile.gettempdir()) / "integran_images"
                temp_dir.mkdir(exist_ok=True)

                # Create filename based on original and target size
                original_name = original_path.stem
                temp_filename = f"{original_name}_single_{new_width}x{new_height}.png"
                temp_path = temp_dir / temp_filename

                # Save resized image with optimization
                resized_img.save(temp_path, "PNG", optimize=True, quality=95)

                logger.debug(f"Resized single image saved to: {temp_path}")
                return str(temp_path)

        except Exception as e:
            logger.error(f"Failed to resize single image {image_path}: {e}")
            return None

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""

        # Load user preferred language on startup
        await self._load_user_preferred_language()

        # For image questions, load enhanced data immediately
        if self.question.is_image_question:
            await self._load_enhanced_content()
            # Refresh the display after loading enhanced data
            if self.enhanced_data and self.enhanced_data.images:
                await self._refresh_image_display()

    async def _load_user_preferred_language(self) -> None:
        """Load user's preferred language and progressive disclosure settings."""
        try:
            query = LoadUserSettingsQuery(user_id=1)
            result = await self.load_user_settings_query_handler.handle(query)

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

        # Add a small safety check to prevent immediate auto-selection
        # This helps avoid accidental selection during widget initialization
        import time

        if not hasattr(self, "_component_ready_time"):
            self._component_ready_time = time.time()

        # Prevent selection within first 500ms of component creation (but allow tests)
        time_diff = time.time() - self._component_ready_time
        if time_diff < 0.5 and not hasattr(self, "_test_mode"):
            logger.debug("Ignoring early button press - component still initializing")
            return

        # Extract option number from button ID
        button_id = event.button.id
        # Format: option_1, option_2, etc.
        option_num = int(button_id.split("_")[1])

        self.selected_answer = self.question.options_list[option_num - 1]

        # Highlight selected option - disable all other buttons
        for i in range(1, 5):
            try:
                btn = self.query_one(f"#option_{i}", Button)
                if i == option_num:
                    btn.variant = "primary"
                    btn.add_class("selected")
                else:
                    btn.disabled = True
            except Exception:
                logger.debug(f"Button #option_{i} not found")

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

    @on(Button.Pressed, ".menu-btn")
    async def on_menu_button_pressed(self, event: Button.Pressed) -> None:  # noqa: ARG002
        """Handle Menu button press to go back to main menu."""
        try:
            # Call our own cleanup method defined in this widget
            await self.action_cleanup_and_exit()
        except Exception as e:
            logger.error(f"Error in menu button handler: {e}")
            # Ensure we can still navigate back even if cleanup fails
            self.app.pop_screen()

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
            query = EnhancedQuestionContentQuery(
                question_id=self.question.id,
                preferred_language=self.preferred_language,
            )

            result = await self.enhanced_question_query_handler.handle(query)

            if result.success and result.enhanced_data:
                self.enhanced_data = result.enhanced_data
                logger.info(f"Loaded enhanced content for question {self.question.id}")

                # If this is an image question, refresh the display to show images
                if self.enhanced_data.is_image_question and self.enhanced_data.images:
                    await self._refresh_image_display()
            else:
                logger.warning(
                    f"Failed to load enhanced content: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Error loading enhanced content: {e}")

    async def _refresh_image_display(self) -> None:
        """Refresh the question display to show images after enhanced data is loaded."""
        try:
            # Since images are already displayed during compose, we don't need to refresh much
            # Just log that enhanced data is available
            if self.enhanced_data and self.enhanced_data.images:
                logger.info(
                    f"Enhanced data loaded for Q{self.question.id} with {len(self.enhanced_data.images)} images"
                )
            else:
                logger.warning(
                    f"Enhanced data still not available for Q{self.question.id} during refresh"
                )

        except Exception as e:
            logger.error(f"Error refreshing image display for Q{self.question.id}: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

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
                    try:
                        collapsible.query_one("#mnemonic", Static)
                        # If we get here, the element exists
                        collapsible.add_class("hidden")
                        break
                    except Exception as e:
                        logger.debug(
                            f"Could not find mnemonic element in collapsible: {e}"
                        )
                        continue
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
                try:
                    collapsible.query_one("#detailed-explanation", Static)
                    section_id = "explanation"
                except Exception:
                    try:
                        collapsible.query_one("#key-concept", Static)
                        section_id = "key_concepts"
                    except Exception:
                        try:
                            collapsible.query_one("#mnemonic", Static)
                            section_id = "mnemonics"
                        except Exception:
                            try:
                                collapsible.query_one("#wrong-analysis")
                                section_id = "wrong_analysis"
                            except Exception:
                                try:
                                    collapsible.query_one("#image-descriptions")
                                    section_id = "image_descriptions"
                                except Exception as e:
                                    logger.debug(
                                        f"Could not identify collapsible section: {e}"
                                    )
                                    continue

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

    BINDINGS = [
        ("escape", "back_to_menu", "Back to Menu"),
    ]

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
        max-height: 65vh;
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

    /* Single image layout - for questions with only 1 image */
    .single-image-container {
        width: 100%;
        height: auto;
        max-height: 65vh;  /* Limit container height */
        margin: 1 0;
        padding: 2;
        align: center middle;
        background: $panel;
        border: solid $primary;
        overflow: auto;  /* Allow scrolling if needed */
    }

    .single-question-image {
        width: auto;
        max-width: 90%;
        height: auto;
        max-height: 50vh;  /* Use viewport height instead of fixed cells */
        margin: 1;
        align: center middle;
    }

    .image-fallback-text-large {
        text-align: center;
        padding: 4;
        height: 20;
        width: 60;
        background: $warning 20%;
        margin: 1;
        border: solid $warning;
        align: center middle;
    }

    /* Image options styling - horizontal row layout for multiple images */
    .image-options-row {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 1;
        align: center middle;
    }

    .image-option-wrapper {
        width: 1fr;
        margin: 0 1;
        padding: 1;
        align: center middle;
        background: $surface;
        border: solid $primary;
    }

    /* Responsive image sizing based on image count */
    .image-count-2 .image-option-wrapper {
        width: 1fr;
        max-width: 50;
    }

    .image-count-3 .image-option-wrapper {
        width: 1fr;
        max-width: 35;
    }

    .image-count-4 .image-option-wrapper {
        width: 1fr;
        max-width: 25;
    }


    /* Image containers and images */
    .image-option-container {
        width: 100%;
        height: auto;
        align: center middle;
        background: $panel;
        border: solid white;
        margin-bottom: 1;
    }

    .coat-of-arms-image {
        width: 100%;
        height: auto;
        max-height: 15;
        margin-bottom: 1;
    }

    /* New styles for direct image display */
    .question-image {
        width: 100%;
        height: auto;
        max-height: 20;
        min-height: 10;
        margin-bottom: 1;
    }

    .image-fallback-text {
        text-align: center;
        padding: 2;
        height: 8;
        background: $warning 20%;
        margin-bottom: 1;
    }

    .image-missing-text {
        text-align: center;
        padding: 2;
        height: 8;
        background: $error 20%;
        margin-bottom: 1;
    }

    .image-answer-button {
        width: 100%;
        height: 3;
        text-align: center;
        margin-top: 0;
    }

    .options-header {
        text-align: center;
        margin: 1 0;
        color: $accent;
        text-style: bold;
    }

    .image-buttons-row {
        width: 100%;
        margin: 1 0;
        align: center middle;
    }

    .image-answer-button-fallback {
        width: 1fr;
        height: 3;
        margin: 0 1;
        text-align: center;
    }

    .external-viewer-hint {
        text-align: center;
        margin-top: 1;
        padding: 1;
        color: $text-muted;
    }

    .image-fallback {
        color: $warning;
        text-align: center;
        padding: 1;
        background: $warning 20%;
        border: solid $warning;
        margin-bottom: 1;
        height: auto;
        min-height: 8;
    }

    .image-option-button {
        width: 100%;
        height: auto;
        min-height: 3;
        text-align: center;
        margin-top: 1;
    }

    .info-message {
        text-align: center;
        margin-bottom: 1;
        padding: 1;
        background: $accent 20%;
        border-left: solid $accent;
    }

    .loading-message {
        text-align: center;
        margin-bottom: 1;
        padding: 1;
        background: $warning 30%;
        border-left: solid $warning;
        color: $warning;
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
        min-height: 8;
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

    .menu-btn {
        width: 1fr;
        min-width: 8;
        height: 3;
        margin-left: 1;
    }
    """
    )

    BINDINGS = [
        ("1", "select_option_1", "Option 1"),
        ("2", "select_option_2", "Option 2"),
        ("3", "select_option_3", "Option 3"),
        ("4", "select_option_4", "Option 4"),
        ("5", "invalid_option", ""),
        ("6", "invalid_option", ""),
        ("7", "invalid_option", ""),
        ("8", "invalid_option", ""),
        ("9", "invalid_option", ""),
        ("v", "view_images_externally", "View Images"),
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    def __init__(
        self,
        practice_mode: str = "random",
        user_repository=None,
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

        # State for question cycling - will be loaded from user settings
        self._question_state = {
            "category_index": 0,
            "question_indices": {},
            "last_question_id": 0,
        }
        self._state_loaded = False

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

            # Load session state from user settings
            await self._load_session_state()

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
            # Get command handler and container
            command_handler = self.start_practice_command_handler
            container = None

            if not command_handler:
                if hasattr(self.app, "container") and self.app.container:
                    container = self.app.container
                    command_handler = (
                        container.get_start_practice_session_command_handler()
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
            else:
                # Get container for command creation
                if hasattr(self.app, "container") and self.app.container:
                    container = self.app.container
                else:
                    from src.infrastructure.containers.main_container import (
                        MainContainer,
                    )

                    container = MainContainer()

            # Create command with current state
            from src.application.commands.start_practice_session_command import (
                StartPracticeSessionCommand,
            )

            command = StartPracticeSessionCommand(
                practice_mode=self.practice_mode,
                user_repository=container.get_user_repository(),
                session_repository=container.get_session_repository(),
                event_bus=container.get_event_bus(),
                user_id=1,
                limit=1,
                category_index=self._question_state["category_index"],
                question_indices=self._question_state["question_indices"],
                last_question_id=self._question_state["last_question_id"],
                existing_session_id=self.session_id,  # Pass existing session ID to avoid duplicates
            )

            # Execute command
            result = await command_handler.handle(command)

            if result.success and result.question:
                self.current_question = result.question

                # Store session ID for tracking progress
                if result.session_id:
                    self.session_id = result.session_id
                    logger.info(
                        f"Practice session {self.session_id} started for {self.practice_mode} mode"
                    )

                # Update state for next question
                if result.session_state:
                    self._question_state.update(result.session_state)
                    # Save updated state to persist progress
                    await self._save_session_state()

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
            # Create a simple error screen and replace the current screen
            await self._show_error_screen(str(e))
            return

        # Get submit answer command handler or fallback
        submit_handler = self.submit_answer_command_handler
        if not submit_handler and hasattr(self.app, "container") and self.app.container:
            submit_handler = self.app.container.get_submit_answer_command_handler()

        # Get query handlers from container
        enhanced_question_query_handler = None
        load_user_settings_query_handler = None

        if hasattr(self.app, "container") and self.app.container:
            enhanced_question_query_handler = (
                self.app.container.get_enhanced_question_content_query_handler()
            )
            load_user_settings_query_handler = (
                self.app.container.get_load_user_settings_query_handler()
            )
        else:
            # Fallback: create temporary container
            from src.infrastructure.containers.main_container import MainContainer

            temp_container = MainContainer()
            enhanced_question_query_handler = (
                temp_container.get_enhanced_question_content_query_handler()
            )
            load_user_settings_query_handler = (
                temp_container.get_load_user_settings_query_handler()
            )

        # Validate required handlers
        if not enhanced_question_query_handler:
            logger.error("Enhanced question query handler not available")
            raise RuntimeError(
                "Enhanced question query handler not initialized - check container setup"
            )

        if not load_user_settings_query_handler:
            logger.error("Load user settings query handler not available")
            raise RuntimeError(
                "Load user settings query handler not initialized - check container setup"
            )

        # Create enhanced question widget with command handler support
        # Use provided user repository or raise error if not available
        user_repo = self.user_repository
        if not user_repo:
            logger.error("No user repository provided - cannot create question widget")
            raise RuntimeError(
                "User repository not available - check dependency injection in parent"
            )

        question_widget = QuestionWidget(
            question=self.current_question,
            event_bus=self.app.event_bus,
            enhanced_question_query_handler=enhanced_question_query_handler,
            load_user_settings_query_handler=load_user_settings_query_handler,
            learning_repository=user_repo,
            submit_answer_command_handler=submit_handler,
            preferred_language=Language.ENGLISH,  # Will be updated from user settings
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
        # Get the question widget first
        question_widgets = self.query(QuestionWidget)
        if not question_widgets:
            logger.debug("No QuestionWidget found")
            return

        question_widget = question_widgets.first()

        # First check if we should be selecting a rating button instead
        try:
            # Check if the rating container is visible
            rating_containers = question_widget.query(".fsrs-rating")
            if rating_containers:
                rating_container = rating_containers.first()
                if rating_container and not rating_container.has_class("hidden"):
                    # Select rating button instead
                    rating_btn = question_widget.query_one(
                        f"#rating_{option_num}", Button
                    )
                    rating_btn.press()
                    return
        except Exception as e:
            logger.debug(f"Could not press rating button: {e}")

        # Otherwise select answer option
        try:
            btn = question_widget.query_one(f"#option_{option_num}", Button)
            btn.press()
        except Exception as e:
            # Button not found or not available
            logger.debug(f"Could not select option {option_num}: {e}")

    def action_invalid_option(self) -> None:
        """Handle invalid option number press."""
        self.notify("Only options 1-4 are available", severity="warning", timeout=2)

    def action_back_to_menu(self) -> None:
        """Go back to main menu with proper session cleanup."""
        # Schedule session cleanup asynchronously
        self.run_action("cleanup_and_exit")

    async def action_cleanup_and_exit(self) -> None:
        """Properly clean up session and navigate to main menu."""
        try:
            logger.info("Starting session cleanup before navigating to main menu")

            # Save current session state first
            await self._save_session_state()
            logger.info("Session state saved successfully")

            # End current session properly if it exists
            if (
                self.session_id
                and hasattr(self.app, "container")
                and self.app.container
            ):
                try:
                    # Get the session workflow to properly end the session
                    session_workflow = self.app.container.get_session_workflow()
                    await session_workflow.complete_session(self.session_id)
                    logger.info(f"Session {self.session_id} ended successfully")
                except Exception as e:
                    # Don't fail the navigation if session ending fails
                    logger.warning(f"Failed to end session {self.session_id}: {e}")

            # Now safely navigate away
            self.app.pop_screen()
            logger.info("Successfully navigated back to main menu")

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            # Always allow navigation even if cleanup fails
            self.app.pop_screen()

    async def action_view_images_externally(self) -> None:
        """Open current question's images in external viewer."""
        logger.info("'v' key pressed - attempting to view images externally")

        if not self.current_question:
            logger.warning("No current question available")
            self.notify("No question loaded", severity="warning")
            return

        if not self.current_question.is_image_question:
            logger.info(f"Q{self.current_question.id} is not an image question")
            self.notify("This is not an image question", severity="info")
            return

        logger.info(f"Processing external image view for Q{self.current_question.id}")

        try:
            # Get the question widget to access enhanced data
            question_widgets = self.query(QuestionWidget)
            if not question_widgets:
                self.notify("Question widget not found", severity="error")
                return
            question_widget = question_widgets.first()

            # 🔥 FIX: Ensure enhanced data is loaded before accessing images
            if (
                not question_widget.enhanced_data
                or not question_widget.enhanced_data.images
            ):
                self.notify("Loading image data...", timeout=1)
                logger.info(
                    f"Enhanced data not loaded for Q{self.current_question.id}, loading now..."
                )
                await question_widget._load_enhanced_content()

            # Check if enhanced data is available
            if question_widget.enhanced_data and question_widget.enhanced_data.images:
                # Import the external viewer
                from src.presentation.terminal.actions.external_image_viewer import (
                    ExternalImageViewer,
                )

                # Convert enhanced image data to format expected by viewer
                images = [
                    {"path": img.path} for img in question_widget.enhanced_data.images
                ]

                # Open in external viewer
                self.notify("Opening images in external viewer...", timeout=2)
                success = await ExternalImageViewer.view_question_images(
                    question_id=self.current_question.id,
                    images=images,
                    question_text=self.current_question.question,
                )

                if success:
                    self.notify("Images opened successfully", severity="information")
                    logger.info(
                        f"External viewer opened successfully for Q{self.current_question.id}"
                    )
                else:
                    self.notify(
                        "Failed to open images. Check that you have an image viewer installed.",
                        severity="error",
                    )
                    logger.error(
                        "External viewer failed to open images for Q%s",
                        self.current_question.id,
                    )
            else:
                # Fallback: Look for image files directly
                logger.info(
                    "Enhanced data not available, falling back to direct image file access"
                )
                from pathlib import Path

                # Check for image files in the data/images directory
                image_files = []
                for i in range(1, 5):  # Check for images 1-4
                    image_path = f"data/images/q{self.current_question.id}_{i}.png"
                    if Path(image_path).exists():
                        image_files.append({"path": image_path})

                if image_files:
                    # Import the external viewer
                    from src.presentation.terminal.actions.external_image_viewer import (
                        ExternalImageViewer,
                    )

                    # Open in external viewer using direct file paths
                    self.notify("Opening images in external viewer...", timeout=2)
                    success = await ExternalImageViewer.view_question_images(
                        question_id=self.current_question.id,
                        images=image_files,
                        question_text=self.current_question.question,
                    )

                    if success:
                        self.notify(
                            "Images opened successfully", severity="information"
                        )
                        logger.info(
                            f"External viewer opened successfully for Q{self.current_question.id} using direct file access"
                        )
                    else:
                        self.notify(
                            "Failed to open images. Check that you have an image viewer installed.",
                            severity="error",
                        )
                        logger.error(
                            "External viewer failed to open images for Q%s",
                            self.current_question.id,
                        )
                else:
                    self.notify(
                        "No image files found for this question", severity="warning"
                    )
                    logger.warning(
                        f"No image files found for Q{self.current_question.id} in data/images/"
                    )

        except ImportError as e:
            logger.error(f"PIL not available for external viewer: {e}")
            self.notify(
                "PIL (Pillow) library required for external viewer. Install with: pip install pillow",
                severity="error",
            )
        except Exception as e:
            logger.error(f"Error opening images externally: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            self.notify(f"Error opening images: {str(e)}", severity="error")

    @on(QuestionWidget.QuestionCompleted)
    async def on_question_completed(
        self, event: QuestionWidget.QuestionCompleted
    ) -> None:
        """Handle question completion."""
        self.questions_answered += 1

        if self.current_question and event.rating in [3, 4]:  # Good or Easy
            self.correct_answers += 1

        # Save updated state and load next question
        await self._save_session_state()
        logger.info(f"Question completed with rating {event.rating}")
        await self.load_next_question()

    async def _load_session_state(self) -> None:
        """Load session state from user settings for resume capability."""
        try:
            if self._state_loaded:
                return

            # Get user settings to load session state
            if hasattr(self.app, "container") and self.app.container:
                load_user_settings_query_handler = (
                    self.app.container.get_load_user_settings_query_handler()
                )
            else:
                logger.warning("No app container available for loading session state")
                return

            from src.application.queries.load_user_settings_query import (
                LoadUserSettingsQuery,
            )

            query = LoadUserSettingsQuery(user_id=1)
            result = await load_user_settings_query_handler.handle(query)

            if (
                result.success
                and result.user_settings
                and result.user_settings.flow_state
            ):
                flow_data = result.user_settings.flow_state.flow_data

                # Load practice mode specific state
                practice_state_key = f"practice_state_{self.practice_mode}"
                if practice_state_key in flow_data:
                    saved_state = flow_data[practice_state_key]
                    logger.info(
                        f"Loading saved session state for {self.practice_mode} mode: {saved_state}"
                    )

                    # Update our state with saved values
                    self._question_state.update(
                        {
                            "category_index": saved_state.get("category_index", 0),
                            "question_indices": saved_state.get("question_indices", {}),
                            "last_question_id": saved_state.get("last_question_id", 0),
                        }
                    )

                    logger.info(
                        f"Session state loaded for {self.practice_mode}: {self._question_state}"
                    )
                else:
                    logger.info(
                        f"No saved session state found for {self.practice_mode} mode"
                    )
            else:
                logger.warning("Could not load user settings for session state")

            self._state_loaded = True

        except Exception as e:
            logger.error(f"Error loading session state: {e}")
            # Continue with default state
            self._state_loaded = True

    async def _show_error_screen(self, error_message: str) -> None:
        """Show an error screen with working navigation."""
        from textual.containers import Container
        from textual.widgets import Button, Static

        # Clear existing content
        await self.remove_children()

        # Create error display with proper key bindings
        error_widget = Container(
            Static("[red]Failed to load question:[/red]", classes="text-title"),
            Static(f"{error_message}", classes="error-text"),
            Static(
                "Press Escape to return to menu or click the button below:",
                classes="text-help",
            ),
            Button(
                "📋 Back to Main Menu",
                id="error_back_to_menu",
                variant="primary",
            ),
            classes="container-centered",
        )

        # Mount the error widget
        await self.mount(error_widget)

        # Focus the button so keyboard events work
        button = self.query_one("#error_back_to_menu", Button)
        button.focus()

    @on(Button.Pressed, "#error_back_to_menu")
    async def on_error_back_button_pressed(self, event: Button.Pressed) -> None:  # noqa: ARG002
        """Handle error screen back button press."""
        await self.action_cleanup_and_exit()

    async def _save_session_state(self) -> None:
        """Save current session state to user settings for resume capability."""
        try:
            # Get user settings handler
            if hasattr(self.app, "container") and self.app.container:
                save_user_settings_command_handler = (
                    self.app.container.get_save_user_settings_command_handler()
                )
                load_user_settings_query_handler = (
                    self.app.container.get_load_user_settings_query_handler()
                )
            else:
                logger.warning("No app container available for saving session state")
                return

            # First load current settings
            from src.application.queries.load_user_settings_query import (
                LoadUserSettingsQuery,
            )

            query = LoadUserSettingsQuery(user_id=1)
            result = await load_user_settings_query_handler.handle(query)

            if not result.success or not result.user_settings:
                logger.warning("Could not load current user settings for state update")
                return

            # Update flow data with current practice state
            current_flow_data = result.user_settings.flow_state.flow_data.copy()
            practice_state_key = f"practice_state_{self.practice_mode}"
            current_flow_data[practice_state_key] = self._question_state.copy()

            # Create updated flow state
            from src.domain.user.models.user_models import UserFlowState

            updated_flow_state = UserFlowState(
                current_screen=result.user_settings.flow_state.current_screen,
                session_in_progress=result.user_settings.flow_state.session_in_progress,
                current_session_id=result.user_settings.flow_state.current_session_id,
                last_question_id=result.user_settings.flow_state.last_question_id,
                setup_step=result.user_settings.flow_state.setup_step,
                flow_data=current_flow_data,
            )

            # Create updated user settings
            updated_settings = result.user_settings.update_flow_state(
                updated_flow_state
            )

            # Save updated settings
            from src.application.commands.save_user_settings_command import (
                SaveUserSettingsCommand,
            )

            command = SaveUserSettingsCommand(user_settings=updated_settings)

            save_result = await save_user_settings_command_handler.handle(command)

            if save_result.success:
                logger.info(
                    f"Session state saved for {self.practice_mode}: {self._question_state}"
                )
            else:
                logger.warning(
                    f"Failed to save session state: {save_result.error_message}"
                )

        except Exception as e:
            logger.error(f"Error saving session state: {e}")
            # Continue without saving (non-critical error)

    async def _create_practice_session(self) -> None:
        """Create a practice session for progress tracking using CQRS command."""
        try:
            # Create session once per PracticeScreen instance to avoid duplicate sessions
            if self.session_id is not None:
                logger.info(f"Session {self.session_id} already exists, reusing")
                return

            # Get session repository from container
            container = None
            if hasattr(self.app, "container") and self.app.container:
                container = self.app.container
            else:
                from src.infrastructure.containers.main_container import MainContainer

                container = MainContainer()

            session_repository = container.get_session_repository()

            # Create a new session for this practice screen instance
            self.session_id = await session_repository.create_session(
                user_id=1,
                session_type=self.practice_mode,
                configuration={"limit": 50},  # Default limit for practice sessions
            )
            logger.info(
                f"Created practice session {self.session_id} for mode {self.practice_mode}"
            )

        except Exception as e:
            logger.warning(f"Failed to create practice session: {e}")
            # Continue without session tracking
            self.session_id = None
