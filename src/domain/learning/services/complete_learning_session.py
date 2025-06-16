"""CompleteLearningSession domain service for session management and coordination.

This domain service encapsulates the business logic for managing learning sessions,
including session lifecycle, question selection, progress tracking, and completion
following the Domain-Driven Design pattern with async operations and event publishing.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.infrastructure.database.database import DatabaseManager

from src.domain.content.models.question_models import Question
from src.domain.learning.events.card_events import (
    SessionCompletedEvent,
    SessionStartedEvent,
)
from src.domain.learning.models.learning_models import FSRSCard
from src.domain.learning.services.schedule_card import ScheduleCard, ScheduleCardRequest
from src.domain.shared.models import FSRSRating
from src.domain.shared.services import (
    BusinessRuleViolationError,
    DomainService,
    ValidationError,
    log_domain_operation,
)
from src.infrastructure.messaging.event_bus import EventBus

logger = logging.getLogger(__name__)


class SessionType(str, Enum):
    """Types of learning sessions."""

    REVIEW = "review"  # Scheduled reviews
    LEARN = "learn"  # New cards
    WEAK_FOCUS = "weak_focus"  # Focus on difficult cards
    QUIZ = "quiz"  # Timed quiz mode
    MIXED = "mixed"  # Combination of new and review


class SessionStatus(str, Enum):
    """Session status indicators."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SessionConfig:
    """Configuration for a learning session."""

    session_type: SessionType
    max_reviews: int = 50
    max_new_cards: int = 20
    target_retention: float = 0.9
    time_limit_minutes: int | None = None
    categories: list[str] | None = None
    shuffle_questions: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_reviews <= 0:
            raise ValueError("max_reviews must be positive")
        if self.max_new_cards <= 0:
            raise ValueError("max_new_cards must be positive")
        if not 0.0 <= self.target_retention <= 1.0:
            raise ValueError("target_retention must be between 0.0 and 1.0")


@dataclass
class QuestionPresentation:
    """Data structure for presenting a question to the user."""

    question: Question
    card: FSRSCard
    question_number: int
    total_questions: int
    category: str
    difficulty_rating: str  # "New", "Learning", "Review", "Hard"
    last_review_date: datetime | None
    predicted_retention: float
    time_since_last_review_days: int | None


@dataclass
class SessionProgress:
    """Current progress within a learning session."""

    session_id: int
    questions_total: int
    questions_completed: int
    questions_correct: int
    questions_incorrect: int
    questions_skipped: int
    average_response_time_ms: int
    current_retention_rate: float
    estimated_time_remaining_minutes: int
    session_start_time: datetime
    elapsed_time_minutes: int


@dataclass
class StartSessionRequest:
    """Request DTO for starting a learning session."""

    config: SessionConfig
    user_id: int = 1

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not isinstance(self.config, SessionConfig):
            raise ValueError("config must be a valid SessionConfig")


@dataclass
class StartSessionResult:
    """Result DTO for starting a learning session."""

    success: bool
    session_id: int
    questions: list[QuestionPresentation]
    initial_progress: SessionProgress
    error_message: str | None = None


@dataclass
class SubmitAnswerRequest:
    """Request DTO for submitting an answer during a session."""

    session_id: int
    card_id: int
    user_answer: str | None  # A, B, C, D, or None for skipped
    response_time_ms: int
    rating: FSRSRating | None = None  # Optional explicit rating

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.session_id <= 0:
            raise ValueError("session_id must be positive")
        if self.card_id <= 0:
            raise ValueError("card_id must be positive")
        if self.response_time_ms < 0:
            raise ValueError("response_time_ms must be non-negative")
        if self.user_answer is not None and self.user_answer not in [
            "A",
            "B",
            "C",
            "D",
        ]:
            raise ValueError("user_answer must be A, B, C, D, or None")


@dataclass
class SubmitAnswerResult:
    """Result DTO for submitting an answer."""

    success: bool
    is_correct: bool
    is_skipped: bool
    auto_rating: FSRSRating
    schedule_result: Any  # ScheduleCardResult
    updated_progress: SessionProgress
    error_message: str | None = None


@dataclass
class CompleteSessionRequest:
    """Request DTO for completing a learning session."""

    session_id: int

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.session_id <= 0:
            raise ValueError("session_id must be positive")


@dataclass
class CompleteSessionResult:
    """Result DTO for completing a learning session."""

    success: bool
    session_summary: dict[str, Any]
    error_message: str | None = None


class CompleteLearningSession(
    DomainService[
        StartSessionRequest | SubmitAnswerRequest | CompleteSessionRequest,
        StartSessionResult | SubmitAnswerResult | CompleteSessionResult,
    ]
):
    """Domain service for complete learning session management.

    This service encapsulates all business logic for:
    - Starting learning sessions with proper question selection
    - Processing answers and updating session progress
    - Managing session state and calculating metrics
    - Completing sessions with comprehensive summaries
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        schedule_card_service: ScheduleCard,
        event_bus: EventBus,
    ) -> None:
        """Initialize the learning session domain service.

        Args:
            db_manager: Database manager for data persistence
            schedule_card_service: Domain service for FSRS card scheduling
            event_bus: Event bus for publishing domain events
        """
        super().__init__(event_bus)
        self.db_manager = db_manager
        self.schedule_card_service = schedule_card_service
        self._active_sessions: dict[int, SessionProgress] = {}

    @log_domain_operation
    async def call(
        self,
        request: StartSessionRequest | SubmitAnswerRequest | CompleteSessionRequest,
    ) -> StartSessionResult | SubmitAnswerResult | CompleteSessionResult:
        """Execute learning session operation based on request type.

        Args:
            request: Domain request for session operation

        Returns:
            Result of the session operation

        Raises:
            ValidationError: If request validation fails
            BusinessRuleViolationError: If business rules are violated
        """
        try:
            if isinstance(request, StartSessionRequest):
                return await self._start_session(request)
            elif isinstance(request, SubmitAnswerRequest):
                return await self._submit_answer(request)
            elif isinstance(request, CompleteSessionRequest):
                return await self._complete_session(request)
            else:
                raise ValidationError(f"Unsupported request type: {type(request)}")

        except Exception as e:
            logger.error(f"Failed to process session request: {e}")
            if isinstance(request, StartSessionRequest):
                return StartSessionResult(
                    success=False,
                    session_id=0,
                    questions=[],
                    initial_progress=self._create_empty_progress(),
                    error_message=str(e),
                )
            elif isinstance(request, SubmitAnswerRequest):
                return SubmitAnswerResult(
                    success=False,
                    is_correct=False,
                    is_skipped=True,
                    auto_rating=FSRSRating.AGAIN,
                    schedule_result=None,
                    updated_progress=self._create_empty_progress(),
                    error_message=str(e),
                )
            else:  # CompleteSessionRequest
                return CompleteSessionResult(
                    success=False,
                    session_summary={},
                    error_message=str(e),
                )

    async def _start_session(self, request: StartSessionRequest) -> StartSessionResult:
        """Start a new learning session with question selection."""
        logger.info(
            f"Starting {request.config.session_type.value} session for user {request.user_id}"
        )

        # Create session in database
        session_id = self.db_manager.create_learning_session(
            session_type=request.config.session_type.value,
            user_id=request.user_id,
            target_retention=request.config.target_retention,
            max_reviews=request.config.max_reviews,
        )

        # Get questions based on session type
        questions = await self._get_session_questions(request.config, request.user_id)

        # Create session progress tracking
        initial_progress = SessionProgress(
            session_id=session_id,
            questions_total=len(questions),
            questions_completed=0,
            questions_correct=0,
            questions_incorrect=0,
            questions_skipped=0,
            average_response_time_ms=0,
            current_retention_rate=0.0,
            estimated_time_remaining_minutes=self._estimate_session_time(
                len(questions)
            ),
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=0,
        )

        self._active_sessions[session_id] = initial_progress

        # Publish domain event
        await self.event_bus.publish(
            SessionStartedEvent(
                session_id=session_id,
                user_id=request.user_id,
                session_type=request.config.session_type.value,
                target_retention=request.config.target_retention,
                max_reviews=request.config.max_reviews,
            )
        )

        logger.info(f"Started session {session_id} with {len(questions)} questions")

        return StartSessionResult(
            success=True,
            session_id=session_id,
            questions=questions,
            initial_progress=initial_progress,
        )

    async def _submit_answer(self, request: SubmitAnswerRequest) -> SubmitAnswerResult:
        """Process an answer submission during a learning session."""
        if request.session_id not in self._active_sessions:
            raise BusinessRuleViolationError(
                f"Session {request.session_id} not found or not active"
            )

        # Get card and question to check correctness
        card = self.db_manager.get_fsrs_card_by_id(request.card_id)
        if not card:
            raise ValidationError(f"Card {request.card_id} not found")

        question = self.db_manager.get_question(card.question_id)
        if not question:
            raise ValidationError(f"Question {card.question_id} not found")

        # Determine if answer is correct
        is_correct = (
            request.user_answer == question.correct if request.user_answer else False
        )
        is_skipped = request.user_answer is None

        # Auto-determine FSRS rating if not provided
        auto_rating = self._determine_rating(
            request.rating, is_correct, is_skipped, request.response_time_ms
        )

        # Process review with domain service
        schedule_request = ScheduleCardRequest(
            card_id=request.card_id,
            rating=auto_rating,
            response_time_ms=request.response_time_ms,
            session_id=request.session_id,
        )

        schedule_result = await self.schedule_card_service.call(schedule_request)

        # Update session progress
        updated_progress = self._update_session_progress(
            request.session_id, is_correct, is_skipped, request.response_time_ms
        )

        logger.info(
            f"Processed answer for card {request.card_id}: "
            f"correct={is_correct}, rating={auto_rating.value}"
        )

        return SubmitAnswerResult(
            success=True,
            is_correct=is_correct,
            is_skipped=is_skipped,
            auto_rating=auto_rating,
            schedule_result=schedule_result,
            updated_progress=updated_progress,
        )

    async def _complete_session(
        self, request: CompleteSessionRequest
    ) -> CompleteSessionResult:
        """Complete a learning session and generate summary statistics."""
        if request.session_id not in self._active_sessions:
            raise BusinessRuleViolationError(f"Session {request.session_id} not found")

        # End session in database
        self.db_manager.end_learning_session(request.session_id)

        # Get final progress
        progress = self._active_sessions[request.session_id]

        # Calculate final statistics
        session_summary = self._calculate_session_summary(progress)

        # Publish completion event
        await self.event_bus.publish(
            SessionCompletedEvent(
                session_id=request.session_id,
                user_id=1,  # TODO: Get from session data
                duration_seconds=progress.elapsed_time_minutes * 60,
                questions_reviewed=progress.questions_completed,
                questions_correct=progress.questions_correct,
                new_cards_learned=0,  # TODO: Track new cards separately
                retention_rate=progress.current_retention_rate,
            )
        )

        # Remove from active sessions
        del self._active_sessions[request.session_id]

        logger.info(f"Completed session {request.session_id}")

        return CompleteSessionResult(
            success=True,
            session_summary=session_summary,
        )

    def _determine_rating(
        self,
        explicit_rating: FSRSRating | None,
        is_correct: bool,
        is_skipped: bool,
        response_time_ms: int,
    ) -> FSRSRating:
        """Determine FSRS rating based on performance and response time."""
        if explicit_rating is not None:
            return explicit_rating

        if is_skipped:
            return FSRSRating.AGAIN  # Treat skipped as failed

        if is_correct:
            # Auto-rate based on response time (simple heuristic)
            if response_time_ms < 3000:  # < 3 seconds
                return FSRSRating.EASY
            elif response_time_ms < 8000:  # < 8 seconds
                return FSRSRating.GOOD
            else:  # > 8 seconds
                return FSRSRating.HARD
        else:
            return FSRSRating.AGAIN

    async def _get_session_questions(
        self, config: SessionConfig, user_id: int
    ) -> list[QuestionPresentation]:
        """Get questions for the session based on configuration."""
        questions = []

        if config.session_type == SessionType.REVIEW:
            # Get due cards
            due_cards = self._get_due_cards(limit=config.max_reviews, user_id=user_id)
            for card in due_cards:
                question = self.db_manager.get_question(card.question_id)
                if question:
                    presentation = self._create_question_presentation(
                        question, card, len(questions) + 1, config.max_reviews
                    )
                    questions.append(presentation)

        elif config.session_type == SessionType.LEARN:
            # Get new cards (cards that haven't been reviewed)
            with self.db_manager.get_session() as session:
                new_cards = (
                    session.query(FSRSCard)
                    .filter(FSRSCard.user_id == user_id, FSRSCard.review_count == 0)
                    .limit(config.max_new_cards)
                    .all()
                )

                for card in new_cards:
                    question = self.db_manager.get_question(card.question_id)
                    if question:
                        presentation = self._create_question_presentation(
                            question, card, len(questions) + 1, config.max_new_cards
                        )
                        questions.append(presentation)

        elif config.session_type == SessionType.WEAK_FOCUS:
            # Get cards with low retention or high lapse count
            with self.db_manager.get_session() as session:
                weak_cards = (
                    session.query(FSRSCard)
                    .filter(FSRSCard.user_id == user_id, FSRSCard.lapse_count >= 3)
                    .order_by(FSRSCard.lapse_count.desc())
                    .limit(config.max_reviews)
                    .all()
                )

                for card in weak_cards:
                    question = self.db_manager.get_question(card.question_id)
                    if question:
                        presentation = self._create_question_presentation(
                            question, card, len(questions) + 1, len(weak_cards)
                        )
                        questions.append(presentation)

        return questions

    def _create_question_presentation(
        self, question: Question, card: FSRSCard, question_num: int, total: int
    ) -> QuestionPresentation:
        """Create a question presentation from question and card data."""
        predicted_retention = self._predict_retention(card)
        difficulty_rating = self._get_difficulty_rating(card)

        last_review = None
        days_since_review = None
        if card.last_review_date:
            last_review = datetime.fromtimestamp(card.last_review_date, UTC)
            days_since_review = (datetime.now(UTC) - last_review).days

        return QuestionPresentation(
            question=question,
            card=card,
            question_number=question_num,
            total_questions=total,
            category=question.category,
            difficulty_rating=difficulty_rating,
            last_review_date=last_review,
            predicted_retention=predicted_retention,
            time_since_last_review_days=days_since_review,
        )

    def _get_difficulty_rating(self, card: FSRSCard) -> str:
        """Get human-readable difficulty rating for a card."""
        if card.review_count == 0:
            return "New"
        elif card.lapse_count >= 5:
            return "Very Hard"
        elif card.lapse_count >= 3:
            return "Hard"
        elif card.review_count < 3:
            return "Learning"
        else:
            return "Review"

    def _update_session_progress(
        self, session_id: int, is_correct: bool, is_skipped: bool, response_time_ms: int
    ) -> SessionProgress:
        """Update session progress after answering a question."""
        progress = self._active_sessions[session_id]

        progress.questions_completed += 1

        if is_skipped:
            progress.questions_skipped += 1
        elif is_correct:
            progress.questions_correct += 1
        else:
            progress.questions_incorrect += 1

        # Update average response time
        if progress.questions_completed == 1:
            progress.average_response_time_ms = response_time_ms
        else:
            # Rolling average
            total_time = progress.average_response_time_ms * (
                progress.questions_completed - 1
            )
            progress.average_response_time_ms = int(
                (total_time + response_time_ms) / progress.questions_completed
            )

        # Update retention rate
        if progress.questions_completed > progress.questions_skipped:
            answered_questions = (
                progress.questions_completed - progress.questions_skipped
            )
            progress.current_retention_rate = (
                progress.questions_correct / answered_questions
            )
        else:
            progress.current_retention_rate = 0.0

        # Update elapsed time
        elapsed = datetime.now(UTC) - progress.session_start_time
        progress.elapsed_time_minutes = int(elapsed.total_seconds() / 60)

        # Update estimated remaining time
        if progress.questions_completed > 0:
            avg_time_per_question = (
                progress.elapsed_time_minutes / progress.questions_completed
            )
            remaining_questions = (
                progress.questions_total - progress.questions_completed
            )
            progress.estimated_time_remaining_minutes = int(
                avg_time_per_question * remaining_questions
            )

        return progress

    def _calculate_session_summary(self, progress: SessionProgress) -> dict[str, Any]:
        """Calculate comprehensive session summary statistics."""
        accuracy = (
            (progress.questions_correct / progress.questions_completed * 100)
            if progress.questions_completed > 0
            else 0
        )

        return {
            "session_id": progress.session_id,
            "questions_completed": progress.questions_completed,
            "accuracy_percentage": round(accuracy, 1),
            "correct_answers": progress.questions_correct,
            "incorrect_answers": progress.questions_incorrect,
            "skipped": progress.questions_skipped,
            "total_time_minutes": progress.elapsed_time_minutes,
            "average_response_time_ms": progress.average_response_time_ms,
            "retention_rate": progress.current_retention_rate,
            "completion_rate": round(
                progress.questions_completed / progress.questions_total * 100, 1
            ),
        }

    def _estimate_session_time(self, num_questions: int) -> int:
        """Estimate session completion time in minutes."""
        # Estimate 30 seconds per question on average
        return max(1, int(num_questions * 0.5))

    def _get_due_cards(self, limit: int = 50, user_id: int = 1) -> list[FSRSCard]:
        """Get cards due for review."""
        return self.db_manager.get_due_fsrs_cards(user_id=user_id, limit=limit)

    def _predict_retention(self, card: FSRSCard, days_ahead: int = 1) -> float:
        """Predict retention rate for a card after specified days."""
        if card.stability <= 0:
            return 0.0

        # R = exp(-t/S) where t=time, S=stability
        return math.exp(-days_ahead / card.stability)

    def _create_empty_progress(self) -> SessionProgress:
        """Create empty session progress for error cases."""
        return SessionProgress(
            session_id=0,
            questions_total=0,
            questions_completed=0,
            questions_correct=0,
            questions_incorrect=0,
            questions_skipped=0,
            average_response_time_ms=0,
            current_retention_rate=0.0,
            estimated_time_remaining_minutes=0,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=0,
        )
