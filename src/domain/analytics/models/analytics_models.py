"""Analytics and progress tracking domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from src.domain.shared.models import Base

# ============================================================================
# Progress Tracking Models
# ============================================================================


class UserProgress(Base):
    """Overall user progress tracking."""

    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True)
    total_questions_seen = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_time_spent = Column(Float, default=0.0)  # seconds
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_practice = Column(DateTime)
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    __table_args__ = ({"extend_existing": True},)


class CategoryProgress(Base):
    """Progress tracking per category."""

    __tablename__ = "category_progress"

    id = Column(Integer, primary_key=True)
    category = Column(String(100), unique=True, nullable=False)
    total_questions = Column(Integer, default=0)
    questions_seen = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    average_time = Column(Float, default=0.0)
    last_practiced = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("category"),
        {"extend_existing": True},
    )


class UserAnalytics(Base):
    """Learning analytics for user progress tracking."""

    __tablename__ = "user_analytics"

    analytics_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD format

    # Daily Statistics
    reviews_due = Column(Integer, default=0)
    reviews_completed = Column(Integer, default=0)
    new_cards_learned = Column(Integer, default=0)
    retention_rate = Column(Float)

    # Category Performance (JSON)
    category_stats = Column(Text)  # Per-category performance

    # Streak Tracking
    study_streak_days = Column(Integer, default=0)

    created_at = Column(
        Float, nullable=False, default=lambda: datetime.now(UTC).timestamp()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "date"),
        Index("idx_user_analytics_date", "date"),
        {"extend_existing": True},
    )


class Category(Base):
    """Learning categories for better organization."""

    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    total_questions = Column(Integer, default=0)
    color_hex = Column(String(7), default="#3498db")

    __table_args__ = (
        UniqueConstraint("name"),
        {"extend_existing": True},
    )


# ============================================================================
# Analytics Data Classes
# ============================================================================


@dataclass
class CategoryStats:
    """Statistics for a specific category."""

    category: str
    total_questions: int = 0
    questions_seen: int = 0
    correct_answers: int = 0
    accuracy: float = 0.0
    average_time: float = 0.0
    last_practiced: datetime | None = None


@dataclass
class DailyStats:
    """Daily learning statistics."""

    date: str  # YYYY-MM-DD format
    reviews_due: int = 0
    reviews_completed: int = 0
    new_cards_learned: int = 0
    retention_rate: float = 0.0
    study_time_minutes: int = 0
    categories_practiced: list[str] = field(default_factory=list)


@dataclass
class WeeklyStats:
    """Weekly learning statistics."""

    week_start: str  # YYYY-MM-DD format
    total_reviews: int = 0
    total_new_cards: int = 0
    average_retention: float = 0.0
    study_days: int = 0
    total_study_time_minutes: int = 0
    daily_stats: list[DailyStats] = field(default_factory=list)


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""

    metric: str  # "retention_rate", "reviews_per_day", etc.
    period_days: int = 30
    current_value: float = 0.0
    previous_value: float = 0.0
    change_percent: float = 0.0
    trend_direction: str = "stable"  # "improving", "declining", "stable"


@dataclass
class LearningInsights:
    """Learning insights and recommendations."""

    user_id: int
    analysis_date: datetime
    performance_trends: list[PerformanceTrend] = field(default_factory=list)
    category_insights: list[CategoryStats] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    areas_for_improvement: list[str] = field(default_factory=list)
