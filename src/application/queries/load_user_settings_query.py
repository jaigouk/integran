"""Query for loading user settings following CQRS pattern."""

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
class LoadUserSettingsQuery:
    """Query to load user settings."""

    user_id: int = 1


@dataclass
class LoadUserSettingsQueryResult:
    """Result of loading user settings query."""

    success: bool
    user_settings: UserSettings | None = None
    is_first_time: bool = False
    error_message: str | None = None


class LoadUserSettingsQueryHandler:
    """Query handler for loading user settings using domain service."""

    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        """Initialize with user repository and event bus."""
        self.load_user_settings_service = LoadUserSettings(event_bus, user_repository)

    async def handle(self, query: LoadUserSettingsQuery) -> LoadUserSettingsQueryResult:
        """Handle load user settings query using domain service."""
        try:
            # Create domain service request
            request = LoadUserSettingsRequest(user_id=query.user_id)

            # Call domain service
            result = await self.load_user_settings_service.call(request)

            # Convert domain result to query result
            return LoadUserSettingsQueryResult(
                success=result.success,
                user_settings=result.user_settings,
                is_first_time=result.is_first_time,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error in LoadUserSettingsQueryHandler: {e}")
            return LoadUserSettingsQueryResult(
                success=False,
                error_message=f"Failed to load user settings: {e}",
            )
