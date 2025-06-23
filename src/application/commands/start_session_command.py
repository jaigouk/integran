"""Command for starting a new learning session - thin coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.commands import Command, CommandHandler, CommandResult
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
    SessionConfig,
    SessionType,
    StartSessionRequest,
)


@dataclass
class StartSessionCommand(Command):
    """Command to start a new learning session."""

    session_type: str
    max_questions: int = 20
    user_id: int = 1

    def validate(self) -> bool:
        return self.session_type in ["review", "learn", "random", "quiz"]


@dataclass
class StartSessionResult(CommandResult):
    """Result of starting a session."""

    success: bool = False
    error_message: str | None = None
    session_id: int | None = None
    total_questions: int = 0

    def get_result_data(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "total_questions": self.total_questions}


class StartSessionCommandHandler(
    CommandHandler[StartSessionCommand, StartSessionResult]
):
    """Handler for starting learning sessions - thin coordinator only."""

    def __init__(self, learning_service: CompleteLearningSession):
        self.learning_service = learning_service

    async def handle(self, command: StartSessionCommand) -> StartSessionResult:
        """Validate input and delegate to domain service."""
        if not command.validate():
            return StartSessionResult(error_message="Invalid session type")
        # Map string to enum
        session_type_map = {
            "review": SessionType.REVIEW,
            "learn": SessionType.LEARN,
            "quiz": SessionType.QUIZ,
            "random": SessionType.REVIEW,  # Map random to review
        }
        config = SessionConfig(
            session_type=session_type_map[command.session_type],
            max_reviews=command.max_questions,
        )
        request = StartSessionRequest(config=config, user_id=command.user_id)
        result = await self.learning_service.call(request)
        return StartSessionResult(
            success=result.success,
            session_id=result.session_id,
            total_questions=len(result.questions) if result.questions else 0,
            error_message=result.error_message,
        )
