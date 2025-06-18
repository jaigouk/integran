"""Tests for dependency injection containers."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.containers.main_container import MainContainer
from src.infrastructure.containers.user_container import UserContainer
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus


@pytest.fixture(autouse=True)
def disable_vertex_ai(monkeypatch):
    """Disable Vertex AI for all tests to avoid GCP_PROJECT_ID requirement."""
    monkeypatch.setenv("USE_VERTEX_AI", "false")
    monkeypatch.setenv(
        "GCP_PROJECT_ID", "test-project"
    )  # Set a dummy value just in case


class TestMainContainer:
    """Test MainContainer dependency injection."""

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.UserContainer")
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
        mock_user_container,
        mock_db_manager_class,
        mock_event_bus_class,
    ):
        """Test that container initializes all dependencies correctly."""
        # Arrange
        mock_event_bus = Mock(spec=EnhancedEventBus)
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_user_repo = Mock()
        mock_user_container_instance = Mock(spec=UserContainer)
        mock_user_container_instance.get_repository.return_value = mock_user_repo

        mock_event_bus_class.create_basic.return_value = mock_event_bus
        mock_db_manager_class.return_value = mock_db_manager
        mock_user_container.return_value = mock_user_container_instance

        # Act
        MainContainer()

        # Assert - Core infrastructure
        mock_event_bus_class.create_basic.assert_called_once()
        mock_db_manager_class.assert_called_once()

        # Assert - Sub-containers
        mock_user_container.assert_called_once_with(
            event_bus=mock_event_bus,
            database_manager=mock_db_manager,
        )
        mock_content_container.assert_called_once_with(
            event_bus=mock_event_bus,
            user_repository=mock_user_repo,
        )

        # Assert - Domain services (updated for repository-based constructor)
        # ScheduleCard now takes learning_repository instead of db_manager
        mock_schedule_card.assert_called_once()
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

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_event_bus(
        self,
        _mock_query_handler,
        _mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        _mock_content_container,
        _mock_db_manager_class,
        mock_event_bus_class,
    ):
        """Test getting event bus instance."""
        mock_event_bus = Mock(spec=EnhancedEventBus)
        mock_event_bus_class.create_basic.return_value = mock_event_bus

        container = MainContainer()
        result = container.get_event_bus()

        assert result == mock_event_bus

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_db_manager(
        self,
        _mock_query_handler,
        _mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        _mock_content_container,
        mock_db_manager_class,
        _mock_event_bus_class,
    ):
        """Test getting database manager instance."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db_manager_class.return_value = mock_db

        container = MainContainer()
        result = container.get_db_manager()

        assert result == mock_db

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_content_container(
        self,
        _mock_query_handler,
        _mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        mock_content_container,
        _mock_db_manager_class,
        _mock_event_bus_class,
    ):
        """Test getting content container instance."""
        mock_content = Mock(spec=ContentContainer)
        mock_content_container.return_value = mock_content

        container = MainContainer()
        result = container.get_content_container()

        assert result == mock_content

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_session_workflow(
        self,
        _mock_query_handler,
        mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        _mock_content_container,
        _mock_db_manager_class,
        _mock_event_bus_class,
    ):
        """Test getting session workflow instance."""
        mock_workflow = Mock(spec=SessionWorkflow)
        mock_session_workflow.return_value = mock_workflow

        container = MainContainer()
        result = container.get_session_workflow()

        assert result == mock_workflow

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_query_service(
        self,
        mock_query_handler,
        _mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        _mock_content_container,
        _mock_db_manager_class,
        _mock_event_bus_class,
    ):
        """Test getting query service instance."""
        mock_query = Mock(spec=GetSessionProgressQueryHandler)
        mock_query_handler.return_value = mock_query

        container = MainContainer()
        result = container.get_query_service()

        assert result == mock_query

    @patch("src.infrastructure.containers.main_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.main_container.DatabaseManager")
    @patch("src.infrastructure.containers.main_container.UserContainer")
    @patch("src.infrastructure.containers.main_container.ContentContainer")
    @patch("src.infrastructure.containers.main_container.ScheduleCard")
    @patch("src.infrastructure.containers.main_container.CompleteLearningSession")
    @patch("src.infrastructure.containers.main_container.SessionWorkflow")
    @patch(
        "src.infrastructure.containers.main_container.GetSessionProgressQueryHandler"
    )
    def test_get_user_container(
        self,
        _mock_query_handler,
        _mock_session_workflow,
        _mock_complete_learning_session,
        _mock_schedule_card,
        _mock_content_container,
        mock_user_container,
        _mock_db_manager_class,
        _mock_event_bus_class,
    ):
        """Test getting user container instance."""
        mock_user = Mock(spec=UserContainer)
        mock_user_container.return_value = mock_user
        mock_user.get_repository.return_value = Mock()  # Mock user repo

        container = MainContainer()
        result = container.get_user_container()

        assert result == mock_user


class TestContentContainer:
    """Test ContentContainer dependency injection."""

    @patch("src.infrastructure.containers.content_container.EnhancedEventBus")
    @patch("src.infrastructure.containers.content_container.ContentRepository")
    def test_container_initialization_with_provided_event_bus(
        self,
        mock_repository,
        mock_event_bus_class,
    ):
        """Test container initialization with provided event bus (lazy initialization)."""
        # Arrange
        provided_event_bus = Mock(spec=EnhancedEventBus)

        # Act
        container = ContentContainer(event_bus=provided_event_bus)

        # Assert - Uses provided event bus, services not initialized yet (lazy)
        mock_event_bus_class.assert_not_called()
        mock_repository.assert_called_once()

        # Verify the container stores the event bus correctly
        assert container._event_bus == provided_event_bus
        assert container._repository == mock_repository.return_value

        # Verify services are None initially (lazy initialization)
        assert container._generate_answer is None
        assert container._process_image is None
        assert container._create_image_mapping is None
        assert container._build_dataset is None
        assert container._content_builder is None

    def test_lazy_initialization_of_services(self):
        """Test that services are only initialized when accessed."""
        # Arrange
        provided_event_bus = Mock(spec=EnhancedEventBus)

        with (
            patch(
                "src.infrastructure.containers.content_container.GenerateAnswer"
            ) as mock_generate_answer,
            patch(
                "src.infrastructure.containers.content_container.ProcessImage"
            ) as mock_process_image,
            patch(
                "src.infrastructure.containers.content_container.CreateImageMapping"
            ) as mock_create_mapping,
            patch(
                "src.infrastructure.containers.content_container.BuildDataset"
            ) as mock_build_dataset,
        ):
            # Create container
            container = ContentContainer(event_bus=provided_event_bus)

            # Assert services not called yet
            mock_generate_answer.assert_not_called()
            mock_process_image.assert_not_called()
            mock_create_mapping.assert_not_called()
            mock_build_dataset.assert_not_called()

            # Access services to trigger lazy initialization
            container.get_generate_answer_service()
            mock_generate_answer.assert_called_once_with(
                event_bus=provided_event_bus,
                user_repository=container._user_repository,
            )

            container.get_process_image_service()
            mock_process_image.assert_called_once_with(
                event_bus=provided_event_bus,
                user_repository=container._user_repository,
            )

            container.get_create_image_mapping_service()
            mock_create_mapping.assert_called_once_with(event_bus=provided_event_bus)

    @patch("src.infrastructure.containers.content_container.EnhancedEventBus")
    def test_container_initialization_without_event_bus(self, mock_event_bus_class):
        """Test container initialization without provided event bus."""
        # Arrange
        mock_event_bus = Mock(spec=EnhancedEventBus)
        mock_event_bus_class.create_basic.return_value = mock_event_bus

        # Act
        ContentContainer()

        # Assert - Creates new event bus
        mock_event_bus_class.create_basic.assert_called_once()

    def test_get_event_bus(self):
        """Test getting event bus instance."""
        provided_event_bus = Mock(spec=EnhancedEventBus)
        container = ContentContainer(event_bus=provided_event_bus)

        result = container.get_event_bus()
        assert result == provided_event_bus

    @patch("src.infrastructure.containers.content_container.ContentRepository")
    def test_get_repository(self, mock_repository):
        """Test getting repository instance."""
        mock_repo = Mock()
        mock_repository.return_value = mock_repo

        container = ContentContainer()
        result = container.get_repository()

        assert result == mock_repo

    @patch("src.infrastructure.containers.content_container.GenerateAnswer")
    def test_get_generate_answer_service(self, mock_generate_answer):
        """Test getting generate answer service with lazy initialization."""
        mock_service = Mock()
        mock_generate_answer.return_value = mock_service
        provided_event_bus = Mock(spec=EnhancedEventBus)

        container = ContentContainer(event_bus=provided_event_bus)
        result = container.get_generate_answer_service()

        # Service should be created on first access
        mock_generate_answer.assert_called_once_with(
            event_bus=provided_event_bus,
            user_repository=container._user_repository,
        )
        assert result == mock_service

        # Subsequent calls should return the same instance without creating new one
        result2 = container.get_generate_answer_service()
        mock_generate_answer.assert_called_once()  # Still only called once
        assert result2 == mock_service

    @patch("src.infrastructure.containers.content_container.ProcessImage")
    def test_get_process_image_service(self, mock_process_image):
        """Test getting process image service with lazy initialization."""
        mock_service = Mock()
        mock_process_image.return_value = mock_service
        provided_event_bus = Mock(spec=EnhancedEventBus)

        container = ContentContainer(event_bus=provided_event_bus)
        result = container.get_process_image_service()

        mock_process_image.assert_called_once_with(
            event_bus=provided_event_bus,
            user_repository=container._user_repository,
        )
        assert result == mock_service

    @patch("src.infrastructure.containers.content_container.CreateImageMapping")
    def test_get_create_image_mapping_service(self, mock_create_mapping):
        """Test getting create image mapping service with lazy initialization."""
        mock_service = Mock()
        mock_create_mapping.return_value = mock_service
        provided_event_bus = Mock(spec=EnhancedEventBus)

        container = ContentContainer(event_bus=provided_event_bus)
        result = container.get_create_image_mapping_service()

        mock_create_mapping.assert_called_once_with(event_bus=provided_event_bus)
        assert result == mock_service

    @patch("src.infrastructure.containers.content_container.DatasetBuildWorkflow")
    @patch("src.infrastructure.containers.content_container.BuildDataset")
    @patch("src.infrastructure.containers.content_container.GenerateAnswer")
    @patch("src.infrastructure.containers.content_container.ProcessImage")
    @patch("src.infrastructure.containers.content_container.CreateImageMapping")
    def test_get_content_builder_service(
        self,
        mock_create_mapping,
        mock_process_image,
        mock_generate_answer,
        mock_build_dataset,
        mock_workflow,
    ):
        """Test getting content builder service with lazy initialization."""
        mock_build_service = Mock()
        mock_workflow_service = Mock()
        mock_build_dataset.return_value = mock_build_service
        mock_workflow.return_value = mock_workflow_service
        provided_event_bus = Mock(spec=EnhancedEventBus)

        # Mock the service instances
        mock_generate_service = Mock()
        mock_process_service = Mock()
        mock_mapping_service = Mock()
        mock_generate_answer.return_value = mock_generate_service
        mock_process_image.return_value = mock_process_service
        mock_create_mapping.return_value = mock_mapping_service

        with patch(
            "src.infrastructure.containers.content_container.ContentRepository"
        ) as mock_repository:
            mock_repo = Mock()
            mock_repository.return_value = mock_repo

            container = ContentContainer(event_bus=provided_event_bus)
            result = container.get_content_builder_service()

            # BuildDataset should be created first
            mock_build_dataset.assert_called_once_with(
                event_bus=provided_event_bus,
                repository=mock_repo,
                generate_answer=mock_generate_service,
                process_image=mock_process_service,
                create_mapping=mock_mapping_service,
                user_repository=container._user_repository,
            )
            # Then DatasetBuildWorkflow should be created
            mock_workflow.assert_called_once_with(
                build_dataset_service=mock_build_service,
            )
            assert result == mock_workflow_service
