"""Performance metrics entities for the analytics domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """User performance metrics."""

    total_cards_studied: int
    average_accuracy: float
    study_streak: int
    total_study_time_minutes: int
    cards_due_today: int
    mastery_percentage: float


@dataclass
class DifficultyDistribution:
    """Distribution of card difficulties."""

    easy_count: int
    medium_count: int
    hard_count: int
    easy_percentage: float
    medium_percentage: float
    hard_percentage: float


@dataclass
class PerformanceInsights:
    """AI-generated performance insights."""

    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    focus_areas: list[str]
