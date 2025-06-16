"""Tests for EventFlowOrchestrator."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from src.infrastructure.messaging.event_bus import DomainEvent, EventBus
from src.infrastructure.messaging.event_flow_orchestrator import (
    EventFlowDefinition,
    EventFlowOrchestrator,
    EventFlowValidationError,
)


class TestEvent(DomainEvent):
    """Test event for orchestrator testing."""

    def __init__(self, test_data: str = "test"):
        super().__init__()
        self.test_data = test_data


class AnotherTestEvent(DomainEvent):
    """Another test event for orchestrator testing."""

    def __init__(self, other_data: str = "other"):
        super().__init__()
        self.other_data = other_data


@pytest.fixture
def valid_flow_definition():
    """Create valid flow definition for testing."""
    return {
        "version": "1.0",
        "last_updated": "2025-06-16",
        "categories": {"test": "Test events", "system": "System events"},
        "events": {
            "TestEvent": {
                "category": "test",
                "triggers": ["AnotherTestEvent"],
                "dependencies": [],
                "description": "Test event",
            },
            "AnotherTestEvent": {
                "category": "test",
                "triggers": [],
                "dependencies": ["TestEvent"],
                "description": "Another test event",
            },
        },
        "flows": {
            "test_flow": {
                "name": "Test Flow",
                "description": "A test flow",
                "sequence": ["TestEvent", "AnotherTestEvent"],
                "validation": ["no_circular_dependencies"],
            }
        },
        "validation_rules": {
            "no_circular_dependencies": {
                "description": "Events cannot trigger themselves"
            }
        },
        "processing": {
            "async_execution": True,
            "event_bus_type": "in_memory",
            "max_event_queue_size": 1000,
        },
    }


@pytest.fixture
def circular_dependency_definition():
    """Create flow definition with circular dependencies."""
    return {
        "version": "1.0",
        "events": {
            "EventA": {
                "category": "test",
                "triggers": ["EventB"],
                "dependencies": ["EventB"],  # Circular dependency
                "description": "Event A",
            },
            "EventB": {
                "category": "test",
                "triggers": ["EventA"],
                "dependencies": ["EventA"],  # Circular dependency
                "description": "Event B",
            },
        },
    }


@pytest.fixture
def temp_yaml_file(valid_flow_definition):
    """Create temporary YAML file with flow definition."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(valid_flow_definition, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestEventFlowDefinition:
    """Test EventFlowDefinition class."""

    def test_initialization(self, valid_flow_definition):
        """Test EventFlowDefinition initialization."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert definition.version == "1.0"
        assert definition.last_updated == "2025-06-16"
        assert "test" in definition.categories
        assert "TestEvent" in definition.events
        assert "test_flow" in definition.flows

    def test_dependency_graph_building(self, valid_flow_definition):
        """Test dependency graph building."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert "TestEvent" in definition.dependency_graph
        assert "AnotherTestEvent" in definition.dependency_graph
        assert definition.dependency_graph["TestEvent"] == []
        assert definition.dependency_graph["AnotherTestEvent"] == ["TestEvent"]

    def test_trigger_graph_building(self, valid_flow_definition):
        """Test trigger graph building."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert definition.trigger_graph["TestEvent"] == ["AnotherTestEvent"]
        assert definition.trigger_graph["AnotherTestEvent"] == []

    def test_get_event_category(self, valid_flow_definition):
        """Test getting event category."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert definition.get_event_category("TestEvent") == "test"
        assert definition.get_event_category("NonExistentEvent") is None

    def test_get_event_dependencies(self, valid_flow_definition):
        """Test getting event dependencies."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert definition.get_event_dependencies("TestEvent") == []
        assert definition.get_event_dependencies("AnotherTestEvent") == ["TestEvent"]
        assert definition.get_event_dependencies("NonExistentEvent") == []

    def test_get_event_triggers(self, valid_flow_definition):
        """Test getting event triggers."""
        definition = EventFlowDefinition(valid_flow_definition)

        assert definition.get_event_triggers("TestEvent") == ["AnotherTestEvent"]
        assert definition.get_event_triggers("AnotherTestEvent") == []
        assert definition.get_event_triggers("NonExistentEvent") == []


class TestEventFlowOrchestrator:
    """Test EventFlowOrchestrator class."""

    def test_initialization_with_valid_file(self, temp_yaml_file):
        """Test orchestrator initialization with valid YAML file."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        assert orchestrator.flow_definition is not None
        assert orchestrator.validation_enabled
        assert orchestrator.monitoring_enabled

    def test_initialization_with_invalid_file(self):
        """Test orchestrator initialization with invalid file."""
        event_bus = EventBus()

        with pytest.raises(EventFlowValidationError, match="not found"):
            EventFlowOrchestrator(event_bus, "/nonexistent/path.yaml")

    def test_circular_dependency_detection(self, circular_dependency_definition):
        """Test circular dependency detection."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(circular_dependency_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(EventFlowValidationError, match="Circular dependency"):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_invalid_flow_references(self):
        """Test validation of invalid flow references."""
        invalid_definition = {
            "version": "1.0",
            "events": {
                "ValidEvent": {"category": "test", "triggers": [], "dependencies": []}
            },
            "flows": {
                "invalid_flow": {
                    "sequence": [
                        "ValidEvent",
                        "InvalidEvent",
                    ]  # InvalidEvent not defined
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(
                EventFlowValidationError, match="references undefined event"
            ):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.asyncio
    async def test_event_monitoring(self, temp_yaml_file):
        """Test event monitoring functionality."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Publish test event
        test_event = TestEvent("monitoring_test")
        await event_bus.publish(test_event)

        # Check that event was recorded
        history = orchestrator.get_event_history()
        assert len(history) > 0

        event_names = [name for name, _ in history]
        assert "TestEvent" in event_names

        # Check metrics
        metrics = orchestrator.get_event_metrics()
        assert "TestEvent" in metrics
        assert metrics["TestEvent"]["count"] >= 1

    def test_health_status(self, temp_yaml_file):
        """Test health status reporting."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        health = orchestrator.get_health_status()

        assert "orchestrator_status" in health
        assert "validation_enabled" in health
        assert "monitoring_enabled" in health
        assert "flow_definition_loaded" in health
        assert health["flow_definition_loaded"] is True

    def test_enable_disable_validation(self, temp_yaml_file):
        """Test enabling and disabling validation."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Initially enabled
        assert orchestrator.validation_enabled

        # Disable
        orchestrator.disable_validation()
        assert not orchestrator.validation_enabled

        # Re-enable
        orchestrator.enable_validation()
        assert orchestrator.validation_enabled

    def test_enable_disable_monitoring(self, temp_yaml_file):
        """Test enabling and disabling monitoring."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Initially enabled
        assert orchestrator.monitoring_enabled

        # Disable
        orchestrator.disable_monitoring()
        assert not orchestrator.monitoring_enabled

        # Re-enable
        orchestrator.enable_monitoring()
        assert orchestrator.monitoring_enabled

    @pytest.mark.asyncio
    async def test_event_replay(self, temp_yaml_file):
        """Test event replay functionality."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Publish multiple events
        await event_bus.publish(TestEvent("replay_test_1"))
        await event_bus.publish(AnotherTestEvent("replay_test_2"))
        await event_bus.publish(TestEvent("replay_test_3"))

        # Replay all events
        all_events = orchestrator.replay_events()
        assert len(all_events) >= 3

        # Replay specific event type
        test_events = orchestrator.replay_events(event_names=["TestEvent"])
        test_event_names = [name for name, _ in test_events]
        assert all(name == "TestEvent" for name in test_event_names)

        # Replay events since timestamp
        recent_time = datetime.now(UTC)
        recent_events = orchestrator.replay_events(since=recent_time)
        # Should be empty since we're asking for events after now
        assert len(recent_events) == 0

    def test_flow_sequence_status(self, temp_yaml_file):
        """Test flow sequence status reporting."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Get status for test flow
        status = orchestrator.get_flow_sequence_status("test_flow")

        assert "flow_name" in status
        assert "sequence" in status
        assert "completion_rate" in status
        assert status["flow_name"] == "test_flow"
        assert len(status["sequence"]) == 2  # TestEvent, AnotherTestEvent

        # Get status for non-existent flow
        error_status = orchestrator.get_flow_sequence_status("nonexistent_flow")
        assert "error" in error_status

    @pytest.mark.asyncio
    async def test_performance_metrics(self, temp_yaml_file):
        """Test performance metrics collection."""
        event_bus = EventBus()
        orchestrator = EventFlowOrchestrator(event_bus, temp_yaml_file)

        # Publish events to generate metrics
        for i in range(5):
            await event_bus.publish(TestEvent(f"perf_test_{i}"))

        metrics = orchestrator.get_event_metrics()
        test_metrics = metrics.get("TestEvent")

        assert test_metrics is not None
        assert test_metrics["count"] >= 5
        assert "avg_duration_ms" in test_metrics
        assert "min_duration_ms" in test_metrics
        assert "max_duration_ms" in test_metrics
        assert "total_duration_ms" in test_metrics
        assert "last_published" in test_metrics

    def test_yaml_parsing_error(self):
        """Test handling of YAML parsing errors."""
        # Create invalid YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(EventFlowValidationError, match="Invalid YAML"):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_self_referencing_circular_dependency(self):
        """Test detection of self-referencing circular dependencies."""
        self_ref_definition = {
            "version": "1.0",
            "events": {
                "SelfRefEvent": {
                    "category": "test",
                    "triggers": ["SelfRefEvent"],  # Self-referencing
                    "dependencies": [],
                    "description": "Self referencing event",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(self_ref_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(EventFlowValidationError, match="Circular dependency"):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_three_node_circular_dependency(self):
        """Test detection of three-node circular dependencies."""
        three_node_definition = {
            "version": "1.0",
            "events": {
                "EventA": {
                    "category": "test",
                    "triggers": ["EventB"],
                    "dependencies": [],
                    "description": "Event A",
                },
                "EventB": {
                    "category": "test",
                    "triggers": ["EventC"],
                    "dependencies": ["EventA"],
                    "description": "Event B",
                },
                "EventC": {
                    "category": "test",
                    "triggers": ["EventA"],  # Creates A -> B -> C -> A cycle
                    "dependencies": ["EventB"],
                    "description": "Event C",
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(three_node_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(EventFlowValidationError, match="Circular dependency"):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_complex_dependency_circular_dependency(self):
        """Test detection of complex circular dependency in dependencies only."""
        complex_dep_definition = {
            "version": "1.0",
            "events": {
                "StartEvent": {
                    "category": "test",
                    "triggers": [],
                    "dependencies": ["EndEvent"],  # Creates cycle in dependencies
                    "description": "Start event",
                },
                "MiddleEvent": {
                    "category": "test",
                    "triggers": [],
                    "dependencies": ["StartEvent"],
                    "description": "Middle event",
                },
                "EndEvent": {
                    "category": "test",
                    "triggers": [],
                    "dependencies": ["MiddleEvent"],  # Completes dependency cycle
                    "description": "End event",
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(complex_dep_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(
                EventFlowValidationError, match="Circular dependency.*dependencies"
            ):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_valid_complex_dependency_graph(self):
        """Test that valid complex dependency graphs pass validation."""
        valid_complex_definition = {
            "version": "1.0",
            "events": {
                "UserRegistered": {
                    "category": "user",
                    "triggers": ["ProfileCreated", "WelcomeEmailSent"],
                    "dependencies": [],
                    "description": "User registration",
                },
                "ProfileCreated": {
                    "category": "user",
                    "triggers": ["ProfileValidated"],
                    "dependencies": ["UserRegistered"],
                    "description": "Profile created",
                },
                "WelcomeEmailSent": {
                    "category": "user",
                    "triggers": [],
                    "dependencies": ["UserRegistered"],
                    "description": "Welcome email sent",
                },
                "ProfileValidated": {
                    "category": "user",
                    "triggers": ["AccountActivated"],
                    "dependencies": ["ProfileCreated"],
                    "description": "Profile validated",
                },
                "AccountActivated": {
                    "category": "user",
                    "triggers": [],
                    "dependencies": ["ProfileValidated"],
                    "description": "Account activated",
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_complex_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            # Should not raise an exception
            orchestrator = EventFlowOrchestrator(event_bus, temp_path)
            assert orchestrator.flow_definition is not None
            assert orchestrator.validation_enabled
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_dependency_cycle_in_triggers_graph(self):
        """Test detection of circular dependency in triggers graph specifically."""
        trigger_cycle_definition = {
            "version": "1.0",
            "events": {
                "EventX": {
                    "category": "test",
                    "triggers": ["EventY"],
                    "dependencies": [],
                    "description": "Event X",
                },
                "EventY": {
                    "category": "test",
                    "triggers": ["EventZ"],
                    "dependencies": [],
                    "description": "Event Y",
                },
                "EventZ": {
                    "category": "test",
                    "triggers": [
                        "EventX"
                    ],  # Creates cycle in triggers: X -> Y -> Z -> X
                    "dependencies": [],
                    "description": "Event Z",
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(trigger_cycle_definition, f)
            temp_path = Path(f.name)

        try:
            event_bus = EventBus()

            with pytest.raises(
                EventFlowValidationError, match="Circular dependency.*triggers"
            ):
                EventFlowOrchestrator(event_bus, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
