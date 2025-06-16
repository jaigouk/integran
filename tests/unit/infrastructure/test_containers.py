"""Tests for dependency injection containers."""

from __future__ import annotations

from unittest.mock import Mock, patch

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.containers.main_container import MainContainer
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.event_bus import EventBus


class TestMainContainer:
    """Test MainContainer dependency injection."""

    @patch("src.infrastructure.containers.main_container.EventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_container_initialization(
        self,
        mock_query_handler,
        mock_session_workflow,
        mock_complete_learning_session,
        mock_schedule_card,
        mock_content_container,
        mock_db_manager_class,
        mock_event_bus_class,
    ):
        """Test that container initializes all dependencies correctly."""
        # Arrange
        mock_event_bus = Mock(spec=EventBus)
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_event_bus_class.return_value = mock_event_bus
        mock_db_manager_class.return_value = mock_db_manager

        # Act
        MainContainer()

        # Assert - Core infrastructure
        mock_event_bus_class.assert_called_once()
        mock_db_manager_class.assert_called_once()

        # Assert - Sub-containers
        mock_content_container.assert_called_once_with(event_bus=mock_event_bus)

        # Assert - Domain services
        mock_schedule_card.assert_called_once_with(
            db_manager=mock_db_manager,
            event_bus=mock_event_bus,
        )
        mock_complete_learning_session.assert_called_once_with(
            db_manager=mock_db_manager,
            schedule_card_service=mock_schedule_card.return_value,
            event_bus=mock_event_bus,
        )

        # Assert - Application services
        mock_session_workflow.assert_called_once_with(
            complete_learning_session=mock_complete_learning_session.return_value,
        )

        # Assert - Query services
        mock_query_handler.assert_called_once_with(
            db_manager=mock_db_manager,
        )

    def test_get_event_bus(self):
        """Test getting event bus instance."""
        with patch(
            "src.infrastructure.containers.main_container.EventBus"
        ) as mock_event_bus_class:
            mock_event_bus = Mock(spec=EventBus)
            mock_event_bus_class.return_value = mock_event_bus

            container = MainContainer()
            result = container.get_event_bus()

            assert result == mock_event_bus

    def test_get_db_manager(self):
        """Test getting database manager instance."""
        with patch(
            "src.infrastructure.containers.main_container.DatabaseManager"
        ) as mock_db_class:
            mock_db = Mock(spec=DatabaseManager)
            mock_db_class.return_value = mock_db

            container = MainContainer()
            result = container.get_db_manager()

            assert result == mock_db

    def test_get_content_container(self):
        """Test getting content container instance."""
        with patch(
            "src.infrastructure.containers.main_container.ContentContainer"
        ) as mock_content_class:
            mock_content = Mock(spec=ContentContainer)
            mock_content_class.return_value = mock_content

            container = MainContainer()
            result = container.get_content_container()

            assert result == mock_content

    def test_get_session_workflow(self):
        """Test getting session workflow instance."""
        with patch(
            "src.infrastructure.containers.main_container.SessionWorkflow"
        ) as mock_workflow_class:
            mock_workflow = Mock(spec=SessionWorkflow)
            mock_workflow_class.return_value = mock_workflow

            container = MainContainer()
            result = container.get_session_workflow()

            assert result == mock_workflow

    def test_get_query_service(self):
        """Test getting query service instance."""
        with patch(
            "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
        ) as mock_query_class:
            mock_query = Mock(spec=GetSessionProgressQueryHandler)
            mock_query_class.return_value = mock_query

            container = MainContainer()
            result = container.get_query_service()

            assert result == mock_query


class TestContentContainer:
    """Test ContentContainer dependency injection."""

    @patch("src.infrastructure.containers.content_container.EventBus")
    @patch("src.infrastructure.containers.content_container.ContentRepository")
    @patch("src.infrastructure.containers.content_container.GenerateAnswer")
    @patch("src.infrastructure.containers.content_container.ProcessImage")
    @patch("src.infrastructure.containers.content_container.CreateImageMapping")
    @patch("src.infrastructure.containers.content_container.BuildDataset")
    @patch("src.infrastructure.containers.content_container.DatasetBuildWorkflow")
    def test_container_initialization_with_provided_event_bus(
        self,
        mock_workflow,
        mock_build_dataset,
        mock_create_mapping,
        mock_process_image,
        mock_generate_answer,
        mock_repository,
        mock_event_bus_class,
    ):
        """Test container initialization with provided event bus."""
        # Arrange
        provided_event_bus = Mock(spec=EventBus)

        # Act
        ContentContainer(event_bus=provided_event_bus)

        # Assert - Uses provided event bus
        mock_event_bus_class.assert_not_called()
        mock_repository.assert_called_once()

        # Assert - Domain services initialized with provided event bus
        mock_generate_answer.assert_called_once_with(event_bus=provided_event_bus)
        mock_process_image.assert_called_once_with(event_bus=provided_event_bus)
        mock_create_mapping.assert_called_once_with(event_bus=provided_event_bus)
        mock_build_dataset.assert_called_once_with(
            event_bus=provided_event_bus,
            repository=mock_repository.return_value,
        )

        # Assert - Application service initialized
        mock_workflow.assert_called_once_with(
            build_dataset_service=mock_build_dataset.return_value,
        )

    @patch("src.infrastructure.containers.content_container.EventBus")
    def test_container_initialization_without_event_bus(self, mock_event_bus_class):
        """Test container initialization without provided event bus."""
        # Arrange
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus_class.return_value = mock_event_bus

        # Act
        ContentContainer()

        # Assert - Creates new event bus
        mock_event_bus_class.assert_called_once()

    def test_get_event_bus(self):
        """Test getting event bus instance."""
        provided_event_bus = Mock(spec=EventBus)
        container = ContentContainer(event_bus=provided_event_bus)

        result = container.get_event_bus()
        assert result == provided_event_bus

    def test_get_repository(self):
        """Test getting repository instance."""
        with patch(
            "src.infrastructure.containers.content_container.ContentRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            container = ContentContainer()
            result = container.get_repository()

            assert result == mock_repo

    def test_get_generate_answer_service(self):
        """Test getting generate answer service."""
        with patch(
            "src.infrastructure.containers.content_container.GenerateAnswer"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            container = ContentContainer()
            result = container.get_generate_answer_service()

            assert result == mock_service

    def test_get_process_image_service(self):
        """Test getting process image service."""
        with patch(
            "src.infrastructure.containers.content_container.ProcessImage"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            container = ContentContainer()
            result = container.get_process_image_service()

            assert result == mock_service

    def test_get_create_image_mapping_service(self):
        """Test getting create image mapping service."""
        with patch(
            "src.infrastructure.containers.content_container.CreateImageMapping"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            container = ContentContainer()
            result = container.get_create_image_mapping_service()

            assert result == mock_service

    def test_get_content_builder_service(self):
        """Test getting content builder service."""
        with patch(
            "src.infrastructure.containers.content_container.DatasetBuildWorkflow"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            container = ContentContainer()
            result = container.get_content_builder_service()

            assert result == mock_service
