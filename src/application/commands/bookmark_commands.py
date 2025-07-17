"""Bookmark command handlers following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.shared.events import BookmarkAddedEvent, BookmarkRemovedEvent
from src.domain.shared.repositories import RepositoryError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.domain.shared.repositories import BookmarkRepository
    from src.domain.shared.services import EventBusInterface


@dataclass
class AddBookmarkCommand:
    """Command to add a bookmark."""

    user_id: int
    question_id: int
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate command data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class AddBookmarkCommandResult:
    """Result of adding a bookmark."""

    success: bool
    bookmark_id: int | None = None
    error_message: str | None = None

    @classmethod
    def success_result(cls, bookmark_id: int) -> AddBookmarkCommandResult:
        """Create successful result."""
        return cls(success=True, bookmark_id=bookmark_id)

    @classmethod
    def error_result(cls, message: str) -> AddBookmarkCommandResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class AddBookmarkCommandHandler:
    """Handler for add bookmark command."""

    def __init__(
        self, bookmark_repository: BookmarkRepository, event_bus: EventBusInterface
    ):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository
        self.event_bus = event_bus

    async def handle(self, command: AddBookmarkCommand) -> AddBookmarkCommandResult:
        """Handle add bookmark command."""
        try:
            # Add bookmark via repository
            bookmark = await self.bookmark_repository.add_bookmark(
                user_id=command.user_id,
                question_id=command.question_id,
                notes=command.notes,
            )

            # Publish domain event
            event = BookmarkAddedEvent(
                user_id=command.user_id,
                question_id=command.question_id,
                bookmark_id=bookmark.id,
                notes=command.notes,
            )

            try:
                await self.event_bus.publish(event)
            except Exception as e:
                # Event publishing failure shouldn't fail the command
                logger.debug(f"Failed to publish bookmark added event: {e}")

            return AddBookmarkCommandResult.success_result(bookmark.id)

        except RepositoryError as e:
            return AddBookmarkCommandResult.error_result(str(e))
        except Exception as e:
            return AddBookmarkCommandResult.error_result(f"Unexpected error: {e}")


@dataclass
class RemoveBookmarkCommand:
    """Command to remove a bookmark."""

    user_id: int
    question_id: int

    def __post_init__(self) -> None:
        """Validate command data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class RemoveBookmarkCommandResult:
    """Result of removing a bookmark."""

    success: bool
    error_message: str | None = None

    @classmethod
    def success_result(cls) -> RemoveBookmarkCommandResult:
        """Create successful result."""
        return cls(success=True)

    @classmethod
    def error_result(cls, message: str) -> RemoveBookmarkCommandResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class RemoveBookmarkCommandHandler:
    """Handler for remove bookmark command."""

    def __init__(
        self, bookmark_repository: BookmarkRepository, event_bus: EventBusInterface
    ):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository
        self.event_bus = event_bus

    async def handle(
        self, command: RemoveBookmarkCommand
    ) -> RemoveBookmarkCommandResult:
        """Handle remove bookmark command."""
        try:
            # Get existing bookmark for event data
            existing_bookmark = await self.bookmark_repository.get_bookmark_by_question(
                command.user_id, command.question_id
            )

            # Remove bookmark via repository
            removed = await self.bookmark_repository.remove_bookmark(
                user_id=command.user_id, question_id=command.question_id
            )

            if not removed:
                return RemoveBookmarkCommandResult.error_result(
                    f"Bookmark not found for user {command.user_id} and question {command.question_id}"
                )

            # Publish domain event
            event = BookmarkRemovedEvent(
                user_id=command.user_id,
                question_id=command.question_id,
                bookmark_id=existing_bookmark.id if existing_bookmark else None,
            )

            try:
                await self.event_bus.publish(event)
            except Exception as e:
                # Event publishing failure shouldn't fail the command
                logger.debug(f"Failed to publish bookmark removed event: {e}")

            return RemoveBookmarkCommandResult.success_result()

        except RepositoryError as e:
            return RemoveBookmarkCommandResult.error_result(str(e))
        except Exception as e:
            return RemoveBookmarkCommandResult.error_result(f"Unexpected error: {e}")


@dataclass
class UpdateBookmarkNotesCommand:
    """Command to update bookmark notes."""

    user_id: int
    question_id: int
    notes: str | None

    def __post_init__(self) -> None:
        """Validate command data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class UpdateBookmarkNotesCommandResult:
    """Result of updating bookmark notes."""

    success: bool
    error_message: str | None = None

    @classmethod
    def success_result(cls) -> UpdateBookmarkNotesCommandResult:
        """Create successful result."""
        return cls(success=True)

    @classmethod
    def error_result(cls, message: str) -> UpdateBookmarkNotesCommandResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class UpdateBookmarkNotesCommandHandler:
    """Handler for update bookmark notes command."""

    def __init__(
        self, bookmark_repository: BookmarkRepository, event_bus: EventBusInterface
    ):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository
        self.event_bus = event_bus

    async def handle(
        self, command: UpdateBookmarkNotesCommand
    ) -> UpdateBookmarkNotesCommandResult:
        """Handle update bookmark notes command."""
        try:
            # Check if bookmark exists
            existing_bookmark = await self.bookmark_repository.get_bookmark_by_question(
                command.user_id, command.question_id
            )

            if existing_bookmark is None:
                return UpdateBookmarkNotesCommandResult.error_result(
                    f"Bookmark not found for user {command.user_id} and question {command.question_id}"
                )

            # Update bookmark notes via repository
            await self.bookmark_repository.update_bookmark_notes(
                user_id=command.user_id,
                question_id=command.question_id,
                notes=command.notes,
            )

            return UpdateBookmarkNotesCommandResult.success_result()

        except RepositoryError as e:
            return UpdateBookmarkNotesCommandResult.error_result(str(e))
        except Exception as e:
            return UpdateBookmarkNotesCommandResult.error_result(
                f"Unexpected error: {e}"
            )
