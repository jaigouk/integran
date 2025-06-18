"""Concrete implementation of SessionRepository interface."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.shared.repositories import SessionRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def create_session(
        self,
        user_id: int,  # noqa: ARG002
        session_type: str,
        configuration: dict[str, Any],  # noqa: ARG002
    ) -> int:
        """Create a new session and return session ID."""
        # DatabaseManager create_session only takes mode parameter
        return self.db_manager.create_session(session_type)

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
        # NOTE: DatabaseManager doesn't have get_session_statistics method
        raise NotImplementedError(
            "get_session_statistics not implemented in DatabaseManager"
        )

    async def delete_user_sessions(self, user_id: int) -> dict[str, int]:
        """Delete all sessions for a user and return counts."""
        # NOTE: DatabaseManager doesn't have delete_user_sessions method
        raise NotImplementedError(
            "delete_user_sessions not implemented in DatabaseManager"
        )
