"""Query for loading user preferences following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.shared.repositories import UserRepository
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import (
    LoadUserSettingsRequest,
    UserSettings,
)
from src.domain.user.services.load_user_settings import LoadUserSettings

logger = logging.getLogger(__name__)


@dataclass
class LoadUserPreferencesQuery:
    """Query to load user preferences and settings."""

    user_repository: UserRepository
    event_bus: EventBusInterface
    user_id: int = 1

    async def handle(self) -> LoadUserPreferencesResult:
        """Handle the query to load user preferences."""
        try:
            logger.info(f"Loading user preferences for user {self.user_id}")

            # Initialize domain service
            load_user_settings_service = LoadUserSettings(
                event_bus=self.event_bus, user_repository=self.user_repository
            )

            # Create load user settings request
            request = LoadUserSettingsRequest(user_id=self.user_id)

            # Load user settings using domain service
            result = await load_user_settings_service.call(request)

            if result.success and result.user_settings:
                return LoadUserPreferencesResult(
                    success=True,
                    user_settings=result.user_settings,
                )
            else:
                return LoadUserPreferencesResult(
                    success=False,
                    error_message=result.error_message
                    or "Failed to load user preferences",
                )

        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
            return LoadUserPreferencesResult(
                success=False,
                error_message=f"Failed to load user preferences: {e}",
            )


@dataclass
class LoadUserPreferencesResult:
    """Result of loading user preferences."""

    success: bool
    user_settings: UserSettings | None = None
    error_message: str | None = None


# Legacy handler class - deprecated in favor of query.handle()
# Kept for backward compatibility during transition
class LoadUserPreferencesQueryHandler:
    """DEPRECATED: Handler for loading user preferences.

    Use LoadUserPreferencesQuery.handle() method instead.
    """

    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        """Initialize with user repository and event bus."""
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def handle(
        self, query: LoadUserPreferencesQuery
    ) -> LoadUserPreferencesResult:
        """Handle the query to load user preferences."""
        # Delegate to query's handle method for proper CQRS pattern
        query.user_repository = self.user_repository
        query.event_bus = self.event_bus
        return await query.handle()
