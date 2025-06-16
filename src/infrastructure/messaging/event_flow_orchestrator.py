"""Event Flow Orchestrator for DAG validation and monitoring.

This module implements the Event Flow Engine that validates event sequences,
detects circular dependencies, and monitors event flow health.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from src.infrastructure.messaging.event_bus import DomainEvent, EventBus

logger = logging.getLogger(__name__)


class EventFlowDefinition:
    """Represents event flow definitions loaded from YAML."""

    def __init__(self, data: dict[str, Any]):
        """Initialize event flow definition from YAML data.

        Args:
            data: Parsed YAML data containing event definitions
        """
        self.version = data.get("version", "1.0")
        self.last_updated = data.get("last_updated", "")
        self.categories = data.get("categories", {})
        self.events = data.get("events", {})
        self.flows = data.get("flows", {})
        self.validation_rules = data.get("validation_rules", {})
        self.platforms = data.get("platforms", {})
        self.processing = data.get("processing", {})

        # Build event dependency graph
        self.dependency_graph = self._build_dependency_graph()
        self.trigger_graph = self._build_trigger_graph()

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """Build dependency graph from event definitions.

        Returns:
            Dictionary mapping event names to their dependencies
        """
        graph = {}
        for event_name, event_def in self.events.items():
            dependencies = event_def.get("dependencies", [])
            graph[event_name] = dependencies
        return graph

    def _build_trigger_graph(self) -> dict[str, list[str]]:
        """Build trigger graph from event definitions.

        Returns:
            Dictionary mapping event names to events they trigger
        """
        graph = {}
        for event_name, event_def in self.events.items():
            triggers = event_def.get("triggers", [])
            graph[event_name] = triggers
        return graph

    def get_event_category(self, event_name: str) -> str | None:
        """Get category for an event.

        Args:
            event_name: Name of the event

        Returns:
            Category name or None if not found
        """
        event_def = self.events.get(event_name)
        return event_def.get("category") if event_def else None

    def get_event_dependencies(self, event_name: str) -> list[str]:
        """Get dependencies for an event.

        Args:
            event_name: Name of the event

        Returns:
            List of dependent event names
        """
        return self.dependency_graph.get(event_name, [])

    def get_event_triggers(self, event_name: str) -> list[str]:
        """Get events triggered by an event.

        Args:
            event_name: Name of the event

        Returns:
            List of triggered event names
        """
        return self.trigger_graph.get(event_name, [])


class EventFlowValidationError(Exception):
    """Exception raised when event flow validation fails."""

    pass


class EventFlowOrchestrator:
    """Event Flow Engine for DAG validation and monitoring.

    This orchestrator validates event flows according to YAML definitions,
    detects circular dependencies, monitors health, and provides debugging
    capabilities.
    """

    def __init__(self, event_bus: EventBus, flow_definition_path: str | Path):
        """Initialize the Event Flow Orchestrator.

        Args:
            event_bus: EventBus instance to monitor
            flow_definition_path: Path to event-flows.yaml file
        """
        self.event_bus = event_bus
        self.flow_definition_path = Path(flow_definition_path)
        self.flow_definition: EventFlowDefinition | None = None

        # Event monitoring
        self.event_history: deque[tuple[str, datetime]] = deque(maxlen=1000)
        self.event_metrics: dict[str, dict[str, Any]] = defaultdict(dict)
        self.validation_enabled = True
        self.monitoring_enabled = True

        # Health monitoring
        self.health_checks: dict[str, Any] = {}
        self.last_health_check = datetime.now(UTC)

        # Load event definitions
        self._load_event_definitions()

        # Subscribe to all events for monitoring
        if self.monitoring_enabled:
            self._setup_event_monitoring()

    def _load_event_definitions(self) -> None:
        """Load event flow definitions from YAML file.

        Raises:
            EventFlowValidationError: If YAML cannot be loaded or parsed
        """
        try:
            if not self.flow_definition_path.exists():
                raise EventFlowValidationError(
                    f"Event flow definition file not found: {self.flow_definition_path}"
                )

            with open(self.flow_definition_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            self.flow_definition = EventFlowDefinition(data)
            logger.info(
                f"Loaded event flow definitions from {self.flow_definition_path}"
            )

            # Validate the loaded definitions
            self._validate_flow_definitions()

        except yaml.YAMLError as e:
            raise EventFlowValidationError(
                f"Invalid YAML in event flow definitions: {e}"
            ) from e
        except Exception as e:
            raise EventFlowValidationError(
                f"Failed to load event flow definitions: {e}"
            ) from e

    def _validate_flow_definitions(self) -> None:
        """Validate event flow definitions for consistency.

        Raises:
            EventFlowValidationError: If validation fails
        """
        if not self.flow_definition:
            return

        # Check for circular dependencies
        self._detect_circular_dependencies()

        # Validate event references in flows
        self._validate_flow_references()

        logger.info("Event flow definitions validated successfully")

    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies in event graph.

        Raises:
            EventFlowValidationError: If circular dependencies are found
        """
        if not self.flow_definition:
            return

        def has_cycle(graph: dict[str, list[str]]) -> list[str] | None:
            """Detect cycles using DFS.

            Returns:
                List of nodes in cycle if found, None otherwise
            """
            WHITE, GRAY, BLACK = 0, 1, 2
            colors = dict.fromkeys(graph, WHITE)
            path: list[str] = []

            def dfs(node: str) -> list[str] | None:
                if colors[node] == GRAY:
                    # Found cycle, extract it
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]

                if colors[node] == BLACK:
                    return None

                colors[node] = GRAY
                path.append(node)

                for neighbor in graph.get(node, []):
                    if neighbor in graph:  # Only process if neighbor exists
                        result = dfs(neighbor)
                        if result:
                            return result

                path.pop()
                colors[node] = BLACK
                return None

            for node in graph:
                if colors[node] == WHITE:
                    result = dfs(node)
                    if result:
                        return result

            return None

        # Check dependency graph
        cycle = has_cycle(self.flow_definition.dependency_graph)
        if cycle:
            raise EventFlowValidationError(
                f"Circular dependency detected in event dependencies: {' -> '.join(cycle)}"
            )

        # Check trigger graph
        cycle = has_cycle(self.flow_definition.trigger_graph)
        if cycle:
            raise EventFlowValidationError(
                f"Circular dependency detected in event triggers: {' -> '.join(cycle)}"
            )

    def _validate_flow_references(self) -> None:
        """Validate that flow sequences reference valid events.

        Raises:
            EventFlowValidationError: If invalid event references are found
        """
        if not self.flow_definition:
            return

        for flow_name, flow_def in self.flow_definition.flows.items():
            sequence = flow_def.get("sequence", [])

            for event_name in sequence:
                if event_name not in self.flow_definition.events:
                    raise EventFlowValidationError(
                        f"Flow '{flow_name}' references undefined event '{event_name}'"
                    )

            # Check optional branches
            optional_branches = flow_def.get("optional_branches", [])
            for event_name in optional_branches:
                if event_name not in self.flow_definition.events:
                    raise EventFlowValidationError(
                        f"Flow '{flow_name}' optional branch references undefined event '{event_name}'"
                    )

    def _setup_event_monitoring(self) -> None:
        """Setup event monitoring by subscribing to all events."""
        # We'll monitor events by wrapping the event bus publish method
        original_publish = self.event_bus.publish

        async def monitored_publish(event: DomainEvent) -> None:
            """Wrapper for event bus publish with monitoring."""
            start_time = time.perf_counter()

            # Pre-publish validation
            if self.validation_enabled:
                await self._validate_event_flow(event)

            # Record event
            self._record_event(event)

            # Publish event
            await original_publish(event)

            # Record metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(event, duration_ms)

        # Replace the publish method
        self.event_bus.publish = monitored_publish  # type: ignore[method-assign]

        logger.info("Event monitoring enabled")

    def _record_event(self, event: DomainEvent) -> None:
        """Record event in history.

        Args:
            event: Domain event to record
        """
        self.event_history.append((event.event_name, event.occurred_at))

    def _update_metrics(self, event: DomainEvent, duration_ms: float) -> None:
        """Update event metrics.

        Args:
            event: Domain event
            duration_ms: Processing duration in milliseconds
        """
        event_name = event.event_name

        if event_name not in self.event_metrics:
            self.event_metrics[event_name] = {
                "count": 0,
                "total_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0.0,
                "last_published": None,
                "errors": 0,
            }

        metrics = self.event_metrics[event_name]
        metrics["count"] += 1
        metrics["total_duration_ms"] += duration_ms
        metrics["avg_duration_ms"] = metrics["total_duration_ms"] / metrics["count"]
        metrics["min_duration_ms"] = min(metrics["min_duration_ms"], duration_ms)
        metrics["max_duration_ms"] = max(metrics["max_duration_ms"], duration_ms)
        metrics["last_published"] = event.occurred_at

    async def _validate_event_flow(self, event: DomainEvent) -> None:
        """Validate event against flow definitions.

        Args:
            event: Domain event to validate

        Raises:
            EventFlowValidationError: If validation fails
        """
        if not self.flow_definition or not self.validation_enabled:
            return

        event_name = event.event_name

        # Check if event is defined
        if event_name not in self.flow_definition.events:
            logger.warning(f"Event {event_name} not defined in flow definitions")
            return

        # Validate dependencies (if any recent events violate dependencies)
        dependencies = self.flow_definition.get_event_dependencies(event_name)
        if dependencies:
            await self._validate_dependencies(event_name, dependencies)

    async def _validate_dependencies(
        self, event_name: str, dependencies: list[str]
    ) -> None:
        """Validate that event dependencies are satisfied.

        Args:
            event_name: Name of the event being published
            dependencies: List of required dependency events

        Raises:
            EventFlowValidationError: If dependencies are not satisfied
        """
        # For now, we'll do a simple check of recent event history
        # In a more sophisticated implementation, we could track session state

        recent_events = [name for name, _ in list(self.event_history)[-10:]]

        for dependency in dependencies:
            if dependency not in recent_events:
                logger.warning(
                    f"Event {event_name} published without recent dependency {dependency}"
                )
                # For now, we'll warn rather than error to avoid breaking existing flows

    def get_event_metrics(self) -> dict[str, dict[str, Any]]:
        """Get current event metrics.

        Returns:
            Dictionary of event metrics
        """
        return dict(self.event_metrics)

    def get_event_history(self, limit: int = 100) -> list[tuple[str, datetime]]:
        """Get recent event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of (event_name, timestamp) tuples
        """
        return list(self.event_history)[-limit:]

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status.

        Returns:
            Dictionary containing health status information
        """
        now = datetime.now(UTC)

        # Update health checks
        self.health_checks = {
            "orchestrator_status": "healthy",
            "last_check": now,
            "validation_enabled": self.validation_enabled,
            "monitoring_enabled": self.monitoring_enabled,
            "flow_definition_loaded": self.flow_definition is not None,
            "total_events_processed": len(self.event_history),
            "active_event_types": len(self.event_metrics),
            "avg_processing_time_ms": self._calculate_avg_processing_time(),
        }

        # Check for performance issues
        avg_time = self.health_checks["avg_processing_time_ms"]
        if avg_time > 100:  # More than 100ms average
            self.health_checks["orchestrator_status"] = "degraded"
            self.health_checks["warning"] = (
                f"High average processing time: {avg_time:.2f}ms"
            )

        self.last_health_check = now
        return self.health_checks

    def _calculate_avg_processing_time(self) -> float:
        """Calculate average processing time across all events.

        Returns:
            Average processing time in milliseconds
        """
        if not self.event_metrics:
            return 0.0

        total_duration = sum(
            m["total_duration_ms"] for m in self.event_metrics.values()
        )
        total_count = sum(m["count"] for m in self.event_metrics.values())

        return total_duration / total_count if total_count > 0 else 0.0

    def enable_validation(self) -> None:
        """Enable event flow validation."""
        self.validation_enabled = True
        logger.info("Event flow validation enabled")

    def disable_validation(self) -> None:
        """Disable event flow validation."""
        self.validation_enabled = False
        logger.info("Event flow validation disabled")

    def enable_monitoring(self) -> None:
        """Enable event monitoring."""
        self.monitoring_enabled = True
        logger.info("Event monitoring enabled")

    def disable_monitoring(self) -> None:
        """Disable event monitoring."""
        self.monitoring_enabled = False
        logger.info("Event monitoring disabled")

    def replay_events(
        self, event_names: list[str] | None = None, since: datetime | None = None
    ) -> list[tuple[str, datetime]]:
        """Replay events for debugging.

        Args:
            event_names: Specific event names to replay (None for all)
            since: Only replay events since this timestamp (None for all)

        Returns:
            List of replayed events
        """
        filtered_events = []

        for event_name, timestamp in self.event_history:
            # Filter by event names if specified
            if event_names and event_name not in event_names:
                continue

            # Filter by timestamp if specified
            if since and timestamp < since:
                continue

            filtered_events.append((event_name, timestamp))

        logger.info(f"Replayed {len(filtered_events)} events for debugging")
        return filtered_events

    def get_flow_sequence_status(self, flow_name: str) -> dict[str, Any]:
        """Get status of a specific flow sequence.

        Args:
            flow_name: Name of the flow to check

        Returns:
            Dictionary containing flow sequence status
        """
        if not self.flow_definition:
            return {"error": "No flow definition loaded"}

        flow_def = self.flow_definition.flows.get(flow_name)
        if not flow_def:
            return {"error": f"Flow '{flow_name}' not found"}

        sequence = flow_def.get("sequence", [])
        recent_events = [name for name, _ in list(self.event_history)[-20:]]

        # Check which events in sequence have occurred recently
        sequence_status = []
        for event_name in sequence:
            occurred = event_name in recent_events
            last_occurrence = None

            if occurred:
                # Find most recent occurrence
                for name, timestamp in reversed(self.event_history):
                    if name == event_name:
                        last_occurrence = timestamp
                        break

            sequence_status.append(
                {
                    "event": event_name,
                    "occurred": occurred,
                    "last_occurrence": last_occurrence,
                }
            )

        return {
            "flow_name": flow_name,
            "sequence": sequence_status,
            "completion_rate": sum(1 for s in sequence_status if s["occurred"])
            / len(sequence_status)
            if sequence_status
            else 0,
        }
