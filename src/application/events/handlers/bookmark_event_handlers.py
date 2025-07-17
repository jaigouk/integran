"""Event handlers for bookmark-related domain events."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.shared.events import (
    BookmarkAddedEvent,
    BookmarkRemovedEvent,
    BookmarksViewedEvent,
)

if TYPE_CHECKING:
    from src.domain.shared.repositories import AnalyticsRepository

logger = logging.getLogger(__name__)


class BookmarkAddedEventHandler:
    """Handler for bookmark added events."""

    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize handler."""
        self.analytics_repository = analytics_repository

    async def handle(self, event: BookmarkAddedEvent) -> None:
        """Handle bookmark added event."""
        try:
            # Record bookmark activity
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                activity_type="bookmark_added",
                metadata={
                    "bookmark_id": event.bookmark_id,
                    "notes": event.notes,
                    "timestamp": event.occurred_at,
                },
            )

            # Update user engagement metrics
            await self.analytics_repository.update_user_engagement_metrics(
                user_id=event.user_id,
                activity_type="bookmark_created",
                timestamp=event.occurred_at,
            )

            # Track question popularity
            await self.analytics_repository.increment_question_bookmark_count(
                question_id=event.question_id
            )

            logger.info(
                f"Processed bookmark added event for user {event.user_id}, "
                f"question {event.question_id}, bookmark {event.bookmark_id}"
            )

        except Exception as e:
            # Log error but don't re-raise to avoid breaking the application
            logger.error(
                f"Error handling bookmark added event for user {event.user_id}, "
                f"question {event.question_id}: {e}"
            )


class BookmarkRemovedEventHandler:
    """Handler for bookmark removed events."""

    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize handler."""
        self.analytics_repository = analytics_repository

    async def handle(self, event: BookmarkRemovedEvent) -> None:
        """Handle bookmark removed event."""
        try:
            # Record bookmark activity
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                activity_type="bookmark_removed",
                metadata={
                    "bookmark_id": event.bookmark_id,
                    "timestamp": event.occurred_at,
                },
            )

            # Update user engagement metrics
            await self.analytics_repository.update_user_engagement_metrics(
                user_id=event.user_id,
                activity_type="bookmark_removed",
                timestamp=event.occurred_at,
            )

            # Update question bookmark count
            await self.analytics_repository.decrement_question_bookmark_count(
                question_id=event.question_id
            )

            logger.info(
                f"Processed bookmark removed event for user {event.user_id}, "
                f"question {event.question_id}, bookmark {event.bookmark_id}"
            )

        except Exception as e:
            # Log error but don't re-raise to avoid breaking the application
            logger.error(
                f"Error handling bookmark removed event for user {event.user_id}, "
                f"question {event.question_id}: {e}"
            )


class BookmarksViewedEventHandler:
    """Handler for bookmarks viewed events."""

    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize handler."""
        self.analytics_repository = analytics_repository

    async def handle(self, event: BookmarksViewedEvent) -> None:
        """Handle bookmarks viewed event."""
        try:
            # Record bookmark activity
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=None,  # No specific question for viewing list
                activity_type="bookmarks_viewed",
                metadata={
                    "bookmark_count": event.bookmark_count,
                    "view_type": event.view_type,
                    "timestamp": event.occurred_at,
                },
            )

            # Handle specific view types
            if event.view_type == "practice":
                # Track practice session initiation
                await self.analytics_repository.record_practice_session_start(
                    user_id=event.user_id,
                    practice_mode="bookmarks",
                    question_count=event.bookmark_count,
                    timestamp=event.occurred_at,
                )
            elif event.view_type == "manage":
                # Track bookmark management usage
                await self.analytics_repository.record_feature_usage(
                    user_id=event.user_id,
                    feature="bookmark_management",
                    context={"view_type": event.view_type},
                    timestamp=event.occurred_at,
                )

            # Track empty state views
            if event.bookmark_count == 0:
                await self.analytics_repository.record_empty_state_view(
                    user_id=event.user_id,
                    feature="bookmarks",
                    timestamp=event.occurred_at,
                )

            logger.info(
                f"Processed bookmarks viewed event for user {event.user_id}, "
                f"view_type {event.view_type}, count {event.bookmark_count}"
            )

        except Exception as e:
            # Log error but don't re-raise to avoid breaking the application
            logger.error(
                f"Error handling bookmarks viewed event for user {event.user_id}, "
                f"view_type {event.view_type}: {e}"
            )
