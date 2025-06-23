"""Tests for EventBus infrastructure component."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.shared.events import DomainEvent
from src.infrastructure.messaging.enhanced_event_bus import EventBus


@dataclass
class MockEvent(DomainEvent):
    """Test event for testing."""

    message: str
    value: int = 0


@dataclass
class AnotherMockEvent(DomainEvent):
    """Another test event for testing."""

    data: str


class TestEventBus:
    """Test EventBus functionality."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create EventBus instance for testing."""
        return EventBus()

    @pytest.mark.asyncio
    async def test_publish_with_no_handlers(self, event_bus: EventBus) -> None:
        """Test publishing event with no registered handlers."""
        event = MockEvent(message="test", value=42)

        # Should not raise any exceptions
        await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_with_single_handler(self, event_bus: EventBus) -> None:
        """Test publishing event with single handler."""
        handler = AsyncMock()
        event = MockEvent(message="test", value=42)

        event_bus.subscribe(MockEvent, handler)
        await event_bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_with_multiple_handlers(self, event_bus: EventBus) -> None:
        """Test publishing event with multiple handlers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()

        event = MockEvent(message="test", value=42)

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)
        event_bus.subscribe(MockEvent, handler3)

        await event_bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        handler3.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_different_event_types(self, event_bus: EventBus) -> None:
        """Test publishing different event types to different handlers."""
        test_handler = AsyncMock()
        another_handler = AsyncMock()

        test_event = MockEvent(message="test")
        another_event = AnotherMockEvent(data="data")

        event_bus.subscribe(MockEvent, test_handler)
        event_bus.subscribe(AnotherMockEvent, another_handler)

        await event_bus.publish(test_event)
        await event_bus.publish(another_event)

        test_handler.assert_called_once_with(test_event)
        another_handler.assert_called_once_with(another_event)

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, event_bus: EventBus) -> None:
        """Test that handler errors don't affect other handlers."""
        good_handler1 = AsyncMock()
        bad_handler = AsyncMock(side_effect=Exception("Handler error"))
        good_handler2 = AsyncMock()

        event = MockEvent(message="test")

        event_bus.subscribe(MockEvent, good_handler1)
        event_bus.subscribe(MockEvent, bad_handler)
        event_bus.subscribe(MockEvent, good_handler2)

        # Should not raise exception despite bad handler
        await event_bus.publish(event)

        # Good handlers should still be called
        good_handler1.assert_called_once_with(event)
        good_handler2.assert_called_once_with(event)
        bad_handler.assert_called_once_with(event)

    def test_subscribe_handler(self, event_bus: EventBus) -> None:
        """Test subscribing handler to event type."""
        handler = Mock()

        event_bus.subscribe(MockEvent, handler)

        assert MockEvent in event_bus._handlers
        assert handler in event_bus._handlers[MockEvent]

    def test_subscribe_multiple_handlers_same_event(self, event_bus: EventBus) -> None:
        """Test subscribing multiple handlers to same event type."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)

        assert len(event_bus._handlers[MockEvent]) == 2
        assert handler1 in event_bus._handlers[MockEvent]
        assert handler2 in event_bus._handlers[MockEvent]

    def test_unsubscribe_handler(self, event_bus: EventBus) -> None:
        """Test unsubscribing handler from event type."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)

        event_bus.unsubscribe(MockEvent, handler1)

        assert handler1 not in event_bus._handlers[MockEvent]
        assert handler2 in event_bus._handlers[MockEvent]

    def test_unsubscribe_nonexistent_handler(self, event_bus: EventBus) -> None:
        """Test unsubscribing handler that wasn't subscribed."""
        handler = Mock()

        # Should not raise exception
        event_bus.unsubscribe(MockEvent, handler)

    def test_unsubscribe_from_nonexistent_event_type(self, event_bus: EventBus) -> None:
        """Test unsubscribing from event type that has no handlers."""
        handler = Mock()

        # Should not raise exception
        event_bus.unsubscribe(MockEvent, handler)

    @pytest.mark.asyncio
    async def test_sync_handler_support(self, event_bus: EventBus) -> None:
        """Test that synchronous handlers are also supported."""
        sync_handler = Mock()
        async_handler = AsyncMock()

        event = MockEvent(message="test")

        event_bus.subscribe(MockEvent, sync_handler)
        event_bus.subscribe(MockEvent, async_handler)

        await event_bus.publish(event)

        sync_handler.assert_called_once_with(event)
        async_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing(self, event_bus: EventBus) -> None:
        """Test concurrent event publishing."""
        handler = AsyncMock()

        event1 = MockEvent(message="event1", value=1)
        event2 = MockEvent(message="event2", value=2)
        event3 = MockEvent(message="event3", value=3)

        event_bus.subscribe(MockEvent, handler)

        # Publish events concurrently
        await asyncio.gather(
            event_bus.publish(event1),
            event_bus.publish(event2),
            event_bus.publish(event3),
        )

        # All events should be handled
        assert handler.call_count == 3
        handler.assert_any_call(event1)
        handler.assert_any_call(event2)
        handler.assert_any_call(event3)

    @pytest.mark.asyncio
    async def test_handler_execution_order(self, event_bus: EventBus) -> None:
        """Test that handlers are executed concurrently (no guaranteed order)."""
        call_order = []

        async def handler1(_event: MockEvent) -> None:
            await asyncio.sleep(0.02)  # Longer delay
            call_order.append("handler1")

        async def handler2(_event: MockEvent) -> None:
            await asyncio.sleep(0.01)  # Shorter delay
            call_order.append("handler2")

        event = MockEvent(message="test")

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)

        await event_bus.publish(event)

        # handler2 should complete first due to shorter delay
        assert call_order == ["handler2", "handler1"]

    def test_event_bus_isolation(self) -> None:
        """Test that different EventBus instances are isolated."""
        bus1 = EventBus()
        bus2 = EventBus()

        handler1 = Mock()
        handler2 = Mock()

        bus1.subscribe(MockEvent, handler1)
        bus2.subscribe(MockEvent, handler2)

        # Each bus should have its own handlers
        assert MockEvent in bus1._handlers
        assert MockEvent in bus2._handlers
        assert bus1._handlers[MockEvent] != bus2._handlers[MockEvent]

    @pytest.mark.asyncio
    async def test_large_number_of_handlers(self, event_bus: EventBus) -> None:
        """Test performance with large number of handlers."""
        handlers = [AsyncMock() for _ in range(100)]
        event = MockEvent(message="load_test")

        # Subscribe all handlers
        for handler in handlers:
            event_bus.subscribe(MockEvent, handler)

        # Publish event
        await event_bus.publish(event)

        # All handlers should be called
        for handler in handlers:
            handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_nested_event_publishing(self, event_bus: EventBus) -> None:
        """Test publishing events from within event handlers."""
        nested_handler = AsyncMock()

        async def trigger_handler(event: MockEvent) -> None:
            if event.message == "trigger":
                nested_event = MockEvent(message="nested")
                await event_bus.publish(nested_event)

        event_bus.subscribe(MockEvent, trigger_handler)
        event_bus.subscribe(MockEvent, nested_handler)

        trigger_event = MockEvent(message="trigger")
        await event_bus.publish(trigger_event)

        # Both original and nested events should be handled
        assert nested_handler.call_count == 2  # trigger + nested
