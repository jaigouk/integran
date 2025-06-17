"""Tests for EventBus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.messaging.enhanced_event_bus import DomainEvent, EventBus


@dataclass
class MockEvent(DomainEvent):
    """Test event for testing purposes."""

    test_data: str
    test_value: int = 42

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


@dataclass
class AnotherMockEvent(DomainEvent):
    """Another test event for testing purposes."""

    message: str

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


class TestDomainEvent:
    """Test DomainEvent base class."""

    def test_domain_event_creation(self):
        """Test DomainEvent creation with auto-generated fields."""
        event = MockEvent(test_data="hello", test_value=100)

        assert event.test_data == "hello"
        assert event.test_value == 100
        assert event.event_id is not None
        assert len(event.event_id) > 0
        assert event.occurred_at is not None
        assert isinstance(event.occurred_at, datetime)

    def test_domain_event_with_custom_id_and_time(self):
        """Test DomainEvent with custom event_id and occurred_at."""
        custom_time = datetime.now(UTC)
        event = MockEvent(test_data="custom")
        # Set custom values after creation
        event.event_id = "custom-id-123"
        event.occurred_at = custom_time

        assert event.event_id == "custom-id-123"
        assert event.occurred_at == custom_time

    def test_domain_event_unique_ids(self):
        """Test that domain events get unique IDs."""
        event1 = MockEvent(test_data="first")
        event2 = MockEvent(test_data="second")

        assert event1.event_id != event2.event_id
        assert len(event1.event_id) > 0
        assert len(event2.event_id) > 0

    def test_domain_event_timestamp_close_to_now(self):
        """Test that domain event timestamp is close to current time."""
        before = datetime.now(UTC)
        event = MockEvent(test_data="timing test")
        after = datetime.now(UTC)

        assert before <= event.occurred_at <= after


class TestEventBus:
    """Test EventBus functionality."""

    def test_event_bus_creation(self):
        """Test EventBus creation."""
        event_bus = EventBus()
        assert event_bus._handlers == {}
        assert event_bus._processing is False

    def test_subscribe_single_handler(self):
        """Test subscribing a single handler to an event type."""
        event_bus = EventBus()
        handler = MagicMock()

        event_bus.subscribe(MockEvent, handler)

        assert MockEvent in event_bus._handlers
        assert handler in event_bus._handlers[MockEvent]
        assert len(event_bus._handlers[MockEvent]) == 1

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to the same event type."""
        event_bus = EventBus()
        handler1 = MagicMock()
        handler2 = MagicMock()
        handler3 = MagicMock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)
        event_bus.subscribe(MockEvent, handler3)

        assert len(event_bus._handlers[MockEvent]) == 3
        assert handler1 in event_bus._handlers[MockEvent]
        assert handler2 in event_bus._handlers[MockEvent]
        assert handler3 in event_bus._handlers[MockEvent]

    def test_subscribe_different_event_types(self):
        """Test subscribing handlers to different event types."""
        event_bus = EventBus()
        handler1 = MagicMock()
        handler2 = MagicMock()

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(AnotherMockEvent, handler2)

        assert MockEvent in event_bus._handlers
        assert AnotherMockEvent in event_bus._handlers
        assert handler1 in event_bus._handlers[MockEvent]
        assert handler2 in event_bus._handlers[AnotherMockEvent]

    def test_unsubscribe_existing_handler(self):
        """Test unsubscribing an existing handler."""
        event_bus = EventBus()
        handler = MagicMock()

        event_bus.subscribe(MockEvent, handler)
        assert handler in event_bus._handlers[MockEvent]

        event_bus.unsubscribe(MockEvent, handler)
        assert handler not in event_bus._handlers[MockEvent]

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that wasn't subscribed."""
        event_bus = EventBus()
        handler = MagicMock()

        # Should not raise an exception
        event_bus.unsubscribe(MockEvent, handler)

        # Subscribe and then try to unsubscribe a different handler
        event_bus.subscribe(MockEvent, handler)
        different_handler = MagicMock()
        event_bus.unsubscribe(MockEvent, different_handler)

        # Original handler should still be there
        assert handler in event_bus._handlers[MockEvent]

    def test_unsubscribe_from_nonexistent_event_type(self):
        """Test unsubscribing from an event type that has no handlers."""
        event_bus = EventBus()
        handler = MagicMock()

        # Should not raise an exception
        event_bus.unsubscribe(MockEvent, handler)

    @pytest.mark.asyncio
    async def test_publish_with_no_handlers(self):
        """Test publishing an event with no handlers registered."""
        event_bus = EventBus()
        event = MockEvent(test_data="no handlers")

        # Should not raise an exception
        await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_with_sync_handler(self):
        """Test publishing an event to a synchronous handler."""
        event_bus = EventBus()
        handler = MagicMock()

        event_bus.subscribe(MockEvent, handler)
        event = MockEvent(test_data="sync test")

        await event_bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_with_async_handler(self):
        """Test publishing an event to an asynchronous handler."""
        event_bus = EventBus()
        handler = AsyncMock()

        event_bus.subscribe(MockEvent, handler)
        event = MockEvent(test_data="async test")

        await event_bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_with_multiple_handlers(self):
        """Test publishing an event to multiple handlers."""
        event_bus = EventBus()
        sync_handler = MagicMock()
        async_handler = AsyncMock()

        event_bus.subscribe(MockEvent, sync_handler)
        event_bus.subscribe(MockEvent, async_handler)

        event = MockEvent(test_data="multiple handlers")

        await event_bus.publish(event)

        sync_handler.assert_called_once_with(event)
        async_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_with_handler_exception(self):
        """Test publishing an event when a handler raises an exception."""
        event_bus = EventBus()

        # Create handlers where one fails
        good_handler = MagicMock()
        bad_handler = MagicMock(side_effect=Exception("Handler error"))
        another_good_handler = MagicMock()

        event_bus.subscribe(MockEvent, good_handler)
        event_bus.subscribe(MockEvent, bad_handler)
        event_bus.subscribe(MockEvent, another_good_handler)

        event = MockEvent(test_data="exception test")

        # Should not raise exception - errors are logged and isolated
        await event_bus.publish(event)

        # Good handlers should still be called
        good_handler.assert_called_once_with(event)
        another_good_handler.assert_called_once_with(event)
        bad_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_with_async_handler_exception(self):
        """Test publishing an event when an async handler raises an exception."""
        event_bus = EventBus()

        good_handler = AsyncMock()
        bad_handler = AsyncMock(side_effect=Exception("Async handler error"))

        event_bus.subscribe(MockEvent, good_handler)
        event_bus.subscribe(MockEvent, bad_handler)

        event = MockEvent(test_data="async exception test")

        await event_bus.publish(event)

        good_handler.assert_called_once_with(event)
        bad_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_different_event_types(self):
        """Test publishing different event types to different handlers."""
        event_bus = EventBus()

        test_handler = MagicMock()
        another_handler = MagicMock()

        event_bus.subscribe(MockEvent, test_handler)
        event_bus.subscribe(AnotherMockEvent, another_handler)

        test_event = MockEvent(test_data="test event")
        another_event = AnotherMockEvent(message="another event")

        await event_bus.publish(test_event)
        await event_bus.publish(another_event)

        test_handler.assert_called_once_with(test_event)
        another_handler.assert_called_once_with(another_event)

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing(self):
        """Test publishing multiple events concurrently."""

        event_bus = EventBus()
        handler = AsyncMock()

        event_bus.subscribe(MockEvent, handler)

        # Create multiple events
        events = [MockEvent(test_data=f"event_{i}", test_value=i) for i in range(5)]

        # Publish all events concurrently
        await asyncio.gather(*[event_bus.publish(event) for event in events])

        # All events should be handled
        assert handler.call_count == 5

    @pytest.mark.asyncio
    async def test_event_handler_receives_correct_event_data(self):
        """Test that event handlers receive the correct event data."""
        event_bus = EventBus()
        received_events = []

        def capturing_handler(event):
            received_events.append(event)

        event_bus.subscribe(MockEvent, capturing_handler)

        original_event = MockEvent(test_data="specific data", test_value=999)
        await event_bus.publish(original_event)

        assert len(received_events) == 1
        received_event = received_events[0]
        assert received_event.test_data == "specific data"
        assert received_event.test_value == 999
        assert received_event.event_id == original_event.event_id
        assert received_event.occurred_at == original_event.occurred_at

    def test_event_bus_isolation(self):
        """Test that multiple event buses are isolated from each other."""
        event_bus1 = EventBus()
        event_bus2 = EventBus()

        handler1 = MagicMock()
        handler2 = MagicMock()

        event_bus1.subscribe(MockEvent, handler1)
        event_bus2.subscribe(MockEvent, handler2)

        # Each bus should have its own handlers
        assert len(event_bus1._handlers[MockEvent]) == 1
        assert len(event_bus2._handlers[MockEvent]) == 1
        assert handler1 in event_bus1._handlers[MockEvent]
        assert handler2 in event_bus2._handlers[MockEvent]
        assert handler1 not in event_bus2._handlers.get(MockEvent, [])
        assert handler2 not in event_bus1._handlers.get(MockEvent, [])

    @pytest.mark.asyncio
    async def test_handler_with_complex_logic(self):
        """Test handler that performs complex operations."""
        event_bus = EventBus()
        results = []

        async def complex_handler(event):
            # Simulate complex async operation
            await asyncio.sleep(0.01)
            results.append(f"Processed: {event.test_data}")
            if event.test_value > 50:
                results.append("High value detected")

        event_bus.subscribe(MockEvent, complex_handler)

        await event_bus.publish(MockEvent(test_data="low", test_value=10))
        await event_bus.publish(MockEvent(test_data="high", test_value=100))

        assert len(results) == 3
        assert "Processed: low" in results
        assert "Processed: high" in results
        assert "High value detected" in results

    @pytest.mark.asyncio
    async def test_empty_event_bus_performance(self):
        """Test that empty event bus performs well."""
        event_bus = EventBus()

        # Publishing many events to empty bus should be fast
        events = [MockEvent(test_data=f"event_{i}") for i in range(100)]

        import time

        start_time = time.time()
        for event in events:
            await event_bus.publish(event)
        end_time = time.time()

        # Should complete very quickly (less than 1 second for 100 events)
        assert (end_time - start_time) < 1.0

    def test_domain_event_str_representation(self):
        """Test DomainEvent __str__ method."""
        event = MockEvent(test_data="test_string")

        str_repr = str(event)
        assert "MockEvent" in str_repr
        assert event.event_id in str_repr
        assert str_repr.startswith("MockEvent(event_id=")

    def test_domain_event_name_property(self):
        """Test DomainEvent event_name property."""
        event = MockEvent(test_data="test_name")
        another_event = AnotherMockEvent(message="test")

        assert event.event_name == "MockEvent"
        assert another_event.event_name == "AnotherMockEvent"

    @pytest.mark.asyncio
    async def test_event_bus_error_logging(self):
        """Test EventBus error logging during publish."""
        event_bus = EventBus()

        # Create a handler that will cause an error
        def bad_handler(_event):
            raise RuntimeError("Critical error in handler")

        # Subscribe the bad handler
        event_bus.subscribe(MockEvent, bad_handler)

        event = MockEvent(test_data="error_test")

        # The error should be caught and logged, not raised
        await event_bus.publish(event)  # Should not raise

    @pytest.mark.asyncio
    async def test_event_bus_critical_publish_error(self):
        """Test EventBus critical error during publish that gets re-raised."""
        event_bus = EventBus()

        # Mock asyncio.gather to raise an exception
        with patch("asyncio.gather", side_effect=RuntimeError("Critical gather error")):
            event = MockEvent(test_data="critical_test")

            # Add a handler so publish() gets to the gather() call
            def handler(_event):
                pass

            event_bus.subscribe(MockEvent, handler)

            # The critical error should be logged and re-raised
            with pytest.raises(RuntimeError, match="Critical gather error"):
                await event_bus.publish(event)

    def test_get_active_subscriptions(self):
        """Test getting active subscription counts."""
        event_bus = EventBus()

        # Initially no subscriptions
        subscriptions = event_bus.get_active_subscriptions()
        assert subscriptions == {}

        # Add some handlers
        def handler1(_event):
            pass

        def handler2(_event):
            pass

        event_bus.subscribe(MockEvent, handler1)
        event_bus.subscribe(MockEvent, handler2)

        # Check subscription count
        subscriptions = event_bus.get_active_subscriptions()
        assert "MockEvent" in subscriptions
        assert subscriptions["MockEvent"] == 2

    def test_clear_subscriptions(self):
        """Test clearing all event subscriptions."""
        event_bus = EventBus()

        # Add some handlers
        def handler(_event):
            pass

        event_bus.subscribe(MockEvent, handler)
        assert event_bus.get_handler_count(MockEvent) == 1

        # Clear all subscriptions
        event_bus.clear_subscriptions()
        assert event_bus.get_handler_count(MockEvent) == 0
        assert event_bus.get_active_subscriptions() == {}

    def test_get_handler_count(self):
        """Test getting handler count for specific event type."""
        event_bus = EventBus()

        # Initially no handlers
        assert event_bus.get_handler_count(MockEvent) == 0

        # Add handlers
        def handler1(_event):
            pass

        def handler2(_event):
            pass

        event_bus.subscribe(MockEvent, handler1)
        assert event_bus.get_handler_count(MockEvent) == 1

        event_bus.subscribe(MockEvent, handler2)
        assert event_bus.get_handler_count(MockEvent) == 2
