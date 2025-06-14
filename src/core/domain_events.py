"""Core domain events for cross-context communication.

This module defines the domain events that enable communication between
bounded contexts in the DDD architecture. Events are processed in-memory
for optimal performance in local-first applications.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.event_bus import DomainEvent

# =============================================================================
# Learning Context Events
# =============================================================================


@dataclass
class CardScheduledEvent(DomainEvent):
    """Event emitted when a card is scheduled using FSRS algorithm.

    This event is published by the ScheduleCard domain service when
    a card's review schedule is successfully updated.
    """

    card_id: int
    question_id: int
    new_difficulty: float
    new_stability: float
    new_retrievability: float
    next_review_date: datetime
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    response_time_ms: int
    session_id: int | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class SessionStartedEvent(DomainEvent):
    """Event emitted when a learning session begins."""

    session_id: int
    user_id: int
    session_type: str  # 'review', 'learn', 'weak_focus', 'quiz'
    target_retention: float
    max_reviews: int

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class SessionCompletedEvent(DomainEvent):
    """Event emitted when a learning session ends."""

    session_id: int
    user_id: int
    duration_seconds: int
    questions_reviewed: int
    questions_correct: int
    new_cards_learned: int
    retention_rate: float

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class ProgressTrackedEvent(DomainEvent):
    """Event emitted when user progress is updated."""

    user_id: int
    date: str  # YYYY-MM-DD format
    reviews_completed: int
    new_cards_learned: int
    retention_rate: float
    study_streak_days: int

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# Content Context Events
# =============================================================================


@dataclass
class AnswerGeneratedEvent(DomainEvent):
    """Event emitted when multilingual answers are generated for a question."""

    question_id: int
    languages: list[str]  # ['en', 'de', 'tr', 'uk', 'ar']
    generation_time_ms: int
    success: bool
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class ImageProcessedEvent(DomainEvent):
    """Event emitted when image processing is completed."""

    question_id: int
    image_paths: list[str]
    descriptions: list[str]
    processing_time_ms: int
    success: bool
    ai_model_used: str | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class QuestionLoadedEvent(DomainEvent):
    """Event emitted when questions are loaded from dataset."""

    question_count: int
    categories: list[str]
    image_question_count: int
    language: str
    source_file: str

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# Analytics Context Events
# =============================================================================


@dataclass
class LeechDetectedEvent(DomainEvent):
    """Event emitted when a card is identified as a leech.

    A leech is a difficult question that has been failed
    multiple times and requires special attention.
    """

    card_id: int
    question_id: int
    lapse_count: int
    leech_threshold: int
    recommended_action: str  # 'suspend', 'note_added', 'modified'
    difficulty_level: str  # 'new', 'hard', 'learning', 'review'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class PerformanceAnalyzedEvent(DomainEvent):
    """Event emitted when performance analysis is completed."""

    user_id: int
    analysis_period_days: int
    retention_rate: float
    weak_categories: list[str]
    strong_categories: list[str]
    recommendations: list[str]

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class InterleavingOptimizedEvent(DomainEvent):
    """Event emitted when interleaving strategy is optimized."""

    session_id: int
    strategy_used: str  # 'random', 'similarity_based', 'contrast_based', etc.
    categories_mixed: list[str]
    optimization_score: float
    question_count: int

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# User Context Events
# =============================================================================


@dataclass
class SettingsSavedEvent(DomainEvent):
    """Event emitted when user settings are updated."""

    user_id: int
    setting_key: str
    old_value: str | None
    new_value: str
    setting_type: str  # 'string', 'integer', 'boolean', 'json'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class DataExportedEvent(DomainEvent):
    """Event emitted when user data is exported."""

    user_id: int
    export_type: str  # 'full', 'progress_only', 'settings_only'
    file_path: str
    record_count: int
    file_size_bytes: int

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class DataImportedEvent(DomainEvent):
    """Event emitted when user data is imported."""

    user_id: int
    import_type: str  # 'full', 'progress_only', 'settings_only'
    source_file: str
    records_imported: int
    conflicts_resolved: int
    import_strategy: str  # 'merge', 'overwrite', 'skip_conflicts'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# System Events
# =============================================================================


@dataclass
class SystemErrorEvent(DomainEvent):
    """Event emitted when system-level errors occur."""

    error_type: str
    error_message: str
    component: str  # Component where error occurred
    severity: str  # 'low', 'medium', 'high', 'critical'
    stack_trace: str | None = None
    user_id: int | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class DatabaseMigrationEvent(DomainEvent):
    """Event emitted during database migration operations."""

    migration_version: str
    migration_type: str  # 'schema', 'data', 'index'
    success: bool
    duration_ms: int
    records_affected: int | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# Event Factory Functions
# =============================================================================


def create_card_scheduled_event(
    card_id: int,
    question_id: int,
    fsrs_result: Any,  # FSRSResult from models
    rating: int,
    response_time_ms: int,
    session_id: int | None = None,
) -> CardScheduledEvent:
    """Factory function to create CardScheduledEvent from FSRS result.

    Args:
        card_id: ID of the scheduled card
        question_id: ID of the associated question
        fsrs_result: Result object from FSRS algorithm
        rating: User rating (1-4)
        response_time_ms: Time taken to answer
        session_id: Optional session ID

    Returns:
        Properly formatted CardScheduledEvent
    """
    return CardScheduledEvent(
        card_id=card_id,
        question_id=question_id,
        new_difficulty=fsrs_result.difficulty,
        new_stability=fsrs_result.stability,
        new_retrievability=fsrs_result.retrievability,
        next_review_date=fsrs_result.next_review_date,
        rating=rating,
        response_time_ms=response_time_ms,
        session_id=session_id,
    )


def create_leech_detected_event(
    card_id: int,
    question_id: int,
    lapse_count: int,
    leech_threshold: int = 8,
    difficulty_level: str = "unknown",
) -> LeechDetectedEvent:
    """Factory function to create LeechDetectedEvent.

    Args:
        card_id: ID of the leech card
        question_id: ID of the associated question
        lapse_count: Number of times the card was failed
        leech_threshold: Threshold for leech detection
        difficulty_level: Current difficulty level of the card

    Returns:
        Properly formatted LeechDetectedEvent
    """
    # Determine recommended action based on lapse count
    if lapse_count >= leech_threshold * 2:
        recommended_action = "suspend"
    elif lapse_count >= leech_threshold * 1.5:
        recommended_action = "modified"
    else:
        recommended_action = "note_added"

    return LeechDetectedEvent(
        card_id=card_id,
        question_id=question_id,
        lapse_count=lapse_count,
        leech_threshold=leech_threshold,
        recommended_action=recommended_action,
        difficulty_level=difficulty_level,
    )
