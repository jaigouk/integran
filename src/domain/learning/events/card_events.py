"""Learning Context specific domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.infrastructure.messaging.event_bus import DomainEvent


@dataclass
class CardScheduledEvent(DomainEvent):
    """Event emitted when a card is scheduled using FSRS algorithm."""

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
