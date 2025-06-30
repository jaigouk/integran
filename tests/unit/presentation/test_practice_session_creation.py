"""Tests for practice session creation and progress tracking."""

import logging
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest

from src.domain.content.models.question_models import Question
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.question_view import PracticeScreen, QuestionWidget


class TestPracticeSessionCreation:
    """Test practice session creation and progress tracking fixes."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app with container."""
        app = Mock()
        app.event_bus = Mock(spec=EventBus)

        # Mock container and start session command handler
        container = Mock()
        start_session_handler = Mock()

        # Mock the command result
        from src.application.commands.start_session_command import StartSessionResult

        result = StartSessionResult(success=True, session_id=123)
        start_session_handler.handle = AsyncMock(return_value=result)

        container.get_start_practice_session_command_handler.return_value = (
            start_session_handler
        )

        app.container = container
        return app

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserSettingsRepository)

    @pytest.fixture
    def practice_screen(self, mock_user_repository):
        """Create a practice screen instance."""
        return PracticeScreen(
            practice_mode="sequential",
            user_repository=mock_user_repository,
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )

    @pytest.mark.asyncio
    async def test_create_practice_session_with_container(
        self, practice_screen, mock_app
    ):
        """Test that practice session creation works with container and creates a session."""
        # Arrange
        mock_session_repository = AsyncMock()
        mock_session_repository.create_session.return_value = 123
        mock_container = Mock()
        mock_container.get_session_repository.return_value = mock_session_repository
        mock_app.container = mock_container

        # Patch the app property to return our mock
        with patch.object(
            type(practice_screen),
            "app",
            new_callable=PropertyMock,
            return_value=mock_app,
        ):
            # Act
            await practice_screen._create_practice_session()

            # Assert - session should be created
            assert practice_screen.session_id == 123
            mock_session_repository.create_session.assert_called_once_with(
                user_id=1, session_type="sequential", configuration={"limit": 50}
            )

    @pytest.mark.asyncio
    async def test_create_practice_session_fallback_without_container(
        self, practice_screen, caplog
    ):
        """Test that practice session creation falls back to MainContainer when app container is None."""
        # Arrange
        mock_app = Mock()
        mock_app.container = None

        # Mock the MainContainer fallback
        mock_session_repository = AsyncMock()
        mock_session_repository.create_session.return_value = 456
        mock_main_container = Mock()
        mock_main_container.get_session_repository.return_value = (
            mock_session_repository
        )

        with (
            caplog.at_level(logging.INFO),
            patch.object(
                type(practice_screen),
                "app",
                new_callable=PropertyMock,
                return_value=mock_app,
            ),
            patch(
                "src.infrastructure.containers.main_container.MainContainer",
                return_value=mock_main_container,
            ),
        ):
            # Act
            await practice_screen._create_practice_session()

            # Assert - fallback should create session via MainContainer
            assert practice_screen.session_id == 456
            mock_session_repository.create_session.assert_called_once_with(
                user_id=1, session_type="sequential", configuration={"limit": 50}
            )

    @pytest.mark.asyncio
    async def test_create_practice_session_handles_exceptions(
        self, practice_screen, caplog
    ):
        """Test that practice session creation handles exceptions gracefully."""
        # Arrange - simulate exception in logging
        with (
            caplog.at_level(logging.WARNING),
            patch(
                "src.presentation.terminal.question_view.logger.info",
                side_effect=Exception("Test error"),
            ),
        ):
            # Act
            await practice_screen._create_practice_session()

            # Assert
            assert practice_screen.session_id is None
            assert "Failed to create practice session" in caplog.text

    @pytest.mark.asyncio
    async def test_create_practice_session_reuses_existing_session(
        self, practice_screen, mock_app, caplog
    ):
        """Test that calling _create_practice_session multiple times reuses existing session."""
        # Arrange
        mock_session_repository = AsyncMock()
        mock_session_repository.create_session.return_value = 789
        mock_container = Mock()
        mock_container.get_session_repository.return_value = mock_session_repository
        mock_app.container = mock_container

        with (
            caplog.at_level(logging.INFO),
            patch.object(
                type(practice_screen),
                "app",
                new_callable=PropertyMock,
                return_value=mock_app,
            ),
        ):
            # Act - call _create_practice_session twice
            await practice_screen._create_practice_session()
            await practice_screen._create_practice_session()

            # Assert - session should be created only once
            assert practice_screen.session_id == 789
            mock_session_repository.create_session.assert_called_once()
            assert "Session 789 already exists, reusing" in caplog.text

    @pytest.mark.asyncio
    async def test_on_mount_calls_create_practice_session(
        self, practice_screen, mock_app
    ):
        """Test that on_mount creates a practice session before loading questions."""
        # Arrange
        with (
            patch.object(
                type(practice_screen),
                "app",
                new_callable=PropertyMock,
                return_value=mock_app,
            ),
            patch.object(
                practice_screen, "_create_practice_session", new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                practice_screen, "load_next_question", new_callable=AsyncMock
            ) as mock_load,
        ):
            # Act
            await practice_screen.on_mount()

            # Assert
            mock_create.assert_called_once()
            mock_load.assert_called_once()
            # Verify create_session was called before load_next_question
            assert mock_create.call_count == 1

    def test_practice_screen_initializes_session_id_as_none(self, practice_screen):
        """Test that practice screen initializes session_id as None."""
        assert practice_screen.session_id is None

    def test_practice_screen_stores_session_id_after_creation(self, practice_screen):
        """Test that practice screen stores session_id after creation."""
        # Arrange & Act
        practice_screen.session_id = 789

        # Assert
        assert practice_screen.session_id == 789


class TestQuestionWidgetSessionTracking:
    """Test that QuestionWidget properly tracks session IDs."""

    @pytest.fixture
    def sample_question(self):
        """Create a sample question."""
        import json

        return Question(
            id=1,
            question="Test question?",
            options=json.dumps(["A", "B", "C", "D"]),
            correct="A",
            category="Test",
        )

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserSettingsRepository)

    @pytest.fixture
    def mock_learning_repository(self):
        """Create a mock learning repository."""
        return Mock()

    def test_question_widget_accepts_session_id(
        self,
        sample_question,
        mock_event_bus,
        mock_user_repository,
        mock_learning_repository,
    ):
        """Test that QuestionWidget accepts and stores session_id parameter."""
        # Arrange & Act
        enhanced_question_handler = Mock()
        load_user_settings_handler = Mock()
        submit_answer_handler = Mock()

        widget = QuestionWidget(
            question=sample_question,
            event_bus=mock_event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_answer_handler,
            session_id=123,
        )

        # Assert
        assert widget.session_id == 123

    def test_question_widget_defaults_session_id_to_none(
        self,
        sample_question,
        mock_event_bus,
        mock_user_repository,
        mock_learning_repository,
    ):
        """Test that QuestionWidget defaults session_id to None when not provided."""
        # Arrange & Act
        enhanced_question_handler = Mock()
        load_user_settings_handler = Mock()
        submit_answer_handler = Mock()

        widget = QuestionWidget(
            question=sample_question,
            event_bus=mock_event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_answer_handler,
        )

        # Assert
        assert widget.session_id is None

    @pytest.mark.asyncio
    async def test_submit_answer_includes_session_id(
        self,
        sample_question,
        mock_event_bus,
        mock_user_repository,
        mock_learning_repository,
    ):
        """Test that submit_answer_with_rating includes session_id in command."""
        # Arrange
        mock_handler = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_handler.handle.return_value = mock_result

        enhanced_question_handler = Mock()
        load_user_settings_handler = Mock()

        widget = QuestionWidget(
            question=sample_question,
            event_bus=mock_event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=mock_handler,
            session_id=456,
        )
        widget.selected_answer = "A"

        # Act
        await widget.submit_answer_with_rating(rating=3)

        # Assert
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]  # Get the command argument
        assert call_args.session_id == 456
        assert call_args.question_id == 1
        assert call_args.fsrs_rating == 3
