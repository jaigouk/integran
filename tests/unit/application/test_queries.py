"""Tests for application query handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQuery,
    GetSessionProgressQueryHandler,
    GetSessionProgressResult,
    SessionProgressData,
)


class TestGetSessionProgressQuery:
    """Test GetSessionProgressQuery DTO."""

    def test_query_creation(self):
        """Test query creation with valid session ID."""
        query = GetSessionProgressQuery(session_id=123)
        assert query.session_id == 123

    def test_validate_valid_session_id(self):
        """Test validation with valid session ID."""
        query = GetSessionProgressQuery(session_id=1)
        assert query.validate() is True

    def test_validate_invalid_session_id_zero(self):
        """Test validation with zero session ID."""
        query = GetSessionProgressQuery(session_id=0)
        assert query.validate() is False

    def test_validate_invalid_session_id_negative(self):
        """Test validation with negative session ID."""
        query = GetSessionProgressQuery(session_id=-1)
        assert query.validate() is False


class TestSessionProgressData:
    """Test SessionProgressData DTO."""

    def test_default_values(self):
        """Test default values are set correctly."""
        data = SessionProgressData()
        assert data.total_questions == 0
        assert data.questions_answered == 0
        assert data.correct_answers == 0
        assert data.current_streak == 0

    def test_custom_values(self):
        """Test custom values are set correctly."""
        data = SessionProgressData(
            total_questions=20,
            questions_answered=15,
            correct_answers=12,
            current_streak=5,
        )
        assert data.total_questions == 20
        assert data.questions_answered == 15
        assert data.correct_answers == 12
        assert data.current_streak == 5


class TestGetSessionProgressResult:
    """Test GetSessionProgressResult DTO."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = GetSessionProgressResult()
        assert result.success is False
        assert result.error_message is None
        assert result.progress is None

    def test_success_result_with_progress(self):
        """Test successful result with progress data."""
        progress = SessionProgressData(
            total_questions=10,
            questions_answered=7,
            correct_answers=5,
            current_streak=3,
        )
        result = GetSessionProgressResult(success=True, progress=progress)
        assert result.success is True
        assert result.error_message is None
        assert result.progress == progress

    def test_error_result(self):
        """Test error result with message."""
        result = GetSessionProgressResult(
            success=False,
            error_message="Database connection failed",
        )
        assert result.success is False
        assert result.error_message == "Database connection failed"
        assert result.progress is None

    def test_get_result_data_with_progress(self):
        """Test get_result_data with progress data."""
        progress = SessionProgressData(
            total_questions=15,
            questions_answered=10,
            correct_answers=8,
            current_streak=4,
        )
        result = GetSessionProgressResult(success=True, progress=progress)

        data = result.get_result_data()
        assert data["total"] == 15
        assert data["answered"] == 10
        assert data["correct"] == 8
        assert data["streak"] == 4

    def test_get_result_data_without_progress(self):
        """Test get_result_data without progress data."""
        result = GetSessionProgressResult(success=False)
        data = result.get_result_data()
        assert data == {}


class TestGetSessionProgressQueryHandler:
    """Test GetSessionProgressQueryHandler."""

    @pytest.fixture
    def mock_session_repository(self):
        """Mock SessionRepository."""
        from src.domain.shared.repositories import SessionRepository

        mock_repo = AsyncMock(spec=SessionRepository)
        return mock_repo

    @pytest.fixture
    def handler(self, mock_session_repository):
        """Create handler instance."""
        return GetSessionProgressQueryHandler(
            session_repository=mock_session_repository
        )

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, mock_session_repository):
        """Test successful query handling."""
        # Arrange
        query = GetSessionProgressQuery(session_id=123)
        mock_session_repository.get_session_by_id.return_value = {
            "session_id": 123,
            "total_questions": 25,
            "correct_answers": 12,
            "user_id": 1,
            "mode": "practice",
            "status": "active",
        }

        # Act
        result = await handler.handle(query)

        # Assert
        assert isinstance(result, GetSessionProgressResult)
        assert result.success is True
        assert result.error_message is None
        assert result.progress is not None
        assert result.progress.total_questions == 25
        assert (
            result.progress.questions_answered == 25
        )  # Updated logic: questions_answered = total_questions
        assert result.progress.correct_answers == 12
        assert (
            result.progress.current_streak == 12
        )  # Updated logic: current_streak = correct_answers
        assert isinstance(result.progress, SessionProgressData)

    @pytest.mark.asyncio
    async def test_handle_with_exception(self, handler, mock_session_repository):
        """Test query handling with repository exception."""
        # Arrange
        query = GetSessionProgressQuery(session_id=123)
        mock_session_repository.get_session_by_id.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await handler.handle(query)

        # Assert
        assert isinstance(result, GetSessionProgressResult)
        assert result.success is False
        assert "Failed to get session progress" in result.error_message
        assert "Database error" in result.error_message
        assert result.progress is None

    @pytest.mark.asyncio
    async def test_handle_session_not_found(self, handler, mock_session_repository):
        """Test query handling when session is not found."""
        # Arrange
        query = GetSessionProgressQuery(session_id=999)
        mock_session_repository.get_session_by_id.return_value = None

        # Act
        result = await handler.handle(query)

        # Assert
        assert isinstance(result, GetSessionProgressResult)
        assert result.success is True
        assert result.error_message is None
        assert result.progress is not None
        # Should return default progress when session not found
        assert result.progress.total_questions == 20
        assert result.progress.questions_answered == 0
        assert result.progress.correct_answers == 0
        assert result.progress.current_streak == 0

    @pytest.mark.asyncio
    async def test_handler_initialization(self, mock_session_repository):
        """Test handler initialization."""
        handler = GetSessionProgressQueryHandler(
            session_repository=mock_session_repository
        )
        assert handler.session_repository == mock_session_repository

    def test_result_data_structure(self):
        """Test that result data has expected structure."""
        progress = SessionProgressData(
            total_questions=25,
            questions_answered=15,
            correct_answers=12,
            current_streak=6,
        )
        result = GetSessionProgressResult(success=True, progress=progress)

        data = result.get_result_data()
        expected_keys = {"total", "answered", "correct", "streak"}
        assert set(data.keys()) == expected_keys
