"""Tests for bookmark event handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.events.handlers.bookmark_event_handlers import (
    BookmarkAddedEventHandler,
    BookmarkRemovedEventHandler,
    BookmarksViewedEventHandler,
)
from src.domain.shared.events import (
    BookmarkAddedEvent,
    BookmarkRemovedEvent,
    BookmarksViewedEvent,
)
from src.domain.shared.repositories import AnalyticsRepository, RepositoryError


class TestBookmarkAddedEventHandler:
    """Test BookmarkAddedEventHandler."""

    @pytest.fixture
    def mock_analytics_repository(self):
        """Mock analytics repository."""
        return AsyncMock(spec=AnalyticsRepository)

    @pytest.fixture
    def event_handler(self, mock_analytics_repository):
        """Create event handler."""
        return BookmarkAddedEventHandler(mock_analytics_repository)

    @pytest.fixture
    def sample_bookmark_added_event(self):
        """Create sample bookmark added event."""
        return BookmarkAddedEvent(
            user_id=100, question_id=42, bookmark_id=1, notes="Test bookmark"
        )

    @pytest.mark.asyncio
    async def test_bookmark_added_event_handler_success(
        self, event_handler, mock_analytics_repository, sample_bookmark_added_event
    ):
        """Test successful handling of bookmark added event."""
        # Act
        await event_handler.handle(sample_bookmark_added_event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=42,
            activity_type="bookmark_added",
            metadata={
                "bookmark_id": 1,
                "notes": "Test bookmark",
                "timestamp": sample_bookmark_added_event.occurred_at,
            },
        )

    @pytest.mark.asyncio
    async def test_bookmark_added_event_handler_without_notes(
        self, event_handler, mock_analytics_repository
    ):
        """Test handling bookmark added event without notes."""
        # Arrange
        event = BookmarkAddedEvent(
            user_id=100, question_id=42, bookmark_id=1, notes=None
        )

        # Act
        await event_handler.handle(event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=42,
            activity_type="bookmark_added",
            metadata={"bookmark_id": 1, "notes": None, "timestamp": event.occurred_at},
        )

    @pytest.mark.asyncio
    async def test_bookmark_added_event_handler_analytics_error(
        self, event_handler, mock_analytics_repository, sample_bookmark_added_event
    ):
        """Test handling of analytics repository error."""
        # Arrange
        mock_analytics_repository.record_bookmark_activity.side_effect = (
            RepositoryError("Analytics database error", "DATABASE_ERROR")
        )

        # Act & Assert - should not raise exception
        try:
            await event_handler.handle(sample_bookmark_added_event)
        except Exception as e:
            pytest.fail(f"Event handler should not raise exception: {e}")

        # Verify analytics was attempted
        mock_analytics_repository.record_bookmark_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_bookmark_added_event_handler_updates_user_metrics(
        self, event_handler, mock_analytics_repository, sample_bookmark_added_event
    ):
        """Test that handler updates user engagement metrics."""
        # Act
        await event_handler.handle(sample_bookmark_added_event)

        # Assert
        # In addition to bookmark activity, should update user engagement
        assert mock_analytics_repository.record_bookmark_activity.call_count == 1
        mock_analytics_repository.update_user_engagement_metrics.assert_called_once_with(
            user_id=100,
            activity_type="bookmark_created",
            timestamp=sample_bookmark_added_event.occurred_at,
        )

    @pytest.mark.asyncio
    async def test_bookmark_added_event_handler_tracks_question_popularity(
        self, event_handler, mock_analytics_repository, sample_bookmark_added_event
    ):
        """Test that handler tracks question popularity."""
        # Act
        await event_handler.handle(sample_bookmark_added_event)

        # Assert
        mock_analytics_repository.increment_question_bookmark_count.assert_called_once_with(
            question_id=42
        )


class TestBookmarkRemovedEventHandler:
    """Test BookmarkRemovedEventHandler."""

    @pytest.fixture
    def mock_analytics_repository(self):
        """Mock analytics repository."""
        return AsyncMock(spec=AnalyticsRepository)

    @pytest.fixture
    def event_handler(self, mock_analytics_repository):
        """Create event handler."""
        return BookmarkRemovedEventHandler(mock_analytics_repository)

    @pytest.fixture
    def sample_bookmark_removed_event(self):
        """Create sample bookmark removed event."""
        return BookmarkRemovedEvent(user_id=100, question_id=42, bookmark_id=1)

    @pytest.mark.asyncio
    async def test_bookmark_removed_event_handler_success(
        self, event_handler, mock_analytics_repository, sample_bookmark_removed_event
    ):
        """Test successful handling of bookmark removed event."""
        # Act
        await event_handler.handle(sample_bookmark_removed_event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=42,
            activity_type="bookmark_removed",
            metadata={
                "bookmark_id": 1,
                "timestamp": sample_bookmark_removed_event.occurred_at,
            },
        )

    @pytest.mark.asyncio
    async def test_bookmark_removed_event_handler_without_bookmark_id(
        self, event_handler, mock_analytics_repository
    ):
        """Test handling bookmark removed event without bookmark ID."""
        # Arrange
        event = BookmarkRemovedEvent(user_id=100, question_id=42, bookmark_id=None)

        # Act
        await event_handler.handle(event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=42,
            activity_type="bookmark_removed",
            metadata={"bookmark_id": None, "timestamp": event.occurred_at},
        )

    @pytest.mark.asyncio
    async def test_bookmark_removed_event_handler_updates_metrics(
        self, event_handler, mock_analytics_repository, sample_bookmark_removed_event
    ):
        """Test that handler updates relevant metrics."""
        # Act
        await event_handler.handle(sample_bookmark_removed_event)

        # Assert
        # Should update user engagement metrics
        mock_analytics_repository.update_user_engagement_metrics.assert_called_once_with(
            user_id=100,
            activity_type="bookmark_removed",
            timestamp=sample_bookmark_removed_event.occurred_at,
        )

        # Should decrement question bookmark count
        mock_analytics_repository.decrement_question_bookmark_count.assert_called_once_with(
            question_id=42
        )

    @pytest.mark.asyncio
    async def test_bookmark_removed_event_handler_error_handling(
        self, event_handler, mock_analytics_repository, sample_bookmark_removed_event
    ):
        """Test error handling in bookmark removed event handler."""
        # Arrange
        mock_analytics_repository.record_bookmark_activity.side_effect = Exception(
            "Unexpected error"
        )

        # Act & Assert - should not raise exception
        try:
            await event_handler.handle(sample_bookmark_removed_event)
        except Exception as e:
            pytest.fail(f"Event handler should not raise exception: {e}")


class TestBookmarksViewedEventHandler:
    """Test BookmarksViewedEventHandler."""

    @pytest.fixture
    def mock_analytics_repository(self):
        """Mock analytics repository."""
        return AsyncMock(spec=AnalyticsRepository)

    @pytest.fixture
    def event_handler(self, mock_analytics_repository):
        """Create event handler."""
        return BookmarksViewedEventHandler(mock_analytics_repository)

    @pytest.fixture
    def sample_bookmarks_viewed_event(self):
        """Create sample bookmarks viewed event."""
        return BookmarksViewedEvent(user_id=100, bookmark_count=15, view_type="list")

    @pytest.mark.asyncio
    async def test_bookmarks_viewed_event_handler_success(
        self, event_handler, mock_analytics_repository, sample_bookmarks_viewed_event
    ):
        """Test successful handling of bookmarks viewed event."""
        # Act
        await event_handler.handle(sample_bookmarks_viewed_event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=None,  # No specific question for viewing list
            activity_type="bookmarks_viewed",
            metadata={
                "bookmark_count": 15,
                "view_type": "list",
                "timestamp": sample_bookmarks_viewed_event.occurred_at,
            },
        )

    @pytest.mark.asyncio
    async def test_bookmarks_viewed_event_handler_practice_view(
        self, event_handler, mock_analytics_repository
    ):
        """Test handling bookmarks viewed event for practice."""
        # Arrange
        event = BookmarksViewedEvent(
            user_id=100, bookmark_count=5, view_type="practice"
        )

        # Act
        await event_handler.handle(event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=None,
            activity_type="bookmarks_viewed",
            metadata={
                "bookmark_count": 5,
                "view_type": "practice",
                "timestamp": event.occurred_at,
            },
        )

        # Should also track practice session initiation
        mock_analytics_repository.record_practice_session_start.assert_called_once_with(
            user_id=100,
            practice_mode="bookmarks",
            question_count=5,
            timestamp=event.occurred_at,
        )

    @pytest.mark.asyncio
    async def test_bookmarks_viewed_event_handler_manage_view(
        self, event_handler, mock_analytics_repository
    ):
        """Test handling bookmarks viewed event for management."""
        # Arrange
        event = BookmarksViewedEvent(user_id=100, bookmark_count=20, view_type="manage")

        # Act
        await event_handler.handle(event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=None,
            activity_type="bookmarks_viewed",
            metadata={
                "bookmark_count": 20,
                "view_type": "manage",
                "timestamp": event.occurred_at,
            },
        )

        # Should track bookmark management usage
        mock_analytics_repository.record_feature_usage.assert_called_once_with(
            user_id=100,
            feature="bookmark_management",
            context={"view_type": "manage"},
            timestamp=event.occurred_at,
        )

    @pytest.mark.asyncio
    async def test_bookmarks_viewed_event_handler_zero_bookmarks(
        self, event_handler, mock_analytics_repository
    ):
        """Test handling bookmarks viewed event with zero bookmarks."""
        # Arrange
        event = BookmarksViewedEvent(user_id=100, bookmark_count=0, view_type="list")

        # Act
        await event_handler.handle(event)

        # Assert
        mock_analytics_repository.record_bookmark_activity.assert_called_once_with(
            user_id=100,
            question_id=None,
            activity_type="bookmarks_viewed",
            metadata={
                "bookmark_count": 0,
                "view_type": "list",
                "timestamp": event.occurred_at,
            },
        )

        # Should track empty state view
        mock_analytics_repository.record_empty_state_view.assert_called_once_with(
            user_id=100, feature="bookmarks", timestamp=event.occurred_at
        )


class TestBookmarkEventHandlerIntegration:
    """Test integration between bookmark event handlers."""

    @pytest.fixture
    def mock_analytics_repository(self):
        """Mock analytics repository."""
        return AsyncMock(spec=AnalyticsRepository)

    @pytest.fixture
    def added_handler(self, mock_analytics_repository):
        """Create bookmark added handler."""
        return BookmarkAddedEventHandler(mock_analytics_repository)

    @pytest.fixture
    def removed_handler(self, mock_analytics_repository):
        """Create bookmark removed handler."""
        return BookmarkRemovedEventHandler(mock_analytics_repository)

    @pytest.fixture
    def viewed_handler(self, mock_analytics_repository):
        """Create bookmarks viewed handler."""
        return BookmarksViewedEventHandler(mock_analytics_repository)

    @pytest.mark.asyncio
    async def test_bookmark_lifecycle_event_sequence(
        self,
        added_handler,
        removed_handler,
        viewed_handler,
        mock_analytics_repository,
    ):
        """Test complete bookmark lifecycle event sequence."""
        user_id = 100
        question_id = 42

        # Step 1: Handle bookmark added event
        added_event = BookmarkAddedEvent(
            user_id=user_id,
            question_id=question_id,
            bookmark_id=1,
            notes="Test bookmark",
        )
        await added_handler.handle(added_event)

        # Step 2: Handle bookmarks viewed event
        viewed_event = BookmarksViewedEvent(
            user_id=user_id, bookmark_count=1, view_type="list"
        )
        await viewed_handler.handle(viewed_event)

        # Step 3: Handle bookmark removed event
        removed_event = BookmarkRemovedEvent(
            user_id=user_id, question_id=question_id, bookmark_id=1
        )
        await removed_handler.handle(removed_event)

        # Assert all events were processed
        assert mock_analytics_repository.record_bookmark_activity.call_count == 3
        assert mock_analytics_repository.update_user_engagement_metrics.call_count == 2
        assert (
            mock_analytics_repository.increment_question_bookmark_count.call_count == 1
        )
        assert (
            mock_analytics_repository.decrement_question_bookmark_count.call_count == 1
        )

    @pytest.mark.asyncio
    async def test_concurrent_event_handling(
        self,
        added_handler,
        removed_handler,
        viewed_handler,
        mock_analytics_repository,
    ):
        """Test concurrent event handling."""
        # Arrange
        events = [
            BookmarkAddedEvent(
                user_id=100, question_id=41, bookmark_id=1, notes="Bookmark 1"
            ),
            BookmarkAddedEvent(
                user_id=100, question_id=42, bookmark_id=2, notes="Bookmark 2"
            ),
            BookmarksViewedEvent(user_id=100, bookmark_count=2, view_type="list"),
            BookmarkRemovedEvent(user_id=100, question_id=41, bookmark_id=1),
        ]

        # Act
        import asyncio

        await asyncio.gather(
            added_handler.handle(events[0]),
            added_handler.handle(events[1]),
            viewed_handler.handle(events[2]),
            removed_handler.handle(events[3]),
        )

        # Assert
        # Should have processed all events
        assert mock_analytics_repository.record_bookmark_activity.call_count == 4
        assert mock_analytics_repository.update_user_engagement_metrics.call_count == 3
        assert (
            mock_analytics_repository.increment_question_bookmark_count.call_count == 2
        )
        assert (
            mock_analytics_repository.decrement_question_bookmark_count.call_count == 1
        )

    @pytest.mark.asyncio
    async def test_event_handler_error_isolation(
        self,
        added_handler,
        removed_handler,
        mock_analytics_repository,
    ):
        """Test that event handler errors are isolated."""
        # Arrange
        # Make one handler fail
        mock_analytics_repository.record_bookmark_activity.side_effect = [
            None,  # First call succeeds
            Exception("Handler error"),  # Second call fails
        ]

        added_event = BookmarkAddedEvent(
            user_id=100, question_id=42, bookmark_id=1, notes="Test"
        )
        removed_event = BookmarkRemovedEvent(user_id=100, question_id=42, bookmark_id=1)

        # Act
        await added_handler.handle(added_event)  # Should succeed

        # Should not raise exception
        try:
            await removed_handler.handle(
                removed_event
            )  # Should handle error gracefully
        except Exception as e:
            pytest.fail(f"Event handler should not raise exception: {e}")

        # Assert
        assert mock_analytics_repository.record_bookmark_activity.call_count == 2

    @pytest.mark.asyncio
    async def test_event_handler_performance(
        self,
        added_handler,
        mock_analytics_repository,
    ):
        """Test event handler performance with many events."""
        # Arrange
        events = [
            BookmarkAddedEvent(
                user_id=100, question_id=40 + i, bookmark_id=i, notes=f"Bookmark {i}"
            )
            for i in range(100)
        ]

        # Act
        import asyncio
        import time

        start_time = time.time()
        await asyncio.gather(*[added_handler.handle(event) for event in events])
        end_time = time.time()

        # Assert
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should process 100 events in under 1 second
        assert mock_analytics_repository.record_bookmark_activity.call_count == 100
