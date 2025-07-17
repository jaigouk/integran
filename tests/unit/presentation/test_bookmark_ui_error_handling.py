"""Tests for bookmark UI error handling and edge cases."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.commands.bookmark_commands import (
    AddBookmarkCommandResult,
)
from src.application.queries.bookmark_queries import (
    GetBookmarksQueryResult,
)
from src.domain.shared.repositories import RepositoryError
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection


class MockBookmarkErrorHandler:
    """Mock bookmark error handler for testing."""

    def __init__(self):
        """Initialize mock error handler."""
        self.error_messages = []
        self.error_count = 0
        self.last_error_type = None

    def handle_error(self, error_type: str, message: str) -> None:
        """Handle error for testing."""
        self.error_messages.append(message)
        self.error_count += 1
        self.last_error_type = error_type

    def clear_errors(self) -> None:
        """Clear error state."""
        self.error_messages.clear()
        self.error_count = 0
        self.last_error_type = None


class MockBookmarkUIWithErrorHandling:
    """Mock bookmark UI with error handling."""

    def __init__(self, bookmark_query_handler, bookmark_command_handler):
        """Initialize mock UI with error handling."""
        self.bookmark_query_handler = bookmark_query_handler
        self.bookmark_command_handler = bookmark_command_handler
        self.error_handler = MockBookmarkErrorHandler()
        self.is_loading = False
        self.bookmarks = []
        self.connection_status = "connected"

    async def load_bookmarks_with_error_handling(self, user_id: int) -> bool:
        """Load bookmarks with error handling."""
        try:
            self.is_loading = True

            from src.application.queries.bookmark_queries import GetBookmarksQuery

            query = GetBookmarksQuery(user_id=user_id)
            result = await self.bookmark_query_handler.handle(query)

            if result.success:
                self.bookmarks = result.bookmarks.bookmarks
                return True
            else:
                self.error_handler.handle_error("LOAD_ERROR", result.error_message)
                return False

        except Exception as e:
            self.error_handler.handle_error("EXCEPTION", str(e))
            return False
        finally:
            self.is_loading = False

    async def add_bookmark_with_error_handling(
        self, user_id: int, question_id: int
    ) -> bool:
        """Add bookmark with error handling."""
        try:
            self.is_loading = True

            from src.application.commands.bookmark_commands import AddBookmarkCommand

            command = AddBookmarkCommand(user_id=user_id, question_id=question_id)
            result = await self.bookmark_command_handler.handle(command)

            if result.success:
                return True
            else:
                self.error_handler.handle_error("ADD_ERROR", result.error_message)
                return False

        except Exception as e:
            self.error_handler.handle_error("EXCEPTION", str(e))
            return False
        finally:
            self.is_loading = False

    def simulate_network_error(self) -> None:
        """Simulate network connectivity error."""
        self.connection_status = "disconnected"
        self.error_handler.handle_error("NETWORK_ERROR", "No internet connection")

    def simulate_recovery(self) -> None:
        """Simulate recovery from error."""
        self.connection_status = "connected"
        self.error_handler.clear_errors()


class TestBookmarkUIErrorHandling:
    """Test bookmark UI error handling scenarios."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock()

    @pytest.fixture
    def mock_bookmark_command_handler(self):
        """Mock bookmark command handler."""
        return AsyncMock()

    @pytest.fixture
    def bookmark_ui(self, mock_bookmark_query_handler, mock_bookmark_command_handler):
        """Create bookmark UI with error handling."""
        return MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=mock_bookmark_command_handler,
        )

    @pytest.mark.asyncio
    async def test_bookmark_load_error_handling(
        self, bookmark_ui, mock_bookmark_query_handler
    ):
        """Test bookmark loading error handling."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.error_result("Database connection failed")
        )

        # Act
        result = await bookmark_ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is False
        assert bookmark_ui.error_handler.error_count == 1
        assert bookmark_ui.error_handler.last_error_type == "LOAD_ERROR"
        assert (
            "Database connection failed" in bookmark_ui.error_handler.error_messages[0]
        )
        assert bookmark_ui.is_loading is False

    @pytest.mark.asyncio
    async def test_bookmark_add_error_handling(
        self, bookmark_ui, mock_bookmark_command_handler
    ):
        """Test bookmark adding error handling."""
        # Arrange
        mock_bookmark_command_handler.handle.return_value = (
            AddBookmarkCommandResult.error_result("Bookmark already exists")
        )

        # Act
        result = await bookmark_ui.add_bookmark_with_error_handling(
            user_id=100, question_id=42
        )

        # Assert
        assert result is False
        assert bookmark_ui.error_handler.error_count == 1
        assert bookmark_ui.error_handler.last_error_type == "ADD_ERROR"
        assert "Bookmark already exists" in bookmark_ui.error_handler.error_messages[0]
        assert bookmark_ui.is_loading is False

    @pytest.mark.asyncio
    async def test_bookmark_exception_handling(
        self, bookmark_ui, mock_bookmark_query_handler
    ):
        """Test bookmark exception handling."""
        # Arrange
        mock_bookmark_query_handler.handle.side_effect = Exception("Unexpected error")

        # Act
        result = await bookmark_ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is False
        assert bookmark_ui.error_handler.error_count == 1
        assert bookmark_ui.error_handler.last_error_type == "EXCEPTION"
        assert "Unexpected error" in bookmark_ui.error_handler.error_messages[0]
        assert bookmark_ui.is_loading is False

    @pytest.mark.asyncio
    async def test_bookmark_loading_state_management(
        self, bookmark_ui, mock_bookmark_query_handler
    ):
        """Test bookmark loading state management."""
        # Arrange
        call_count = 0

        async def mock_handle(_query):
            nonlocal call_count
            call_count += 1
            # Check loading state during operation
            assert bookmark_ui.is_loading is True
            return GetBookmarksQueryResult.success_result(
                BookmarkCollection(user_id=100, bookmarks=[], total_count=0)
            )

        mock_bookmark_query_handler.handle.side_effect = mock_handle

        # Act
        result = await bookmark_ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is True
        assert bookmark_ui.is_loading is False
        assert call_count == 1

    def test_bookmark_network_error_simulation(self, bookmark_ui):
        """Test network error simulation."""
        # Initially connected
        assert bookmark_ui.connection_status == "connected"
        assert bookmark_ui.error_handler.error_count == 0

        # Simulate network error
        bookmark_ui.simulate_network_error()

        # Check error state
        assert bookmark_ui.connection_status == "disconnected"
        assert bookmark_ui.error_handler.error_count == 1
        assert bookmark_ui.error_handler.last_error_type == "NETWORK_ERROR"
        assert "No internet connection" in bookmark_ui.error_handler.error_messages[0]

    def test_bookmark_error_recovery(self, bookmark_ui):
        """Test error recovery."""
        # Simulate error first
        bookmark_ui.simulate_network_error()
        assert bookmark_ui.error_handler.error_count == 1

        # Simulate recovery
        bookmark_ui.simulate_recovery()

        # Check recovery state
        assert bookmark_ui.connection_status == "connected"
        assert bookmark_ui.error_handler.error_count == 0
        assert len(bookmark_ui.error_handler.error_messages) == 0

    @pytest.mark.asyncio
    async def test_bookmark_timeout_handling(
        self, bookmark_ui, mock_bookmark_query_handler
    ):
        """Test bookmark timeout handling."""
        # Arrange
        mock_bookmark_query_handler.handle.side_effect = TimeoutError(
            "Operation timeout"
        )

        # Act
        result = await bookmark_ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is False
        assert bookmark_ui.error_handler.error_count == 1
        assert bookmark_ui.error_handler.last_error_type == "EXCEPTION"
        assert "Operation timeout" in bookmark_ui.error_handler.error_messages[0]


class TestBookmarkUIEdgeCases:
    """Test bookmark UI edge cases."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock()

    @pytest.fixture
    def mock_bookmark_command_handler(self):
        """Mock bookmark command handler."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_bookmark_empty_state_handling(self, mock_bookmark_query_handler):
        """Test bookmark empty state handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        empty_collection = BookmarkCollection(user_id=100, bookmarks=[], total_count=0)
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(empty_collection)
        )

        # Act
        result = await ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is True
        assert len(ui.bookmarks) == 0
        assert ui.error_handler.error_count == 0

    @pytest.mark.asyncio
    async def test_bookmark_large_dataset_handling(self, mock_bookmark_query_handler):
        """Test bookmark large dataset handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        # Create large bookmark collection
        large_bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 10001)  # 10,000 bookmarks
        ]

        large_collection = BookmarkCollection(
            user_id=100, bookmarks=large_bookmarks, total_count=10000
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(large_collection)
        )

        # Act
        import time

        start_time = time.time()
        result = await ui.load_bookmarks_with_error_handling(user_id=100)
        end_time = time.time()

        # Assert
        assert result is True
        assert len(ui.bookmarks) == 10000
        assert ui.error_handler.error_count == 0

        # Should handle large dataset efficiently
        processing_time = end_time - start_time
        assert processing_time < 5.0  # Should process in under 5 seconds

    @pytest.mark.asyncio
    async def test_bookmark_special_characters_handling(
        self, mock_bookmark_query_handler
    ):
        """Test bookmark special characters handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        # Create bookmarks with special characters
        special_bookmarks = [
            Bookmark(
                id=1,
                user_id=100,
                question_id=1,
                notes="Special chars: äöü ß 日本語 🔖 €",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=100,
                question_id=2,
                notes="Quotes: 'single' \"double\" `backtick`",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=3,
                user_id=100,
                question_id=3,
                notes="Symbols: @#$%^&*()_+-=[]{}|\\:;\"'<>,.?/~",
                created_at=datetime.now(UTC),
            ),
        ]

        collection = BookmarkCollection(
            user_id=100, bookmarks=special_bookmarks, total_count=3
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(collection)
        )

        # Act
        result = await ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is True
        assert len(ui.bookmarks) == 3
        assert ui.error_handler.error_count == 0

        # Verify special characters are preserved
        assert "äöü ß 日本語 🔖 €" in ui.bookmarks[0].notes
        assert "'single' \"double\" `backtick`" in ui.bookmarks[1].notes
        assert "@#$%^&*()_+-=[]{}|\\:;\"'<>,.?/~" in ui.bookmarks[2].notes

    @pytest.mark.asyncio
    async def test_bookmark_null_values_handling(self, mock_bookmark_query_handler):
        """Test bookmark null values handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        # Create bookmarks with null values
        null_bookmarks = [
            Bookmark(
                id=1,
                user_id=100,
                question_id=1,
                notes=None,  # Null notes
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=100,
                question_id=2,
                notes="",  # Empty notes
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=3,
                user_id=100,
                question_id=3,
                notes="   ",  # Whitespace only
                created_at=datetime.now(UTC),
            ),
        ]

        collection = BookmarkCollection(
            user_id=100, bookmarks=null_bookmarks, total_count=3
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(collection)
        )

        # Act
        result = await ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is True
        assert len(ui.bookmarks) == 3
        assert ui.error_handler.error_count == 0

        # Verify null values are handled
        assert ui.bookmarks[0].notes is None
        assert ui.bookmarks[1].notes == ""
        assert ui.bookmarks[2].notes == "   "

    @pytest.mark.asyncio
    async def test_bookmark_concurrent_operations_error_handling(
        self, mock_bookmark_query_handler, mock_bookmark_command_handler
    ):
        """Test concurrent bookmark operations error handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=mock_bookmark_command_handler,
        )

        # Mock mixed success/failure responses
        mock_bookmark_command_handler.handle.side_effect = [
            AddBookmarkCommandResult.success_result(bookmark_id=1),
            AddBookmarkCommandResult.error_result("Duplicate bookmark"),
            AddBookmarkCommandResult.success_result(bookmark_id=2),
            AddBookmarkCommandResult.error_result("Database error"),
        ]

        # Act
        import asyncio

        tasks = [
            ui.add_bookmark_with_error_handling(user_id=100, question_id=41),
            ui.add_bookmark_with_error_handling(user_id=100, question_id=42),
            ui.add_bookmark_with_error_handling(user_id=100, question_id=43),
            ui.add_bookmark_with_error_handling(user_id=100, question_id=44),
        ]

        results = await asyncio.gather(*tasks)

        # Assert
        assert results == [True, False, True, False]
        assert ui.error_handler.error_count == 2
        assert "Duplicate bookmark" in ui.error_handler.error_messages[0]
        assert "Database error" in ui.error_handler.error_messages[1]

    @pytest.mark.asyncio
    async def test_bookmark_memory_pressure_handling(self, mock_bookmark_query_handler):
        """Test bookmark memory pressure handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        # Simulate memory pressure by creating very large notes
        large_notes = "x" * 100000  # 100KB notes
        memory_pressure_bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=large_notes,
                created_at=datetime.now(UTC),
            )
            for i in range(1, 101)  # 100 bookmarks with large notes
        ]

        collection = BookmarkCollection(
            user_id=100, bookmarks=memory_pressure_bookmarks, total_count=100
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(collection)
        )

        # Act
        result = await ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is True
        assert len(ui.bookmarks) == 100
        assert ui.error_handler.error_count == 0

        # Verify large notes are handled
        assert len(ui.bookmarks[0].notes) == 100000

    @pytest.mark.asyncio
    async def test_bookmark_database_corruption_handling(
        self, mock_bookmark_query_handler
    ):
        """Test bookmark database corruption handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=mock_bookmark_query_handler,
            bookmark_command_handler=Mock(),
        )

        # Simulate database corruption error
        mock_bookmark_query_handler.handle.side_effect = RepositoryError(
            "Database file is corrupt", "DATABASE_CORRUPTION"
        )

        # Act
        result = await ui.load_bookmarks_with_error_handling(user_id=100)

        # Assert
        assert result is False
        assert ui.error_handler.error_count == 1
        assert ui.error_handler.last_error_type == "EXCEPTION"
        assert "Database file is corrupt" in ui.error_handler.error_messages[0]

    @pytest.mark.asyncio
    async def test_bookmark_invalid_question_id_handling(
        self, mock_bookmark_command_handler
    ):
        """Test bookmark invalid question ID handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=Mock(),
            bookmark_command_handler=mock_bookmark_command_handler,
        )

        # Test with invalid question IDs
        invalid_question_ids = [0, -1, 999999, None]

        for question_id in invalid_question_ids:
            # Mock validation error
            mock_bookmark_command_handler.handle.return_value = (
                AddBookmarkCommandResult.error_result(
                    f"Invalid question ID: {question_id}"
                )
            )

            # Act
            result = await ui.add_bookmark_with_error_handling(
                user_id=100, question_id=question_id
            )

            # Assert
            assert result is False

        # Should have handled all invalid IDs
        assert ui.error_handler.error_count == len(invalid_question_ids)

    @pytest.mark.asyncio
    async def test_bookmark_rate_limiting_handling(self, mock_bookmark_command_handler):
        """Test bookmark rate limiting handling."""
        # Arrange
        ui = MockBookmarkUIWithErrorHandling(
            bookmark_query_handler=Mock(),
            bookmark_command_handler=mock_bookmark_command_handler,
        )

        # Simulate rate limiting after 5 requests
        call_count = 0

        async def mock_handle(_command):
            nonlocal call_count
            call_count += 1
            if call_count > 5:
                return AddBookmarkCommandResult.error_result("Rate limit exceeded")
            return AddBookmarkCommandResult.success_result(bookmark_id=call_count)

        mock_bookmark_command_handler.handle.side_effect = mock_handle

        # Act - make 10 requests
        import asyncio

        tasks = [
            ui.add_bookmark_with_error_handling(user_id=100, question_id=40 + i)
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # Assert
        successful_requests = sum(results)
        failed_requests = len(results) - successful_requests

        assert successful_requests == 5
        assert failed_requests == 5
        assert ui.error_handler.error_count == 5
        assert all(
            "Rate limit exceeded" in msg for msg in ui.error_handler.error_messages
        )
