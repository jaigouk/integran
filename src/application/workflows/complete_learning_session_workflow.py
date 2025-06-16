"""Thin workflow coordinator for learning sessions following CQRS and DDD patterns."""

from __future__ import annotations

from typing import Any

from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
    CompleteSessionRequest,
    SessionConfig,
    StartSessionRequest,
    SubmitAnswerRequest,
)
from src.domain.shared.models import FSRSRating


class SessionWorkflow:
    """Thin coordinator - delegates all operations to CompleteLearningSession domain service."""

    def __init__(self, complete_learning_session: CompleteLearningSession) -> None:
        self.complete_learning_session = complete_learning_session

    async def start_session(
        self, config: SessionConfig, user_id: int = 1
    ) -> dict[str, Any]:
        """Start session - validate input and delegate to domain service."""
        request = StartSessionRequest(config=config, user_id=user_id)
        result = await self.complete_learning_session.call(request)
        return {
            "session_id": result.session_id,
            "questions": result.questions,
            "success": result.success,
        }

    async def submit_answer(
        self,
        session_id: int,
        card_id: int,
        user_answer: str | None,
        response_time_ms: int,
        rating: FSRSRating | None = None,
    ) -> dict[str, Any]:
        """Submit answer - validate input and delegate to domain service."""
        request = SubmitAnswerRequest(
            session_id, card_id, user_answer, response_time_ms, rating
        )
        result = await self.complete_learning_session.call(request)
        return {
            "success": result.success,
            "is_correct": result.is_correct,
            "schedule_result": result.schedule_result,
            "progress": result.updated_progress,
        }

    async def complete_session(self, session_id: int) -> dict[str, Any]:
        """Complete session - validate input and delegate to domain service."""
        request = CompleteSessionRequest(session_id=session_id)
        result = await self.complete_learning_session.call(request)
        return {"success": result.success, "summary": result.session_summary}
