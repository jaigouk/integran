"""Concrete implementation of SessionRepository interface."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.domain.shared.repositories import SessionRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def create_session(
        self,
        user_id: int,
        session_type: str,
        configuration: dict[str, Any],  # noqa: ARG002
    ) -> int:
        """Create a new session and return session ID."""
        # DatabaseManager create_session now takes user_id parameter
        return self.db_manager.create_session(session_type, user_id)

    async def end_session(
        self,
        session_id: int,
        end_time: datetime,  # noqa: ARG002
        summary: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """End a session with summary data."""
        # DatabaseManager end_session only takes session_id
        self.db_manager.end_session(session_id)

    async def get_session_statistics(self, user_id: int) -> dict[str, Any]:
        """Get session statistics for a user."""
        return self.db_manager.get_session_statistics(user_id)

    async def delete_user_sessions(self, user_id: int) -> dict[str, int]:
        """Delete all sessions for a user and return counts."""

        def _delete_user_sessions() -> dict[str, int]:
            with self.db_manager.get_session() as session:
                from src.domain.content.models.question_models import (
                    PracticeSession,
                    QuestionAttempt,
                )

                # Count items before deletion
                practice_sessions_count = (
                    session.query(PracticeSession).filter_by(user_id=user_id).count()
                )

                # Count attempts in sessions belonging to this user
                question_attempts_count = (
                    session.query(QuestionAttempt)
                    .join(PracticeSession)
                    .filter(PracticeSession.user_id == user_id)
                    .count()
                )

                # Delete in proper order (respecting foreign keys)
                session.query(QuestionAttempt).join(PracticeSession).filter(
                    PracticeSession.user_id == user_id
                ).delete(synchronize_session=False)
                session.query(PracticeSession).filter_by(user_id=user_id).delete()

                session.commit()

                return {
                    "practice_sessions": practice_sessions_count,
                    "question_attempts": question_attempts_count,
                }

        return await self._run_in_executor(_delete_user_sessions)

    async def update_session_status(self, session_id: int, status: str) -> None:
        """Update the status of a session."""
        # Now implemented with proper session status tracking in DatabaseManager
        self.db_manager.update_session_status(session_id, status)

    async def get_pause_duration(self, session_id: int) -> int | None:
        """Get total pause duration for a session in seconds."""
        # Now implemented with proper pause duration tracking in DatabaseManager
        return self.db_manager.get_session_pause_duration(session_id)

    async def start_pause(self, session_id: int) -> None:
        """Start pause tracking for a session."""
        self.db_manager.start_session_pause(session_id)

    async def end_pause(self, session_id: int) -> int:
        """End pause tracking and return pause duration in seconds."""
        return self.db_manager.end_session_pause(session_id)

    async def update_card_counts(
        self, session_id: int, new_cards: int, review_cards: int
    ) -> None:
        """Update new and review card counts for a session."""
        self.db_manager.update_session_card_counts(session_id, new_cards, review_cards)
