"""Learning and spaced repetition domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.domain.shared.models import Base, FSRSState

# ============================================================================
# Legacy Learning Models (SM-2 Algorithm)
# ============================================================================


class LearningData(Base):
    """Spaced repetition learning data per question."""

    __tablename__ = "learning_data"

    id = Column(Integer, primary_key=True)
    question_id = Column(
        Integer, ForeignKey("questions.id"), unique=True, nullable=False
    )
    repetitions = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)  # SM-2 algorithm
    interval = Column(Integer, default=1)  # days
    next_review = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_reviewed = Column(DateTime)

    # Relationships
    question = relationship("Question", back_populates="learning_data")

    __table_args__ = (UniqueConstraint("question_id"), {"extend_existing": True})


# ============================================================================
# FSRS Models (Phase 3.0) - Free Spaced Repetition Scheduler
# ============================================================================


class FSRSCard(Base):
    """Individual card learning states using FSRS algorithm."""

    __tablename__ = "fsrs_cards"

    card_id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, default=1)

    # FSRS Core State (DSR Model)
    difficulty = Column(
        Float, nullable=False, default=5.0
    )  # D: Inherent difficulty (0-10)
    stability = Column(Float, nullable=False, default=1.0)  # S: Memory strength (days)
    retrievability = Column(
        Float, nullable=False, default=1.0
    )  # R: Current recall probability (0-1)

    # Learning Progress
    state = Column(
        Integer, nullable=False, default=0
    )  # 0:New, 1:Learning, 2:Review, 3:Relearning
    step_number = Column(Integer, default=0)  # Current learning step
    last_review_date = Column(Float)  # Unix timestamp
    next_review_date = Column(Float)  # Scheduled review time

    # Performance Tracking
    review_count = Column(Integer, default=0)  # Total reviews
    lapse_count = Column(Integer, default=0)  # Number of times forgotten
    success_count = Column(Integer, default=0)  # Successful recalls

    # Metadata
    created_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )
    updated_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )

    # Relationships
    question = relationship("Question")
    reviews = relationship("ReviewHistory", back_populates="card")

    __table_args__ = (
        UniqueConstraint("question_id", "user_id"),
        Index("idx_fsrs_cards_next_review", "next_review_date"),
        Index("idx_fsrs_cards_question", "question_id"),
        Index("idx_fsrs_cards_state", "state"),
        {"extend_existing": True},
    )


class ReviewHistory(Base):
    """Complete review log for FSRS algorithm."""

    __tablename__ = "review_history"

    review_id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("fsrs_cards.card_id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)

    # Review Details
    review_date = Column(Float, nullable=False)  # Unix timestamp
    rating = Column(Integer, nullable=False)  # 1:Again, 2:Hard, 3:Good, 4:Easy
    response_time_ms = Column(Integer)  # Time to answer

    # FSRS State Before Review
    difficulty_before = Column(Float)
    stability_before = Column(Float)
    retrievability_before = Column(Float)

    # FSRS State After Review
    difficulty_after = Column(Float)
    stability_after = Column(Float)
    retrievability_after = Column(Float)
    next_interval_days = Column(Float)

    # Session Context
    session_id = Column(Integer, ForeignKey("learning_sessions.session_id"))
    review_type = Column(String(20))  # 'learn', 'review', 'relearn', 'cram'

    # Relationships
    card = relationship("FSRSCard", back_populates="reviews")
    question = relationship("Question")
    session = relationship("LearningSession", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_history_date", "review_date"),
        Index("idx_review_history_card", "card_id"),
        Index("idx_review_history_session", "session_id"),
        {"extend_existing": True},
    )


class LearningSession(Base):
    """Study session tracking for FSRS system."""

    __tablename__ = "learning_sessions"

    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)

    # Session Details
    start_time = Column(Float, nullable=False)  # Unix timestamp
    end_time = Column(Float)
    duration_seconds = Column(Integer)

    # Session Stats
    questions_reviewed = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    new_cards_learned = Column(Integer, default=0)

    # Session Configuration
    session_type = Column(String(20))  # 'review', 'learn', 'weak_focus', 'quiz'
    target_retention = Column(Float, default=0.9)  # User's retention goal
    max_reviews = Column(Integer, default=50)

    # Performance Metrics
    average_response_time_ms = Column(Integer)
    retention_rate = Column(Float)

    created_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )

    # Relationships
    reviews = relationship("ReviewHistory", back_populates="session")

    __table_args__ = ({"extend_existing": True},)


class AlgorithmConfig(Base):
    """FSRS algorithm parameters and configuration."""

    __tablename__ = "algorithm_config"

    config_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)

    # FSRS Algorithm Parameters (19 parameters for FSRS-5)
    parameters = Column(Text, nullable=False)  # JSON array of 19 floats
    target_retention = Column(Float, default=0.9)
    maximum_interval_days = Column(Integer, default=365)

    # Learning Steps Configuration
    learning_steps = Column(Text, default="[1, 10]")  # JSON: minutes for new cards
    relearning_steps = Column(Text, default="[10]")  # JSON: minutes for forgotten cards

    # Optimization Settings
    optimization_enabled = Column(Boolean, default=True)
    min_reviews_for_optimization = Column(Integer, default=1000)

    created_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )
    updated_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )

    __table_args__ = (UniqueConstraint("user_id"), {"extend_existing": True})


class LeechCard(Base):
    """Difficult question tracking and management."""

    __tablename__ = "leech_cards"

    leech_id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("fsrs_cards.card_id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)

    # Leech Metrics
    lapse_count = Column(Integer, nullable=False)  # Number of times forgotten
    leech_threshold = Column(Integer, default=8)  # Threshold for leech status
    detected_at = Column(Float, nullable=False)

    # Management Actions
    action_taken = Column(String(20))  # 'suspend', 'note_added', 'modified'
    action_date = Column(Float)
    is_suspended = Column(Boolean, default=False)

    # User Notes
    user_notes = Column(Text)

    # Relationships
    card = relationship("FSRSCard")
    question = relationship("Question")

    __table_args__ = (
        Index("idx_leech_cards_detected", "detected_at"),
        {"extend_existing": True},
    )


# ============================================================================
# FSRS Data Classes and Parameters
# ============================================================================


@dataclass
class FSRSParameters:
    """FSRS algorithm parameters."""

    # Default FSRS-5 parameters
    w: list[float] = field(
        default_factory=lambda: [
            0.5701,
            1.4436,
            4.1386,
            10.9355,
            5.1443,
            1.2006,
            0.8627,
            0.0362,
            1.629,
            0.1342,
            1.0166,
            2.1174,
            0.0839,
            0.3204,
            1.4676,
            0.219,
            2.8237,
            0.2188,
            0.9859,
        ]
    )

    @property
    def request_retention(self) -> float:
        """Default target retention rate."""
        return 0.9

    @property
    def maximum_interval(self) -> int:
        """Maximum interval in days."""
        return 36500  # 100 years


@dataclass
class FSRSCardState:
    """FSRS card state for algorithm calculations."""

    difficulty: float
    stability: float
    retrievability: float
    state: FSRSState
    last_review: datetime | None = None


@dataclass
class ScheduleResult:
    """Result of FSRS scheduling calculation."""

    difficulty: float
    stability: float
    retrievability: float
    next_interval: float
    next_review_date: datetime


@dataclass
class LearningStats:
    """Overall learning statistics."""

    total_mastered: int = 0
    total_learning: int = 0
    total_new: int = 0
    next_review_count: int = 0
    overdue_count: int = 0
    average_easiness: float = 2.5
    study_streak: int = 0
    # New stats for Phase 1.8
    image_questions_completed: int = 0
    multilingual_explanations_viewed: int = 0
    preferred_language: str = "en"
