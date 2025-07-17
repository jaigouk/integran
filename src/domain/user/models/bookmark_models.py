"""Bookmark domain models for user question bookmarking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Bookmark:
    """Domain entity representing a user's bookmarked question.

    A bookmark allows users to save questions for later review,
    creating a personalized collection of important questions.
    """

    id: int
    user_id: int
    question_id: int
    created_at: datetime
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate bookmark data after initialization."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")
        if self.created_at is None:
            self.created_at = datetime.now(UTC)

    def has_notes(self) -> bool:
        """Check if bookmark has notes."""
        return self.notes is not None and self.notes.strip() != ""

    def age_in_days(self) -> int:
        """Calculate age of bookmark in days."""
        now = datetime.now(UTC)
        if self.created_at.tzinfo is None:
            # Handle naive datetime (from database)
            created_utc = self.created_at.replace(tzinfo=UTC)
        else:
            created_utc = self.created_at

        delta = now - created_utc
        return delta.days

    def is_recent(self, days: int = 7) -> bool:
        """Check if bookmark was created within specified days."""
        return self.age_in_days() <= days


@dataclass
class BookmarkCollection:
    """Value object representing a collection of bookmarks.

    Provides convenient methods for working with multiple bookmarks
    and calculating collection statistics.
    """

    user_id: int
    bookmarks: list[Bookmark] = field(default_factory=list)
    total_count: int = 0

    def __post_init__(self) -> None:
        """Validate collection data after initialization."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")

        # Ensure total_count matches bookmarks length if not explicitly set
        if self.total_count == 0 and self.bookmarks:
            self.total_count = len(self.bookmarks)

    @property
    def question_ids(self) -> list[int]:
        """Get list of question IDs in the collection."""
        return [bookmark.question_id for bookmark in self.bookmarks]

    @property
    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self.bookmarks) == 0

    @property
    def bookmark_count(self) -> int:
        """Get number of bookmarks in collection."""
        return len(self.bookmarks)

    def contains_question(self, question_id: int) -> bool:
        """Check if a specific question is bookmarked."""
        return question_id in self.question_ids

    def get_bookmark_by_question_id(self, question_id: int) -> Bookmark | None:
        """Get bookmark for a specific question."""
        for bookmark in self.bookmarks:
            if bookmark.question_id == question_id:
                return bookmark
        return None

    def get_recent_bookmarks(self, days: int = 7) -> list[Bookmark]:
        """Get bookmarks created within specified days."""
        return [bookmark for bookmark in self.bookmarks if bookmark.is_recent(days)]

    def get_bookmarks_with_notes(self) -> list[Bookmark]:
        """Get bookmarks that have notes."""
        return [bookmark for bookmark in self.bookmarks if bookmark.has_notes()]

    def get_statistics(self) -> dict[str, Any]:
        """Get collection statistics."""
        if self.is_empty:
            return {
                "total_count": 0,
                "recent_count": 0,
                "with_notes_count": 0,
                "oldest_bookmark_age_days": 0,
                "newest_bookmark_age_days": 0,
                "average_age_days": 0,
            }

        recent_bookmarks = self.get_recent_bookmarks()
        with_notes_bookmarks = self.get_bookmarks_with_notes()
        ages = [bookmark.age_in_days() for bookmark in self.bookmarks]

        return {
            "total_count": self.bookmark_count,
            "recent_count": len(recent_bookmarks),
            "with_notes_count": len(with_notes_bookmarks),
            "oldest_bookmark_age_days": max(ages) if ages else 0,
            "newest_bookmark_age_days": min(ages) if ages else 0,
            "average_age_days": sum(ages) / len(ages) if ages else 0,
        }

    def sort_by_date(self, descending: bool = True) -> BookmarkCollection:
        """Return new collection sorted by creation date."""
        sorted_bookmarks = sorted(
            self.bookmarks, key=lambda b: b.created_at, reverse=descending
        )
        return BookmarkCollection(
            user_id=self.user_id,
            bookmarks=sorted_bookmarks,
            total_count=self.total_count,
        )

    def limit(self, count: int, offset: int = 0) -> BookmarkCollection:
        """Return new collection with limited bookmarks."""
        limited_bookmarks = self.bookmarks[offset : offset + count]
        return BookmarkCollection(
            user_id=self.user_id,
            bookmarks=limited_bookmarks,
            total_count=self.total_count,
        )


# ============================================================================
# Request/Response DTOs for Domain Services
# ============================================================================


@dataclass
class AddBookmarkRequest:
    """Request to add a new bookmark."""

    user_id: int
    question_id: int
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class AddBookmarkResult:
    """Result of adding a bookmark."""

    success: bool
    bookmark: Bookmark | None = None
    error_message: str | None = None

    @classmethod
    def success_result(cls, bookmark: Bookmark) -> AddBookmarkResult:
        """Create successful result."""
        return cls(success=True, bookmark=bookmark)

    @classmethod
    def error_result(cls, message: str) -> AddBookmarkResult:
        """Create error result."""
        return cls(success=False, error_message=message)


@dataclass
class RemoveBookmarkRequest:
    """Request to remove a bookmark."""

    user_id: int
    question_id: int

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class RemoveBookmarkResult:
    """Result of removing a bookmark."""

    success: bool
    error_message: str | None = None

    @classmethod
    def success_result(cls) -> RemoveBookmarkResult:
        """Create successful result."""
        return cls(success=True)

    @classmethod
    def error_result(cls, message: str) -> RemoveBookmarkResult:
        """Create error result."""
        return cls(success=False, error_message=message)


@dataclass
class GetBookmarksRequest:
    """Request to get user's bookmarks."""

    user_id: int
    limit: int | None = None
    offset: int = 0
    include_notes: bool = True
    sort_by_date: bool = True
    sort_descending: bool = True

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.offset < 0:
            raise ValueError("Offset cannot be negative")


@dataclass
class GetBookmarksResult:
    """Result of getting bookmarks."""

    success: bool
    bookmarks: BookmarkCollection | None = None
    error_message: str | None = None

    @classmethod
    def success_result(cls, bookmarks: BookmarkCollection) -> GetBookmarksResult:
        """Create successful result."""
        return cls(success=True, bookmarks=bookmarks)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarksResult:
        """Create error result."""
        return cls(success=False, error_message=message)


@dataclass
class GetBookmarkStatusRequest:
    """Request to check bookmark status."""

    user_id: int
    question_id: int

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")


@dataclass
class GetBookmarkStatusResult:
    """Result of checking bookmark status."""

    success: bool
    is_bookmarked: bool = False
    bookmark: Bookmark | None = None
    error_message: str | None = None

    @classmethod
    def success_result(
        cls, is_bookmarked: bool, bookmark: Bookmark | None = None
    ) -> GetBookmarkStatusResult:
        """Create successful result."""
        return cls(success=True, is_bookmarked=is_bookmarked, bookmark=bookmark)

    @classmethod
    def error_result(cls, message: str) -> GetBookmarkStatusResult:
        """Create error result."""
        return cls(success=False, error_message=message)
