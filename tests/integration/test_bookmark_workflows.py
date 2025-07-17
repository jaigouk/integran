"""Integration tests for bookmark workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.commands.bookmark_commands import (
    AddBookmarkCommand,
    AddBookmarkCommandHandler,
    RemoveBookmarkCommand,
    RemoveBookmarkCommandHandler,
)
from src.application.queries.bookmark_queries import (
    GetBookmarksQuery,
    GetBookmarksQueryHandler,
    GetBookmarkStatsQuery,
    GetBookmarkStatsQueryHandler,
    GetBookmarkStatusQuery,
    GetBookmarkStatusQueryHandler,
)
from src.domain.shared.events import BookmarkAddedEvent, BookmarkRemovedEvent
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection
from src.infrastructure.messaging.enhanced_event_bus import EventBusInterface
from src.infrastructure.repositories.bookmark_repository import BookmarkRepositoryImpl


class TestBookmarkWorkflows:
    """Test complete bookmark workflows."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock(spec=EventBusInterface)

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepositoryImpl)

    @pytest.fixture
    def add_command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create add command handler."""
        return AddBookmarkCommandHandler(mock_bookmark_repository, mock_event_bus)

    @pytest.fixture
    def remove_command_handler(self, mock_bookmark_repository, mock_event_bus):
        """Create remove command handler."""
        return RemoveBookmarkCommandHandler(mock_bookmark_repository, mock_event_bus)

    @pytest.fixture
    def get_bookmarks_query_handler(self, mock_bookmark_repository):
        """Create get bookmarks query handler."""
        return GetBookmarksQueryHandler(mock_bookmark_repository)

    @pytest.fixture
    def get_status_query_handler(self, mock_bookmark_repository):
        """Create get status query handler."""
        return GetBookmarkStatusQueryHandler(mock_bookmark_repository)

    @pytest.fixture
    def get_stats_query_handler(self, mock_bookmark_repository):
        """Create get stats query handler."""
        return GetBookmarkStatsQueryHandler(mock_bookmark_repository)

    @pytest.mark.asyncio
    async def test_complete_bookmark_lifecycle(
        self,
        add_command_handler,
        remove_command_handler,
        get_bookmarks_query_handler,
        get_status_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test complete bookmark lifecycle: add, check, list, remove."""
        user_id = 100
        question_id = 42
        notes = "Important question about German history"

        # Step 1: Add bookmark
        created_bookmark = Bookmark(
            id=1,
            user_id=user_id,
            question_id=question_id,
            notes=notes,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = created_bookmark

        add_command = AddBookmarkCommand(
            user_id=user_id, question_id=question_id, notes=notes
        )
        add_result = await add_command_handler.handle(add_command)

        # Assert bookmark was added
        assert add_result.success is True
        assert add_result.bookmark_id == 1

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, BookmarkAddedEvent)
        assert published_event.user_id == user_id
        assert published_event.question_id == question_id

        # Step 2: Check bookmark status
        mock_bookmark_repository.get_bookmark_by_question.return_value = (
            created_bookmark
        )

        status_query = GetBookmarkStatusQuery(user_id=user_id, question_id=question_id)
        status_result = await get_status_query_handler.handle(status_query)

        # Assert bookmark status is correct
        assert status_result.success is True
        assert status_result.is_bookmarked is True
        assert status_result.bookmark == created_bookmark

        # Step 3: List bookmarks
        bookmark_collection = BookmarkCollection(
            user_id=user_id, bookmarks=[created_bookmark], total_count=1
        )
        mock_bookmark_repository.get_bookmarks.return_value = bookmark_collection

        list_query = GetBookmarksQuery(user_id=user_id)
        list_result = await get_bookmarks_query_handler.handle(list_query)

        # Assert bookmark appears in list
        assert list_result.success is True
        assert len(list_result.bookmarks.bookmarks) == 1
        assert list_result.bookmarks.bookmarks[0] == created_bookmark

        # Step 4: Remove bookmark
        mock_bookmark_repository.remove_bookmark.return_value = True

        remove_command = RemoveBookmarkCommand(user_id=user_id, question_id=question_id)
        remove_result = await remove_command_handler.handle(remove_command)

        # Assert bookmark was removed
        assert remove_result.success is True

        # Verify remove event was published
        assert mock_event_bus.publish.call_count == 2  # Add + Remove
        remove_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(remove_event, BookmarkRemovedEvent)
        assert remove_event.user_id == user_id
        assert remove_event.question_id == question_id

        # Step 5: Verify bookmark is gone
        mock_bookmark_repository.get_bookmark_by_question.return_value = None

        final_status_query = GetBookmarkStatusQuery(
            user_id=user_id, question_id=question_id
        )
        final_status_result = await get_status_query_handler.handle(final_status_query)

        # Assert bookmark is no longer bookmarked
        assert final_status_result.success is True
        assert final_status_result.is_bookmarked is False
        assert final_status_result.bookmark is None

    @pytest.mark.asyncio
    async def test_bookmark_practice_workflow(
        self,
        add_command_handler,
        get_bookmarks_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test bookmark practice workflow."""
        user_id = 100

        # Create multiple bookmarks
        bookmarks = [
            Bookmark(
                id=i,
                user_id=user_id,
                question_id=40 + i,
                notes=f"Question {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 6)  # 5 bookmarks
        ]

        # Step 1: Add multiple bookmarks
        for i, bookmark in enumerate(bookmarks):
            mock_bookmark_repository.add_bookmark.return_value = bookmark

            add_command = AddBookmarkCommand(
                user_id=user_id, question_id=40 + i + 1, notes=f"Question {i + 1}"
            )
            add_result = await add_command_handler.handle(add_command)
            assert add_result.success is True

        # Step 2: Get bookmarks for practice
        bookmark_collection = BookmarkCollection(
            user_id=user_id, bookmarks=bookmarks, total_count=5
        )
        mock_bookmark_repository.get_bookmarks.return_value = bookmark_collection

        practice_query = GetBookmarksQuery(
            user_id=user_id, limit=None
        )  # Get all for practice
        practice_result = await get_bookmarks_query_handler.handle(practice_query)

        # Assert we got all bookmarks for practice
        assert practice_result.success is True
        assert len(practice_result.bookmarks.bookmarks) == 5
        assert practice_result.bookmarks.total_count == 5

        # Step 3: Verify question IDs are available for practice session
        question_ids = practice_result.bookmarks.question_ids
        assert len(question_ids) == 5
        assert set(question_ids) == {41, 42, 43, 44, 45}

        # Step 4: Simulate practice session completion
        # (In real scenario, questions would be presented and answered)
        # For now, just verify we can access all bookmark data
        for bookmark in practice_result.bookmarks.bookmarks:
            assert bookmark.user_id == user_id
            assert bookmark.question_id in question_ids
            assert bookmark.notes is not None

    @pytest.mark.asyncio
    async def test_bookmark_statistics_workflow(
        self,
        add_command_handler,
        get_stats_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test bookmark statistics workflow."""
        user_id = 100

        # Create bookmarks with different ages
        now = datetime.now(UTC)
        bookmarks = [
            Bookmark(
                id=1, user_id=user_id, question_id=41, notes="Recent", created_at=now
            ),
            Bookmark(
                id=2, user_id=user_id, question_id=42, notes="Week old", created_at=now
            ),
            Bookmark(id=3, user_id=user_id, question_id=43, notes=None, created_at=now),
            Bookmark(
                id=4, user_id=user_id, question_id=44, notes="Old", created_at=now
            ),
        ]

        # Step 1: Add bookmarks
        for bookmark in bookmarks:
            mock_bookmark_repository.add_bookmark.return_value = bookmark

            add_command = AddBookmarkCommand(
                user_id=user_id, question_id=bookmark.question_id, notes=bookmark.notes
            )
            add_result = await add_command_handler.handle(add_command)
            assert add_result.success is True

        # Step 2: Get bookmark statistics
        mock_bookmark_repository.get_bookmark_count.return_value = 4

        bookmark_collection = BookmarkCollection(
            user_id=user_id, bookmarks=bookmarks, total_count=4
        )
        mock_bookmark_repository.get_bookmarks.return_value = bookmark_collection

        stats_query = GetBookmarkStatsQuery(user_id=user_id)
        stats_result = await get_stats_query_handler.handle(stats_query)

        # Assert statistics are calculated correctly
        assert stats_result.success is True
        assert stats_result.stats["total_count"] == 4
        assert stats_result.stats["with_notes_count"] == 3  # 3 bookmarks have notes
        assert "bookmark_creation_trend" in stats_result.stats

    @pytest.mark.asyncio
    async def test_bookmark_error_scenarios(
        self,
        add_command_handler,
        remove_command_handler,
        get_bookmarks_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test error scenarios in bookmark workflows."""
        user_id = 100
        question_id = 42

        # Test 1: Add duplicate bookmark
        from src.domain.shared.repositories import RepositoryError

        # First add succeeds
        bookmark = Bookmark(
            id=1,
            user_id=user_id,
            question_id=question_id,
            notes="First bookmark",
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        add_command = AddBookmarkCommand(user_id=user_id, question_id=question_id)
        add_result = await add_command_handler.handle(add_command)
        assert add_result.success is True

        # Second add fails (duplicate)
        mock_bookmark_repository.add_bookmark.side_effect = RepositoryError(
            "Bookmark already exists", "DUPLICATE_BOOKMARK"
        )

        duplicate_add_command = AddBookmarkCommand(
            user_id=user_id, question_id=question_id
        )
        duplicate_add_result = await add_command_handler.handle(duplicate_add_command)
        assert duplicate_add_result.success is False
        assert "already exists" in duplicate_add_result.error_message

        # Test 2: Remove non-existent bookmark
        mock_bookmark_repository.get_bookmark_by_question.return_value = None
        mock_bookmark_repository.remove_bookmark.return_value = False

        remove_command = RemoveBookmarkCommand(user_id=user_id, question_id=999)
        remove_result = await remove_command_handler.handle(remove_command)
        assert remove_result.success is False
        assert "not found" in remove_result.error_message

        # Test 3: Database error during query
        mock_bookmark_repository.get_bookmarks.side_effect = RepositoryError(
            "Database connection failed", "DATABASE_ERROR"
        )

        list_query = GetBookmarksQuery(user_id=user_id)
        list_result = await get_bookmarks_query_handler.handle(list_query)
        assert list_result.success is False
        assert "Database connection failed" in list_result.error_message

    @pytest.mark.asyncio
    async def test_bookmark_pagination_workflow(
        self,
        get_bookmarks_query_handler,
        mock_bookmark_repository,
    ):
        """Test bookmark pagination workflow."""
        user_id = 100

        # Create large number of bookmarks
        all_bookmarks = [
            Bookmark(
                id=i,
                user_id=user_id,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 51)  # 50 bookmarks
        ]

        # Test pagination
        page_size = 10
        total_pages = 5

        for page in range(total_pages):
            offset = page * page_size
            # Repository returns newest first (descending by created_at)
            # So reverse the slice to simulate this behavior
            page_bookmarks = list(reversed(all_bookmarks))[offset : offset + page_size]

            mock_bookmark_repository.get_bookmarks.return_value = BookmarkCollection(
                user_id=user_id, bookmarks=page_bookmarks, total_count=50
            )

            query = GetBookmarksQuery(user_id=user_id, limit=page_size, offset=offset)
            result = await get_bookmarks_query_handler.handle(query)

            # Assert pagination works correctly
            assert result.success is True
            assert len(result.bookmarks.bookmarks) == page_size
            assert result.bookmarks.total_count == 50

            # Verify correct bookmarks for this page (newest first order)
            # For page 0: [50, 49, 48, ...], page 1: [40, 39, 38, ...], etc.
            expected_ids = list(range(50 - offset, 50 - offset - page_size, -1))
            actual_ids = [b.question_id for b in result.bookmarks.bookmarks]
            assert actual_ids == expected_ids

    @pytest.mark.asyncio
    async def test_bookmark_concurrency_workflow(
        self,
        add_command_handler,
        remove_command_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test concurrent bookmark operations."""
        user_id = 100

        # Simulate concurrent bookmark additions
        import asyncio

        async def add_bookmark_task(question_id: int):
            """Task to add a bookmark."""
            bookmark = Bookmark(
                id=question_id,
                user_id=user_id,
                question_id=question_id,
                notes=f"Bookmark {question_id}",
                created_at=datetime.now(UTC),
            )
            mock_bookmark_repository.add_bookmark.return_value = bookmark

            command = AddBookmarkCommand(
                user_id=user_id,
                question_id=question_id,
                notes=f"Bookmark {question_id}",
            )
            return await add_command_handler.handle(command)

        # Run 10 concurrent bookmark additions
        tasks = [add_bookmark_task(i) for i in range(1, 11)]
        results = await asyncio.gather(*tasks)

        # Assert all operations succeeded
        assert len(results) == 10
        assert all(result.success for result in results)

        # Verify all events were published
        assert mock_event_bus.publish.call_count == 10

    @pytest.mark.asyncio
    async def test_bookmark_data_consistency_workflow(
        self,
        add_command_handler,
        get_bookmarks_query_handler,
        get_status_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test data consistency across operations."""
        user_id = 100
        question_id = 42
        notes = "Test bookmark with special chars: äöü ß 🔖"

        # Add bookmark with special characters
        bookmark = Bookmark(
            id=1,
            user_id=user_id,
            question_id=question_id,
            notes=notes,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = bookmark

        add_command = AddBookmarkCommand(
            user_id=user_id, question_id=question_id, notes=notes
        )
        add_result = await add_command_handler.handle(add_command)
        assert add_result.success is True

        # Verify data consistency in status query
        mock_bookmark_repository.get_bookmark_by_question.return_value = bookmark

        status_query = GetBookmarkStatusQuery(user_id=user_id, question_id=question_id)
        status_result = await get_status_query_handler.handle(status_query)

        assert status_result.success is True
        assert status_result.bookmark.notes == notes
        assert (
            status_result.bookmark.notes == "Test bookmark with special chars: äöü ß 🔖"
        )

        # Verify data consistency in list query
        collection = BookmarkCollection(
            user_id=user_id, bookmarks=[bookmark], total_count=1
        )
        mock_bookmark_repository.get_bookmarks.return_value = collection

        list_query = GetBookmarksQuery(user_id=user_id)
        list_result = await get_bookmarks_query_handler.handle(list_query)

        assert list_result.success is True
        assert len(list_result.bookmarks.bookmarks) == 1
        assert list_result.bookmarks.bookmarks[0].notes == notes

    @pytest.mark.asyncio
    async def test_bookmark_edge_cases_workflow(
        self,
        add_command_handler,
        get_bookmarks_query_handler,
        mock_bookmark_repository,
        mock_event_bus,
    ):
        """Test edge cases in bookmark workflows."""
        user_id = 100

        # Test 1: Empty bookmark list
        empty_collection = BookmarkCollection(
            user_id=user_id, bookmarks=[], total_count=0
        )
        mock_bookmark_repository.get_bookmarks.return_value = empty_collection

        empty_query = GetBookmarksQuery(user_id=user_id)
        empty_result = await get_bookmarks_query_handler.handle(empty_query)

        assert empty_result.success is True
        assert empty_result.bookmarks.is_empty is True
        assert empty_result.bookmarks.total_count == 0

        # Test 2: Bookmark with very long notes
        long_notes = "x" * 10000  # 10KB of notes
        long_bookmark = Bookmark(
            id=1,
            user_id=user_id,
            question_id=42,
            notes=long_notes,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = long_bookmark

        long_notes_command = AddBookmarkCommand(
            user_id=user_id, question_id=42, notes=long_notes
        )
        long_notes_result = await add_command_handler.handle(long_notes_command)

        assert long_notes_result.success is True
        assert long_notes_result.bookmark_id == 1

        # Test 3: Bookmark with None notes
        none_notes_bookmark = Bookmark(
            id=2,
            user_id=user_id,
            question_id=43,
            notes=None,
            created_at=datetime.now(UTC),
        )
        mock_bookmark_repository.add_bookmark.return_value = none_notes_bookmark

        none_notes_command = AddBookmarkCommand(
            user_id=user_id, question_id=43, notes=None
        )
        none_notes_result = await add_command_handler.handle(none_notes_command)

        assert none_notes_result.success is True
        assert none_notes_result.bookmark_id == 2

        # Verify event was published with None notes
        published_event = mock_event_bus.publish.call_args[0][0]
        assert published_event.notes is None
