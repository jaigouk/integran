"""Tests for DDD infrastructure components.

This module tests the core DDD infrastructure including EventBus,
DomainService base classes, and domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core import (
    BusinessRuleViolationError,
    CardScheduledEvent,
    DomainEvent,
    DomainService,
    DomainServiceError,
    EventBus,
    ValidationError,
    create_card_scheduled_event,
)


class TestDomainEvent:
    """Test DomainEvent base class."""

    def test_domain_event_auto_generates_id_and_timestamp(self):
        """Test that domain events automatically get ID and timestamp."""

        class TestEvent(DomainEvent):
            def __init__(self, message: str):
                super().__init__()
                self.message = message

        event = TestEvent(message="test")

        assert event.event_id is not None
        assert len(event.event_id) > 0
        assert event.occurred_at is not None
        assert isinstance(event.occurred_at, datetime)
        assert event.occurred_at.tzinfo is not None


class TestEventBus:
    """Test EventBus functionality."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        return EventBus()

    def test_event_bus_initialization(self, event_bus):
        """Test event bus initializes correctly."""
        assert event_bus.get_active_subscriptions() == {}
        assert event_bus.get_handler_count(CardScheduledEvent) == 0

    def test_subscribe_and_get_active_subscriptions(self, event_bus):
        """Test event subscription and querying."""

        def test_handler(_event):
            pass

        event_bus.subscribe(CardScheduledEvent, test_handler)

        subscriptions = event_bus.get_active_subscriptions()
        assert "CardScheduledEvent" in subscriptions
        assert subscriptions["CardScheduledEvent"] == 1
        assert event_bus.get_handler_count(CardScheduledEvent) == 1

    def test_unsubscribe(self, event_bus):
        """Test event unsubscription."""

        def test_handler(_event):
            pass

        event_bus.subscribe(CardScheduledEvent, test_handler)
        assert event_bus.get_handler_count(CardScheduledEvent) == 1

        event_bus.unsubscribe(CardScheduledEvent, test_handler)
        assert event_bus.get_handler_count(CardScheduledEvent) == 0

    def test_unsubscribe_nonexistent_handler(self, event_bus):
        """Test unsubscribing a handler that doesn't exist."""

        def test_handler(_event):
            pass

        # Should not raise an exception
        event_bus.unsubscribe(CardScheduledEvent, test_handler)

    @pytest.mark.asyncio
    async def test_publish_event_with_no_handlers(self, event_bus):
        """Test publishing event with no registered handlers."""

        event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=5.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2000,
        )

        # Should not raise an exception
        await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_event_with_sync_handler(self, event_bus):
        """Test publishing event with synchronous handler."""

        handler_called = False
        received_event = None

        def sync_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event

        event_bus.subscribe(CardScheduledEvent, sync_handler)

        event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=5.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2000,
        )

        await event_bus.publish(event)

        assert handler_called
        assert received_event == event

    @pytest.mark.asyncio
    async def test_publish_event_with_async_handler(self, event_bus):
        """Test publishing event with asynchronous handler."""

        handler_called = False
        received_event = None

        async def async_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event

        event_bus.subscribe(CardScheduledEvent, async_handler)

        event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=5.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2000,
        )

        await event_bus.publish(event)

        assert handler_called
        assert received_event == event

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, event_bus):
        """Test that handler errors don't affect other handlers."""

        good_handler_called = False

        def failing_handler(_event):
            raise Exception("Handler failed")

        def good_handler(_event):
            nonlocal good_handler_called
            good_handler_called = True

        event_bus.subscribe(CardScheduledEvent, failing_handler)
        event_bus.subscribe(CardScheduledEvent, good_handler)

        event = CardScheduledEvent(
            card_id=1,
            question_id=1,
            new_difficulty=5.0,
            new_stability=1.0,
            new_retrievability=1.0,
            next_review_date=datetime.now(UTC),
            rating=3,
            response_time_ms=2000,
        )

        # Should not raise an exception
        await event_bus.publish(event)

        # Good handler should still be called
        assert good_handler_called

    def test_clear_subscriptions(self, event_bus):
        """Test clearing all subscriptions."""

        def test_handler(_event):
            pass

        event_bus.subscribe(CardScheduledEvent, test_handler)
        assert event_bus.get_handler_count(CardScheduledEvent) == 1

        event_bus.clear_subscriptions()
        assert event_bus.get_handler_count(CardScheduledEvent) == 0
        assert event_bus.get_active_subscriptions() == {}


class TestDomainService:
    """Test DomainService base class."""

    @pytest.fixture
    def event_bus(self):
        """Create a mock event bus for testing."""
        return AsyncMock(spec=EventBus)

    def test_domain_service_initialization(self, event_bus):
        """Test domain service initialization."""

        class TestService(DomainService[str, str]):
            async def call(self, request: str) -> str:
                return f"processed: {request}"

        service = TestService(event_bus)
        assert service.event_bus == event_bus
        assert service.logger is not None

    @pytest.mark.asyncio
    async def test_domain_service_call(self, event_bus):
        """Test domain service call method."""

        class TestService(DomainService[str, str]):
            async def call(self, request: str) -> str:
                await self._publish_event(
                    CardScheduledEvent(
                        card_id=1,
                        question_id=1,
                        new_difficulty=5.0,
                        new_stability=1.0,
                        new_retrievability=1.0,
                        next_review_date=datetime.now(UTC),
                        rating=3,
                        response_time_ms=2000,
                    )
                )
                return f"processed: {request}"

        service = TestService(event_bus)
        result = await service.call("test")

        assert result == "processed: test"
        event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_error_handling(self, event_bus):
        """Test that event publishing errors don't break service logic."""

        # Configure mock to raise exception on publish
        event_bus.publish.side_effect = Exception("Event bus error")

        class TestService(DomainService[str, str]):
            async def call(self, request: str) -> str:
                await self._publish_event(
                    CardScheduledEvent(
                        card_id=1,
                        question_id=1,
                        new_difficulty=5.0,
                        new_stability=1.0,
                        new_retrievability=1.0,
                        next_review_date=datetime.now(UTC),
                        rating=3,
                        response_time_ms=2000,
                    )
                )
                return f"processed: {request}"

        service = TestService(event_bus)

        # Should not raise exception despite event bus error
        result = await service.call("test")
        assert result == "processed: test"


class TestDomainServiceExceptions:
    """Test domain service exception classes."""

    def test_domain_service_error(self):
        """Test DomainServiceError base exception."""

        error = DomainServiceError("Test error", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.error_code == "TEST_CODE"

    def test_validation_error(self):
        """Test ValidationError exception."""

        error = ValidationError("Invalid field", "email")
        assert str(error) == "Invalid field"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field == "email"

    def test_business_rule_violation_error(self):
        """Test BusinessRuleViolationError exception."""

        error = BusinessRuleViolationError("Rule violated", "max_attempts")
        assert str(error) == "Rule violated"
        assert error.error_code == "BUSINESS_RULE_VIOLATION"
        assert error.rule == "max_attempts"


class TestDomainEventFactories:
    """Test domain event factory functions."""

    def test_create_card_scheduled_event(self):
        """Test CardScheduledEvent factory function."""

        # Mock FSRS result
        fsrs_result = MagicMock()
        fsrs_result.difficulty = 6.0
        fsrs_result.stability = 2.5
        fsrs_result.retrievability = 0.9
        fsrs_result.next_review_date = datetime.now(UTC)

        event = create_card_scheduled_event(
            card_id=123,
            question_id=456,
            fsrs_result=fsrs_result,
            rating=4,
            response_time_ms=1500,
            session_id=789,
        )

        assert event.card_id == 123
        assert event.question_id == 456
        assert event.new_difficulty == 6.0
        assert event.new_stability == 2.5
        assert event.new_retrievability == 0.9
        assert event.rating == 4
        assert event.response_time_ms == 1500
        assert event.session_id == 789
        assert event.next_review_date == fsrs_result.next_review_date
