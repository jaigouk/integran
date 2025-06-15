"""Analytics Context Domain Events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.infrastructure.messaging.event_bus import DomainEvent


@dataclass
class PerformanceAnalyzedEvent(DomainEvent):
    """Event published when performance analysis is completed."""

    user_id: int
    analysis_type: str  # "comprehensive", "retention", "category", "velocity"
    analysis_results: dict[str, Any]
    insights_generated: int
    analysis_duration_ms: int

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class LeechDetectedEvent(DomainEvent):
    """Event published when leech cards are detected."""

    user_id: int
    card_id: int
    question_id: int
    severity: str  # "mild", "moderate", "severe"
    lapse_count: int
    success_rate: float
    intervention_recommended: bool
    intervention_type: str | None = None

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class LeechResolvedEvent(DomainEvent):
    """Event published when a leech card is resolved."""

    user_id: int
    card_id: int
    question_id: int
    previous_severity: str
    resolution_method: str
    days_to_resolution: int
    final_success_rate: float

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class InterleavingOptimizedEvent(DomainEvent):
    """Event published when interleaving strategy is optimized."""

    user_id: int
    session_id: int
    strategy: str  # "random", "similarity_based", "contrast_based", etc.
    questions_optimized: int
    category_distribution: dict[str, int]
    estimated_effectiveness: float
    optimization_duration_ms: int

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class InterleavingSessionCreatedEvent(DomainEvent):
    """Event published when an interleaved session is created."""

    user_id: int
    session_id: int
    strategy: str
    target_questions: int
    categories_included: list[str]
    difficulty_balance: str
    estimated_duration_minutes: int

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class StudyForecastGeneratedEvent(DomainEvent):
    """Event published when study forecast is generated."""

    user_id: int
    forecast_type: str  # "daily", "weekly", "monthly"
    reviews_due: int
    new_cards_recommended: int
    estimated_study_time_minutes: int
    peak_workload_day: str
    forecast_generated_at: datetime

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class LearningInsightsGeneratedEvent(DomainEvent):
    """Event published when comprehensive learning insights are generated."""

    user_id: int
    total_cards_analyzed: int
    progress_percentage: float
    retention_rate: float
    categories_analyzed: int
    recommendations_generated: int
    insights_quality_score: float

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class CategoryPerformanceAnalyzedEvent(DomainEvent):
    """Event published when category performance is analyzed."""

    user_id: int
    category: str
    total_questions: int
    mastery_percentage: float
    retention_rate: float
    recommended_focus: bool
    improvement_trend: str  # "improving", "stable", "declining"

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class LearningVelocityCalculatedEvent(DomainEvent):
    """Event published when learning velocity metrics are calculated."""

    user_id: int
    time_period_days: int
    cards_mastered_per_day: float
    reviews_per_day: float
    mastery_rate: float
    velocity_trend: str  # "accelerating", "stable", "slowing"

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)
