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

    async def handle(self, query: GetSessionProgressQuery) -> GetSessionProgressResult:
        """Handle get session progress query."""
        try:
            # Get session-specific data using the session_id from the query
            session_data = await self.session_repository.get_session_by_id(
                query.session_id
            )

            if session_data:
                # Calculate progress based on session-specific data
                total_questions = session_data.get("total_questions", 0)
                correct_answers = session_data.get("correct_answers", 0)

                # For current streak, we need to check recent attempts in this session
                # For now, we'll use a simple calculation: consecutive correct answers
                current_streak = correct_answers if total_questions > 0 else 0

                progress = SessionProgressData(
                    total_questions=total_questions,
                    questions_answered=total_questions,  # Session tracks total questions attempted
                    correct_answers=correct_answers,
                    current_streak=current_streak,
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
