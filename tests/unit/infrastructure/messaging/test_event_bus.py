"""Tests for the lightweight in-memory event bus."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.messaging.enhanced_event_bus import DomainEvent, EventBus


class MockEvent(DomainEvent):
    """Test event for testing."""

    def __init__(self, data: str = "test", **kwargs):
        super().__init__(**kwargs)
        self.data = data


class AnotherMockEvent(DomainEvent):
    """Another test event for testing multiple event types."""

    def __init__(self, value: int = 42, **kwargs):
        super().__init__(**kwargs)
        self.value = value


class TestDomainEvent:
    """Test the DomainEvent base class."""

    def test_auto_generates_event_id(self):
        """Test that event ID is auto-generated if not provided."""
        event = MockEvent()
        assert event.event_id
        assert len(event.event_id) == 36  # UUID format

    def test_uses_provided_event_id(self):
        """Test that provided event ID is used."""
        event_id = "custom-id-123"
        event = MockEvent(event_id=event_id)
        assert event.event_id == event_id

    def test_auto_generates_timestamp(self):
        """Test that timestamp is auto-generated if not provided."""
        before = datetime.now(UTC)
        event = MockEvent()
        after = datetime.now(UTC)
        assert before <= event.occurred_at <= after

    def test_uses_provided_timestamp(self):
        """Test that provided timestamp is used."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = MockEvent(occurred_at=timestamp)
        assert event.occurred_at == timestamp

    def test_string_representation(self):
        """Test string representation of event."""
        event = MockEvent(event_id="test-123")
        assert str(event) == "MockEvent(event_id=test-123)"

    def test_event_name_property(self):
        """Test event_name property returns class name."""
        event = MockEvent()
        assert event.event_name == "MockEvent"


class TestEventBus:
    """Test the EventBus implementation."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        return EventBus()

    @pytest.mark.asyncio
    async def test_publish_no_handlers(self, event_bus):
        """Test publishing event with no handlers."""
        event = MockEvent()
        # Should not raise any exceptions
        await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_to_sync_handler(self, event_bus):
        """Test publishing event to synchronous handler."""
        handler = Mock()
        event_bus.subscribe(MockEvent, handler)

        event = MockEvent(data="sync-test")
        await event_bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_to_async_handler(self, event_bus):
        """Test publishing event to asynchronous handler."""
        handler_called = False
        received_event = None

        async def async_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event

        event_bus.subscribe(MockEvent, async_handler)

        event = MockEvent(data="async-test")
        await event_bus.publish(event)

        assert handler_called
        assert received_event == event

    @pytest.mark.asyncio
    async def test_publish_to_multiple_handlers(self, event_bus):
        """Test publishing event to multiple handlers."""
        handler1 = Mock()
        handler2 = Mock()

        async def async_handler(event):
            handler2(event)

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, async_handler)

        event = MockEvent()
        await event_bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handlers_run_concurrently(self, event_bus):
        """Test that handlers run concurrently."""
        call_order = []

        async def slow_handler(_event):
            call_order.append("slow_start")
            await asyncio.sleep(0.1)
            call_order.append("slow_end")

        async def fast_handler(_event):
            call_order.append("fast_start")
            await asyncio.sleep(0.01)
            call_order.append("fast_end")

        event_bus.subscribe(MockEvent, slow_handler)
        event_bus.subscribe(MockEvent, fast_handler)

        await event_bus.publish(MockEvent())

        # Fast handler should complete before slow handler
        assert call_order == ["slow_start", "fast_start", "fast_end", "slow_end"]

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, event_bus):
        """Test that handler errors don't affect other handlers."""
        handler1_called = False
        handler3_called = False

        def handler1(_event):
            nonlocal handler1_called
            handler1_called = True

        def handler2(_event):
            raise ValueError("Handler 2 error")

        def handler3(_event):
            nonlocal handler3_called
            handler3_called = True

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)
        event_bus.subscribe(MockEvent, handler3)

        # Should not raise despite handler2 error
        await event_bus.publish(MockEvent())

        assert handler1_called
        assert handler3_called

    @pytest.mark.asyncio
    async def test_critical_publish_error(self, event_bus):
        """Test critical error during event publishing."""

        async def bad_handler(_event):
            raise RuntimeError("Critical error")

        event_bus.subscribe(MockEvent, bad_handler)

        # Mock asyncio.gather to raise an exception
        with (
            patch("asyncio.gather", side_effect=Exception("Critical gather error")),
            pytest.raises(Exception, match="Critical gather error"),
        ):
            await event_bus.publish(MockEvent())

    def test_subscribe_new_event_type(self, event_bus):
        """Test subscribing to new event type."""
        handler = Mock()
        event_bus.subscribe(MockEvent, handler)

        assert event_bus.get_handler_count(MockEvent) == 1
        assert MockEvent in event_bus._handlers

    def test_subscribe_multiple_handlers(self, event_bus):
        """Test subscribing multiple handlers to same event type."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)

        assert event_bus.get_handler_count(MockEvent) == 2

    def test_unsubscribe_handler(self, event_bus):
        """Test unsubscribing handler."""
        handler = Mock()
        event_bus.subscribe(MockEvent, handler)
        event_bus.unsubscribe(MockEvent, handler)

        assert event_bus.get_handler_count(MockEvent) == 0

    def test_unsubscribe_non_existent_handler(self, event_bus):
        """Test unsubscribing handler that wasn't subscribed."""
        handler = Mock()
        # Should not raise exception
        event_bus.unsubscribe(MockEvent, handler)

    def test_unsubscribe_from_multiple_handlers(self, event_bus):
        """Test unsubscribing one handler when multiple are subscribed."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)
        event_bus.unsubscribe(MockEvent, handler1)

        assert event_bus.get_handler_count(MockEvent) == 1
        assert handler2 in event_bus._handlers[MockEvent]

    def test_get_active_subscriptions(self, event_bus):
        """Test getting active subscription counts."""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)
        event_bus.subscribe(AnotherMockEvent, handler3)

        subscriptions = event_bus.get_active_subscriptions()

        assert subscriptions == {"MockEvent": 2, "AnotherMockEvent": 1}

    def test_clear_subscriptions(self, event_bus):
        """Test clearing all subscriptions."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(AnotherMockEvent, handler2)

        event_bus.clear_subscriptions()

        assert event_bus.get_handler_count(MockEvent) == 0
        assert event_bus.get_handler_count(AnotherMockEvent) == 0
        assert len(event_bus._handlers) == 0

    def test_get_handler_count_no_handlers(self, event_bus):
        """Test getting handler count for event type with no handlers."""
        assert event_bus.get_handler_count(MockEvent) == 0

    @pytest.mark.asyncio
    async def test_logging_publish(self, event_bus, caplog):
        """Test logging during event publishing."""
        handler = Mock()
        event_bus.subscribe(MockEvent, handler)

        with caplog.at_level(logging.INFO):
            await event_bus.publish(MockEvent())

        assert "Publishing MockEvent to 1 handlers" in caplog.text

    @pytest.mark.asyncio
    async def test_logging_no_handlers(self, event_bus, caplog):
        """Test logging when no handlers registered."""
        with caplog.at_level(logging.DEBUG):
            await event_bus.publish(MockEvent())

        assert "No handlers registered for MockEvent" in caplog.text

    @pytest.mark.asyncio
    async def test_logging_handler_error(self, event_bus, caplog):
        """Test logging when handler fails."""

        def failing_handler(_event):
            raise ValueError("Test error")

        failing_handler.__name__ = "failing_handler"  # Ensure name is set
        event_bus.subscribe(MockEvent, failing_handler)

        with caplog.at_level(logging.ERROR):
            await event_bus.publish(MockEvent())

        # Check that error was logged (exact format may vary)
        error_messages = [msg for msg in caplog.messages if "failed" in msg.lower()]
        assert len(error_messages) > 0, (
            f"Expected error message not found in: {caplog.messages}"
        )
        assert any("Test error" in msg for msg in caplog.messages)

    def test_logging_subscribe(self, event_bus, caplog):
        """Test logging during subscription."""
        handler = Mock()
        handler.__name__ = "mock_handler"  # Set handler name explicitly

        with caplog.at_level(logging.INFO):
            event_bus.subscribe(MockEvent, handler)

        assert "Subscribed mock_handler to MockEvent" in caplog.text

    def test_logging_unsubscribe(self, event_bus, caplog):
        """Test logging during unsubscription."""
        handler = Mock()
        handler.__name__ = "mock_handler"  # Set handler name explicitly
        event_bus.subscribe(MockEvent, handler)

        with caplog.at_level(logging.INFO):
            event_bus.unsubscribe(MockEvent, handler)

        assert "Unsubscribed mock_handler from MockEvent" in caplog.text

    def test_logging_clear(self, event_bus, caplog):
        """Test logging when clearing subscriptions."""
        with caplog.at_level(logging.INFO):
            event_bus.clear_subscriptions()

        assert "Cleared all event subscriptions" in caplog.text
