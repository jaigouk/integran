"""Command for pausing or resuming a learning session - thin coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.commands import Command, CommandHandler, CommandResult
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
    PauseSessionRequest,
)


@dataclass
class PauseSessionCommand(Command):
    """Command to pause or resume a learning session."""

    session_id: int
    is_pause: bool  # True for pause, False for resume
    user_id: int = 1

    def validate(self) -> bool:
        return self.session_id > 0


@dataclass
class PauseSessionResult(CommandResult):
    """Result of pausing or resuming a session."""

    success: bool = False
    error_message: str | None = None
    session_id: int | None = None
    is_paused: bool = False
    pause_duration_seconds: int | None = None

    def get_result_data(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "is_paused": self.is_paused,
            "pause_duration_seconds": self.pause_duration_seconds,
        }


class PauseSessionCommandHandler(
    CommandHandler[PauseSessionCommand, PauseSessionResult]
):
    """Handler for pausing/resuming learning sessions - thin coordinator only."""

    def __init__(self, learning_service: CompleteLearningSession):
        self.learning_service = learning_service

    async def handle(self, command: PauseSessionCommand) -> PauseSessionResult:
        """Validate input and delegate to domain service."""
        if not command.validate():
            return PauseSessionResult(error_message="Invalid session ID")

        request = PauseSessionRequest(
            session_id=command.session_id,
            is_pause=command.is_pause,
            user_id=command.user_id,
        )

        result = await self.learning_service.call(request)

        return PauseSessionResult(
            success=result.success,
            session_id=result.session_id,
            is_paused=result.is_paused,
            pause_duration_seconds=result.pause_duration_seconds,
            error_message=result.error_message,
        )
