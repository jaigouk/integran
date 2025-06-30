"""Abstract repository interfaces for domain layer.

This module defines repository interfaces that domain services depend on,
following the dependency inversion principle. Concrete implementations
are provided in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.content.models.question_models import Question
    from src.domain.learning.models.learning_models import FSRSCard, LearningSession
    from src.domain.user.models.user_models import UserSettings


class RepositoryError(Exception):
    """Exception raised by repository operations."""

    def __init__(self, message: str, error_code: str | None = None):
        """Initialize repository error."""
        super().__init__(message)
        self.error_code = error_code


class QuestionRepository(ABC):
    """Repository interface for question-related data operations."""

    @abstractmethod
    async def get_question_by_id(self, question_id: int) -> Question | None:
        """Get a single question by ID."""
        pass

    @abstractmethod
    async def get_questions_by_category(self, category: str) -> list[Question]:
        """Get all questions in a specific category."""
        pass

    @abstractmethod
    async def get_questions_for_review(
        self, user_id: int, limit: int = 10
    ) -> list[Question]:
        """Get questions due for review for a specific user."""
        pass

    @abstractmethod
    async def get_all_questions(self) -> list[Question]:
        """Get all questions in the database."""
        pass

    @abstractmethod
    async def get_image_questions(self) -> list[Question]:
        """Get all questions that have images."""
        pass

    @abstractmethod
    async def get_questions_by_state(self, state: str | None = None) -> list[Question]:
        """Get questions filtered by federal state.

        Args:
            state: Federal state name (e.g., "Baden-Württemberg").
                  If None, returns general questions (no state restriction).

        Returns:
            List of questions for the specified state or general questions.
        """
        pass

    @abstractmethod
    async def get_questions_for_active_learning(
        self,
        user_id: int = 1,
        desired_retention: float = 0.90,
        stability_threshold: int = 30,
        retrievability_threshold: float = 0.9,
        include_leeches: bool = True,
        limit: int = 100,
    ) -> list[Question]:
        """Get questions that need active learning (excludes well-mastered questions).

        Args:
            user_id: User ID for FSRS card lookup
            desired_retention: Target retention rate (affects what's considered 'due')
            stability_threshold: Days of stability above which questions are considered mastered
            retrievability_threshold: Retrievability above which questions are excluded
            include_leeches: Whether to include questions with high lapse counts
            limit: Maximum number of questions to return

        Returns:
            List of questions needing practice, prioritized by learning urgency
        """
        pass

    @abstractmethod
    async def save_question(self, question: Question) -> Question:
        """Save or update a question."""
        pass


class UserRepository(ABC):
    """Repository interface for user-related data operations."""

    @abstractmethod
    async def get_user_settings(self, user_id: int) -> UserSettings | None:
        """Get user settings by user ID."""
        pass

    @abstractmethod
    async def save_user_settings(self, user_settings: UserSettings) -> UserSettings:
        """Save or update user settings."""
        pass

    @abstractmethod
    async def delete_user_data(self, user_id: int) -> int:
        """Delete all user data and return count of deleted items."""
        pass

    @abstractmethod
    async def user_exists(self, user_id: int) -> bool:
        """Check if a user exists."""
        pass


class LearningRepository(ABC):
    """Repository interface for learning-related data operations."""

    @abstractmethod
    async def get_fsrs_card(self, question_id: int, user_id: int) -> FSRSCard | None:
        """Get FSRS card for a specific question and user."""
        pass

    @abstractmethod
    async def save_fsrs_card(self, card: FSRSCard) -> FSRSCard:
        """Save or update an FSRS card."""
        pass

    @abstractmethod
    async def get_due_cards(self, user_id: int, limit: int = 10) -> list[FSRSCard]:
        """Get cards due for review for a specific user."""
        pass

    @abstractmethod
    async def count_due_cards(self, user_id: int) -> int:
        """Count cards due for review for a specific user."""
        pass

    @abstractmethod
    async def delete_user_learning_data(self, user_id: int) -> dict[str, int]:
        """Delete all learning data for a user and return counts."""
        pass

    @abstractmethod
    async def get_learning_session(self, session_id: int) -> LearningSession | None:
        """Get a learning session by ID."""
        pass

    @abstractmethod
    async def save_learning_session(self, session: LearningSession) -> LearningSession:
        """Save or update a learning session."""
        pass

    @abstractmethod
    async def get_active_sessions(self, user_id: int) -> list[LearningSession]:
        """Get active learning sessions for a user."""
        pass

    @abstractmethod
    async def get_fsrs_card_by_id(self, card_id: int) -> FSRSCard | None:
        """Get FSRS card by card ID."""
        pass

    @abstractmethod
    async def update_fsrs_card_state(
        self,
        card_id: int,
        difficulty: float,
        stability: float,
        retrievability: float,
        state: int,
        next_review_date: float,
    ) -> None:
        """Update FSRS card state after review."""
        pass

    @abstractmethod
    async def increment_lapse_count(self, card_id: int) -> None:
        """Increment lapse count for a card."""
        pass

    @abstractmethod
    async def record_review_history(
        self,
        card_id: int,
        question_id: int,
        rating: int,
        response_time_ms: int,
        difficulty_before: float,
        stability_before: float,
        retrievability_before: float,
        difficulty_after: float,
        stability_after: float,
        retrievability_after: float,
        next_interval_days: float,
        session_id: int | None = None,
    ) -> None:
        """Record review in history."""
        pass


class AnalyticsRepository(ABC):
    """Repository interface for analytics-related data operations."""

    @abstractmethod
    async def get_learning_stats(self, user_id: int) -> dict[str, Any]:
        """Get comprehensive learning statistics for a user."""
        pass

    @abstractmethod
    async def get_session_progress(self, user_id: int) -> dict[str, Any]:
        """Get session progress data for a user."""
        pass

    @abstractmethod
    async def save_user_progress(
        self, user_id: int, progress_data: dict[str, Any]
    ) -> None:
        """Save user progress data."""
        pass

    @abstractmethod
    async def delete_user_analytics(self, user_id: int) -> dict[str, int]:
        """Delete all analytics data for a user and return counts."""
        pass

    @abstractmethod
    async def get_category_progress(self, user_id: int) -> dict[str, Any]:
        """Get progress by category for a user."""
        pass

    @abstractmethod
    async def record_question_attempt(
        self,
        user_id: int,
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
        session_id: int | None = None,
    ) -> None:
        """Record a question attempt."""
        pass

    @abstractmethod
    async def get_hourly_session_stats(
        self, user_id: int, days: int = 30
    ) -> dict[int, dict[str, Any]]:
        """Get session statistics grouped by hour of day for time-based analysis.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dict mapping hour (0-23) to session stats (count, total_duration, avg_accuracy)
        """
        pass

    @abstractmethod
    async def get_daily_study_patterns(
        self, user_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get daily study patterns with session times and performance.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of daily study data with timestamps, duration, and performance
        """
        pass

    @abstractmethod
    async def get_fsrs_card_statistics(self, user_id: int) -> dict[str, Any]:
        """Get FSRS card state distribution statistics.

        Args:
            user_id: User ID

        Returns:
            Dict with counts of cards in each FSRS state (new, learning, review, relearning)
        """
        pass

    @abstractmethod
    async def get_stability_distribution(self, user_id: int) -> dict[str, Any]:
        """Get stability distribution for FSRS cards.

        Args:
            user_id: User ID

        Returns:
            Dict with stability ranges and statistics
        """
        pass

    @abstractmethod
    async def get_retrievability_distribution(self, user_id: int) -> dict[str, Any]:
        """Get retrievability distribution for FSRS cards.

        Args:
            user_id: User ID

        Returns:
            Dict with retrievability ranges and statistics
        """
        pass

    @abstractmethod
    async def get_leech_statistics(self, user_id: int) -> dict[str, Any]:
        """Get leech card statistics and analysis.

        Args:
            user_id: User ID

        Returns:
            Dict with leech counts, categories, and difficult questions
        """
        pass

    @abstractmethod
    async def get_performance_trends(self, user_id: int) -> dict[str, Any]:
        """Get FSRS performance trends over time.

        Args:
            user_id: User ID

        Returns:
            Dict with retention rates, graduation statistics, and trends
        """
        pass


class SessionRepository(ABC):
    """Repository interface for session-related data operations."""

    @abstractmethod
    async def create_session(
        self,
        user_id: int,
        session_type: str,
        configuration: dict[str, Any],
    ) -> int:
        """Create a new session and return session ID."""
        pass

    @abstractmethod
    async def end_session(
        self,
        session_id: int,
        end_time: datetime,
        summary: dict[str, Any],
    ) -> None:
        """End a session with summary data."""
        pass

    @abstractmethod
    async def get_session_statistics(self, user_id: int) -> dict[str, Any]:
        """Get session statistics for a user."""
        pass

    @abstractmethod
    async def delete_user_sessions(self, user_id: int) -> dict[str, int]:
        """Delete all sessions for a user and return counts."""
        pass

    @abstractmethod
    async def update_session_status(self, session_id: int, status: str) -> None:
        """Update the status of a session."""
        pass

    @abstractmethod
    async def update_session_progress(
        self,
        session_id: int,
        total_questions: int,
        correct_answers: int,
        incorrect_answers: int,
    ) -> None:
        """Update session progress during practice."""
        pass

    @abstractmethod
    async def get_pause_duration(self, session_id: int) -> int | None:
        """Get total pause duration for a session in seconds."""
        pass

    @abstractmethod
    async def get_session_by_id(self, session_id: int) -> dict[str, Any] | None:
        """Get session data by session ID."""
        pass


class ImageRepository(ABC):
    """Repository interface for image-related data operations."""

    @abstractmethod
    async def get_image_data(self, path: str) -> bytes | None:
        """Get image data by path."""
        pass

    @abstractmethod
    async def validate_image_exists(self, path: str) -> bool:
        """Check if image file exists."""
        pass

    @abstractmethod
    async def get_image_metadata(self, path: str) -> dict[str, Any] | None:
        """Get image metadata (size, format, etc.)."""
        pass

    @abstractmethod
    async def list_available_images(self, directory: str = "data/images") -> list[str]:
        """List all available image files in directory."""
        pass
