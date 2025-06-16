"""Query for getting learning session progress - thin query handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.queries import Query, QueryHandler, QueryResult
from src.infrastructure.database.database import DatabaseManager


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
    """Handler for getting session progress - direct DB query."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def handle(self, _query: GetSessionProgressQuery) -> GetSessionProgressResult:
        """Handle get session progress query."""
        try:
            # Direct database query for session progress
            # This is a placeholder - actual implementation would query session data
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
