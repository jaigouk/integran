"""Tests for GetQuestionsByModeQuery following CQRS patterns."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.queries.get_questions_by_mode_query import (
    GetQuestionsByModeQuery,
    GetQuestionsByModeQueryHandler,
)
from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository
from src.domain.user.models.user_models import FederalState, UserPreferences


class TestGetQuestionsByModeQuery:
    """Test GetQuestionsByModeQuery CQRS compliance."""

    def test_query_constructor_signature(self):
        """Test that query constructor only accepts query parameters, not dependencies."""
        # Arrange
        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)

        # Act - This should work without any repository dependencies
        query = GetQuestionsByModeQuery(
            practice_mode="images",
            user_preferences=user_preferences,
            user_id=1,
            limit=1,
            category_index=0,
            question_indices=None,
            last_question_id=0,
        )

        # Assert - Verify all fields are set correctly
        assert query.practice_mode == "images"
        assert query.user_preferences == user_preferences
        assert query.user_id == 1
        assert query.limit == 1
        assert query.category_index == 0
        assert query.question_indices is None
        assert query.last_question_id == 0

    def test_query_constructor_rejects_repository_dependency(self):
        """Test that query constructor rejects repository dependencies (CQRS compliance)."""
        # Arrange
        mock_repository = Mock()
        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)

        # Act & Assert - This should fail because queries shouldn't have dependencies
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            GetQuestionsByModeQuery(
                practice_mode="images",
                question_repository=mock_repository,  # This should be rejected
                user_preferences=user_preferences,
                user_id=1,
            )


class TestGetQuestionsByModeQueryHandler:
    """Test GetQuestionsByModeQueryHandler following CQRS patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = AsyncMock(spec=QuestionRepository)
        self.handler = GetQuestionsByModeQueryHandler(
            question_repository=self.mock_repository
        )

    @pytest.mark.asyncio
    async def test_handler_requires_repository_dependency(self):
        """Test that handler requires repository dependency (CQRS compliance)."""
        # Arrange
        mock_repository = AsyncMock(spec=QuestionRepository)

        # Act - Handler should require repository dependency
        handler = GetQuestionsByModeQueryHandler(question_repository=mock_repository)

        # Assert
        assert handler.question_repository == mock_repository

    @pytest.mark.asyncio
    async def test_images_mode_query_success(self):
        """Test successful handling of images mode query with FSRS filtering."""
        # Arrange
        mock_question = Mock(spec=Question)
        mock_question.id = 1
        mock_question.is_image_question = True
        # FSRS filtering is enabled by default, so we need to mock get_questions_for_active_learning
        self.mock_repository.get_questions_for_active_learning.return_value = [
            mock_question
        ]
        self.mock_repository.get_questions_by_state.return_value = [mock_question]

        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)
        query = GetQuestionsByModeQuery(
            practice_mode="images",
            user_preferences=user_preferences,
            user_id=1,
            limit=1,
            last_question_id=0,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is True
        assert result.question == mock_question
        assert result.next_state is not None
        assert result.error_message is None
        # With FSRS enabled by default, it should use get_questions_for_active_learning
        self.mock_repository.get_questions_for_active_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_images_mode_query_no_questions(self):
        """Test handling of images mode query when no questions available."""
        # Arrange
        # With FSRS enabled by default, it will call get_questions_for_active_learning but return empty list
        self.mock_repository.get_questions_for_active_learning.return_value = []

        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)
        query = GetQuestionsByModeQuery(
            practice_mode="images",
            user_preferences=user_preferences,
            user_id=1,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is False
        assert result.question is None
        assert (
            result.error_message
            == "No image questions available for practice with FSRS filtering"
        )
        self.mock_repository.get_questions_for_active_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_federal_state_filtering_applied(self):
        """Test that federal state filtering is properly applied."""
        # Arrange
        mock_question = Mock(spec=Question)
        mock_question.id = 1
        mock_question.is_image_question = True
        # With FSRS enabled by default, mock get_questions_for_active_learning
        self.mock_repository.get_questions_for_active_learning.return_value = [
            mock_question
        ]

        # Mock federal state filtering
        self.mock_repository.get_questions_by_state.return_value = [mock_question]

        user_preferences = UserPreferences(federal_state=FederalState.BAYERN)
        query = GetQuestionsByModeQuery(
            practice_mode="images",
            user_preferences=user_preferences,
            user_id=1,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is True
        # Verify federal state filtering was called
        self.mock_repository.get_questions_by_state.assert_called()

    @pytest.mark.asyncio
    async def test_random_mode_query_success(self):
        """Test successful handling of random mode query with FSRS filtering."""
        # Arrange
        mock_question = Mock(spec=Question)
        mock_question.id = 1
        # With FSRS enabled by default, random mode uses get_questions_for_active_learning
        self.mock_repository.get_questions_for_active_learning.return_value = [
            mock_question
        ]
        self.mock_repository.get_questions_by_state.return_value = [mock_question]

        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)
        query = GetQuestionsByModeQuery(
            practice_mode="random",
            user_preferences=user_preferences,
            user_id=1,
            category_index=0,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is True
        assert result.question == mock_question
        # Random mode with FSRS doesn't maintain state like category_index
        assert result.error_message is None
        # With FSRS enabled by default, it should use get_questions_for_active_learning
        self.mock_repository.get_questions_for_active_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_sequential_mode_query_success(self):
        """Test successful handling of sequential mode query."""
        # Arrange
        mock_question = Mock(spec=Question)
        mock_question.id = 1
        self.mock_repository.get_questions_for_active_learning.return_value = [
            mock_question
        ]
        self.mock_repository.get_questions_by_state.return_value = [mock_question]

        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)
        query = GetQuestionsByModeQuery(
            practice_mode="sequential",
            user_preferences=user_preferences,
            user_id=1,
            last_question_id=0,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is True
        assert result.question == mock_question
        assert result.next_state is not None
        assert "last_question_id" in result.next_state
        self.mock_repository.get_questions_for_active_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_handler_error_handling(self):
        """Test that handler properly handles repository errors."""
        # Arrange
        # With FSRS enabled by default, mock the FSRS method to raise exception
        self.mock_repository.get_questions_for_active_learning.side_effect = Exception(
            "Database error"
        )

        user_preferences = UserPreferences(federal_state=FederalState.GENERAL)
        query = GetQuestionsByModeQuery(
            practice_mode="images",
            user_preferences=user_preferences,
            user_id=1,
        )

        # Act
        result = await self.handler.handle(query)

        # Assert
        assert result.success is False
        assert result.question is None
        assert "Failed to get questions" in result.error_message
        assert "Database error" in result.error_message
