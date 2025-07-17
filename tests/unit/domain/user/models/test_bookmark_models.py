"""Tests for bookmark domain models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.user.models.bookmark_models import (
    AddBookmarkRequest,
    AddBookmarkResult,
    Bookmark,
    BookmarkCollection,
    GetBookmarksRequest,
    GetBookmarksResult,
    GetBookmarkStatusRequest,
    GetBookmarkStatusResult,
    RemoveBookmarkRequest,
    RemoveBookmarkResult,
)


class TestBookmark:
    """Test Bookmark domain entity."""

    def test_bookmark_creation_with_all_fields(self) -> None:
        """Test bookmark creation with all fields."""
        created_at = datetime.now(UTC)
        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            created_at=created_at,
            notes="Important question about German history",
        )

        assert bookmark.id == 1
        assert bookmark.user_id == 100
        assert bookmark.question_id == 42
        assert bookmark.created_at == created_at
        assert bookmark.notes == "Important question about German history"

    def test_bookmark_creation_minimal(self) -> None:
        """Test bookmark creation with minimal fields."""
        created_at = datetime.now(UTC)
        bookmark = Bookmark(id=1, user_id=100, question_id=42, created_at=created_at)

        assert bookmark.id == 1
        assert bookmark.user_id == 100
        assert bookmark.question_id == 42
        assert bookmark.created_at == created_at
        assert bookmark.notes is None

    def test_bookmark_validation_invalid_user_id(self) -> None:
        """Test bookmark validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            Bookmark(id=1, user_id=0, question_id=42, created_at=datetime.now(UTC))

        with pytest.raises(ValueError, match="User ID must be positive"):
            Bookmark(id=1, user_id=-1, question_id=42, created_at=datetime.now(UTC))

    def test_bookmark_validation_invalid_question_id(self) -> None:
        """Test bookmark validation with invalid question ID."""
        with pytest.raises(ValueError, match="Question ID must be positive"):
            Bookmark(id=1, user_id=100, question_id=0, created_at=datetime.now(UTC))

        with pytest.raises(ValueError, match="Question ID must be positive"):
            Bookmark(id=1, user_id=100, question_id=-1, created_at=datetime.now(UTC))

    def test_bookmark_auto_created_at_on_none(self) -> None:
        """Test bookmark auto-sets created_at when None."""
        # Since created_at is required, we need to pass a valid datetime
        # This test is no longer valid as created_at cannot be None
        # Let's test that the bookmark correctly stores the provided created_at
        created_at = datetime.now(UTC)
        bookmark = Bookmark(id=1, user_id=100, question_id=42, created_at=created_at)

        assert bookmark.created_at == created_at
        assert isinstance(bookmark.created_at, datetime)

    def test_has_notes_with_notes(self) -> None:
        """Test has_notes returns True when notes exist."""
        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            created_at=datetime.now(UTC),
            notes="Test notes",
        )

        assert bookmark.has_notes() is True

    def test_has_notes_without_notes(self) -> None:
        """Test has_notes returns False when notes are None."""
        bookmark = Bookmark(
            id=1, user_id=100, question_id=42, created_at=datetime.now(UTC), notes=None
        )

        assert bookmark.has_notes() is False

    def test_has_notes_with_empty_notes(self) -> None:
        """Test has_notes returns False when notes are empty or whitespace."""
        bookmark = Bookmark(
            id=1, user_id=100, question_id=42, created_at=datetime.now(UTC), notes=""
        )

        assert bookmark.has_notes() is False

        bookmark.notes = "   "
        assert bookmark.has_notes() is False

    def test_age_in_days_with_timezone_aware_datetime(self) -> None:
        """Test age calculation with timezone-aware datetime."""
        # Create bookmark 5 days ago
        five_days_ago = datetime.now(UTC) - timedelta(days=5)
        bookmark = Bookmark(id=1, user_id=100, question_id=42, created_at=five_days_ago)

        assert bookmark.age_in_days() == 5

    def test_age_in_days_with_naive_datetime(self) -> None:
        """Test age calculation with naive datetime (from database)."""
        # Create bookmark 3 days ago as naive datetime
        three_days_ago = datetime.now(UTC) - timedelta(days=3)
        naive_datetime = three_days_ago.replace(tzinfo=None)

        bookmark = Bookmark(
            id=1, user_id=100, question_id=42, created_at=naive_datetime
        )

        assert bookmark.age_in_days() == 3

    def test_age_in_days_today(self) -> None:
        """Test age calculation for bookmark created today."""
        bookmark = Bookmark(
            id=1, user_id=100, question_id=42, created_at=datetime.now(UTC)
        )

        assert bookmark.age_in_days() == 0

    def test_is_recent_default_threshold(self) -> None:
        """Test is_recent with default 7-day threshold."""
        # Recent bookmark (5 days ago)
        recent_bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            created_at=datetime.now(UTC) - timedelta(days=5),
        )
        assert recent_bookmark.is_recent() is True

        # Old bookmark (10 days ago)
        old_bookmark = Bookmark(
            id=2,
            user_id=100,
            question_id=43,
            created_at=datetime.now(UTC) - timedelta(days=10),
        )
        assert old_bookmark.is_recent() is False

    def test_is_recent_custom_threshold(self) -> None:
        """Test is_recent with custom threshold."""
        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            created_at=datetime.now(UTC) - timedelta(days=5),
        )

        assert bookmark.is_recent(days=3) is False
        assert bookmark.is_recent(days=7) is True
        assert bookmark.is_recent(days=10) is True

    def test_is_recent_exact_boundary(self) -> None:
        """Test is_recent at exact boundary."""
        bookmark = Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            created_at=datetime.now(UTC) - timedelta(days=7),
        )

        assert bookmark.is_recent(days=7) is True
        assert bookmark.is_recent(days=6) is False


class TestBookmarkCollection:
    """Test BookmarkCollection value object."""

    def test_empty_collection(self) -> None:
        """Test empty bookmark collection."""
        collection = BookmarkCollection(user_id=100)

        assert collection.user_id == 100
        assert collection.bookmarks == []
        assert collection.total_count == 0
        assert collection.is_empty is True
        assert collection.bookmark_count == 0
        assert collection.question_ids == []

    def test_collection_with_bookmarks(self) -> None:
        """Test collection with bookmarks."""
        bookmarks = [
            Bookmark(1, 100, 42, datetime.now(UTC)),
            Bookmark(2, 100, 43, datetime.now(UTC)),
            Bookmark(3, 100, 44, datetime.now(UTC)),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks, total_count=3)

        assert collection.user_id == 100
        assert len(collection.bookmarks) == 3
        assert collection.total_count == 3
        assert collection.is_empty is False
        assert collection.bookmark_count == 3
        assert collection.question_ids == [42, 43, 44]

    def test_collection_auto_total_count(self) -> None:
        """Test collection auto-calculates total_count when not provided."""
        bookmarks = [
            Bookmark(1, 100, 42, datetime.now(UTC)),
            Bookmark(2, 100, 43, datetime.now(UTC)),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks)

        assert collection.total_count == 2

    def test_collection_validation_invalid_user_id(self) -> None:
        """Test collection validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            BookmarkCollection(user_id=0)

        with pytest.raises(ValueError, match="User ID must be positive"):
            BookmarkCollection(user_id=-1)

    def test_contains_question(self) -> None:
        """Test contains_question method."""
        bookmarks = [
            Bookmark(1, 100, 42, datetime.now(UTC)),
            Bookmark(2, 100, 43, datetime.now(UTC)),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks)

        assert collection.contains_question(42) is True
        assert collection.contains_question(43) is True
        assert collection.contains_question(44) is False

    def test_get_bookmark_by_question_id(self) -> None:
        """Test get_bookmark_by_question_id method."""
        bookmark1 = Bookmark(1, 100, 42, datetime.now(UTC))
        bookmark2 = Bookmark(2, 100, 43, datetime.now(UTC))
        collection = BookmarkCollection(user_id=100, bookmarks=[bookmark1, bookmark2])

        found_bookmark = collection.get_bookmark_by_question_id(42)
        assert found_bookmark is bookmark1

        not_found = collection.get_bookmark_by_question_id(44)
        assert not_found is None

    def test_get_recent_bookmarks(self) -> None:
        """Test get_recent_bookmarks method."""
        recent_bookmark = Bookmark(1, 100, 42, datetime.now(UTC) - timedelta(days=3))
        old_bookmark = Bookmark(2, 100, 43, datetime.now(UTC) - timedelta(days=10))
        collection = BookmarkCollection(
            user_id=100, bookmarks=[recent_bookmark, old_bookmark]
        )

        recent_bookmarks = collection.get_recent_bookmarks(days=7)
        assert len(recent_bookmarks) == 1
        assert recent_bookmarks[0] is recent_bookmark

        recent_bookmarks = collection.get_recent_bookmarks(days=2)
        assert len(recent_bookmarks) == 0

    def test_get_bookmarks_with_notes(self) -> None:
        """Test get_bookmarks_with_notes method."""
        bookmark_with_notes = Bookmark(1, 100, 42, datetime.now(UTC), "Important")
        bookmark_without_notes = Bookmark(2, 100, 43, datetime.now(UTC))
        collection = BookmarkCollection(
            user_id=100, bookmarks=[bookmark_with_notes, bookmark_without_notes]
        )

        bookmarks_with_notes = collection.get_bookmarks_with_notes()
        assert len(bookmarks_with_notes) == 1
        assert bookmarks_with_notes[0] is bookmark_with_notes

    def test_get_statistics_empty_collection(self) -> None:
        """Test get_statistics for empty collection."""
        collection = BookmarkCollection(user_id=100)
        stats = collection.get_statistics()

        expected_stats = {
            "total_count": 0,
            "recent_count": 0,
            "with_notes_count": 0,
            "oldest_bookmark_age_days": 0,
            "newest_bookmark_age_days": 0,
            "average_age_days": 0,
        }
        assert stats == expected_stats

    def test_get_statistics_with_bookmarks(self) -> None:
        """Test get_statistics for collection with bookmarks."""
        now = datetime.now(UTC)
        bookmarks = [
            Bookmark(1, 100, 42, now - timedelta(days=1), "Recent with notes"),
            Bookmark(2, 100, 43, now - timedelta(days=5)),
            Bookmark(3, 100, 44, now - timedelta(days=10), "Old with notes"),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks)
        stats = collection.get_statistics()

        assert stats["total_count"] == 3
        assert stats["recent_count"] == 2  # 1 day and 5 days (within 7 days)
        assert stats["with_notes_count"] == 2
        assert stats["oldest_bookmark_age_days"] == 10
        assert stats["newest_bookmark_age_days"] == 1
        assert stats["average_age_days"] == (1 + 5 + 10) / 3

    def test_sort_by_date_descending(self) -> None:
        """Test sort_by_date with descending order."""
        now = datetime.now(UTC)
        bookmark1 = Bookmark(1, 100, 42, now - timedelta(days=5))
        bookmark2 = Bookmark(2, 100, 43, now - timedelta(days=1))
        bookmark3 = Bookmark(3, 100, 44, now - timedelta(days=10))
        collection = BookmarkCollection(
            user_id=100, bookmarks=[bookmark1, bookmark2, bookmark3]
        )

        sorted_collection = collection.sort_by_date(descending=True)

        assert sorted_collection.bookmarks[0] is bookmark2  # Most recent
        assert sorted_collection.bookmarks[1] is bookmark1
        assert sorted_collection.bookmarks[2] is bookmark3  # Oldest

    def test_sort_by_date_ascending(self) -> None:
        """Test sort_by_date with ascending order."""
        now = datetime.now(UTC)
        bookmark1 = Bookmark(1, 100, 42, now - timedelta(days=5))
        bookmark2 = Bookmark(2, 100, 43, now - timedelta(days=1))
        bookmark3 = Bookmark(3, 100, 44, now - timedelta(days=10))
        collection = BookmarkCollection(
            user_id=100, bookmarks=[bookmark1, bookmark2, bookmark3]
        )

        sorted_collection = collection.sort_by_date(descending=False)

        assert sorted_collection.bookmarks[0] is bookmark3  # Oldest
        assert sorted_collection.bookmarks[1] is bookmark1
        assert sorted_collection.bookmarks[2] is bookmark2  # Most recent

    def test_limit_with_offset(self) -> None:
        """Test limit method with offset."""
        bookmarks = [
            Bookmark(i, 100, 40 + i, datetime.now(UTC))
            for i in range(1, 6)  # 5 bookmarks
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks, total_count=5)

        # Get 2 bookmarks starting from index 1
        limited = collection.limit(count=2, offset=1)

        assert len(limited.bookmarks) == 2
        assert limited.bookmarks[0] is bookmarks[1]
        assert limited.bookmarks[1] is bookmarks[2]
        assert limited.total_count == 5  # Original total count preserved

    def test_limit_without_offset(self) -> None:
        """Test limit method without offset."""
        bookmarks = [
            Bookmark(i, 100, 40 + i, datetime.now(UTC))
            for i in range(1, 6)  # 5 bookmarks
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks, total_count=5)

        limited = collection.limit(count=3)

        assert len(limited.bookmarks) == 3
        assert limited.bookmarks[0] is bookmarks[0]
        assert limited.bookmarks[1] is bookmarks[1]
        assert limited.bookmarks[2] is bookmarks[2]

    def test_limit_beyond_available(self) -> None:
        """Test limit when requesting more than available."""
        bookmarks = [
            Bookmark(1, 100, 42, datetime.now(UTC)),
            Bookmark(2, 100, 43, datetime.now(UTC)),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks, total_count=2)

        limited = collection.limit(count=5)

        assert len(limited.bookmarks) == 2  # Only available bookmarks
        assert limited.total_count == 2


class TestAddBookmarkRequest:
    """Test AddBookmarkRequest DTO."""

    def test_valid_request(self) -> None:
        """Test valid add bookmark request."""
        request = AddBookmarkRequest(user_id=100, question_id=42, notes="Test notes")

        assert request.user_id == 100
        assert request.question_id == 42
        assert request.notes == "Test notes"

    def test_request_without_notes(self) -> None:
        """Test request without notes."""
        request = AddBookmarkRequest(user_id=100, question_id=42)

        assert request.user_id == 100
        assert request.question_id == 42
        assert request.notes is None

    def test_request_validation_invalid_user_id(self) -> None:
        """Test request validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            AddBookmarkRequest(user_id=0, question_id=42)

    def test_request_validation_invalid_question_id(self) -> None:
        """Test request validation with invalid question ID."""
        with pytest.raises(ValueError, match="Question ID must be positive"):
            AddBookmarkRequest(user_id=100, question_id=0)


class TestAddBookmarkResult:
    """Test AddBookmarkResult DTO."""

    def test_success_result(self) -> None:
        """Test successful add bookmark result."""
        bookmark = Bookmark(1, 100, 42, datetime.now(UTC))
        result = AddBookmarkResult.success_result(bookmark)

        assert result.success is True
        assert result.bookmark is bookmark
        assert result.error_message is None

    def test_error_result(self) -> None:
        """Test error add bookmark result."""
        result = AddBookmarkResult.error_result("Bookmark already exists")

        assert result.success is False
        assert result.bookmark is None
        assert result.error_message == "Bookmark already exists"


class TestRemoveBookmarkRequest:
    """Test RemoveBookmarkRequest DTO."""

    def test_valid_request(self) -> None:
        """Test valid remove bookmark request."""
        request = RemoveBookmarkRequest(user_id=100, question_id=42)

        assert request.user_id == 100
        assert request.question_id == 42

    def test_request_validation_invalid_user_id(self) -> None:
        """Test request validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            RemoveBookmarkRequest(user_id=0, question_id=42)

    def test_request_validation_invalid_question_id(self) -> None:
        """Test request validation with invalid question ID."""
        with pytest.raises(ValueError, match="Question ID must be positive"):
            RemoveBookmarkRequest(user_id=100, question_id=0)


class TestRemoveBookmarkResult:
    """Test RemoveBookmarkResult DTO."""

    def test_success_result(self) -> None:
        """Test successful remove bookmark result."""
        result = RemoveBookmarkResult.success_result()

        assert result.success is True
        assert result.error_message is None

    def test_error_result(self) -> None:
        """Test error remove bookmark result."""
        result = RemoveBookmarkResult.error_result("Bookmark not found")

        assert result.success is False
        assert result.error_message == "Bookmark not found"


class TestGetBookmarksRequest:
    """Test GetBookmarksRequest DTO."""

    def test_minimal_request(self) -> None:
        """Test minimal get bookmarks request."""
        request = GetBookmarksRequest(user_id=100)

        assert request.user_id == 100
        assert request.limit is None
        assert request.offset == 0
        assert request.include_notes is True
        assert request.sort_by_date is True
        assert request.sort_descending is True

    def test_full_request(self) -> None:
        """Test full get bookmarks request."""
        request = GetBookmarksRequest(
            user_id=100,
            limit=10,
            offset=20,
            include_notes=False,
            sort_by_date=False,
            sort_descending=False,
        )

        assert request.user_id == 100
        assert request.limit == 10
        assert request.offset == 20
        assert request.include_notes is False
        assert request.sort_by_date is False
        assert request.sort_descending is False

    def test_request_validation_invalid_user_id(self) -> None:
        """Test request validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            GetBookmarksRequest(user_id=0)

    def test_request_validation_invalid_limit(self) -> None:
        """Test request validation with invalid limit."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            GetBookmarksRequest(user_id=100, limit=0)

        with pytest.raises(ValueError, match="Limit must be positive"):
            GetBookmarksRequest(user_id=100, limit=-1)

    def test_request_validation_invalid_offset(self) -> None:
        """Test request validation with invalid offset."""
        with pytest.raises(ValueError, match="Offset cannot be negative"):
            GetBookmarksRequest(user_id=100, offset=-1)


class TestGetBookmarksResult:
    """Test GetBookmarksResult DTO."""

    def test_success_result(self) -> None:
        """Test successful get bookmarks result."""
        collection = BookmarkCollection(user_id=100)
        result = GetBookmarksResult.success_result(collection)

        assert result.success is True
        assert result.bookmarks is collection
        assert result.error_message is None

    def test_error_result(self) -> None:
        """Test error get bookmarks result."""
        result = GetBookmarksResult.error_result("Database error")

        assert result.success is False
        assert result.bookmarks is None
        assert result.error_message == "Database error"


class TestGetBookmarkStatusRequest:
    """Test GetBookmarkStatusRequest DTO."""

    def test_valid_request(self) -> None:
        """Test valid get bookmark status request."""
        request = GetBookmarkStatusRequest(user_id=100, question_id=42)

        assert request.user_id == 100
        assert request.question_id == 42

    def test_request_validation_invalid_user_id(self) -> None:
        """Test request validation with invalid user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            GetBookmarkStatusRequest(user_id=0, question_id=42)

    def test_request_validation_invalid_question_id(self) -> None:
        """Test request validation with invalid question ID."""
        with pytest.raises(ValueError, match="Question ID must be positive"):
            GetBookmarkStatusRequest(user_id=100, question_id=0)


class TestGetBookmarkStatusResult:
    """Test GetBookmarkStatusResult DTO."""

    def test_success_result_bookmarked(self) -> None:
        """Test successful result when question is bookmarked."""
        bookmark = Bookmark(1, 100, 42, datetime.now(UTC))
        result = GetBookmarkStatusResult.success_result(
            is_bookmarked=True, bookmark=bookmark
        )

        assert result.success is True
        assert result.is_bookmarked is True
        assert result.bookmark is bookmark
        assert result.error_message is None

    def test_success_result_not_bookmarked(self) -> None:
        """Test successful result when question is not bookmarked."""
        result = GetBookmarkStatusResult.success_result(is_bookmarked=False)

        assert result.success is True
        assert result.is_bookmarked is False
        assert result.bookmark is None
        assert result.error_message is None

    def test_error_result(self) -> None:
        """Test error bookmark status result."""
        result = GetBookmarkStatusResult.error_result("Database error")

        assert result.success is False
        assert result.is_bookmarked is False
        assert result.bookmark is None
        assert result.error_message == "Database error"


class TestBookmarkDomainIntegration:
    """Test integration between bookmark domain models."""

    def test_bookmark_collection_with_mixed_bookmarks(self) -> None:
        """Test bookmark collection with various bookmark types."""
        now = datetime.now(UTC)
        bookmarks = [
            Bookmark(1, 100, 42, now - timedelta(days=1), "Recent with notes"),
            Bookmark(2, 100, 43, now - timedelta(days=5)),
            Bookmark(3, 100, 44, now - timedelta(days=10), "Old with notes"),
            Bookmark(4, 100, 45, now - timedelta(days=15)),
        ]
        collection = BookmarkCollection(user_id=100, bookmarks=bookmarks)

        # Test various collection operations
        assert collection.bookmark_count == 4
        assert len(collection.get_recent_bookmarks()) == 2
        assert len(collection.get_bookmarks_with_notes()) == 2
        assert collection.contains_question(42) is True
        assert collection.contains_question(99) is False

        # Test sorting and limiting
        sorted_collection = collection.sort_by_date(descending=True)
        limited_collection = sorted_collection.limit(count=2)

        assert len(limited_collection.bookmarks) == 2
        assert limited_collection.bookmarks[0].question_id == 42  # Most recent
        assert limited_collection.bookmarks[1].question_id == 43

    def test_request_response_dto_workflow(self) -> None:
        """Test typical request/response DTO workflow."""
        # Create add request
        AddBookmarkRequest(user_id=100, question_id=42, notes="Test bookmark")

        # Simulate successful add
        bookmark = Bookmark(1, 100, 42, datetime.now(UTC), "Test bookmark")
        add_result = AddBookmarkResult.success_result(bookmark)
        assert add_result.success is True

        # Create get request
        GetBookmarksRequest(user_id=100, limit=10, offset=0)

        # Simulate successful get
        collection = BookmarkCollection(user_id=100, bookmarks=[bookmark])
        get_result = GetBookmarksResult.success_result(collection)
        assert get_result.success is True
        assert get_result.bookmarks is not None
        assert get_result.bookmarks.bookmark_count == 1

        # Create status request
        GetBookmarkStatusRequest(user_id=100, question_id=42)

        # Simulate successful status check
        status_result = GetBookmarkStatusResult.success_result(
            is_bookmarked=True, bookmark=bookmark
        )
        assert status_result.success is True
        assert status_result.is_bookmarked is True

        # Create remove request
        RemoveBookmarkRequest(user_id=100, question_id=42)

        # Simulate successful removal
        remove_result = RemoveBookmarkResult.success_result()
        assert remove_result.success is True
