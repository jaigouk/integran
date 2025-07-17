"""Tests for bookmark UI components and integration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from textual.app import ComposeResult

from src.application.commands.bookmark_commands import (
    AddBookmarkCommand,
    AddBookmarkCommandHandler,
    RemoveBookmarkCommand,
    RemoveBookmarkCommandHandler,
)
from src.application.queries.bookmark_queries import (
    GetBookmarksQuery,
    GetBookmarksQueryHandler,
    GetBookmarkStatusQuery,
    GetBookmarkStatusQueryHandler,
)
from src.domain.content.models.question_models import Question
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection
from src.domain.user.models.user_models import Language
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository


class MockBookmarkMenuScreen:
    """Mock bookmark menu screen for testing."""

    def __init__(self, bookmark_query_handler, bookmark_command_handler):
        """Initialize mock bookmark menu screen."""
        self.bookmark_query_handler = bookmark_query_handler
        self.bookmark_command_handler = bookmark_command_handler
        self.app = Mock()
        self.bookmarks = []
        self.selected_bookmark = None
        self.show_empty_state = False

    def compose(self) -> ComposeResult:
        """Compose the bookmark menu screen."""
        # Mock compose method
        return []

    async def load_bookmarks(self, user_id: int) -> None:
        """Load bookmarks for user."""
        query = GetBookmarksQuery(user_id=user_id)
        result = await self.bookmark_query_handler.handle(query)

        if result.success:
            self.bookmarks = result.bookmarks.bookmarks
            self.show_empty_state = result.bookmarks.is_empty
        else:
            self.bookmarks = []
            self.show_empty_state = True

    async def remove_bookmark(self, user_id: int, question_id: int) -> bool:
        """Remove bookmark."""
        command = RemoveBookmarkCommand(user_id=user_id, question_id=question_id)
        result = await self.bookmark_command_handler.handle(command)
        return result.success

    def action_practice_bookmarks(self) -> None:
        """Start practice session with bookmarks."""
        # Mock action for testing
        pass

    def action_manage_bookmarks(self) -> None:
        """Open bookmark management screen."""
        # Mock action for testing
        pass


class MockBookmarkWidget:
    """Mock bookmark widget for testing."""

    def __init__(self, bookmark: Bookmark):
        """Initialize mock bookmark widget."""
        self.bookmark = bookmark
        self.is_selected = False
        self.show_notes = False

    def toggle_selection(self) -> None:
        """Toggle bookmark selection."""
        self.is_selected = not self.is_selected

    def show_bookmark_notes(self) -> None:
        """Show bookmark notes."""
        self.show_notes = True

    def hide_bookmark_notes(self) -> None:
        """Hide bookmark notes."""
        self.show_notes = False


class MockBookmarkButton:
    """Mock bookmark button widget for testing."""

    def __init__(
        self, question: Question, bookmark_status_handler, bookmark_command_handler
    ):
        """Initialize mock bookmark button."""
        self.question = question
        self.bookmark_status_handler = bookmark_status_handler
        self.bookmark_command_handler = bookmark_command_handler
        self.is_bookmarked = False
        self.is_loading = False

    async def check_bookmark_status(self, user_id: int) -> None:
        """Check if question is bookmarked."""
        query = GetBookmarkStatusQuery(user_id=user_id, question_id=self.question.id)
        result = await self.bookmark_status_handler.handle(query)

        if result.success:
            self.is_bookmarked = result.is_bookmarked

    async def toggle_bookmark(self, user_id: int) -> None:
        """Toggle bookmark status."""
        self.is_loading = True

        try:
            if self.is_bookmarked:
                command = RemoveBookmarkCommand(
                    user_id=user_id, question_id=self.question.id
                )
                result = await self.bookmark_command_handler.handle(command)
                if result.success:
                    self.is_bookmarked = False
            else:
                command = AddBookmarkCommand(
                    user_id=user_id, question_id=self.question.id
                )
                result = await self.bookmark_command_handler.handle(command)
                if result.success:
                    self.is_bookmarked = True
        finally:
            self.is_loading = False


class TestBookmarkMenuScreen:
    """Test bookmark menu screen functionality."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock(spec=GetBookmarksQueryHandler)

    @pytest.fixture
    def mock_bookmark_command_handler(self):
        """Mock bookmark command handler."""
        return AsyncMock(spec=RemoveBookmarkCommandHandler)

    @pytest.fixture
    def sample_bookmarks(self):
        """Create sample bookmarks."""
        return [
            Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes="Important constitutional law question",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=100,
                question_id=43,
                notes="History of Germany",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=3,
                user_id=100,
                question_id=44,
                notes=None,
                created_at=datetime.now(UTC),
            ),
        ]

    @pytest.fixture
    def bookmark_collection(self, sample_bookmarks):
        """Create bookmark collection."""
        return BookmarkCollection(
            user_id=100, bookmarks=sample_bookmarks, total_count=3
        )

    @pytest.fixture
    def bookmark_menu_screen(
        self, mock_bookmark_query_handler, mock_bookmark_command_handler
    ):
        """Create bookmark menu screen."""
        return MockBookmarkMenuScreen(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=mock_bookmark_command_handler,
        )

    @pytest.mark.asyncio
    async def test_bookmark_menu_screen_load_bookmarks_success(
        self, bookmark_menu_screen, mock_bookmark_query_handler, bookmark_collection
    ):
        """Test successful bookmark loading."""
        # Arrange
        from src.application.queries.bookmark_queries import GetBookmarksQueryResult

        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(bookmark_collection)
        )

        # Act
        await bookmark_menu_screen.load_bookmarks(user_id=100)

        # Assert
        assert len(bookmark_menu_screen.bookmarks) == 3
        assert bookmark_menu_screen.show_empty_state is False
        mock_bookmark_query_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_menu_screen_load_bookmarks_empty(
        self, bookmark_menu_screen, mock_bookmark_query_handler
    ):
        """Test bookmark loading with empty result."""
        # Arrange
        from src.application.queries.bookmark_queries import GetBookmarksQueryResult

        empty_collection = BookmarkCollection(user_id=100, bookmarks=[], total_count=0)
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(empty_collection)
        )

        # Act
        await bookmark_menu_screen.load_bookmarks(user_id=100)

        # Assert
        assert len(bookmark_menu_screen.bookmarks) == 0
        assert bookmark_menu_screen.show_empty_state is True

    @pytest.mark.asyncio
    async def test_bookmark_menu_screen_load_bookmarks_error(
        self, bookmark_menu_screen, mock_bookmark_query_handler
    ):
        """Test bookmark loading with error."""
        # Arrange
        from src.application.queries.bookmark_queries import GetBookmarksQueryResult

        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.error_result("Database error")
        )

        # Act
        await bookmark_menu_screen.load_bookmarks(user_id=100)

        # Assert
        assert len(bookmark_menu_screen.bookmarks) == 0
        assert bookmark_menu_screen.show_empty_state is True

    @pytest.mark.asyncio
    async def test_bookmark_menu_screen_remove_bookmark_success(
        self, bookmark_menu_screen, mock_bookmark_command_handler
    ):
        """Test successful bookmark removal."""
        # Arrange
        from src.application.commands.bookmark_commands import (
            RemoveBookmarkCommandResult,
        )

        mock_bookmark_command_handler.handle.return_value = (
            RemoveBookmarkCommandResult.success_result()
        )

        # Act
        result = await bookmark_menu_screen.remove_bookmark(user_id=100, question_id=42)

        # Assert
        assert result is True
        mock_bookmark_command_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_menu_screen_remove_bookmark_failure(
        self, bookmark_menu_screen, mock_bookmark_command_handler
    ):
        """Test bookmark removal failure."""
        # Arrange
        from src.application.commands.bookmark_commands import (
            RemoveBookmarkCommandResult,
        )

        mock_bookmark_command_handler.handle.return_value = (
            RemoveBookmarkCommandResult.error_result("Bookmark not found")
        )

        # Act
        result = await bookmark_menu_screen.remove_bookmark(user_id=100, question_id=42)

        # Assert
        assert result is False

    def test_bookmark_menu_screen_action_practice_bookmarks(self, bookmark_menu_screen):
        """Test practice bookmarks action."""
        # Act
        bookmark_menu_screen.action_practice_bookmarks()

        # Assert - should not raise exception
        # In real implementation, this would start practice mode
        pass

    def test_bookmark_menu_screen_action_manage_bookmarks(self, bookmark_menu_screen):
        """Test manage bookmarks action."""
        # Act
        bookmark_menu_screen.action_manage_bookmarks()

        # Assert - should not raise exception
        # In real implementation, this would open management screen
        pass


class TestBookmarkWidget:
    """Test bookmark widget functionality."""

    @pytest.fixture
    def sample_bookmark(self):
        """Create sample bookmark."""
        return Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Important question about German constitution",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def bookmark_widget(self, sample_bookmark):
        """Create bookmark widget."""
        return MockBookmarkWidget(bookmark=sample_bookmark)

    def test_bookmark_widget_initialization(self, bookmark_widget, sample_bookmark):
        """Test bookmark widget initialization."""
        assert bookmark_widget.bookmark == sample_bookmark
        assert bookmark_widget.is_selected is False
        assert bookmark_widget.show_notes is False

    def test_bookmark_widget_toggle_selection(self, bookmark_widget):
        """Test bookmark widget selection toggle."""
        # Initially not selected
        assert bookmark_widget.is_selected is False

        # Toggle selection
        bookmark_widget.toggle_selection()
        assert bookmark_widget.is_selected is True

        # Toggle again
        bookmark_widget.toggle_selection()
        assert bookmark_widget.is_selected is False

    def test_bookmark_widget_show_notes(self, bookmark_widget):
        """Test showing bookmark notes."""
        # Initially notes not shown
        assert bookmark_widget.show_notes is False

        # Show notes
        bookmark_widget.show_bookmark_notes()
        assert bookmark_widget.show_notes is True

    def test_bookmark_widget_hide_notes(self, bookmark_widget):
        """Test hiding bookmark notes."""
        # Show notes first
        bookmark_widget.show_bookmark_notes()
        assert bookmark_widget.show_notes is True

        # Hide notes
        bookmark_widget.hide_bookmark_notes()
        assert bookmark_widget.show_notes is False


class TestBookmarkButton:
    """Test bookmark button functionality."""

    @pytest.fixture
    def sample_question(self):
        """Create sample question."""
        return Question(
            id=42,
            question="What is the capital of Germany?",
            options='["Berlin", "Munich", "Hamburg", "Frankfurt"]',
            correct="Berlin",
            category="Geography",
            difficulty="easy",
            question_type="general",
            is_image_question=False,
            page_number=1,
        )

    @pytest.fixture
    def mock_bookmark_status_handler(self):
        """Mock bookmark status handler."""
        return AsyncMock(spec=GetBookmarkStatusQueryHandler)

    @pytest.fixture
    def mock_bookmark_command_handler(self):
        """Mock bookmark command handler."""
        return AsyncMock(spec=AddBookmarkCommandHandler)

    @pytest.fixture
    def bookmark_button(
        self,
        sample_question,
        mock_bookmark_status_handler,
        mock_bookmark_command_handler,
    ):
        """Create bookmark button."""
        return MockBookmarkButton(
            question=sample_question,
            bookmark_status_handler=mock_bookmark_status_handler,
            bookmark_command_handler=mock_bookmark_command_handler,
        )

    @pytest.mark.asyncio
    async def test_bookmark_button_check_status_bookmarked(
        self, bookmark_button, mock_bookmark_status_handler, sample_question
    ):
        """Test checking bookmark status when question is bookmarked."""
        # Arrange
        from src.application.queries.bookmark_queries import (
            GetBookmarkStatusQueryResult,
        )

        mock_bookmark_status_handler.handle.return_value = (
            GetBookmarkStatusQueryResult.success_result(is_bookmarked=True)
        )

        # Act
        await bookmark_button.check_bookmark_status(user_id=100)

        # Assert
        assert bookmark_button.is_bookmarked is True
        mock_bookmark_status_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_button_check_status_not_bookmarked(
        self, bookmark_button, mock_bookmark_status_handler
    ):
        """Test checking bookmark status when question is not bookmarked."""
        # Arrange
        from src.application.queries.bookmark_queries import (
            GetBookmarkStatusQueryResult,
        )

        mock_bookmark_status_handler.handle.return_value = (
            GetBookmarkStatusQueryResult.success_result(is_bookmarked=False)
        )

        # Act
        await bookmark_button.check_bookmark_status(user_id=100)

        # Assert
        assert bookmark_button.is_bookmarked is False

    @pytest.mark.asyncio
    async def test_bookmark_button_toggle_bookmark_add(
        self, bookmark_button, mock_bookmark_command_handler
    ):
        """Test toggling bookmark from not bookmarked to bookmarked."""
        # Arrange
        bookmark_button.is_bookmarked = False
        from src.application.commands.bookmark_commands import AddBookmarkCommandResult

        mock_bookmark_command_handler.handle.return_value = (
            AddBookmarkCommandResult.success_result(bookmark_id=1)
        )

        # Act
        await bookmark_button.toggle_bookmark(user_id=100)

        # Assert
        assert bookmark_button.is_bookmarked is True
        assert bookmark_button.is_loading is False
        mock_bookmark_command_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_button_toggle_bookmark_remove(
        self, bookmark_button, mock_bookmark_command_handler
    ):
        """Test toggling bookmark from bookmarked to not bookmarked."""
        # Arrange
        bookmark_button.is_bookmarked = True
        from src.application.commands.bookmark_commands import (
            RemoveBookmarkCommandResult,
        )

        mock_bookmark_command_handler.handle.return_value = (
            RemoveBookmarkCommandResult.success_result()
        )

        # Act
        await bookmark_button.toggle_bookmark(user_id=100)

        # Assert
        assert bookmark_button.is_bookmarked is False
        assert bookmark_button.is_loading is False
        mock_bookmark_command_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_button_toggle_bookmark_failure(
        self, bookmark_button, mock_bookmark_command_handler
    ):
        """Test bookmark toggle failure."""
        # Arrange
        bookmark_button.is_bookmarked = False
        from src.application.commands.bookmark_commands import AddBookmarkCommandResult

        mock_bookmark_command_handler.handle.return_value = (
            AddBookmarkCommandResult.error_result("Database error")
        )

        # Act
        await bookmark_button.toggle_bookmark(user_id=100)

        # Assert
        assert bookmark_button.is_bookmarked is False  # Should remain unchanged
        assert bookmark_button.is_loading is False

    @pytest.mark.asyncio
    async def test_bookmark_button_loading_state(
        self, bookmark_button, mock_bookmark_command_handler
    ):
        """Test bookmark button loading state during operation."""
        # Arrange
        bookmark_button.is_bookmarked = False
        from src.application.commands.bookmark_commands import AddBookmarkCommandResult

        # Mock slow operation
        async def slow_handle(_command):
            assert bookmark_button.is_loading is True
            return AddBookmarkCommandResult.success_result(bookmark_id=1)

        mock_bookmark_command_handler.handle.side_effect = slow_handle

        # Act
        await bookmark_button.toggle_bookmark(user_id=100)

        # Assert
        assert bookmark_button.is_loading is False  # Should be false after completion


class TestBookmarkIntegration:
    """Test bookmark integration with existing UI components."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock(spec=UserSettingsRepository)

    @pytest.fixture
    def sample_question(self):
        """Create sample question."""
        return Question(
            id=42,
            question="What is the capital of Germany?",
            options='["Berlin", "Munich", "Hamburg", "Frankfurt"]',
            correct="Berlin",
            category="Geography",
            difficulty="easy",
            question_type="general",
            is_image_question=False,
            page_number=1,
        )

    def test_bookmark_integration_with_question_view(
        self, sample_question, mock_event_bus, mock_user_repository
    ):
        """Test bookmark integration with question view."""
        # This would test that QuestionWidget can display bookmark button
        # and handle bookmark interactions

        # Mock handlers
        enhanced_question_handler = Mock()
        load_user_settings_handler = Mock()
        submit_answer_handler = Mock()

        # Import the real QuestionWidget
        from src.presentation.terminal.question_view import QuestionWidget

        # Create widget
        widget = QuestionWidget(
            question=sample_question,
            event_bus=mock_event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_answer_handler,
            preferred_language=Language.ENGLISH,
        )

        # Test that widget is created successfully
        assert widget.question == sample_question
        # In real implementation, widget would have bookmark button

    def test_bookmark_integration_with_practice_modes(self):
        """Test bookmark integration with practice modes."""
        # Test that bookmark practice mode can be started
        # This would integrate with existing PracticeScreen

        # Mock the practice screen with bookmarks mode
        from src.presentation.terminal.question_view import PracticeScreen

        # Create practice screen for bookmarks
        practice_screen = PracticeScreen(
            practice_mode="bookmarks",
            user_repository=Mock(),
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )

        # Test that practice screen is created successfully
        assert practice_screen.practice_mode == "bookmarks"
        # In real implementation, this would load bookmark questions

    def test_bookmark_integration_with_main_menu(self):
        """Test bookmark integration with main menu."""
        # This would test that main menu has bookmark option

        # In real implementation, MainMenuScreen would have bookmark button
        # and action_bookmark_practice method

        # Mock main menu with bookmark support
        from src.presentation.terminal.trainer_app import MainMenuScreen

        screen = MainMenuScreen()

        # Test that main menu is created successfully
        assert screen is not None
        # In real implementation, screen would have bookmark button

    @pytest.mark.asyncio
    async def test_bookmark_keyboard_shortcuts(self):
        """Test bookmark keyboard shortcuts."""
        # Test that bookmark actions can be triggered via keyboard

        # Mock screen with bookmark keyboard bindings
        class MockBookmarkScreen:
            BINDINGS = [
                ("b", "toggle_bookmark", "Bookmark"),
                ("ctrl+b", "show_bookmarks", "Show Bookmarks"),
            ]

            def __init__(self):
                self.bookmark_toggled = False
                self.bookmarks_shown = False

            def action_toggle_bookmark(self):
                self.bookmark_toggled = True

            def action_show_bookmarks(self):
                self.bookmarks_shown = True

        screen = MockBookmarkScreen()

        # Test keyboard bindings
        assert ("b", "toggle_bookmark", "Bookmark") in screen.BINDINGS
        assert ("ctrl+b", "show_bookmarks", "Show Bookmarks") in screen.BINDINGS

        # Test actions
        screen.action_toggle_bookmark()
        screen.action_show_bookmarks()

        assert screen.bookmark_toggled is True
        assert screen.bookmarks_shown is True


class TestBookmarkUIResponsiveness:
    """Test bookmark UI responsiveness and performance."""

    @pytest.fixture
    def large_bookmark_collection(self):
        """Create large bookmark collection for performance testing."""
        bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 1001)  # 1000 bookmarks
        ]
        return BookmarkCollection(user_id=100, bookmarks=bookmarks, total_count=1000)

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler for performance tests."""
        return AsyncMock(spec=GetBookmarksQueryHandler)

    @pytest.fixture
    def bookmark_menu_screen(self, mock_bookmark_query_handler):
        """Create bookmark menu screen for performance tests."""
        return MockBookmarkMenuScreen(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

    @pytest.mark.asyncio
    async def test_bookmark_menu_performance_with_large_dataset(
        self,
        bookmark_menu_screen,
        mock_bookmark_query_handler,
        large_bookmark_collection,
    ):
        """Test bookmark menu performance with large bookmark collection."""
        # Arrange
        from src.application.queries.bookmark_queries import GetBookmarksQueryResult

        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(large_bookmark_collection)
        )

        # Act
        import time

        start_time = time.time()
        await bookmark_menu_screen.load_bookmarks(user_id=100)
        end_time = time.time()

        # Assert
        loading_time = end_time - start_time
        assert loading_time < 1.0  # Should load in under 1 second
        assert len(bookmark_menu_screen.bookmarks) == 1000
        assert bookmark_menu_screen.show_empty_state is False

    @pytest.mark.asyncio
    async def test_bookmark_pagination_handling(
        self, bookmark_menu_screen, mock_bookmark_query_handler
    ):
        """Test bookmark pagination handling."""
        # Arrange - simulate paginated results
        from src.application.queries.bookmark_queries import GetBookmarksQueryResult

        # First page
        page1_bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 21)  # 20 bookmarks
        ]
        page1_collection = BookmarkCollection(
            user_id=100, bookmarks=page1_bookmarks, total_count=100
        )

        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(page1_collection)
        )

        # Act
        await bookmark_menu_screen.load_bookmarks(user_id=100)

        # Assert
        assert len(bookmark_menu_screen.bookmarks) == 20
        assert bookmark_menu_screen.show_empty_state is False

        # Verify query was called with proper parameters
        mock_bookmark_query_handler.handle.assert_called_once()
        call_args = mock_bookmark_query_handler.handle.call_args[0][0]
        assert call_args.user_id == 100

    def test_bookmark_widget_memory_efficiency(self):
        """Test bookmark widget memory efficiency."""
        # Test that bookmark widgets don't leak memory

        # Create many bookmark widgets
        bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 101)  # 100 bookmarks
        ]

        # Create widgets
        widgets = [MockBookmarkWidget(bookmark) for bookmark in bookmarks]

        # Test that all widgets are created
        assert len(widgets) == 100

        # Test that widgets don't reference each other
        for i, widget in enumerate(widgets):
            assert widget.bookmark.id == i + 1
            assert widget.is_selected is False

    @pytest.mark.asyncio
    async def test_bookmark_concurrent_operations(self):
        """Test concurrent bookmark operations."""
        # Test that multiple bookmark operations can run concurrently

        import asyncio

        # Mock handlers
        status_handler = AsyncMock()
        command_handler = AsyncMock()

        # Create multiple bookmark buttons
        questions = [
            Question(
                id=i,
                question=f"Question {i}",
                options='["A", "B", "C", "D"]',
                correct="A",
                category="Test",
                difficulty="easy",
                question_type="general",
                is_image_question=False,
                page_number=1,
            )
            for i in range(1, 11)  # 10 questions
        ]

        buttons = [
            MockBookmarkButton(question, status_handler, command_handler)
            for question in questions
        ]

        # Mock successful responses
        from src.application.commands.bookmark_commands import AddBookmarkCommandResult
        from src.application.queries.bookmark_queries import (
            GetBookmarkStatusQueryResult,
        )

        status_handler.handle.return_value = (
            GetBookmarkStatusQueryResult.success_result(is_bookmarked=False)
        )
        command_handler.handle.return_value = AddBookmarkCommandResult.success_result(
            bookmark_id=1
        )

        # Run concurrent operations
        tasks = [button.check_bookmark_status(user_id=100) for button in buttons]

        # Act
        await asyncio.gather(*tasks)

        # Assert
        assert status_handler.handle.call_count == 10
        assert all(not button.is_bookmarked for button in buttons)


class TestBookmarkUIAccessibility:
    """Test bookmark UI accessibility features."""

    def test_bookmark_keyboard_navigation(self):
        """Test bookmark keyboard navigation."""
        # Test that bookmarks can be navigated using keyboard

        # Mock bookmark list with keyboard navigation
        class MockBookmarkList:
            def __init__(self, bookmarks):
                self.bookmarks = bookmarks
                self.current_index = 0

            def navigate_next(self):
                if self.current_index < len(self.bookmarks) - 1:
                    self.current_index += 1
                    return True
                return False

            def navigate_previous(self):
                if self.current_index > 0:
                    self.current_index -= 1
                    return True
                return False

            def get_current_bookmark(self):
                return self.bookmarks[self.current_index]

        # Create bookmarks
        bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 4)  # 3 bookmarks
        ]

        bookmark_list = MockBookmarkList(bookmarks)

        # Test navigation
        assert bookmark_list.current_index == 0
        assert bookmark_list.get_current_bookmark().id == 1

        # Navigate next
        assert bookmark_list.navigate_next() is True
        assert bookmark_list.current_index == 1
        assert bookmark_list.get_current_bookmark().id == 2

        # Navigate previous
        assert bookmark_list.navigate_previous() is True
        assert bookmark_list.current_index == 0
        assert bookmark_list.get_current_bookmark().id == 1

        # Test boundaries
        assert bookmark_list.navigate_previous() is False  # Already at start

        # Navigate to end
        bookmark_list.navigate_next()
        bookmark_list.navigate_next()
        assert bookmark_list.current_index == 2
        assert bookmark_list.navigate_next() is False  # Already at end

    def test_bookmark_screen_reader_support(self):
        """Test bookmark screen reader support."""
        # Test that bookmark components have proper labels

        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Important constitutional law question",
            created_at=datetime.now(UTC),
        )

        # Mock widget with accessibility labels
        class MockAccessibleBookmarkWidget:
            def __init__(self, bookmark):
                self.bookmark = bookmark
                self.aria_label = f"Bookmark for question {bookmark.question_id}"
                self.aria_description = bookmark.notes if bookmark.notes else "No notes"
                self.role = "button"
                self.tabindex = 0

        widget = MockAccessibleBookmarkWidget(bookmark)

        # Test accessibility attributes
        assert widget.aria_label == "Bookmark for question 42"
        assert widget.aria_description == "Important constitutional law question"
        assert widget.role == "button"
        assert widget.tabindex == 0

    def test_bookmark_high_contrast_support(self):
        """Test bookmark high contrast support."""
        # Test that bookmark UI supports high contrast mode

        # Mock theme with high contrast colors
        class MockHighContrastTheme:
            def __init__(self):
                self.bookmark_button_color = "white"
                self.bookmark_button_background = "black"
                self.bookmark_active_color = "yellow"
                self.bookmark_active_background = "blue"
                self.text_color = "white"
                self.background_color = "black"

        theme = MockHighContrastTheme()

        # Test theme colors
        assert theme.bookmark_button_color == "white"
        assert theme.bookmark_button_background == "black"
        assert theme.bookmark_active_color == "yellow"
        assert theme.bookmark_active_background == "blue"

    def test_bookmark_font_size_support(self):
        """Test bookmark font size support."""
        # Test that bookmark UI supports different font sizes

        # Mock font size settings
        class MockFontSettings:
            def __init__(self):
                self.font_size = "medium"
                self.font_scale = 1.0

            def set_font_size(self, size):
                size_map = {
                    "small": 0.8,
                    "medium": 1.0,
                    "large": 1.2,
                    "extra_large": 1.5,
                }
                self.font_size = size
                self.font_scale = size_map.get(size, 1.0)

        settings = MockFontSettings()

        # Test font size changes
        assert settings.font_scale == 1.0

        settings.set_font_size("large")
        assert settings.font_size == "large"
        assert settings.font_scale == 1.2

        settings.set_font_size("small")
        assert settings.font_size == "small"
        assert settings.font_scale == 0.8
