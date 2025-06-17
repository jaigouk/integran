"""Main dependency injection container for the Integran application."""

from __future__ import annotations

from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus


class MainContainer:
    """Main container for all application dependencies."""

    def __init__(self) -> None:
        """Initialize the main container with all dependencies."""
        # Core infrastructure
        self._event_bus = EnhancedEventBus.create_basic()
        self._db_manager = DatabaseManager()

        # Sub-containers
        self._content_container = ContentContainer(event_bus=self._event_bus)

        # Domain services
        self._schedule_card = ScheduleCard(
            db_manager=self._db_manager,
            event_bus=self._event_bus,
        )
        self._complete_learning_session = CompleteLearningSession(
            db_manager=self._db_manager,
            schedule_card_service=self._schedule_card,
            event_bus=self._event_bus,
        )

        # Application services
        self._session_workflow = SessionWorkflow(
            complete_learning_session=self._complete_learning_session,
        )

        # Query services
        self._query_service = GetSessionProgressQueryHandler(
            db_manager=self._db_manager,
        )

    def get_event_bus(self) -> EnhancedEventBus:
        """Get the event bus instance."""
        return self._event_bus

    def get_db_manager(self) -> DatabaseManager:
        """Get the database manager instance."""
        return self._db_manager

    def get_content_container(self) -> ContentContainer:
        """Get the content container."""
        return self._content_container

    def get_session_workflow(self) -> SessionWorkflow:
        """Get the session workflow."""
        return self._session_workflow

    def get_query_service(self) -> GetSessionProgressQueryHandler:
        """Get the query service."""
        return self._query_service
