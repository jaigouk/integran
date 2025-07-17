"""Main dependency injection container for the Integran application."""

from __future__ import annotations

from src.application.commands.bookmark_commands import (
    AddBookmarkCommandHandler,
    RemoveBookmarkCommandHandler,
)
from src.application.commands.pause_session_command import (
    PauseSessionCommandHandler,
)
from src.application.commands.reset_user_progress_command import (
    ResetUserProgressCommandHandler,
)
from src.application.commands.save_user_settings_command import (
    SaveUserSettingsCommandHandler,
)
from src.application.commands.start_dataset_build_command import (
    StartDatasetBuildCommandHandler,
)
from src.application.commands.start_practice_session_command import (
    StartPracticeSessionCommandHandler,
)
from src.application.commands.submit_answer_with_rating_command import (
    SubmitAnswerWithRatingCommandHandler,
)
from src.application.commands.toggle_developer_mode_command import (
    ToggleDeveloperModeCommandHandler,
)
from src.application.events import EventSubscriptionManager
from src.application.events.handlers.card_scheduled_handler import CardScheduledHandler
from src.application.events.handlers.content_processed_handler import (
    ContentProcessedHandler,
)
from src.application.projections.user_progress_projection import UserProgressProjection
from src.application.queries.bookmark_queries import (
    GetBookmarksQueryHandler,
    GetBookmarkStatusQueryHandler,
)
from src.application.queries.enhanced_question_content_query import (
    EnhancedQuestionContentQueryHandler,
)
from src.application.queries.get_fsrs_analytics_query import (
    GetFSRSAnalyticsQueryHandler,
)
from src.application.queries.get_learning_stats_query import (
    GetLearningStatsQueryHandler,
)
from src.application.queries.get_questions_by_mode_query import (
    GetQuestionsByModeQueryHandler,
)
from src.application.queries.get_session_progress_query import (
    GetSessionProgressQueryHandler,
)
from src.application.queries.load_user_preferences_query import (
    LoadUserPreferencesQueryHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQueryHandler,
)
from src.application.workflows.complete_learning_session_workflow import SessionWorkflow
from src.domain.analytics.services.analyze_performance import ProgressAnalytics
from src.domain.analytics.services.reset_user_progress import ResetUserProgress
from src.domain.learning.events.card_events import CardScheduledEvent
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.domain.shared.repositories import (
    AnalyticsRepository,
    BookmarkRepository,
    LearningRepository,
    QuestionRepository,
    SessionRepository,
    UserRepository,
)
from src.infrastructure.containers.content_container import ContentContainer
from src.infrastructure.containers.user_container import UserContainer
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.repositories.analytics_repository import (
    SQLAlchemyAnalyticsRepository,
)
from src.infrastructure.repositories.bookmark_repository import (
    BookmarkRepositoryImpl,
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
        self._db_manager = DatabaseManager(enable_async=False)

        # Repository layer
        self._question_repository = SQLAlchemyQuestionRepository(self._db_manager)
        self._user_repository = SQLAlchemyUserRepository(self._db_manager)
        self._learning_repository = SQLAlchemyLearningRepository(self._db_manager)
        self._analytics_repository = SQLAlchemyAnalyticsRepository(self._db_manager)
        self._session_repository = SQLAlchemySessionRepository(self._db_manager)
        self._bookmark_repository = BookmarkRepositoryImpl(self._db_manager)

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
            session_repository=self._session_repository,
        )
        self._questions_query_service = GetQuestionsByModeQueryHandler(
            question_repository=self._question_repository,
            learning_repository=self._learning_repository,
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
        self._start_practice_session_command_handler = (
            StartPracticeSessionCommandHandler(
                question_repository=self._question_repository,
                user_repository=self._user_repository,
                session_repository=self._session_repository,
                event_bus=self._event_bus,
            )
        )
        self._submit_answer_command_handler = SubmitAnswerWithRatingCommandHandler(
            learning_repository=self._learning_repository,
            event_bus=self._event_bus,
        )
        self._save_user_settings_command_handler = SaveUserSettingsCommandHandler(
            user_repository=self._user_repository,
            event_bus=self._event_bus,
        )
        self._pause_session_command_handler = PauseSessionCommandHandler(
            learning_service=self._complete_learning_session,
        )
        self._toggle_developer_mode_command_handler = ToggleDeveloperModeCommandHandler(
            user_repository=self._user_repository,
            event_bus=self._event_bus,
        )
        self._start_dataset_build_command_handler = StartDatasetBuildCommandHandler(
            user_repository=self._user_repository,
            question_repository=self._question_repository,
            event_bus=self._event_bus,
        )
        self._add_bookmark_command_handler = AddBookmarkCommandHandler(
            bookmark_repository=self._bookmark_repository,
            event_bus=self._event_bus,
        )
        self._remove_bookmark_command_handler = RemoveBookmarkCommandHandler(
            bookmark_repository=self._bookmark_repository,
            event_bus=self._event_bus,
        )

        # Additional query handlers
        self._learning_stats_query_handler = GetLearningStatsQueryHandler(
            analytics_repository=self._analytics_repository,
        )
        self._fsrs_analytics_query_handler = GetFSRSAnalyticsQueryHandler(
            analytics_repository=self._analytics_repository,
        )
        self._user_preferences_query_handler = LoadUserPreferencesQueryHandler(
            user_repository=self._user_repository,
            event_bus=self._event_bus,
        )
        self._load_user_settings_query_handler = LoadUserSettingsQueryHandler(
            user_repository=self._user_repository,
            event_bus=self._event_bus,
        )
        self._enhanced_question_content_query_handler = (
            EnhancedQuestionContentQueryHandler(
                user_repository=self._user_repository,
                event_bus=self._event_bus,
            )
        )
        self._get_bookmarks_query_handler = GetBookmarksQueryHandler(
            bookmark_repository=self._bookmark_repository,
        )
        self._get_bookmark_status_query_handler = GetBookmarkStatusQueryHandler(
            bookmark_repository=self._bookmark_repository,
        )

        # Event handlers and projections
        self._content_processed_handler = ContentProcessedHandler()
        self._user_progress_projection = UserProgressProjection(
            analytics_repository=self._analytics_repository,
            learning_repository=self._learning_repository,
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

    def get_question_repository(self) -> QuestionRepository:
        """Get the question repository."""
        return self._question_repository

    def get_user_repository(self) -> UserRepository:
        """Get the user repository."""
        return self._user_repository

    def get_learning_repository(self) -> LearningRepository:
        """Get the learning repository."""
        return self._learning_repository

    def get_analytics_repository(self) -> AnalyticsRepository:
        """Get the analytics repository."""
        return self._analytics_repository

    def get_session_repository(self) -> SessionRepository:
        """Get the session repository."""
        return self._session_repository

    def get_bookmark_repository(self) -> BookmarkRepository:
        """Get the bookmark repository."""
        return self._bookmark_repository

    def get_start_practice_session_command_handler(
        self,
    ) -> StartPracticeSessionCommandHandler:
        """Get the start practice session command handler."""
        return self._start_practice_session_command_handler

    def get_submit_answer_command_handler(self) -> SubmitAnswerWithRatingCommandHandler:
        """Get the submit answer command handler."""
        return self._submit_answer_command_handler

    def get_save_user_settings_command_handler(self) -> SaveUserSettingsCommandHandler:
        """Get the save user settings command handler."""
        return self._save_user_settings_command_handler

    def get_pause_session_command_handler(self) -> PauseSessionCommandHandler:
        """Get the pause session command handler."""
        return self._pause_session_command_handler

    def get_learning_stats_query_handler(self) -> GetLearningStatsQueryHandler:
        """Get the learning stats query handler."""
        return self._learning_stats_query_handler

    def get_fsrs_analytics_query_handler(self) -> GetFSRSAnalyticsQueryHandler:
        """Get the FSRS analytics query handler."""
        return self._fsrs_analytics_query_handler

    def get_user_preferences_query_handler(self) -> LoadUserPreferencesQueryHandler:
        """Get the user preferences query handler."""
        return self._user_preferences_query_handler

    def get_load_user_settings_query_handler(self) -> LoadUserSettingsQueryHandler:
        """Get the load user settings query handler."""
        return self._load_user_settings_query_handler

    def get_enhanced_question_content_query_handler(
        self,
    ) -> EnhancedQuestionContentQueryHandler:
        """Get the enhanced question content query handler."""
        return self._enhanced_question_content_query_handler

    def get_bookmark_query_handler(self) -> GetBookmarksQueryHandler:
        """Get the bookmark query handler."""
        return self._get_bookmarks_query_handler

    def get_bookmark_status_query_handler(self) -> GetBookmarkStatusQueryHandler:
        """Get the bookmark status query handler."""
        return self._get_bookmark_status_query_handler

    def get_toggle_developer_mode_command_handler(
        self,
    ) -> ToggleDeveloperModeCommandHandler:
        """Get the toggle developer mode command handler."""
        return self._toggle_developer_mode_command_handler

    def get_start_dataset_build_command_handler(
        self,
    ) -> StartDatasetBuildCommandHandler:
        """Get the start dataset build command handler."""
        return self._start_dataset_build_command_handler

    def get_bookmark_command_handler(self) -> AddBookmarkCommandHandler:
        """Get the bookmark command handler."""
        return self._add_bookmark_command_handler

    def get_bookmark_remove_command_handler(self) -> RemoveBookmarkCommandHandler:
        """Get the bookmark remove command handler."""
        return self._remove_bookmark_command_handler

    def get_content_processed_handler(self) -> ContentProcessedHandler:
        """Get the content processed handler."""
        return self._content_processed_handler

    def get_user_progress_projection(self) -> UserProgressProjection:
        """Get the user progress projection."""
        return self._user_progress_projection

    def _setup_event_handlers(self) -> None:
        """Setup all event handlers."""
        # Register CardScheduledEvent handler
        card_scheduled_handler = CardScheduledHandler(self._learning_repository)
        self._event_subscription_manager.subscribe(
            CardScheduledEvent, card_scheduled_handler
        )
