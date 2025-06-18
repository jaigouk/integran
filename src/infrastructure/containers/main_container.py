"""Main dependency injection container for the Integran application."""

from __future__ import annotations

from src.application.events import EventSubscriptionManager
from src.application.events.handlers.card_scheduled_handler import CardScheduledHandler
from src.application.queries.get_questions_by_mode_query import (
    GetQuestionsByModeQueryHandler,
)
from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.domain.analytics.services.analyze_performance import ProgressAnalytics
from src.domain.learning.events.card_events import CardScheduledEvent
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.containers.user_container import UserContainer
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
        self._user_container = UserContainer(
            event_bus=self._event_bus,
            database_manager=self._db_manager,
        )
        self._content_container = ContentContainer(
            event_bus=self._event_bus,
            user_repository=self._user_container.get_repository(),
        )

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
        self._questions_query_service = GetQuestionsByModeQueryHandler(
            db_manager=self._db_manager,
        )

        # Analytics services
        self._analytics_service = ProgressAnalytics(
            db_manager=self._db_manager,
        )

        # Event subscription manager and handlers
        self._event_subscription_manager = EventSubscriptionManager(self._event_bus)
        self._setup_event_handlers()

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

    def get_user_container(self) -> UserContainer:
        """Get the user container."""
        return self._user_container

    def get_analytics_service(self) -> ProgressAnalytics:
        """Get the analytics service."""
        return self._analytics_service

    def get_schedule_card_service(self) -> ScheduleCard:
        """Get the schedule card service."""
        return self._schedule_card

    def get_questions_query_service(self) -> GetQuestionsByModeQueryHandler:
        """Get the questions query service."""
        return self._questions_query_service

    def _setup_event_handlers(self) -> None:
        """Setup all event handlers."""
        # Register CardScheduledEvent handler
        card_scheduled_handler = CardScheduledHandler(self._db_manager)
        self._event_subscription_manager.subscribe(
            CardScheduledEvent, card_scheduled_handler
        )
