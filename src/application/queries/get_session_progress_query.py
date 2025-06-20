"""Query for getting learning session progress - thin query handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.queries import Query, QueryHandler, QueryResult
from src.domain.shared.repositories import SessionRepository


@dataclass
class GetSessionProgressQuery(Query):
    """Query to get current session progress."""

    session_id: int

    def validate(self) -> bool:
        return self.session_id > 0


@dataclass
class SessionProgressData:
    """Session progress data."""

    total_questions: int = 0
    questions_answered: int = 0
    correct_answers: int = 0
    current_streak: int = 0


@dataclass
class GetSessionProgressResult(QueryResult):
    """Result of getting session progress."""

    success: bool = False
    error_message: str | None = None
    progress: SessionProgressData | None = None

    def get_result_data(self) -> dict[str, Any]:
        if self.progress:
            return {
                "total": self.progress.total_questions,
                "answered": self.progress.questions_answered,
                "correct": self.progress.correct_answers,
                "streak": self.progress.current_streak,
            }
        return {}


class GetSessionProgressQueryHandler(
    QueryHandler[GetSessionProgressQuery, GetSessionProgressResult]
):
    """Handler for getting session progress using repository pattern."""

    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    async def handle(self, query: GetSessionProgressQuery) -> GetSessionProgressResult:  # noqa: ARG002
        """Handle get session progress query."""
        try:
            # Use repository to get session progress
            # For now, use default user_id=1 since this is a single-user app
            # TODO: Track actual session-specific progress vs user-level progress
            # Note: query.session_id would be used for session-specific tracking
            session_stats = await self.session_repository.get_session_statistics(
                user_id=1
            )

            if session_stats:
                progress = SessionProgressData(
                    total_questions=session_stats.get("total_questions", 0),
                    questions_answered=session_stats.get(
                        "questions_answered", session_stats.get("total_questions", 0)
                    ),
                    correct_answers=session_stats.get(
                        "correct_answers", session_stats.get("total_correct", 0)
                    ),
                    current_streak=session_stats.get("current_streak", 0),
                )
                return GetSessionProgressResult(success=True, progress=progress)
            else:
                # Return default progress if no session found
                progress = SessionProgressData(
                    total_questions=20,
                    questions_answered=0,
                    correct_answers=0,
                    current_streak=0,
                )
                return GetSessionProgressResult(success=True, progress=progress)
        except Exception as e:
            return GetSessionProgressResult(
                success=False, error_message=f"Failed to get session progress: {str(e)}"
            )
