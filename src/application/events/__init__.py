"""Event handlers for cross-cutting concerns in the application layer.

Event handlers follow CQRS pattern where each handler responds to domain events
and performs side effects, analytics, or cross-context operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.infrastructure.messaging.event_bus import DomainEvent

# Event type variable
T = TypeVar("T", bound=DomainEvent)


class EventHandler(ABC, Generic[T]):
    """Base class for all event handlers."""

    @abstractmethod
    async def handle(self, event: T) -> None:
        """Handle the domain event."""
        pass


class EventSubscriptionManager:
    """Manages event subscriptions for application-level event handlers."""

    def __init__(self, event_bus: Any) -> None:
        self.event_bus = event_bus
        self._handlers: dict[type[DomainEvent], list[EventHandler[Any]]] = {}

    def subscribe(
        self, event_type: type[DomainEvent], handler: EventHandler[Any]
    ) -> None:
        """Subscribe an event handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)

        # Register the handler with the event bus
        self.event_bus.subscribe(event_type, handler.handle)

    def get_subscriptions(self) -> dict[str, int]:
        """Get count of subscriptions by event type."""
        return {
            event_type.__name__: len(handlers)
            for event_type, handlers in self._handlers.items()
        }
