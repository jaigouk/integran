"""Tests for Analytics Domain Events."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.analytics.events.analytics_events import (
    InterleavingOptimizedEvent,
    StudyForecastGeneratedEvent,
)


class TestAnalyticsEvents:
    """Test analytics domain events."""

    def test_interleaving_optimized_event_post_init(self):
        """Test InterleavingOptimizedEvent __post_init__ method."""
        event = InterleavingOptimizedEvent(
            user_id=1,
            session_id=100,
            strategy="similarity_based",
            questions_optimized=25,
            category_distribution={"Politik": 10, "Geschichte": 15},
            estimated_effectiveness=0.85,
            optimization_duration_ms=1200,
        )

        # Verify the event was properly initialized
        assert event.user_id == 1
        assert event.session_id == 100
        assert event.strategy == "similarity_based"
        assert event.questions_optimized == 25
        assert event.category_distribution == {"Politik": 10, "Geschichte": 15}
        assert event.estimated_effectiveness == 0.85
        assert event.optimization_duration_ms == 1200

        # Verify DomainEvent attributes were set by __post_init__
        assert hasattr(event, "event_id")
        assert hasattr(event, "occurred_at")
        assert event.event_id is not None
        assert isinstance(event.occurred_at, datetime)

    def test_study_forecast_generated_event_post_init(self):
        """Test StudyForecastGeneratedEvent __post_init__ method."""
        event = StudyForecastGeneratedEvent(
            user_id=2,
            forecast_type="weekly",
            reviews_due=150,
            new_cards_recommended=25,
            estimated_study_time_minutes=180,
            peak_workload_day="2024-02-15",
            forecast_generated_at=datetime.now(UTC),
        )

        # Verify the event was properly initialized
        assert event.user_id == 2
        assert event.forecast_type == "weekly"
        assert event.reviews_due == 150
        assert event.new_cards_recommended == 25
        assert event.estimated_study_time_minutes == 180
        assert event.peak_workload_day == "2024-02-15"
        assert isinstance(event.forecast_generated_at, datetime)

        # Verify DomainEvent attributes were set by __post_init__
        assert hasattr(event, "event_id")
        assert hasattr(event, "occurred_at")
        assert event.event_id is not None
        assert isinstance(event.occurred_at, datetime)

    def test_event_inheritance(self):
        """Test that events properly inherit from DomainEvent."""
        from src.infrastructure.messaging.event_bus import DomainEvent

        interleaving_event = InterleavingOptimizedEvent(
            user_id=1,
            session_id=100,
            strategy="test",
            questions_optimized=10,
            category_distribution={"Test": 10},
            estimated_effectiveness=0.75,
            optimization_duration_ms=1000,
        )

        forecast_event = StudyForecastGeneratedEvent(
            user_id=1,
            forecast_type="daily",
            reviews_due=50,
            new_cards_recommended=10,
            estimated_study_time_minutes=90,
            peak_workload_day="2024-01-01",
            forecast_generated_at=datetime.now(UTC),
        )

        assert isinstance(interleaving_event, DomainEvent)
        assert isinstance(forecast_event, DomainEvent)
