"""Consolidated EventBus implementation with optional flow validation.

This module provides both basic event bus functionality and enhanced flow validation
capabilities in a single unified implementation.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.shared.events import DomainEvent
from src.domain.shared.services import EventBusInterface

# Import EventFlowOrchestrator only when needed to avoid circular imports
if TYPE_CHECKING:
    from src.infrastructure.messaging.event_flow_orchestrator import (
        EventFlowOrchestrator,
    )

logger = logging.getLogger(__name__)


class EventBus(EventBusInterface):
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


class EnhancedEventBus(EventBus):
    """Enhanced EventBus with flow validation and monitoring.

    Extends the base EventBus with:
    - Event flow validation using YAML definitions
    - Performance monitoring and metrics
    - Health checks and debugging capabilities
    - Event replay for troubleshooting
    """

    def __init__(self, flow_definition_path: str | Path | None = None):
        """Initialize the enhanced event bus.

        Args:
            flow_definition_path: Path to event-flows.yaml file
                                If None, uses default path
        """
        super().__init__()

        # Setup flow orchestrator if path provided
        self.flow_orchestrator: EventFlowOrchestrator | None = None
        if flow_definition_path:
            try:
                # Import at runtime to avoid circular imports
                from src.infrastructure.messaging.event_flow_orchestrator import (
                    EventFlowOrchestrator,
                )

                self.flow_orchestrator = EventFlowOrchestrator(
                    event_bus=self, flow_definition_path=flow_definition_path
                )
                logger.info("Enhanced EventBus initialized with flow validation")
            except Exception as e:
                logger.warning(f"Failed to initialize flow orchestrator: {e}")
                logger.warning("Continuing with basic EventBus functionality")

    @classmethod
    def create_with_flow_validation(
        cls, flow_definition_path: str | Path
    ) -> EnhancedEventBus:
        """Factory method to create EnhancedEventBus with flow validation.

        Args:
            flow_definition_path: Path to event-flows.yaml file

        Returns:
            EnhancedEventBus instance with flow validation enabled
        """
        return cls(flow_definition_path=flow_definition_path)

    @classmethod
    def create_basic(cls) -> EnhancedEventBus:
        """Factory method to create EnhancedEventBus without flow validation.

        Returns:
            EnhancedEventBus instance without flow validation (behaves like basic EventBus)
        """
        return cls(flow_definition_path=None)

    def get_flow_metrics(self) -> dict[str, Any] | None:
        """Get event flow metrics from orchestrator.

        Returns:
            Event metrics dictionary or None if orchestrator not available
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.get_event_metrics()
        return None

    def get_flow_health(self) -> dict[str, Any] | None:
        """Get event flow health status.

        Returns:
            Health status dictionary or None if orchestrator not available
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.get_health_status()
        return None

    def get_event_history(self, limit: int = 100) -> list[tuple[str, Any]] | None:
        """Get recent event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events or None if orchestrator not available
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.get_event_history(limit)
        return None

    def replay_events(
        self, event_names: list[str] | None = None, since: Any = None
    ) -> list[tuple[str, Any]] | None:
        """Replay events for debugging.

        Args:
            event_names: Specific event names to replay (None for all)
            since: Only replay events since this timestamp (None for all)

        Returns:
            List of replayed events or None if orchestrator not available
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.replay_events(event_names, since)
        return None

    def get_flow_sequence_status(self, flow_name: str) -> dict[str, Any] | None:
        """Get status of a specific flow sequence.

        Args:
            flow_name: Name of the flow to check

        Returns:
            Flow sequence status or None if orchestrator not available
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.get_flow_sequence_status(flow_name)
        return None

    def enable_flow_validation(self) -> bool:
        """Enable event flow validation.

        Returns:
            True if validation was enabled, False if orchestrator not available
        """
        if self.flow_orchestrator:
            self.flow_orchestrator.enable_validation()
            return True
        return False

    def disable_flow_validation(self) -> bool:
        """Disable event flow validation.

        Returns:
            True if validation was disabled, False if orchestrator not available
        """
        if self.flow_orchestrator:
            self.flow_orchestrator.disable_validation()
            return True
        return False

    def enable_flow_monitoring(self) -> bool:
        """Enable event flow monitoring.

        Returns:
            True if monitoring was enabled, False if orchestrator not available
        """
        if self.flow_orchestrator:
            self.flow_orchestrator.enable_monitoring()
            return True
        return False

    def disable_flow_monitoring(self) -> bool:
        """Disable event flow monitoring.

        Returns:
            True if monitoring was disabled, False if orchestrator not available
        """
        if self.flow_orchestrator:
            self.flow_orchestrator.disable_monitoring()
            return True
        return False

    def is_flow_validation_enabled(self) -> bool:
        """Check if flow validation is enabled.

        Returns:
            True if validation is enabled, False otherwise
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.validation_enabled
        return False

    def is_flow_monitoring_enabled(self) -> bool:
        """Check if flow monitoring is enabled.

        Returns:
            True if monitoring is enabled, False otherwise
        """
        if self.flow_orchestrator:
            return self.flow_orchestrator.monitoring_enabled
        return False

    def get_debug_info(self) -> dict[str, Any]:
        """Get comprehensive debug information.

        Returns:
            Dictionary containing debug information
        """
        debug_info = {
            "event_bus_type": "enhanced",
            "active_subscriptions": self.get_active_subscriptions(),
            "flow_orchestrator_available": self.flow_orchestrator is not None,
        }

        if self.flow_orchestrator:
            debug_info.update(
                {
                    "flow_validation_enabled": self.flow_orchestrator.validation_enabled,
                    "flow_monitoring_enabled": self.flow_orchestrator.monitoring_enabled,
                    "flow_metrics": self.get_flow_metrics(),
                    "flow_health": self.get_flow_health(),
                    "recent_events": self.get_event_history(10),
                }
            )

        return debug_info
