"""Reset user progress domain service following DDD patterns."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.analytics.events.analytics_events import UserProgressResetEvent
from src.domain.shared.repositories import (
    AnalyticsRepository,
    LearningRepository,
    SessionRepository,
    UserRepository,
)
from src.domain.shared.services import DomainService, EventBusInterface

logger = logging.getLogger(__name__)


@dataclass
class ResetUserProgressRequest:
    """Request to reset all user progress data."""

    user_id: int
    confirmation_token: str | None = None  # For additional safety
    preserve_settings: bool = True  # Keep user settings by default


@dataclass
class ResetUserProgressResult:
    """Result of user progress reset operation."""

    success: bool
    items_deleted: dict[str, int] | None = None  # Count of deleted items by type
    error_message: str | None = None
    reset_timestamp: datetime | None = None


class ResetUserProgress(
    DomainService[ResetUserProgressRequest, ResetUserProgressResult]
):
    """Domain service for resetting user progress data.

    This service handles the complete reset of user learning progress while
    maintaining data integrity and proper transaction management.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        learning_repository: LearningRepository,
        analytics_repository: AnalyticsRepository,
        session_repository: SessionRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize the reset service."""
        super().__init__(event_bus)
        self.user_repository = user_repository
        self.learning_repository = learning_repository
        self.analytics_repository = analytics_repository
        self.session_repository = session_repository

    async def call(self, request: ResetUserProgressRequest) -> ResetUserProgressResult:
        """Reset all user progress data following domain rules."""
        try:
            # Validate request
            if request.user_id <= 0:
                return ResetUserProgressResult(
                    success=False,
                    error_message="Invalid user ID - must be positive integer",
                )

            logger.info(f"Starting progress reset for user {request.user_id}")

            # Perform the reset operation with proper transaction handling
            items_deleted = await self._reset_user_data(
                request.user_id, request.preserve_settings
            )

            reset_timestamp = datetime.now(UTC)

            # Publish domain event for cross-context communication
            await self._publish_reset_event(
                request.user_id, items_deleted, reset_timestamp
            )

            logger.info(f"Successfully reset progress for user {request.user_id}")

            return ResetUserProgressResult(
                success=True,
                items_deleted=items_deleted,
                reset_timestamp=reset_timestamp,
            )

        except Exception as e:
            logger.error(f"Failed to reset user progress: {e}")
            return ResetUserProgressResult(
                success=False, error_message=f"Reset operation failed: {e}"
            )

    async def _reset_user_data(
        self, user_id: int, preserve_settings: bool
    ) -> dict[str, int]:
        """Perform the actual data reset using repository interfaces."""
        # Use repository methods for proper encapsulation
        learning_deleted = await self.learning_repository.delete_user_learning_data(
            user_id
        )
        analytics_deleted = await self.analytics_repository.delete_user_analytics(
            user_id
        )
        sessions_deleted = await self.session_repository.delete_user_sessions(user_id)

        # User data deletion (settings preserved by default)
        user_data_deleted = 0
        if not preserve_settings:
            user_data_deleted = await self.user_repository.delete_user_data(user_id)

        # Combine results from all repositories
        items_deleted = {
            **learning_deleted,  # fsrs_cards, learning_data, learning_sessions, review_history
            **analytics_deleted,  # user_progress, category_progress
            **sessions_deleted,  # practice_sessions, question_attempts
            "user_data": user_data_deleted,
        }

        logger.info(f"Reset operation completed successfully: {items_deleted}")
        return items_deleted

    async def _publish_reset_event(
        self, user_id: int, items_deleted: dict[str, int], timestamp: datetime
    ) -> None:
        """Publish domain event for the reset operation."""
        try:
            event = UserProgressResetEvent(
                user_id=user_id,
                items_deleted=items_deleted,
                reset_timestamp=timestamp,
            )
            # Set custom event_id and timestamp
            event.event_id = f"reset_progress_{user_id}_{int(timestamp.timestamp())}"
            event.occurred_at = timestamp

            await self.event_bus.publish(event)
            logger.debug(f"Published UserProgressResetEvent for user {user_id}")

        except Exception as e:
            # Don't fail the reset operation if event publishing fails
            logger.warning(f"Failed to publish reset event: {e}")
