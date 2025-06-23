"""Tests for session repository fixes and progress tracking."""

from unittest.mock import Mock

import pytest

from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.repositories.session_repository import (
    SQLAlchemySessionRepository,
)


class TestSessionRepositoryFixes:
    """Test the fixes for session repository progress tracking."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def session_repository(self, mock_db_manager):
        """Create a session repository with mock database manager."""
        return SQLAlchemySessionRepository(mock_db_manager)

    @pytest.mark.asyncio
    async def test_get_session_statistics_implementation(
        self, session_repository, mock_db_manager
    ):
        """Test that get_session_statistics is now implemented and calls database manager."""
        # Arrange
        expected_stats = {
            "total_sessions": 5,
            "avg_duration": 180.5,
            "total_time": 902.5,
            "total_questions": 25,
            "total_correct": 20,
        }
        mock_db_manager.get_session_statistics.return_value = expected_stats

        # Act
        result = await session_repository.get_session_statistics(user_id=1)

        # Assert
        mock_db_manager.get_session_statistics.assert_called_once_with(1)
        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_get_session_statistics_with_different_user_id(
        self, session_repository, mock_db_manager
    ):
        """Test that get_session_statistics works with different user IDs."""
        # Arrange
        user_id = 42
        expected_stats = {"total_questions": 10, "total_correct": 8}
        mock_db_manager.get_session_statistics.return_value = expected_stats

        # Act
        result = await session_repository.get_session_statistics(user_id=user_id)

        # Assert
        mock_db_manager.get_session_statistics.assert_called_once_with(user_id)
        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_create_session_passes_correct_parameters(
        self, session_repository, mock_db_manager
    ):
        """Test that create_session passes correct parameters to database manager."""
        # Arrange
        mock_db_manager.create_session.return_value = 123
        user_id = 1
        session_type = "sequential"
        configuration = {"mode": "sequential"}

        # Act
        result = await session_repository.create_session(
            user_id=user_id, session_type=session_type, configuration=configuration
        )

        # Assert
        mock_db_manager.create_session.assert_called_once_with(session_type, user_id)
        assert result == 123

    @pytest.mark.asyncio
    async def test_end_session_passes_correct_parameters(
        self, session_repository, mock_db_manager
    ):
        """Test that end_session passes correct parameters to database manager."""
        # Arrange
        from datetime import UTC, datetime

        session_id = 123
        end_time = datetime.now(UTC)
        summary = {"questions_answered": 5, "correct": 4}

        # Act
        await session_repository.end_session(
            session_id=session_id, end_time=end_time, summary=summary
        )

        # Assert
        mock_db_manager.end_session.assert_called_once_with(session_id)
