"""Bookmark query handlers following CQRS pattern."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.domain.shared.repositories import RepositoryError

if TYPE_CHECKING:
    from src.domain.shared.repositories import BookmarkRepository
    from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection


@dataclass
class GetBookmarksQuery:
    """Query to get user's bookmarks."""

    user_id: int
    limit: int = 20
    offset: int = 0
    sort_by_date: bool = True
    sort_descending: bool = True

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.offset < 0:
            raise ValueError("Offset cannot be negative")


@dataclass
class GetBookmarksQueryResult:
    """Result of getting bookmarks."""

    success: bool
    bookmarks: BookmarkCollection | None = None
    error_message: str | None = None

    @classmethod
    def success_result(cls, bookmarks: BookmarkCollection) -> GetBookmarksQueryResult:
        """Create successful result."""
        return cls(success=True, bookmarks=bookmarks)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarksQueryResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class GetBookmarksQueryHandler:
    """Handler for get bookmarks query - direct database access."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository

    async def handle(self, query: GetBookmarksQuery) -> GetBookmarksQueryResult:
        """Handle get bookmarks query."""
        try:
            # Direct repository access (CQRS read side)
            bookmarks = await self.bookmark_repository.get_bookmarks(
                user_id=query.user_id, limit=query.limit, offset=query.offset
            )

            # Apply sorting if requested (could be done in repository)
            if query.sort_by_date:
                bookmarks = bookmarks.sort_by_date(descending=query.sort_descending)

            return GetBookmarksQueryResult.success_result(bookmarks)

        except TimeoutError:
            return GetBookmarksQueryResult.error_result("Query timeout")
        except RepositoryError as e:
            return GetBookmarksQueryResult.error_result(str(e))
        except Exception as e:
            return GetBookmarksQueryResult.error_result(f"Unexpected error: {e}")


@dataclass
class GetBookmarkStatusQuery:
    """Query to check bookmark status."""

    user_id: int
    question_id: int

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class GetBookmarkStatusQueryResult:
    """Result of checking bookmark status."""

    success: bool
    is_bookmarked: bool = False
    bookmark: Bookmark | None = None
    error_message: str | None = None

    @classmethod
    def success_result(
        cls, is_bookmarked: bool, bookmark: Bookmark | None = None
    ) -> GetBookmarkStatusQueryResult:
        """Create successful result."""
        return cls(success=True, is_bookmarked=is_bookmarked, bookmark=bookmark)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarkStatusQueryResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class GetBookmarkStatusQueryHandler:
    """Handler for get bookmark status query."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository

    async def handle(
        self, query: GetBookmarkStatusQuery
    ) -> GetBookmarkStatusQueryResult:
        """Handle get bookmark status query."""
        try:
            # Direct repository access to check bookmark
            bookmark = await self.bookmark_repository.get_bookmark_by_question(
                query.user_id, query.question_id
            )

            is_bookmarked = bookmark is not None
            return GetBookmarkStatusQueryResult.success_result(is_bookmarked, bookmark)

        except RepositoryError as e:
            return GetBookmarkStatusQueryResult.error_result(str(e))
        except Exception as e:
            return GetBookmarkStatusQueryResult.error_result(f"Unexpected error: {e}")


@dataclass
class GetBookmarkStatsQuery:
    """Query to get bookmark statistics."""

    user_id: int
    days: int = 30  # Time window for recent statistics

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.days <= 0:
            raise ValueError("Days must be positive")


@dataclass
class GetBookmarkStatsQueryResult:
    """Result of getting bookmark statistics."""

    success: bool
    stats: dict[str, Any] | None = None
    error_message: str | None = None

    @classmethod
    def success_result(cls, stats: dict[str, Any]) -> GetBookmarkStatsQueryResult:
        """Create successful result."""
        return cls(success=True, stats=stats)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarkStatsQueryResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class GetBookmarkStatsQueryHandler:
    """Handler for get bookmark statistics query."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository

    async def handle(self, query: GetBookmarkStatsQuery) -> GetBookmarkStatsQueryResult:
        """Handle get bookmark statistics query."""
        try:
            # Get bookmark count
            total_count = await self.bookmark_repository.get_bookmark_count(
                query.user_id
            )

            if total_count == 0:
                # Return empty stats for users with no bookmarks
                empty_stats = {
                    "total_count": 0,
                    "recent_count": 0,
                    "with_notes_count": 0,
                    "oldest_bookmark_age_days": 0,
                    "newest_bookmark_age_days": 0,
                    "average_age_days": 0,
                    "bookmark_creation_trend": {
                        "last_7_days": 0,
                        "last_30_days": 0,
                        "last_90_days": 0,
                    },
                }
                return GetBookmarkStatsQueryResult.success_result(empty_stats)

            # Get all bookmarks for detailed statistics
            bookmarks = await self.bookmark_repository.get_bookmarks(
                user_id=query.user_id,
                limit=None,  # Get all bookmarks
            )

            # Calculate statistics
            stats = self._calculate_bookmark_stats(bookmarks, query.days)
            return GetBookmarkStatsQueryResult.success_result(stats)

        except RepositoryError as e:
            return GetBookmarkStatsQueryResult.error_result(str(e))
        except Exception as e:
            return GetBookmarkStatsQueryResult.error_result(f"Unexpected error: {e}")

    def _calculate_bookmark_stats(
        self, bookmarks: BookmarkCollection, _days: int
    ) -> dict[str, Any]:
        """Calculate comprehensive bookmark statistics."""
        if bookmarks.is_empty:
            return {
                "total_count": 0,
                "recent_count": 0,
                "with_notes_count": 0,
                "oldest_bookmark_age_days": 0,
                "newest_bookmark_age_days": 0,
                "average_age_days": 0,
                "bookmark_creation_trend": {
                    "last_7_days": 0,
                    "last_30_days": 0,
                    "last_90_days": 0,
                },
            }

        # Use the existing statistics method from BookmarkCollection
        base_stats = bookmarks.get_statistics()

        # Add additional statistics
        recent_7_days = len(bookmarks.get_recent_bookmarks(days=7))
        recent_30_days = len(bookmarks.get_recent_bookmarks(days=30))
        recent_90_days = len(bookmarks.get_recent_bookmarks(days=90))

        # Extend base statistics
        stats = {
            **base_stats,
            "bookmark_creation_trend": {
                "last_7_days": recent_7_days,
                "last_30_days": recent_30_days,
                "last_90_days": recent_90_days,
            },
        }

        return stats


# Additional utility queries for specific use cases


@dataclass
class GetBookmarksByQuestionIdsQuery:
    """Query to get bookmarks for specific question IDs."""

    user_id: int
    question_ids: list[int]

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if not self.question_ids:
            raise ValueError("Question IDs list cannot be empty")
        if any(qid <= 0 for qid in self.question_ids):
            raise ValueError("All question IDs must be positive")


@dataclass
class GetBookmarksByQuestionIdsQueryResult:
    """Result of getting bookmarks by question IDs."""

    success: bool
    bookmarks: list[Bookmark] | None = None
    error_message: str | None = None

    @classmethod
    def success_result(
        cls, bookmarks: list[Bookmark]
    ) -> GetBookmarksByQuestionIdsQueryResult:
        """Create successful result."""
        return cls(success=True, bookmarks=bookmarks)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarksByQuestionIdsQueryResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class GetBookmarksByQuestionIdsQueryHandler:
    """Handler for get bookmarks by question IDs query."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository

    async def handle(
        self, query: GetBookmarksByQuestionIdsQuery
    ) -> GetBookmarksByQuestionIdsQueryResult:
        """Handle get bookmarks by question IDs query."""
        try:
            bookmarks = await self.bookmark_repository.get_bookmarks_by_question_ids(
                query.user_id, query.question_ids
            )

            return GetBookmarksByQuestionIdsQueryResult.success_result(bookmarks)

        except RepositoryError as e:
            return GetBookmarksByQuestionIdsQueryResult.error_result(str(e))
        except Exception as e:
            return GetBookmarksByQuestionIdsQueryResult.error_result(
                f"Unexpected error: {e}"
            )


@dataclass
class GetBookmarkCountQuery:
    """Query to get total bookmark count."""

    user_id: int

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")


@dataclass
class GetBookmarkCountQueryResult:
    """Result of getting bookmark count."""

    success: bool
    count: int = 0
    error_message: str | None = None

    @classmethod
    def success_result(cls, count: int) -> GetBookmarkCountQueryResult:
        """Create successful result."""
        return cls(success=True, count=count)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarkCountQueryResult:
        """Create error result."""
        return cls(success=False, error_message=message)


class GetBookmarkCountQueryHandler:
    """Handler for get bookmark count query."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        """Initialize handler."""
        self.bookmark_repository = bookmark_repository

    async def handle(self, query: GetBookmarkCountQuery) -> GetBookmarkCountQueryResult:
        """Handle get bookmark count query."""
        try:
            count = await self.bookmark_repository.get_bookmark_count(query.user_id)
            return GetBookmarkCountQueryResult.success_result(count)

        except RepositoryError as e:
            return GetBookmarkCountQueryResult.error_result(str(e))
        except Exception as e:
            return GetBookmarkCountQueryResult.error_result(f"Unexpected error: {e}")
