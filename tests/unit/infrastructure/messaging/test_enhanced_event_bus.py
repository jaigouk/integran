"""Tests for EnhancedEventBus."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import yaml

from src.infrastructure.messaging.enhanced_event_bus import (
    DomainEvent,
    EnhancedEventBus,
)


class TestEvent(DomainEvent):
    """Test event for enhanced event bus testing."""

    def __init__(self, test_data: str = "test"):
        super().__init__()
        self.test_data = test_data


@pytest.fixture
def valid_flow_definition():
    """Create valid flow definition for testing."""
    return {
        "version": "1.0",
        "events": {
            "TestEvent": {
                "category": "test",
                "triggers": [],
                "dependencies": [],
                "description": "Test event",
            }
        },
        "flows": {"test_flow": {"sequence": ["TestEvent"]}},
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


class TestEnhancedEventBus:
    """Test EnhancedEventBus class."""

    def test_basic_creation(self):
        """Test creating basic enhanced event bus without flow validation."""
        bus = EnhancedEventBus.create_basic()

        assert bus.flow_orchestrator is None
        assert not bus.is_flow_validation_enabled()
        assert not bus.is_flow_monitoring_enabled()

    def test_creation_with_flow_validation(self, temp_yaml_file):
        """Test creating enhanced event bus with flow validation."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        assert bus.flow_orchestrator is not None
        assert bus.is_flow_validation_enabled()
        assert bus.is_flow_monitoring_enabled()

    def test_creation_with_invalid_yaml_path(self):
        """Test creating enhanced event bus with invalid YAML path."""
        # Should not raise exception, just log warning and continue
        bus = EnhancedEventBus("/nonexistent/path.yaml")

        assert bus.flow_orchestrator is None

    @pytest.mark.asyncio
    async def test_basic_event_publishing(self):
        """Test basic event publishing functionality."""
        bus = EnhancedEventBus.create_basic()

        # Should work like normal EventBus
        event_received = False

        def handler(_event):
            nonlocal event_received
            event_received = True

        bus.subscribe(TestEvent, handler)
        await bus.publish(TestEvent("basic_test"))

        # Give handlers time to execute
        await asyncio.sleep(0.01)

        assert event_received

    @pytest.mark.asyncio
    async def test_enhanced_event_publishing(self, temp_yaml_file):
        """Test enhanced event publishing with flow validation."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        event_received = False

        def handler(_event):
            nonlocal event_received
            event_received = True

        bus.subscribe(TestEvent, handler)
        await bus.publish(TestEvent("enhanced_test"))

        # Give handlers time to execute
        await asyncio.sleep(0.01)

        assert event_received

        # Check that event was monitored
        history = bus.get_event_history()
        assert history is not None
        assert len(history) > 0

    def test_flow_metrics_basic_bus(self):
        """Test flow metrics on basic bus (should return None)."""
        bus = EnhancedEventBus.create_basic()

        assert bus.get_flow_metrics() is None
        assert bus.get_flow_health() is None
        assert bus.get_event_history() is None

    def test_flow_metrics_enhanced_bus(self, temp_yaml_file):
        """Test flow metrics on enhanced bus."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        assert bus.get_flow_metrics() is not None
        assert bus.get_flow_health() is not None
        assert bus.get_event_history() is not None

    def test_validation_control_basic_bus(self):
        """Test validation control on basic bus."""
        bus = EnhancedEventBus.create_basic()

        assert not bus.enable_flow_validation()
        assert not bus.disable_flow_validation()
        assert not bus.enable_flow_monitoring()
        assert not bus.disable_flow_monitoring()

    def test_validation_control_enhanced_bus(self, temp_yaml_file):
        """Test validation control on enhanced bus."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        # Initially enabled
        assert bus.is_flow_validation_enabled()
        assert bus.is_flow_monitoring_enabled()

        # Disable validation
        assert bus.disable_flow_validation()
        assert not bus.is_flow_validation_enabled()

        # Re-enable validation
        assert bus.enable_flow_validation()
        assert bus.is_flow_validation_enabled()

        # Disable monitoring
        assert bus.disable_flow_monitoring()
        assert not bus.is_flow_monitoring_enabled()

        # Re-enable monitoring
        assert bus.enable_flow_monitoring()
        assert bus.is_flow_monitoring_enabled()

    def test_flow_sequence_status_basic_bus(self):
        """Test flow sequence status on basic bus."""
        bus = EnhancedEventBus.create_basic()

        assert bus.get_flow_sequence_status("any_flow") is None

    def test_flow_sequence_status_enhanced_bus(self, temp_yaml_file):
        """Test flow sequence status on enhanced bus."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        status = bus.get_flow_sequence_status("test_flow")
        assert status is not None
        assert "flow_name" in status

        # Test non-existent flow
        error_status = bus.get_flow_sequence_status("nonexistent_flow")
        assert error_status is not None
        assert "error" in error_status

    def test_replay_events_basic_bus(self):
        """Test event replay on basic bus."""
        bus = EnhancedEventBus.create_basic()

        assert bus.replay_events() is None
        assert bus.replay_events(["TestEvent"]) is None

    @pytest.mark.asyncio
    async def test_replay_events_enhanced_bus(self, temp_yaml_file):
        """Test event replay on enhanced bus."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        # Publish some events
        await bus.publish(TestEvent("replay_test_1"))
        await bus.publish(TestEvent("replay_test_2"))

        # Replay all events
        all_events = bus.replay_events()
        assert all_events is not None
        assert len(all_events) >= 2

        # Replay specific events
        test_events = bus.replay_events(["TestEvent"])
        assert test_events is not None
        event_names = [name for name, _ in test_events]
        assert all(name == "TestEvent" for name in event_names)

    def test_debug_info_basic_bus(self):
        """Test debug info on basic bus."""
        bus = EnhancedEventBus.create_basic()

        debug_info = bus.get_debug_info()

        assert debug_info["event_bus_type"] == "enhanced"
        assert debug_info["flow_orchestrator_available"] is False
        assert "active_subscriptions" in debug_info

    def test_debug_info_enhanced_bus(self, temp_yaml_file):
        """Test debug info on enhanced bus."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_yaml_file)

        debug_info = bus.get_debug_info()

        assert debug_info["event_bus_type"] == "enhanced"
        assert debug_info["flow_orchestrator_available"] is True
        assert debug_info["flow_validation_enabled"] is True
        assert debug_info["flow_monitoring_enabled"] is True
        assert "flow_metrics" in debug_info
        assert "flow_health" in debug_info
        assert "recent_events" in debug_info

    def test_inherits_base_functionality(self):
        """Test that enhanced bus inherits all base EventBus functionality."""
        bus = EnhancedEventBus.create_basic()

        # Should have all base methods
        assert hasattr(bus, "subscribe")
        assert hasattr(bus, "unsubscribe")
        assert hasattr(bus, "publish")
        assert hasattr(bus, "get_active_subscriptions")
        assert hasattr(bus, "clear_subscriptions")
        assert hasattr(bus, "get_handler_count")

        # Test basic subscription functionality
        handler_called = False

        def test_handler(_event):
            nonlocal handler_called
            handler_called = True

        bus.subscribe(TestEvent, test_handler)
        assert bus.get_handler_count(TestEvent) == 1

        subscriptions = bus.get_active_subscriptions()
        assert "TestEvent" in subscriptions
        assert subscriptions["TestEvent"] == 1
