"""Tests for learning context domain events."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.learning.events.card_events import (
    CardScheduledEvent,
    SessionCompletedEvent,
    SessionStartedEvent,
)


class TestCardScheduledEvent:
    """Test the CardScheduledEvent domain event."""

    def test_card_scheduled_event_creation(self):
        """Test creating a CardScheduledEvent."""
        next_review = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=2.5,
            new_stability=1.8,
            new_retrievability=0.9,
            next_review_date=next_review,
            rating=3,
            response_time_ms=2500,
            session_id=789,
        )

        assert event.card_id == 123
        assert event.question_id == 456
        assert event.new_difficulty == 2.5
        assert event.new_stability == 1.8
        assert event.new_retrievability == 0.9
        assert event.next_review_date == next_review
        assert event.rating == 3
        assert event.response_time_ms == 2500
        assert event.session_id == 789

    def test_card_scheduled_event_with_none_session(self):
        """Test creating a CardScheduledEvent with None session_id."""
        next_review = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=2.5,
            new_stability=1.8,
            new_retrievability=0.9,
            next_review_date=next_review,
            rating=3,
            response_time_ms=2500,
        )

        assert event.session_id is None

    def test_card_scheduled_event_inherits_domain_event(self):
        """Test that CardScheduledEvent properly inherits from DomainEvent."""
        next_review = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=2.5,
            new_stability=1.8,
            new_retrievability=0.9,
            next_review_date=next_review,
            rating=3,
            response_time_ms=2500,
        )

        # Should have DomainEvent attributes
        assert hasattr(event, "event_id")
        assert hasattr(event, "occurred_at")
        assert event.event_id
        assert event.occurred_at
        assert event.event_name == "CardScheduledEvent"

    def test_card_scheduled_event_rating_values(self):
        """Test different rating values for CardScheduledEvent."""
        next_review = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Test each rating value
        for rating in [1, 2, 3, 4]:  # Again, Hard, Good, Easy
            event = CardScheduledEvent(
                card_id=123,
                question_id=456,
                new_difficulty=2.5,
                new_stability=1.8,
                new_retrievability=0.9,
                next_review_date=next_review,
                rating=rating,
                response_time_ms=2500,
            )
            assert event.rating == rating


class TestSessionStartedEvent:
    """Test the SessionStartedEvent domain event."""

    def test_session_started_event_creation(self):
        """Test creating a SessionStartedEvent."""
        event = SessionStartedEvent(
            session_id=123,
            user_id=456,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        assert event.session_id == 123
        assert event.user_id == 456
        assert event.session_type == "review"
        assert event.target_retention == 0.9
        assert event.max_reviews == 20

    def test_session_started_event_different_types(self):
        """Test SessionStartedEvent with different session types."""
        session_types = ["review", "learn", "weak_focus", "quiz"]

        for session_type in session_types:
            event = SessionStartedEvent(
                session_id=123,
                user_id=456,
                session_type=session_type,
                target_retention=0.9,
                max_reviews=20,
            )
            assert event.session_type == session_type

    def test_session_started_event_inherits_domain_event(self):
        """Test that SessionStartedEvent properly inherits from DomainEvent."""
        event = SessionStartedEvent(
            session_id=123,
            user_id=456,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        # Should have DomainEvent attributes
        assert hasattr(event, "event_id")
        assert hasattr(event, "occurred_at")
        assert event.event_id
        assert event.occurred_at
        assert event.event_name == "SessionStartedEvent"


class TestSessionCompletedEvent:
    """Test the SessionCompletedEvent domain event."""

    def test_session_completed_event_creation(self):
        """Test creating a SessionCompletedEvent."""
        event = SessionCompletedEvent(
            session_id=123,
            user_id=456,
            duration_seconds=1800,  # 30 minutes
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        assert event.session_id == 123
        assert event.user_id == 456
        assert event.duration_seconds == 1800
        assert event.questions_reviewed == 25
        assert event.questions_correct == 20
        assert event.new_cards_learned == 5
        assert event.retention_rate == 0.8

    def test_session_completed_event_perfect_score(self):
        """Test SessionCompletedEvent with perfect score."""
        event = SessionCompletedEvent(
            session_id=123,
            user_id=456,
            duration_seconds=900,  # 15 minutes
            questions_reviewed=10,
            questions_correct=10,
            new_cards_learned=0,
            retention_rate=1.0,
        )

        assert event.questions_correct == event.questions_reviewed
        assert event.retention_rate == 1.0

    def test_session_completed_event_inherits_domain_event(self):
        """Test that SessionCompletedEvent properly inherits from DomainEvent."""
        event = SessionCompletedEvent(
            session_id=123,
            user_id=456,
            duration_seconds=1800,
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        # Should have DomainEvent attributes
        assert hasattr(event, "event_id")
        assert hasattr(event, "occurred_at")
        assert event.event_id
        assert event.occurred_at
        assert event.event_name == "SessionCompletedEvent"


class TestEventIntegration:
    """Test integration between different learning events."""

    def test_events_have_unique_types(self):
        """Test that different event types are distinguishable."""
        card_event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=2.5,
            new_stability=1.8,
            new_retrievability=0.9,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2500,
        )

        session_start_event = SessionStartedEvent(
            session_id=123,
            user_id=456,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        session_end_event = SessionCompletedEvent(
            session_id=123,
            user_id=456,
            duration_seconds=1800,
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        assert type(card_event) is not type(session_start_event)
        assert type(session_start_event) is not type(session_end_event)
        assert type(card_event) is not type(session_end_event)

    def test_event_timestamps_ordering(self):
        """Test that event timestamps can be used for ordering."""
        event1 = SessionStartedEvent(
            session_id=123,
            user_id=456,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        # Small delay to ensure different timestamps
        import time

        time.sleep(0.01)

        event2 = SessionCompletedEvent(
            session_id=123,
            user_id=456,
            duration_seconds=1800,
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        # Session started should occur before session completed
        assert event1.occurred_at < event2.occurred_at

    def test_events_can_share_session_id(self):
        """Test that events can be correlated by session_id."""
        session_id = 123

        start_event = SessionStartedEvent(
            session_id=session_id,
            user_id=456,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        card_event = CardScheduledEvent(
            card_id=789,
            question_id=101,
            new_difficulty=2.5,
            new_stability=1.8,
            new_retrievability=0.9,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2500,
            session_id=session_id,
        )

        end_event = SessionCompletedEvent(
            session_id=session_id,
            user_id=456,
            duration_seconds=1800,
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        assert start_event.session_id == session_id
        assert card_event.session_id == session_id
        assert end_event.session_id == session_id
