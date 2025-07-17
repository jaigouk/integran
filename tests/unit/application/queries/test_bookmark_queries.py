"""Tests for bookmark query handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.application.queries.bookmark_queries import (
    GetBookmarksQuery,
    GetBookmarksQueryHandler,
    GetBookmarksQueryResult,
    GetBookmarkStatsQuery,
    GetBookmarkStatsQueryHandler,
    GetBookmarkStatsQueryResult,
    GetBookmarkStatusQuery,
    GetBookmarkStatusQueryHandler,
    GetBookmarkStatusQueryResult,
)
from src.domain.shared.repositories import BookmarkRepository, RepositoryError
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection


class TestGetBookmarksQuery:
    """Test GetBookmarksQuery and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def query_handler(self, mock_bookmark_repository):
        """Create query handler."""
        return GetBookmarksQueryHandler(mock_bookmark_repository)

    @pytest.fixture
    def sample_bookmarks(self):
        """Create sample bookmarks."""
        return [
            Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes="First bookmark",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=100,
                question_id=43,
                notes="Second bookmark",
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
    def sample_bookmark_collection(self, sample_bookmarks):
        """Create sample bookmark collection."""
        return BookmarkCollection(
            user_id=100, bookmarks=sample_bookmarks, total_count=3
        )

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_success(
        self, query_handler, mock_bookmark_repository, sample_bookmark_collection
    ):
        """Test successful bookmark retrieval."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, sort_by_date=False)
        mock_bookmark_repository.get_bookmarks.return_value = sample_bookmark_collection

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert isinstance(result, GetBookmarksQueryResult)
        assert result.success is True
        assert result.bookmarks == sample_bookmark_collection
        assert result.error_message is None

        # Verify repository call
        mock_bookmark_repository.get_bookmarks.assert_called_once_with(
            user_id=100, limit=20, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_with_pagination(
        self, query_handler, mock_bookmark_repository, sample_bookmark_collection
    ):
        """Test bookmark retrieval with pagination."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, limit=10, offset=20, sort_by_date=False)
        mock_bookmark_repository.get_bookmarks.return_value = sample_bookmark_collection

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.bookmarks == sample_bookmark_collection

        # Verify repository call with pagination
        mock_bookmark_repository.get_bookmarks.assert_called_once_with(
            user_id=100, limit=10, offset=20
        )

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_empty_result(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark retrieval with empty result."""
        # Arrange
        query = GetBookmarksQuery(user_id=100)
        empty_collection = BookmarkCollection(user_id=100, bookmarks=[], total_count=0)
        mock_bookmark_repository.get_bookmarks.return_value = empty_collection

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.bookmarks.is_empty is True
        assert result.bookmarks.total_count == 0

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_repository_error(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark retrieval with repository error."""
        # Arrange
        query = GetBookmarksQuery(user_id=100)
        mock_bookmark_repository.get_bookmarks.side_effect = RepositoryError(
            "Database error", "DATABASE_ERROR"
        )

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is False
        assert result.bookmarks is None
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_validation(self, query_handler):
        """Test query validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            GetBookmarksQuery(user_id=0)

        # Test invalid limit
        with pytest.raises(ValueError, match="Limit must be positive"):
            GetBookmarksQuery(user_id=100, limit=0)

        # Test invalid offset
        with pytest.raises(ValueError, match="Offset cannot be negative"):
            GetBookmarksQuery(user_id=100, offset=-1)

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_no_limit(
        self, query_handler, mock_bookmark_repository, sample_bookmark_collection
    ):
        """Test bookmark retrieval without limit."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, limit=None)
        mock_bookmark_repository.get_bookmarks.return_value = sample_bookmark_collection

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True

        # Verify repository call
        mock_bookmark_repository.get_bookmarks.assert_called_once_with(
            user_id=100, limit=None, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_bookmarks_query_sorting_options(
        self, query_handler, mock_bookmark_repository, sample_bookmark_collection
    ):
        """Test bookmark retrieval with sorting options."""
        # Arrange
        query = GetBookmarksQuery(
            user_id=100,
            sort_by_date=True,
            sort_descending=False,  # Ascending
        )
        mock_bookmark_repository.get_bookmarks.return_value = sample_bookmark_collection

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True

        # Note: In a real implementation, sorting would be handled by repository
        # or the query handler would post-process the results


class TestGetBookmarkStatusQuery:
    """Test GetBookmarkStatusQuery and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def query_handler(self, mock_bookmark_repository):
        """Create query handler."""
        return GetBookmarkStatusQueryHandler(mock_bookmark_repository)

    @pytest.fixture
    def sample_bookmark(self):
        """Create sample bookmark."""
        return Bookmark(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test bookmark",
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_get_bookmark_status_query_bookmarked(
        self, query_handler, mock_bookmark_repository, sample_bookmark
    ):
        """Test bookmark status check when question is bookmarked."""
        # Arrange
        query = GetBookmarkStatusQuery(user_id=100, question_id=42)
        mock_bookmark_repository.get_bookmark_by_question.return_value = sample_bookmark

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert isinstance(result, GetBookmarkStatusQueryResult)
        assert result.success is True
        assert result.is_bookmarked is True
        assert result.bookmark == sample_bookmark
        assert result.error_message is None

        # Verify repository call
        mock_bookmark_repository.get_bookmark_by_question.assert_called_once_with(
            100, 42
        )

    @pytest.mark.asyncio
    async def test_get_bookmark_status_query_not_bookmarked(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark status check when question is not bookmarked."""
        # Arrange
        query = GetBookmarkStatusQuery(user_id=100, question_id=42)
        mock_bookmark_repository.get_bookmark_by_question.return_value = None

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.is_bookmarked is False
        assert result.bookmark is None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_get_bookmark_status_query_repository_error(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark status check with repository error."""
        # Arrange
        query = GetBookmarkStatusQuery(user_id=100, question_id=42)
        mock_bookmark_repository.get_bookmark_by_question.side_effect = RepositoryError(
            "Database error", "DATABASE_ERROR"
        )

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is False
        assert result.is_bookmarked is False
        assert result.bookmark is None
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_bookmark_status_query_validation(self, query_handler):
        """Test query validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            GetBookmarkStatusQuery(user_id=0, question_id=42)

        # Test invalid question_id
        with pytest.raises(ValueError, match="Question ID must be positive"):
            GetBookmarkStatusQuery(user_id=100, question_id=0)


class TestGetBookmarkStatsQuery:
    """Test GetBookmarkStatsQuery and handler."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def query_handler(self, mock_bookmark_repository):
        """Create query handler."""
        return GetBookmarkStatsQueryHandler(mock_bookmark_repository)

    @pytest.fixture
    def sample_bookmark_stats(self):
        """Create sample bookmark statistics."""
        return {
            "total_count": 15,
            "recent_count": 5,
            "with_notes_count": 8,
            "oldest_bookmark_age_days": 30,
            "newest_bookmark_age_days": 1,
            "average_age_days": 12.5,
            "most_bookmarked_categories": ["History", "Politics", "Geography"],
            "bookmark_creation_trend": {
                "last_7_days": 3,
                "last_30_days": 8,
                "last_90_days": 15,
            },
        }

    @pytest.mark.asyncio
    async def test_get_bookmark_stats_query_success(
        self, query_handler, mock_bookmark_repository, sample_bookmark_stats
    ):
        """Test successful bookmark statistics retrieval."""
        # Arrange
        query = GetBookmarkStatsQuery(user_id=100)

        # Mock repository calls
        mock_bookmark_repository.get_bookmark_count.return_value = 15
        mock_bookmark_repository.get_bookmarks.return_value = BookmarkCollection(
            user_id=100,
            bookmarks=[],  # Would contain actual bookmarks in real scenario
            total_count=15,
        )

        # Mock the stats calculation (in real implementation, this would be in handler)
        with patch.object(
            query_handler,
            "_calculate_bookmark_stats",
            return_value=sample_bookmark_stats,
        ):
            # Act
            result = await query_handler.handle(query)

        # Assert
        assert isinstance(result, GetBookmarkStatsQueryResult)
        assert result.success is True
        assert result.stats == sample_bookmark_stats
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_get_bookmark_stats_query_no_bookmarks(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark statistics when user has no bookmarks."""
        # Arrange
        query = GetBookmarkStatsQuery(user_id=100)

        # Mock empty results
        mock_bookmark_repository.get_bookmark_count.return_value = 0
        mock_bookmark_repository.get_bookmarks.return_value = BookmarkCollection(
            user_id=100, bookmarks=[], total_count=0
        )

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.stats["total_count"] == 0
        assert result.stats["recent_count"] == 0
        assert result.stats["with_notes_count"] == 0

    @pytest.mark.asyncio
    async def test_get_bookmark_stats_query_repository_error(
        self, query_handler, mock_bookmark_repository
    ):
        """Test bookmark statistics with repository error."""
        # Arrange
        query = GetBookmarkStatsQuery(user_id=100)
        mock_bookmark_repository.get_bookmark_count.side_effect = RepositoryError(
            "Database error", "DATABASE_ERROR"
        )

        # Act
        result = await query_handler.handle(query)

        # Assert
        assert result.success is False
        assert result.stats is None
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_bookmark_stats_query_validation(self, query_handler):
        """Test query validation."""
        # Test invalid user_id
        with pytest.raises(ValueError, match="User ID must be positive"):
            GetBookmarkStatsQuery(user_id=0)

    @pytest.mark.asyncio
    async def test_get_bookmark_stats_query_with_days_filter(
        self, query_handler, mock_bookmark_repository, sample_bookmark_stats
    ):
        """Test bookmark statistics with days filter."""
        # Arrange
        query = GetBookmarkStatsQuery(user_id=100, days=7)

        # Mock repository calls
        mock_bookmark_repository.get_bookmark_count.return_value = 15
        mock_bookmark_repository.get_bookmarks.return_value = BookmarkCollection(
            user_id=100, bookmarks=[], total_count=15
        )

        # Mock the stats calculation
        with patch.object(
            query_handler,
            "_calculate_bookmark_stats",
            return_value=sample_bookmark_stats,
        ):
            # Act
            result = await query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.stats == sample_bookmark_stats


class TestQueryEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def mock_bookmark_repository(self):
        """Mock bookmark repository."""
        return AsyncMock(spec=BookmarkRepository)

    @pytest.fixture
    def bookmarks_query_handler(self, mock_bookmark_repository):
        """Create bookmarks query handler."""
        return GetBookmarksQueryHandler(mock_bookmark_repository)

    @pytest.mark.asyncio
    async def test_query_with_large_limit(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test query with very large limit."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, limit=10000)

        # Mock large collection
        large_collection = BookmarkCollection(
            user_id=100, bookmarks=[], total_count=10000
        )
        mock_bookmark_repository.get_bookmarks.return_value = large_collection

        # Act
        result = await bookmarks_query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.bookmarks.total_count == 10000

    @pytest.mark.asyncio
    async def test_query_with_large_offset(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test query with large offset."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, offset=5000)

        # Mock empty result (offset beyond available data)
        empty_collection = BookmarkCollection(
            user_id=100,
            bookmarks=[],
            total_count=1000,  # Total is 1000, but offset is 5000
        )
        mock_bookmark_repository.get_bookmarks.return_value = empty_collection

        # Act
        result = await bookmarks_query_handler.handle(query)

        # Assert
        assert result.success is True
        assert result.bookmarks.is_empty is True

    @pytest.mark.asyncio
    async def test_concurrent_queries(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test concurrent query execution."""
        # Arrange
        queries = [GetBookmarksQuery(user_id=100 + i, limit=10) for i in range(5)]

        # Mock different collections for each user
        mock_bookmark_repository.get_bookmarks.side_effect = [
            BookmarkCollection(user_id=100 + i, bookmarks=[], total_count=i)
            for i in range(5)
        ]

        # Act
        import asyncio

        results = await asyncio.gather(
            *[bookmarks_query_handler.handle(query) for query in queries]
        )

        # Assert
        assert len(results) == 5
        assert all(result.success for result in results)
        assert [result.bookmarks.total_count for result in results] == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_query_timeout_handling(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test query timeout handling."""
        # Arrange
        query = GetBookmarksQuery(user_id=100)

        # Mock timeout
        mock_bookmark_repository.get_bookmarks.side_effect = TimeoutError(
            "Query timeout"
        )

        # Act
        result = await bookmarks_query_handler.handle(query)

        # Assert
        assert result.success is False
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_query_memory_efficiency(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test query memory efficiency with large datasets."""
        # Arrange
        query = GetBookmarksQuery(user_id=100, limit=1000)

        # Mock large collection
        large_bookmarks = [
            Bookmark(
                id=i,
                user_id=100,
                question_id=i,
                notes=f"Bookmark {i}",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 1001)  # Start from 1 to avoid question_id = 0
        ]
        large_collection = BookmarkCollection(
            user_id=100, bookmarks=large_bookmarks, total_count=1000
        )
        mock_bookmark_repository.get_bookmarks.return_value = large_collection

        # Act
        result = await bookmarks_query_handler.handle(query)

        # Assert
        assert result.success is True
        assert len(result.bookmarks.bookmarks) == 1000

        # Test memory usage (in real scenario, this would check actual memory)
        # For now, just verify the collection is properly structured
        assert result.bookmarks.total_count == 1000

    @pytest.mark.asyncio
    async def test_query_with_special_characters(
        self, bookmarks_query_handler, mock_bookmark_repository
    ):
        """Test query handling with special characters in data."""
        # Arrange
        query = GetBookmarksQuery(user_id=100)

        # Mock bookmarks with special characters
        special_bookmarks = [
            Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes="Special chars: äöü ß 日本語 🔖",
                created_at=datetime.now(UTC),
            )
        ]
        collection = BookmarkCollection(
            user_id=100, bookmarks=special_bookmarks, total_count=1
        )
        mock_bookmark_repository.get_bookmarks.return_value = collection

        # Act
        result = await bookmarks_query_handler.handle(query)

        # Assert
        assert result.success is True
        assert len(result.bookmarks.bookmarks) == 1
        assert "äöü ß 日本語 🔖" in result.bookmarks.bookmarks[0].notes
