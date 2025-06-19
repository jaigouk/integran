"""Main dependency injection container for the Integran application."""

from __future__ import annotations

from src.application.commands.reset_user_progress_command import (
    ResetUserProgressCommandHandler,
)
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
from src.domain.analytics.services.reset_user_progress import ResetUserProgress
from src.domain.learning.events.card_events import CardScheduledEvent
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.containers.user_container import UserContainer
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.repositories.analytics_repository import (
    SQLAlchemyAnalyticsRepository,
)
from src.infrastructure.repositories.learning_repository import (
    SQLAlchemyLearningRepository,
)
from src.infrastructure.repositories.question_repository import (
    SQLAlchemyQuestionRepository,
)
from src.infrastructure.repositories.session_repository import (
    SQLAlchemySessionRepository,
)
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository


class MainContainer:
    """Main container for all application dependencies."""

    def __init__(self) -> None:
        """Initialize the main container with all dependencies."""
        # Core infrastructure
        self._event_bus = EnhancedEventBus.create_basic()
        self._db_manager = DatabaseManager()

        # Repository layer
        self._question_repository = SQLAlchemyQuestionRepository(self._db_manager)
        self._user_repository = SQLAlchemyUserRepository(self._db_manager)
        self._learning_repository = SQLAlchemyLearningRepository(self._db_manager)
        self._analytics_repository = SQLAlchemyAnalyticsRepository(self._db_manager)
        self._session_repository = SQLAlchemySessionRepository(self._db_manager)

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
            learning_repository=self._learning_repository,
            event_bus=self._event_bus,
        )
        self._complete_learning_session = CompleteLearningSession(
            learning_repository=self._learning_repository,
            question_repository=self._question_repository,
            session_repository=self._session_repository,
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
            analytics_repository=self._analytics_repository,
        )
        self._reset_progress_service = ResetUserProgress(
            user_repository=self._user_repository,
            learning_repository=self._learning_repository,
            analytics_repository=self._analytics_repository,
            session_repository=self._session_repository,
            event_bus=self._event_bus,
        )

        # Command handlers
        self._reset_progress_command_handler = ResetUserProgressCommandHandler(
            reset_service=self._reset_progress_service,
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

    def get_reset_progress_command_handler(self) -> ResetUserProgressCommandHandler:
        """Get the reset progress command handler."""
        return self._reset_progress_command_handler

    def get_question_repository(self) -> SQLAlchemyQuestionRepository:
        """Get the question repository."""
        return self._question_repository

    def get_user_repository(self) -> SQLAlchemyUserRepository:
        """Get the user repository."""
        return self._user_repository

    def get_learning_repository(self) -> SQLAlchemyLearningRepository:
        """Get the learning repository."""
        return self._learning_repository

    def get_analytics_repository(self) -> SQLAlchemyAnalyticsRepository:
        """Get the analytics repository."""
        return self._analytics_repository

    def get_session_repository(self) -> SQLAlchemySessionRepository:
        """Get the session repository."""
        return self._session_repository

    def _setup_event_handlers(self) -> None:
        """Setup all event handlers."""
        # Register CardScheduledEvent handler
        card_scheduled_handler = CardScheduledHandler(self._db_manager)
        self._event_subscription_manager.subscribe(
            CardScheduledEvent, card_scheduled_handler
        )
