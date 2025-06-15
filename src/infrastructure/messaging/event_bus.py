"""Lightweight in-memory event bus for local-first architecture.

This module provides an async event bus system designed for local-first applications
where events are processed in-memory without persistent storage to avoid database bloat.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DomainEvent:
    """Base class for all domain events.

    All domain events must inherit from this class and will automatically
    get an event_id and occurred_at timestamp.

    Note: This is not a dataclass to avoid issues with inheritance
    when child classes have required fields.
    """

    def __init__(self, event_id: str = "", occurred_at: datetime | None = None):
        """Initialize domain event with auto-generated ID and timestamp.

        Args:
            event_id: Unique event identifier (auto-generated if empty)
            occurred_at: Event timestamp (auto-generated if None)
        """
        self.event_id = event_id or str(uuid4())
        self.occurred_at = occurred_at or datetime.now(UTC)

    def __str__(self) -> str:
        """Return string representation of the event."""
        return f"{self.__class__.__name__}(event_id={self.event_id})"

    @property
    def event_name(self) -> str:
        """Return the name of this event type."""
        return self.__class__.__name__


class EventBus:
    """Lightweight async event bus for domain event publishing.

    Designed for local-first applications where events are processed
    in-memory without persistent storage to avoid database bloat.

    Features:
    - Async event publishing and handling
    - Error isolation between handlers
    - Concurrent handler execution
    - Subscription management
    - No persistent event storage
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[type[DomainEvent], list[Callable[..., Any]]] = {}
        self._processing = False

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to all registered handlers asynchronously.

        Args:
            event: Domain event to publish

        Raises:
            Exception: If event publishing fails critically
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers registered for {event_type.__name__}")
            return

        logger.info(f"Publishing {event_type.__name__} to {len(handlers)} handlers")

        try:
            # Process all handlers concurrently
            await asyncio.gather(
                *[self._handle_event(handler, event) for handler in handlers],
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Critical error publishing {event_type.__name__}: {e}")
            raise

    async def _handle_event(
        self, handler: Callable[..., Any], event: DomainEvent
    ) -> None:
        """Handle individual event with error isolation.

        Args:
            handler: Event handler function (sync or async)
            event: Domain event to handle
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(
                f"Event handler {handler.__name__} failed for "
                f"{type(event).__name__}: {e}"
            )
            # Don't re-raise to prevent one handler failure from affecting others

    def subscribe(
        self, event_type: type[DomainEvent], handler: Callable[..., Any]
    ) -> None:
        """Subscribe handler to event type.

        Args:
            event_type: Type of domain event to subscribe to
            handler: Handler function (sync or async)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        handler_name = getattr(handler, "__name__", str(handler))
        logger.info(f"Subscribed {handler_name} to {event_type.__name__}")

    def unsubscribe(
        self, event_type: type[DomainEvent], handler: Callable[..., Any]
    ) -> None:
        """Unsubscribe handler from event type.

        Args:
            event_type: Type of domain event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                handler_name = getattr(handler, "__name__", str(handler))
                logger.info(f"Unsubscribed {handler_name} from {event_type.__name__}")
            except ValueError:
                handler_name = getattr(handler, "__name__", str(handler))
                logger.warning(
                    f"Handler {handler_name} not found for {event_type.__name__}"
                )

    def get_active_subscriptions(self) -> dict[str, int]:
        """Get count of active subscriptions by event type.

        Returns:
            Dictionary mapping event type names to handler counts
        """
        return {
            event_type.__name__: len(handlers)
            for event_type, handlers in self._handlers.items()
        }

    def clear_subscriptions(self) -> None:
        """Clear all event subscriptions.

        Useful for testing or application shutdown.
        """
        self._handlers.clear()
        logger.info("Cleared all event subscriptions")

    def get_handler_count(self, event_type: type[DomainEvent]) -> int:
        """Get number of handlers for specific event type.

        Args:
            event_type: Type of domain event

        Returns:
            Number of registered handlers
        """
        return len(self._handlers.get(event_type, []))
