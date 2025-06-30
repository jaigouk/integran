"""Command for saving user settings following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.shared.repositories import UserRepository
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import (
    SaveUserSettingsRequest,
    UserSettings,
)
from src.domain.user.services.save_user_settings import SaveUserSettings

logger = logging.getLogger(__name__)


@dataclass
class SaveUserSettingsCommand:
    """Command to save user settings."""

    user_settings: UserSettings  # Changed to match domain expectation


@dataclass
class SaveUserSettingsCommandResult:
    """Result of save user settings command."""

    success: bool
    user_settings: UserSettings | None = None
    error_message: str | None = None


class SaveUserSettingsCommandHandler:
    """Command handler for saving user settings using domain service."""

    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        """Initialize with user repository and event bus."""
        self.save_user_settings_service = SaveUserSettings(event_bus, user_repository)

    async def handle(
        self, command: SaveUserSettingsCommand
    ) -> SaveUserSettingsCommandResult:
        """Handle save user settings command using domain service."""
        try:
            # Create domain service request
            request = SaveUserSettingsRequest(
                user_settings=command.user_settings,
            )

            # Call domain service
            result = await self.save_user_settings_service.call(request)

            # Convert domain result to command result
            return SaveUserSettingsCommandResult(
                success=result.success,
                user_settings=result.user_settings,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error in SaveUserSettingsCommandHandler: {e}")
            return SaveUserSettingsCommandResult(
                success=False,
                error_message=f"Failed to save user settings: {e}",
            )
