"""Tests for question view with different image configurations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.queries.enhanced_question_content_query import (
    EnhancedQuestionContentQueryHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQueryHandler,
)
from src.domain.content.models.question_models import Question
from src.domain.user.models.user_models import Language
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.question_view import PracticeScreen, QuestionWidget


class TestQuestionView:
    """Test question view for different question types."""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def user_repository(self):
        """Create mock user repository."""
        return MagicMock(spec=UserSettingsRepository)

    @pytest.fixture
    def submit_handler(self):
        """Create mock submit answer command handler."""
        handler = AsyncMock()
        handler.handle = AsyncMock(return_value=MagicMock(success=True))
        return handler

    @pytest.fixture
    def enhanced_question_handler(self):
        """Create mock enhanced question query handler."""
        handler = MagicMock(spec=EnhancedQuestionContentQueryHandler)
        handler.handle = AsyncMock(
            return_value=MagicMock(success=True, enhanced_data=None)
        )
        return handler

    @pytest.fixture
    def load_user_settings_handler(self):
        """Create mock load user settings query handler."""
        handler = MagicMock(spec=LoadUserSettingsQueryHandler)
        handler.handle = AsyncMock(
            return_value=MagicMock(success=True, user_settings=None)
        )
        return handler

    @pytest.fixture
    def text_question(self):
        """Create a question without images."""
        return Question(
            id=1,
            question="Was ist die Hauptstadt von Deutschland?",
            options='["Berlin", "München", "Hamburg", "Frankfurt"]',
            correct="Berlin",
            category="Politik und Geschichte",
            difficulty="easy",
            question_type="general",
            is_image_question=False,
            page_number=1,
        )

    @pytest.fixture
    def single_image_question(self):
        """Create a question with 1 image (like q55)."""
        return Question(
            id=55,
            question="Was zeigt dieses Bild?",
            options='["den Bundestagssitz in Berlin", "das Bundesverfassungsgericht in Karlsruhe", "das Bundesratsgebäude in Berlin", "das Bundeskanzleramt in Berlin"]',
            correct="den Bundestagssitz in Berlin",
            category="Politik und Geschichte",
            difficulty="easy",
            question_type="general",
            is_image_question=True,
            page_number=21,
        )

    @pytest.fixture
    def multi_image_question(self):
        """Create a question with 4 images (like q21)."""
        return Question(
            id=21,
            question="Welches ist das Wappen der Bundesrepublik Deutschland?",
            options='["Bild 1", "Bild 2", "Bild 3", "Bild 4"]',
            correct="Bild 1",
            category="Politik und Geschichte",
            difficulty="easy",
            question_type="general",
            is_image_question=True,
            page_number=9,
        )

    def test_text_question_layout(
        self,
        text_question,
        event_bus,
        enhanced_question_handler,
        load_user_settings_handler,
        submit_handler,
    ):
        """Test layout for questions without images."""
        # Create widget
        widget = QuestionWidget(
            question=text_question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_handler,
            preferred_language=Language.ENGLISH,
        )

        # Test that text questions are handled correctly
        assert not text_question.is_image_question
        assert widget.question.id == 1
        assert len(widget.question.options_list) == 4

    def test_single_image_question_layout(
        self,
        single_image_question,
        event_bus,
        enhanced_question_handler,
        load_user_settings_handler,
        submit_handler,
    ):
        """Test layout for questions with 1 image."""
        # Create widget
        widget = QuestionWidget(
            question=single_image_question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_handler,
            preferred_language=Language.ENGLISH,
        )

        # Test that single image questions are handled correctly
        assert single_image_question.is_image_question
        assert widget.question.id == 55
        assert len(widget.question.options_list) == 4
        assert "Bundestagssitz" in widget.question.options_list[0]

    def test_multi_image_question_layout(
        self,
        multi_image_question,
        event_bus,
        enhanced_question_handler,
        load_user_settings_handler,
        submit_handler,
    ):
        """Test layout for questions with 4 images."""
        # Create widget
        widget = QuestionWidget(
            question=multi_image_question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_handler,
            preferred_language=Language.ENGLISH,
        )

        # Test that multi-image questions are handled correctly
        assert multi_image_question.is_image_question
        assert widget.question.id == 21
        assert len(widget.question.options_list) == 4
        assert all("Bild" in option for option in widget.question.options_list)

    def test_compose_text_options_basic(
        self,
        text_question,
        event_bus,
        enhanced_question_handler,
        load_user_settings_handler,
        submit_handler,
    ):
        """Test that text question widget can be created."""
        widget = QuestionWidget(
            question=text_question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_handler,
        )

        # Test widget properties
        assert widget.question == text_question
        assert widget.selected_answer is None
        assert not widget.answer_revealed
        assert widget.preferred_language == Language.ENGLISH

    def test_image_count_detection_logic(
        self, single_image_question, multi_image_question
    ):
        """Test image count detection logic."""
        # Test that we can distinguish between single and multi-image questions
        assert single_image_question.is_image_question
        assert single_image_question.id == 55

        assert multi_image_question.is_image_question
        assert multi_image_question.id == 21

        # Different question content should indicate different layouts needed
        single_options = single_image_question.options_list
        multi_options = multi_image_question.options_list

        # Single image question has descriptive text options
        assert any("Bundestagssitz" in option for option in single_options)

        # Multi image question has generic "Bild" options
        assert all("Bild" in option for option in multi_options)

    @pytest.mark.asyncio
    async def test_answer_button_click_handling(
        self,
        text_question,
        event_bus,
        enhanced_question_handler,
        load_user_settings_handler,
        submit_handler,
    ):
        """Test that answer buttons can be clicked."""
        widget = QuestionWidget(
            question=text_question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_handler,
        )

        # Enable test mode to bypass timing protection
        widget._test_mode = True

        # Mock button press event
        mock_button = MagicMock()
        mock_button.id = "option_2"
        mock_event = MagicMock()
        mock_event.button = mock_button

        # Mock the DOM query methods and reveal_answer
        mock_button_widget = MagicMock()
        mock_button_widget.variant = "default"
        mock_button_widget.add_class = MagicMock()
        mock_button_widget.disabled = False

        widget.query_one = MagicMock(return_value=mock_button_widget)
        widget.reveal_answer = AsyncMock()

        # Test answer selection
        await widget.on_answer_selected(mock_event)

        # Should set selected answer and call reveal_answer
        assert widget.selected_answer == "München"
        widget.reveal_answer.assert_called_once()

    def test_invalid_option_handling(self):
        """Test handling of invalid option numbers (5-9)."""
        screen = PracticeScreen(
            practice_mode="random",
            user_repository=MagicMock(),
            submit_answer_command_handler=MagicMock(),
            start_practice_command_handler=MagicMock(),
        )

        # Mock notify method
        screen.notify = MagicMock()

        # Test invalid option action
        screen.action_invalid_option()

        # Should show warning
        screen.notify.assert_called_once_with(
            "Only options 1-4 are available", severity="warning", timeout=2
        )

    def test_keyboard_shortcuts(self):
        """Test keyboard shortcuts for options 1-4."""
        screen = PracticeScreen(
            practice_mode="random",
            user_repository=MagicMock(),
            submit_answer_command_handler=MagicMock(),
            start_practice_command_handler=MagicMock(),
        )

        # Check bindings
        bindings = screen.BINDINGS

        # Should have bindings for 1-4
        assert ("1", "select_option_1", "Option 1") in bindings
        assert ("2", "select_option_2", "Option 2") in bindings
        assert ("3", "select_option_3", "Option 3") in bindings
        assert ("4", "select_option_4", "Option 4") in bindings

        # Should have bindings for 5-9 (invalid options)
        assert ("5", "invalid_option", "") in bindings
        assert ("9", "invalid_option", "") in bindings

        # Should have view images binding
        assert ("v", "view_images_externally", "View Images") in bindings

    def test_question_types(
        self, text_question, single_image_question, multi_image_question
    ):
        """Test that we have the right question types for testing."""
        # Text question
        assert not text_question.is_image_question
        assert text_question.id == 1
        assert len(text_question.options_list) == 4

        # Single image question
        assert single_image_question.is_image_question
        assert single_image_question.id == 55
        assert len(single_image_question.options_list) == 4

        # Multi image question
        assert multi_image_question.is_image_question
        assert multi_image_question.id == 21
        assert len(multi_image_question.options_list) == 4
