"""Command for toggling developer mode following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.shared.repositories import UserRepository
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import (
    ToggleDeveloperModeRequest,
    UserSettings,
)
from src.domain.user.services.toggle_developer_mode import ToggleDeveloperMode

logger = logging.getLogger(__name__)


@dataclass
class ToggleDeveloperModeCommand:
    """Command to toggle developer mode."""

    user_id: int
    enabled: bool
    confirmation_accepted: bool = False


@dataclass
class ToggleDeveloperModeCommandResult:
    """Result of toggle developer mode command."""

    success: bool
    user_settings: UserSettings | None = None
    warning_message: str | None = None
    error_message: str | None = None


class ToggleDeveloperModeCommandHandler:
    """Command handler for toggling developer mode using domain service."""

    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        """Initialize with user repository and event bus."""
        self.toggle_developer_mode_service = ToggleDeveloperMode(
            event_bus, user_repository
        )

    async def handle(
        self, command: ToggleDeveloperModeCommand
    ) -> ToggleDeveloperModeCommandResult:
        """Handle toggle developer mode command using domain service."""
        try:
            # Create domain service request
            request = ToggleDeveloperModeRequest(
                user_id=command.user_id,
                enable=command.enabled,  # Map 'enabled' to 'enable' for domain
            )

            # Call domain service
            result = await self.toggle_developer_mode_service.call(request)

            # Convert domain result to command result
            return ToggleDeveloperModeCommandResult(
                success=result.success,
                user_settings=result.user_settings,
                warning_message=result.warning_message,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error in ToggleDeveloperModeCommandHandler: {e}")
            return ToggleDeveloperModeCommandResult(
                success=False,
                error_message=f"Failed to toggle developer mode: {e}",
            )
