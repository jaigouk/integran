"""Enhanced EventBus with flow validation integration.

This module extends the basic EventBus with flow validation capabilities
using the EventFlowOrchestrator.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.infrastructure.messaging.event_bus import EventBus as BaseEventBus
from src.infrastructure.messaging.event_flow_orchestrator import EventFlowOrchestrator

logger = logging.getLogger(__name__)


class EnhancedEventBus(BaseEventBus):
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
            EnhancedEventBus instance without flow validation
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
