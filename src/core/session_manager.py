"""Learning session orchestration and management.

This module manages learning sessions, coordinating between FSRS scheduling,
question presentation, and progress tracking for optimal learning experiences.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core.database import DatabaseManager
from src.core.learning.domain.services.schedule_card import (
    ScheduleCard,
    ScheduleCardRequest,
    ScheduleCardResult,
)
from src.core.models import FSRSCard, FSRSRating, Question


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


class SessionManager:
    """Manages learning session lifecycle and coordination."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        schedule_card_service: ScheduleCard,
    ) -> None:
        """Initialize session manager.

        Args:
            db_manager: Database manager instance
            schedule_card_service: Domain service for card scheduling
        """
        self.db_manager = db_manager
        self.schedule_card_service = schedule_card_service
        self._active_sessions: dict[int, SessionProgress] = {}

    def start_session(
        self,
        config: SessionConfig,
        user_id: int = 1,
    ) -> tuple[int, list[QuestionPresentation]]:
        """Start a new learning session.

        Args:
            config: Session configuration
            user_id: User ID

        Returns:
            Tuple of (session_id, question_list)
        """
        # Create session in database
        session_id = self.db_manager.create_learning_session(
            session_type=config.session_type.value,
            user_id=user_id,
            target_retention=config.target_retention,
            max_reviews=config.max_reviews,
        )

        # Get questions based on session type
        questions = self._get_session_questions(config, user_id)

        # Create session progress tracking
        self._active_sessions[session_id] = SessionProgress(
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

        return session_id, questions

    async def submit_answer(
        self,
        session_id: int,
        card_id: int,
        user_answer: str | None,
        response_time_ms: int,
        rating: FSRSRating | None = None,
    ) -> ScheduleCardResult:
        """Submit an answer for a question in the session.

        Args:
            session_id: Session ID
            card_id: Card ID being answered
            user_answer: User's answer (A, B, C, D, or None for skipped)
            response_time_ms: Time taken to answer
            rating: Optional FSRS difficulty rating

        Returns:
            Schedule card result with updated scheduling
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found or not active")

        # Get card and question to check correctness
        card = self.db_manager.get_fsrs_card_by_id(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")

        question = self.db_manager.get_question(card.question_id)
        if not question:
            raise ValueError(f"Question {card.question_id} not found")

        # Determine if answer is correct
        is_correct = user_answer == question.correct if user_answer else False
        is_skipped = user_answer is None

        # Auto-determine FSRS rating if not provided
        if rating is None:
            if is_skipped:
                rating = FSRSRating.AGAIN  # Treat skipped as failed
            elif is_correct:
                # Auto-rate based on response time (simple heuristic)
                if response_time_ms < 3000:  # < 3 seconds
                    rating = FSRSRating.EASY
                elif response_time_ms < 8000:  # < 8 seconds
                    rating = FSRSRating.GOOD
                else:  # > 8 seconds
                    rating = FSRSRating.HARD
            else:
                rating = FSRSRating.AGAIN

        # Process review with domain service
        request = ScheduleCardRequest(
            card_id=card_id,
            rating=rating,
            response_time_ms=response_time_ms,
            session_id=session_id,
        )

        schedule_result = await self.schedule_card_service.call(request)

        # Update session progress
        self._update_session_progress(
            session_id, is_correct, is_skipped, response_time_ms
        )

        return schedule_result

    def get_session_progress(self, session_id: int) -> SessionProgress:
        """Get current session progress.

        Args:
            session_id: Session ID

        Returns:
            Current session progress
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")

        progress = self._active_sessions[session_id]

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

    def end_session(self, session_id: int) -> dict[str, Any]:
        """End a learning session and return summary statistics.

        Args:
            session_id: Session ID

        Returns:
            Session summary statistics
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")

        # End session in database
        self.db_manager.end_learning_session(session_id)

        # Get final progress
        progress = self._active_sessions[session_id]

        # Calculate final statistics
        accuracy = (
            (progress.questions_correct / progress.questions_completed * 100)
            if progress.questions_completed > 0
            else 0
        )

        summary = {
            "session_id": session_id,
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

        # Remove from active sessions
        del self._active_sessions[session_id]

        return summary

    def pause_session(self, session_id: int) -> None:
        """Pause an active session.

        Args:
            session_id: Session ID
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")

        # For now, just keep session in memory
        # TODO: Implement pause/resume functionality

    def get_next_question(self, session_id: int) -> QuestionPresentation | None:
        """Get the next question in the session.

        Args:
            session_id: Session ID

        Returns:
            Next question presentation or None if session complete
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")

        progress = self._active_sessions[session_id]

        if progress.questions_completed >= progress.questions_total:
            return None

        # Get due cards for this session
        due_cards = self._get_due_cards(limit=1)
        if not due_cards:
            return None

        card = due_cards[0]
        question = self.db_manager.get_question(card.question_id)
        if not question:
            return None

        # Calculate presentation metadata
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
            question_number=progress.questions_completed + 1,
            total_questions=progress.questions_total,
            category=question.category,
            difficulty_rating=difficulty_rating,
            last_review_date=last_review,
            predicted_retention=predicted_retention,
            time_since_last_review_days=days_since_review,
        )

    def _get_session_questions(
        self, config: SessionConfig, user_id: int
    ) -> list[QuestionPresentation]:
        """Get questions for the session based on configuration.

        Args:
            config: Session configuration
            user_id: User ID

        Returns:
            List of question presentations
        """
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
                from src.core.models import FSRSCard

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
                from src.core.models import FSRSCard

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
        """Create a question presentation from question and card data.

        Args:
            question: Question object
            card: FSRS card
            question_num: Question number in session
            total: Total questions in session

        Returns:
            Question presentation
        """
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
        """Get human-readable difficulty rating for a card.

        Args:
            card: FSRS card

        Returns:
            Difficulty rating string
        """
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
    ) -> None:
        """Update session progress after answering a question.

        Args:
            session_id: Session ID
            is_correct: Whether answer was correct
            is_skipped: Whether question was skipped
            response_time_ms: Response time in milliseconds
        """
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

    def _estimate_session_time(self, num_questions: int) -> int:
        """Estimate session completion time in minutes.

        Args:
            num_questions: Number of questions

        Returns:
            Estimated time in minutes
        """
        # Estimate 30 seconds per question on average
        return max(1, int(num_questions * 0.5))

    def _get_due_cards(self, limit: int = 50, user_id: int = 1) -> list[FSRSCard]:
        """Get cards due for review.

        Args:
            limit: Maximum number of cards to return
            user_id: User ID

        Returns:
            List of due cards sorted by priority
        """
        return self.db_manager.get_due_fsrs_cards(user_id=user_id, limit=limit)

    def _predict_retention(self, card: FSRSCard, days_ahead: int = 1) -> float:
        """Predict retention rate for a card after specified days.

        Args:
            card: FSRS card
            days_ahead: Number of days in the future to predict

        Returns:
            Predicted retention probability (0.0-1.0)
        """
        if card.stability <= 0:
            return 0.0

        # R = exp(-t/S) where t=time, S=stability
        return math.exp(-days_ahead / card.stability)
