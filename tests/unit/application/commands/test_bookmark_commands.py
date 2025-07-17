"""Tests for bookmark command handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.commands.bookmark_commands import (
    AddBookmarkCommand,
    AddBookmarkCommandHandler,
    AddBookmarkCommandResult,
    RemoveBookmarkCommand,
    RemoveBookmarkCommandHandler,
    RemoveBookmarkCommandResult,
    UpdateBookmarkNotesCommand,
    UpdateBookmarkNotesCommandHandler,
    UpdateBookmarkNotesCommandResult,
)
from src.domain.shared.events import BookmarkAddedEvent, BookmarkRemovedEvent
from src.domain.shared.repositories import BookmarkRepository, RepositoryError
from src.domain.user.models.bookmark_models import (
    Bookmark,
)
from src.infrastructure.messaging.enhanced_event_bus import EventBusInterface


class TestAddBookmarkCommand:
    """Test AddBookmarkCommand and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock(spec=EventBusInterface)

    @pytest.fixture
    def command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create command handler."""
        return AddBookmarkCommandHandler(mock_bookmark_repository, mock_event_bus)

    @pytest.fixture
    def sample_bookmark(self):
        """Create sample bookmark."""
        return Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test notes",
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_add_bookmark_command_success(
        self, command_handler, mock_bookmark_repository, mock_event_bus, sample_bookmark
    ):
        """Test successful bookmark addition."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test notes")

        mock_bookmark_repository.add_bookmark.return_value = sample_bookmark

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert isinstance(result, AddBookmarkCommandResult)
        assert result.success is True
        assert result.bookmark_id == 1
        assert result.error_message is None

        # Verify repository call
        mock_bookmark_repository.add_bookmark.assert_called_once_with(
            user_id=100, question_id=42, notes="Test notes"
        )

        # Verify event publication
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, BookmarkAddedEvent)
        assert published_event.user_id == 100
        assert published_event.question_id == 42
        assert published_event.bookmark_id == 1
        assert published_event.notes == "Test notes"

    @pytest.mark.asyncio
    async def test_add_bookmark_command_without_notes(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test bookmark addition without notes."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42)

        bookmark = Bookmark(
            id=1, user_id=100, question_id=42, notes=None, created_at=datetime.now(UTC)
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is True
        assert result.bookmark_id == 1

        # Verify repository call
        mock_bookmark_repository.add_bookmark.assert_called_once_with(
            user_id=100, question_id=42, notes=None
        )

        # Verify event with no notes
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.notes is None

    @pytest.mark.asyncio
    async def test_add_bookmark_command_duplicate_error(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test bookmark addition with duplicate error."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test notes")

        mock_bookmark_repository.add_bookmark.side_effect = RepositoryError(
            "Bookmark already exists", "DUPLICATE_BOOKMARK"
        )

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is False
        assert result.bookmark_id is None
        assert "already exists" in result.error_message

        # Verify no event published
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_bookmark_command_database_error(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test bookmark addition with database error."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test notes")

        mock_bookmark_repository.add_bookmark.side_effect = RepositoryError(
            "Database connection failed", "DATABASE_ERROR"
        )

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is False
        assert result.bookmark_id is None
        assert "Database connection failed" in result.error_message

        # Verify no event published
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_bookmark_command_validation(self, command_handler):
        """Test command validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            AddBookmarkCommand(user_id=0, question_id=42)

        # Test invalid question_id
        with pytest.raises(ValueError, match="Question ID must be positive"):
            AddBookmarkCommand(user_id=100, question_id=0)


class TestRemoveBookmarkCommand:
    """Test RemoveBookmarkCommand and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock(spec=EventBusInterface)

    @pytest.fixture
    def command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create command handler."""
        return RemoveBookmarkCommandHandler(mock_bookmark_repository, mock_event_bus)

    @pytest.mark.asyncio
    async def test_remove_bookmark_command_success(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test successful bookmark removal."""
        # Arrange
        command = RemoveBookmarkCommand(user_id=100, question_id=42)

        # Mock existing bookmark
        existing_bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test notes",
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.get_bookmark_by_question.return_value = (
            existing_bookmark
        )
        mock_bookmark_repository.remove_bookmark.return_value = True

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert isinstance(result, RemoveBookmarkCommandResult)
        assert result.success is True
        assert result.error_message is None

        # Verify repository calls
        mock_bookmark_repository.get_bookmark_by_question.assert_called_once_with(
            100, 42
        )
        mock_bookmark_repository.remove_bookmark.assert_called_once_with(
            user_id=100, question_id=42
        )

        # Verify event publication
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, BookmarkRemovedEvent)
        assert published_event.user_id == 100
        assert published_event.question_id == 42
        assert published_event.bookmark_id == 1

    @pytest.mark.asyncio
    async def test_remove_bookmark_command_not_found(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test removing non-existent bookmark."""
        # Arrange
        command = RemoveBookmarkCommand(user_id=100, question_id=42)

        mock_bookmark_repository.get_bookmark_by_question.return_value = None
        mock_bookmark_repository.remove_bookmark.return_value = False

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is False
        assert "not found" in result.error_message

        # Verify no event published
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_bookmark_command_database_error(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test bookmark removal with database error."""
        # Arrange
        command = RemoveBookmarkCommand(user_id=100, question_id=42)

        mock_bookmark_repository.get_bookmark_by_question.side_effect = RepositoryError(
            "Database error", "DATABASE_ERROR"
        )

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

        # Verify no event published
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_bookmark_command_validation(self, command_handler):
        """Test command validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            RemoveBookmarkCommand(user_id=0, question_id=42)

        # Test invalid question_id
        with pytest.raises(ValueError, match="Question ID must be positive"):
            RemoveBookmarkCommand(user_id=100, question_id=0)


class TestUpdateBookmarkNotesCommand:
    """Test UpdateBookmarkNotesCommand and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock(spec=EventBusInterface)

    @pytest.fixture
    def command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create command handler."""
        return UpdateBookmarkNotesCommandHandler(
            mock_bookmark_repository, mock_event_bus
        )

    @pytest.mark.asyncio
    async def test_update_bookmark_notes_command_success(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test successful bookmark notes update."""
        # Arrange
        command = UpdateBookmarkNotesCommand(
            user_id=100, question_id=42, notes="Updated notes"
        )

        # Mock existing bookmark
        existing_bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Old notes",
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.get_bookmark_by_question.return_value = (
            existing_bookmark
        )

        # Mock update (assume repository has update method)
        updated_bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Updated notes",
            created_at=existing_bookmark.created_at,
        )
        mock_bookmark_repository.update_bookmark_notes = AsyncMock(
            return_value=updated_bookmark
        )

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert isinstance(result, UpdateBookmarkNotesCommandResult)
        assert result.success is True
        assert result.error_message is None

        # Verify repository calls
        mock_bookmark_repository.get_bookmark_by_question.assert_called_once_with(
            100, 42
        )
        mock_bookmark_repository.update_bookmark_notes.assert_called_once_with(
            user_id=100, question_id=42, notes="Updated notes"
        )

    @pytest.mark.asyncio
    async def test_update_bookmark_notes_command_not_found(
        self, command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test updating notes for non-existent bookmark."""
        # Arrange
        command = UpdateBookmarkNotesCommand(
            user_id=100, question_id=42, notes="Updated notes"
        )

        mock_bookmark_repository.get_bookmark_by_question.return_value = None

        # Act
        result = await command_handler.handle(command)

        # Assert
        assert result.success is False
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_update_bookmark_notes_command_validation(self, command_handler):
        """Test command validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            UpdateBookmarkNotesCommand(user_id=0, question_id=42, notes="Notes")

        # Test invalid question_id
        with pytest.raises(ValueError, match="Question ID must be positive"):
            UpdateBookmarkNotesCommand(user_id=100, question_id=0, notes="Notes")


class TestCommandEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock(spec=EventBusInterface)

    @pytest.fixture
    def add_command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create add command handler."""
        return AddBookmarkCommandHandler(mock_bookmark_repository, mock_event_bus)

    @pytest.mark.asyncio
    async def test_command_with_very_long_notes(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test command with very long notes."""
        # Arrange
        long_notes = "x" * 10000  # 10KB of notes
        command = AddBookmarkCommand(user_id=100, question_id=42, notes=long_notes)

        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes=long_notes,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        # Act
        result = await add_command_handler.handle(command)

        # Assert
        assert result.success is True
        assert result.bookmark_id == 1

        # Verify the long notes were passed through
        mock_bookmark_repository.add_bookmark.assert_called_once_with(
            user_id=100, question_id=42, notes=long_notes
        )

    @pytest.mark.asyncio
    async def test_command_with_special_characters_in_notes(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test command with special characters in notes."""
        # Arrange
        special_notes = "Test with émojis 🔖 and UTF-8 characters: äöü ß 日本語"
        command = AddBookmarkCommand(user_id=100, question_id=42, notes=special_notes)

        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes=special_notes,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        # Act
        result = await add_command_handler.handle(command)

        # Assert
        assert result.success is True

        # Verify special characters were preserved
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.notes == special_notes

    @pytest.mark.asyncio
    async def test_concurrent_bookmark_operations(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test concurrent bookmark operations."""
        # Arrange
        commands = [
            AddBookmarkCommand(user_id=100, question_id=42 + i, notes=f"Notes {i}")
            for i in range(5)
        ]

        # Mock successful operations
        mock_bookmark_repository.add_bookmark.side_effect = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=42 + i,
                notes=f"Notes {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 6)
        ]

        # Act
        import asyncio

        results = await asyncio.gather(
            *[add_command_handler.handle(command) for command in commands]
        )

        # Assert
        assert len(results) == 5
        assert all(result.success for result in results)
        assert [result.bookmark_id for result in results] == [1, 2, 3, 4, 5]

        # Verify all events were published
        assert mock_event_bus.publish.call_count == 5

    @pytest.mark.asyncio
    async def test_command_handler_exception_handling(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test command handler exception handling."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test")

        # Mock unexpected exception
        mock_bookmark_repository.add_bookmark.side_effect = Exception(
            "Unexpected error"
        )

        # Act
        result = await add_command_handler.handle(command)

        # Assert
        assert result.success is False
        assert "Unexpected error" in result.error_message

        # Verify no event published
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_publishing_failure(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test handling of event publishing failures."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test")

        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test",
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        # Mock event publishing failure
        mock_event_bus.publish.side_effect = Exception("Event bus error")

        # Act
        result = await add_command_handler.handle(command)

        # Assert
        # Command should still succeed even if event publishing fails
        assert result.success is True
        assert result.bookmark_id == 1

        # Verify repository was called (bookmark was still created)
        mock_bookmark_repository.add_bookmark.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_idempotency(
        self, add_command_handler, mock_bookmark_repository, mock_event_bus
    ):
        """Test command idempotency."""
        # Arrange
        command = AddBookmarkCommand(user_id=100, question_id=42, notes="Test")

        # First call succeeds
        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test",
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        # Act - First call
        result1 = await add_command_handler.handle(command)

        # Arrange - Second call should fail with duplicate
        mock_bookmark_repository.add_bookmark.side_effect = RepositoryError(
            "Bookmark already exists", "DUPLICATE_BOOKMARK"
        )

        # Act - Second call
        result2 = await add_command_handler.handle(command)

        # Assert
        assert result1.success is True
        assert result2.success is False
        assert "already exists" in result2.error_message

        # Verify only one event was published
        assert mock_event_bus.publish.call_count == 1
