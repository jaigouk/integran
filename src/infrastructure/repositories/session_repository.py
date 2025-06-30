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
        from datetime import UTC, datetime

        from src.domain.learning.models.learning_models import LearningSession
        from src.infrastructure.database.models import SessionDB

        # Create both session records - let each use auto-generated IDs
        with self.db_manager.get_session() as session:
            # First create the LearningSession to get an auto-generated ID
            learning_session = LearningSession(
                user_id=user_id,
                start_time=datetime.now(UTC).timestamp(),
                session_type=session_type,
                max_reviews=configuration.get("limit", 50),
            )
            session.add(learning_session)
            session.flush()  # Get the ID without committing
            learning_session_id = int(learning_session.session_id)

            # Create the SessionDB record with its own auto-generated ID for analytics
            session_record = SessionDB(
                # Don't specify id - let it auto-generate to avoid conflicts
                user_id=user_id,
                started_at=datetime.now(UTC),
                completed_at=None,
                duration_seconds=0,
                total_questions=0,
                correct_answers=0,
                incorrect_answers=0,
                practice_mode=session_type,
                is_completed=False,
            )
            session.add(session_record)
            session.commit()

            return learning_session_id

    async def end_session(
        self,
        session_id: int,
        end_time: datetime,
        summary: dict[str, Any],
    ) -> None:
        """End a session with summary data."""
        from src.infrastructure.database.models import SessionDB

        # Update session in the sessions table
        with self.db_manager.get_session() as session:
            session_record = session.get(SessionDB, session_id)
            if session_record:
                session_record.completed_at = end_time
                session_record.is_completed = True

                # Update session stats from summary
                if summary:
                    session_record.total_questions = summary.get("total_questions", 0)
                    session_record.correct_answers = summary.get("correct_answers", 0)
                    session_record.incorrect_answers = summary.get(
                        "incorrect_answers", 0
                    )

                    # Calculate duration from start to end time
                    if session_record.started_at:
                        duration = end_time - session_record.started_at
                        session_record.duration_seconds = int(duration.total_seconds())

                session.commit()

    async def update_session_progress(
        self,
        session_id: int,
        total_questions: int,
        correct_answers: int,
        incorrect_answers: int,
    ) -> None:
        """Update session progress during practice."""
        from src.infrastructure.database.models import SessionDB

        with self.db_manager.get_session() as session:
            session_record = session.get(SessionDB, session_id)
            if session_record:
                session_record.total_questions = total_questions
                session_record.correct_answers = correct_answers
                session_record.incorrect_answers = incorrect_answers
                session.commit()

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
                # First get question attempt IDs for this user's sessions
                question_attempt_ids = [
                    result[0]
                    for result in session.query(QuestionAttempt.id)
                    .join(PracticeSession)
                    .filter(PracticeSession.user_id == user_id)
                    .all()
                ]
                # Delete question attempts by IDs
                if question_attempt_ids:
                    session.query(QuestionAttempt).filter(
                        QuestionAttempt.id.in_(question_attempt_ids)
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

    async def get_session_by_id(self, session_id: int) -> dict[str, Any] | None:
        """Get session data by session ID."""

        def _get_session_by_id() -> dict[str, Any] | None:
            with self.db_manager.get_session() as session:
                from src.domain.content.models.question_models import PracticeSession

                practice_session = (
                    session.query(PracticeSession).filter_by(id=session_id).first()
                )

                if not practice_session:
                    return None

                return {
                    "session_id": practice_session.id,
                    "user_id": practice_session.user_id,
                    "mode": practice_session.mode,
                    "status": practice_session.status,
                    "started_at": practice_session.started_at,
                    "ended_at": practice_session.ended_at,
                    "total_questions": practice_session.total_questions,
                    "correct_answers": practice_session.correct_answers,
                    "new_cards_count": practice_session.new_cards_count,
                    "review_cards_count": practice_session.review_cards_count,
                    "total_pause_duration": practice_session.total_pause_duration,
                }

        return await self._run_in_executor(_get_session_by_id)
