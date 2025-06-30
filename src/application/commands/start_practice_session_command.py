"""Command for starting a practice session following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.application.queries.get_questions_by_mode_query import (
    GetQuestionsByModeQuery,
    GetQuestionsByModeQueryHandler,
)
from src.application.queries.load_user_preferences_query import LoadUserPreferencesQuery
from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import (
    QuestionRepository,
    SessionRepository,
    UserRepository,
)
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import FederalState, UserPreferences

logger = logging.getLogger(__name__)


@dataclass
class StartPracticeSessionCommand:
    """Command to start a practice session with specified mode."""

    practice_mode: str  # "random", "sequential", "review", "category"
    user_repository: UserRepository
    session_repository: SessionRepository
    event_bus: EventBusInterface
    user_id: int = 1
    limit: int = 1
    # State for cycling through questions
    category_index: int = 0
    question_indices: dict[str, int] | None = None
    last_question_id: int = 0
    # Optional existing session ID to avoid creating duplicates
    existing_session_id: int | None = None

    async def execute(
        self, question_repository: QuestionRepository
    ) -> StartPracticeSessionResult:
        """Execute the command to start a practice session."""
        try:
            logger.info(
                f"Starting practice session: mode={self.practice_mode}, user_id={self.user_id}"
            )

            # Use existing session or create a new one
            if self.existing_session_id is not None:
                session_id = self.existing_session_id
                logger.info(
                    f"Using existing session {session_id} for practice mode {self.practice_mode}"
                )
            else:
                session_id = await self.session_repository.create_session(
                    user_id=self.user_id,
                    session_type=self.practice_mode,
                    configuration={"limit": self.limit},
                )
                logger.info(
                    f"Created new session {session_id} for practice mode {self.practice_mode}"
                )

            # Load user preferences to get federal state filtering
            user_preferences_query = LoadUserPreferencesQuery(
                user_repository=self.user_repository,
                event_bus=self.event_bus,
                user_id=self.user_id,
            )

            user_preferences_result = await user_preferences_query.handle()

            # Extract user preferences or create default ones
            user_preferences = None
            if (
                user_preferences_result.success
                and user_preferences_result.user_settings
            ):
                user_preferences = user_preferences_result.user_settings.preferences
            else:
                # Default to general federal state if no preferences exist
                logger.info(
                    f"No user preferences found for user {self.user_id}, defaulting to general federal state"
                )
                user_preferences = UserPreferences(federal_state=FederalState.GENERAL)

            # Use the existing query handler to get the first question
            questions_query_handler = GetQuestionsByModeQueryHandler(
                question_repository=question_repository
            )

            query = GetQuestionsByModeQuery(
                practice_mode=self.practice_mode,
                user_preferences=user_preferences,
                user_id=self.user_id,
                limit=self.limit,
                category_index=self.category_index,
                question_indices=self.question_indices,
                last_question_id=self.last_question_id,
            )

            result = await questions_query_handler.handle(query)

            if result.success and result.question:
                return StartPracticeSessionResult(
                    success=True,
                    question=result.question,
                    session_state=result.next_state,
                    practice_mode=self.practice_mode,
                    session_id=session_id,
                )
            else:
                return StartPracticeSessionResult(
                    success=False,
                    practice_mode=self.practice_mode,
                    error_message=result.error_message
                    or f"No questions available for {self.practice_mode} mode",
                )

        except Exception as e:
            logger.error(f"Error starting practice session: {e}")
            return StartPracticeSessionResult(
                success=False,
                practice_mode=self.practice_mode,
                error_message=f"Failed to start practice session: {e}",
            )


@dataclass
class StartPracticeSessionResult:
    """Result of starting a practice session."""

    success: bool
    question: Question | None = None
    session_state: dict[str, Any] | None = None  # State for UI to maintain
    practice_mode: str | None = None
    session_id: int | None = None
    error_message: str | None = None


# Legacy handler class - deprecated in favor of command.execute()
# Kept for backward compatibility during transition
class StartPracticeSessionCommandHandler:
    """DEPRECATED: Handler for starting practice sessions.

    Use StartPracticeSessionCommand.execute() method instead.
    """

    def __init__(
        self,
        question_repository: QuestionRepository,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with question repository, user repository, session repository, and event bus."""
        self.question_repository = question_repository
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.event_bus = event_bus

    async def handle(
        self, command: StartPracticeSessionCommand
    ) -> StartPracticeSessionResult:
        """Handle the command to start a practice session."""
        # Delegate to command's execute method for proper CQRS pattern
        command.user_repository = self.user_repository
        command.session_repository = self.session_repository
        command.event_bus = self.event_bus
        return await command.execute(self.question_repository)
