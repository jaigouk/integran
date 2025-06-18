"""Command for resetting user progress following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from src.domain.analytics.services.reset_user_progress import (
    ResetUserProgress,
    ResetUserProgressRequest,
)

logger = logging.getLogger(__name__)


@dataclass
class ResetUserProgressCommand:
    """Command to reset all user progress data."""

    user_id: int
    confirmation_token: str | None = None
    preserve_settings: bool = True


@dataclass
class ResetUserProgressCommandResult:
    """Result of reset user progress command."""

    success: bool
    items_deleted: dict[str, int] | None = None
    error_message: str | None = None
    reset_timestamp: datetime | None = None


class ResetUserProgressCommandHandler:
    """Handler for reset user progress command following CQRS pattern."""

    def __init__(self, reset_service: ResetUserProgress):
        """Initialize with reset domain service."""
        self.reset_service = reset_service

    async def handle(
        self, command: ResetUserProgressCommand
    ) -> ResetUserProgressCommandResult:
        """Handle the reset user progress command."""
        try:
            # Validate command
            if command.user_id <= 0:
                return ResetUserProgressCommandResult(
                    success=False, error_message="Invalid user ID provided"
                )

            logger.info(f"Processing reset command for user {command.user_id}")

            # Create domain service request
            request = ResetUserProgressRequest(
                user_id=command.user_id,
                confirmation_token=command.confirmation_token,
                preserve_settings=command.preserve_settings,
            )

            # Call domain service
            result = await self.reset_service.call(request)

            # Convert domain result to command result
            return ResetUserProgressCommandResult(
                success=result.success,
                items_deleted=result.items_deleted,
                error_message=result.error_message,
                reset_timestamp=result.reset_timestamp,
            )

        except Exception as e:
            logger.error(f"Error handling reset command: {e}")
            return ResetUserProgressCommandResult(
                success=False, error_message=f"Command handling failed: {e}"
            )
