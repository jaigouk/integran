"""Tests for learning context domain events."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.learning.events.card_events import (
    CardScheduledEvent,
    SessionCompletedEvent,
    SessionStartedEvent,
)


class TestCardEvents:
    """Test learning context domain events."""

    def test_card_scheduled_event(self):
        """Test CardScheduledEvent creation and initialization."""
        next_review = datetime.now(UTC)

        event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=5.2,
            new_stability=3.1,
            new_retrievability=0.85,
            next_review_date=next_review,
            rating=3,
            response_time_ms=2500,
            session_id=789,
        )

        assert event.card_id == 123
        assert event.question_id == 456
        assert event.new_difficulty == 5.2
        assert event.new_stability == 3.1
        assert event.new_retrievability == 0.85
        assert event.next_review_date == next_review
        assert event.rating == 3
        assert event.response_time_ms == 2500
        assert event.session_id == 789

        # Check that DomainEvent fields are initialized
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_card_scheduled_event_no_session(self):
        """Test CardScheduledEvent without session ID."""
        next_review = datetime.now(UTC)

        event = CardScheduledEvent(
            card_id=123,
            question_id=456,
            new_difficulty=5.2,
            new_stability=3.1,
            new_retrievability=0.85,
            next_review_date=next_review,
            rating=4,
            response_time_ms=1800,
        )

        assert event.session_id is None
        assert event.rating == 4
        assert event.response_time_ms == 1800

    def test_session_started_event(self):
        """Test SessionStartedEvent creation and initialization."""
        event = SessionStartedEvent(
            session_id=100,
            user_id=42,
            session_type="review",
            target_retention=0.9,
            max_reviews=20,
        )

        assert event.session_id == 100
        assert event.user_id == 42
        assert event.session_type == "review"
        assert event.target_retention == 0.9
        assert event.max_reviews == 20

        # Check that DomainEvent fields are initialized
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_session_started_event_different_types(self):
        """Test SessionStartedEvent with different session types."""
        learn_event = SessionStartedEvent(
            session_id=101,
            user_id=42,
            session_type="learn",
            target_retention=0.85,
            max_reviews=15,
        )

        quiz_event = SessionStartedEvent(
            session_id=102,
            user_id=42,
            session_type="quiz",
            target_retention=0.95,
            max_reviews=50,
        )

        weak_focus_event = SessionStartedEvent(
            session_id=103,
            user_id=42,
            session_type="weak_focus",
            target_retention=0.8,
            max_reviews=10,
        )

        assert learn_event.session_type == "learn"
        assert quiz_event.session_type == "quiz"
        assert weak_focus_event.session_type == "weak_focus"

    def test_session_completed_event(self):
        """Test SessionCompletedEvent creation and initialization."""
        event = SessionCompletedEvent(
            session_id=100,
            user_id=42,
            duration_seconds=1800,
            questions_reviewed=25,
            questions_correct=20,
            new_cards_learned=5,
            retention_rate=0.8,
        )

        assert event.session_id == 100
        assert event.user_id == 42
        assert event.duration_seconds == 1800
        assert event.questions_reviewed == 25
        assert event.questions_correct == 20
        assert event.new_cards_learned == 5
        assert event.retention_rate == 0.8

        # Check that DomainEvent fields are initialized
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_session_completed_event_perfect_score(self):
        """Test SessionCompletedEvent with perfect retention."""
        event = SessionCompletedEvent(
            session_id=105,
            user_id=42,
            duration_seconds=900,
            questions_reviewed=10,
            questions_correct=10,
            new_cards_learned=0,
            retention_rate=1.0,
        )

        assert event.questions_reviewed == event.questions_correct
        assert event.retention_rate == 1.0
        assert event.new_cards_learned == 0

    def test_session_completed_event_poor_performance(self):
        """Test SessionCompletedEvent with poor retention."""
        event = SessionCompletedEvent(
            session_id=106,
            user_id=42,
            duration_seconds=2400,
            questions_reviewed=30,
            questions_correct=12,
            new_cards_learned=3,
            retention_rate=0.4,
        )

        assert event.retention_rate == 0.4
        assert event.questions_correct < event.questions_reviewed
        assert event.new_cards_learned == 3

    def test_event_names(self):
        """Test that events have correct names via event_name property."""
        card_event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=1.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=1000,
        )

        start_event = SessionStartedEvent(
            session_id=1,
            user_id=1,
            session_type="review",
            target_retention=0.9,
            max_reviews=10,
        )

        complete_event = SessionCompletedEvent(
            session_id=1,
            user_id=1,
            duration_seconds=600,
            questions_reviewed=10,
            questions_correct=8,
            new_cards_learned=2,
            retention_rate=0.8,
        )

        assert card_event.event_name == "CardScheduledEvent"
        assert start_event.event_name == "SessionStartedEvent"
        assert complete_event.event_name == "SessionCompletedEvent"

    def test_events_string_representation(self):
        """Test string representation of events."""
        card_event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=1.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=1000,
        )

        str_repr = str(card_event)
        assert "CardScheduledEvent" in str_repr
        assert "event_id=" in str_repr
        assert card_event.event_id in str_repr
