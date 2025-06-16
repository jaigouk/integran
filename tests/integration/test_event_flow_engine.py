"""Integration tests for the Event Flow Engine.

These tests validate the complete Event Flow Engine functionality
including EventFlowOrchestrator and EnhancedEventBus integration.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
import yaml

from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from tests.fixtures.event_flow_demo import (
    get_monitoring_data,
    run_comprehensive_test,
    simulate_learning_session_flow,
    simulate_user_registration_flow,
    validate_flow_capabilities,
)


@pytest.fixture
def complete_flow_definition():
    """Create complete flow definition for integration testing."""
    return {
        "version": "1.0",
        "last_updated": "2025-06-16",
        "categories": {
            "user": "User management events",
            "learning": "Learning session events",
            "system": "System events",
        },
        "events": {
            "UserRegisteredEvent": {
                "category": "user",
                "triggers": ["ProfileCreatedEvent"],
                "dependencies": [],
                "description": "User registration completed",
            },
            "ProfileCreatedEvent": {
                "category": "user",
                "triggers": ["WelcomeEmailSentEvent"],
                "dependencies": ["UserRegisteredEvent"],
                "description": "User profile created",
            },
            "WelcomeEmailSentEvent": {
                "category": "user",
                "triggers": [],
                "dependencies": ["ProfileCreatedEvent"],
                "description": "Welcome email sent to user",
            },
            "SessionStartedEvent": {
                "category": "learning",
                "triggers": ["QuestionAnsweredEvent"],
                "dependencies": [],
                "description": "Learning session started",
            },
            "QuestionAnsweredEvent": {
                "category": "learning",
                "triggers": [],
                "dependencies": ["SessionStartedEvent"],
                "description": "Question answered in session",
            },
        },
        "flows": {
            "user_registration": {
                "name": "User Registration Flow",
                "description": "Complete user onboarding process",
                "sequence": [
                    "UserRegisteredEvent",
                    "ProfileCreatedEvent",
                    "WelcomeEmailSentEvent",
                ],
                "validation": ["no_circular_dependencies", "sequential_execution"],
            },
            "learning_session": {
                "name": "Learning Session Flow",
                "description": "Interactive learning session",
                "sequence": ["SessionStartedEvent", "QuestionAnsweredEvent"],
                "loops": [
                    {
                        "from": "QuestionAnsweredEvent",
                        "to": "QuestionAnsweredEvent",
                        "condition": "more_questions_available",
                    }
                ],
                "validation": ["conditional_branching_allowed"],
            },
        },
        "validation_rules": {
            "no_circular_dependencies": {
                "description": "Events cannot trigger themselves directly or indirectly"
            },
            "sequential_execution": {
                "description": "Events must execute in defined order"
            },
            "conditional_branching_allowed": {
                "description": "Events may branch based on conditions"
            },
        },
        "platforms": {
            "terminal": {"supports_all_flows": True, "keyboard_navigation": True}
        },
        "processing": {
            "async_execution": True,
            "event_bus_type": "in_memory",
            "max_event_queue_size": 1000,
            "event_timeout_ms": 5000,
        },
    }


@pytest.fixture
def temp_flow_file(complete_flow_definition):
    """Create temporary flow definition file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(complete_flow_definition, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestEventFlowEngineIntegration:
    """Integration tests for Event Flow Engine."""

    def test_basic_event_bus_creation(self):
        """Test creating basic enhanced event bus."""
        bus = EnhancedEventBus.create_basic()

        validation_data = validate_flow_capabilities(bus)

        assert not validation_data["validation_enabled"]
        assert not validation_data["monitoring_enabled"]
        assert not validation_data["orchestrator_available"]

    def test_enhanced_event_bus_creation(self, temp_flow_file):
        """Test creating enhanced event bus with flow validation."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        validation_data = validate_flow_capabilities(bus)

        assert validation_data["validation_enabled"]
        assert validation_data["monitoring_enabled"]
        assert validation_data["orchestrator_available"]
        assert "flows_available" in validation_data
        assert "user_registration" in validation_data["flows_available"]
        assert "learning_session" in validation_data["flows_available"]

    @pytest.mark.asyncio
    async def test_user_registration_flow_simulation(self, temp_flow_file):
        """Test simulating user registration flow."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        events_received = []

        def event_handler(event):
            events_received.append(event.event_name)

        # Subscribe to all user events
        from tests.fixtures.event_flow_demo import (
            ProfileCreatedEvent,
            UserRegisteredEvent,
            WelcomeEmailSentEvent,
        )

        bus.subscribe(UserRegisteredEvent, event_handler)
        bus.subscribe(ProfileCreatedEvent, event_handler)
        bus.subscribe(WelcomeEmailSentEvent, event_handler)

        # Run simulation
        await simulate_user_registration_flow(bus)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Verify events were received in order
        assert len(events_received) == 3
        assert events_received[0] == "UserRegisteredEvent"
        assert events_received[1] == "ProfileCreatedEvent"
        assert events_received[2] == "WelcomeEmailSentEvent"

        # Check monitoring data
        monitoring_data = get_monitoring_data(bus)
        assert monitoring_data["health"] is not None
        assert monitoring_data["metrics"] is not None
        assert len(monitoring_data["history"]) >= 3

    @pytest.mark.asyncio
    async def test_learning_session_flow_simulation(self, temp_flow_file):
        """Test simulating learning session flow."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        events_received = []

        def event_handler(event):
            events_received.append(event.event_name)

        # Subscribe to learning events
        from tests.fixtures.event_flow_demo import (
            QuestionAnsweredEvent,
            SessionStartedEvent,
        )

        bus.subscribe(SessionStartedEvent, event_handler)
        bus.subscribe(QuestionAnsweredEvent, event_handler)

        # Run simulation
        await simulate_learning_session_flow(bus)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Verify events were received
        assert len(events_received) >= 6  # 1 SessionStarted + 5 QuestionAnswered
        assert events_received[0] == "SessionStartedEvent"

        # Count question answered events
        question_events = [e for e in events_received if e == "QuestionAnsweredEvent"]
        assert len(question_events) == 5

    @pytest.mark.asyncio
    async def test_comprehensive_flow_engine_functionality(self, temp_flow_file):
        """Test comprehensive Event Flow Engine functionality."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        # Run comprehensive test
        results = await run_comprehensive_test(bus)

        # Validate initial state
        initial_validation = results["initial_validation"]
        assert initial_validation["validation_enabled"]
        assert initial_validation["monitoring_enabled"]
        assert initial_validation["orchestrator_available"]

        # Validate events were received
        assert results["total_events_received"] >= 8  # 3 user + 6 learning events

        # Check monitoring data
        monitoring_data = results["monitoring_data"]
        assert monitoring_data["health"] is not None
        assert monitoring_data["health"]["orchestrator_status"] == "healthy"
        assert monitoring_data["metrics"] is not None
        assert monitoring_data["debug_info"]["event_bus_type"] == "enhanced"

        # Check debugging features
        debugging_features = results["debugging_features"]
        assert debugging_features["total_events_replay"] >= 8
        assert debugging_features["user_events_replay"] >= 2

        # Check flow statuses
        flow_statuses = debugging_features["flow_statuses"]
        if "user_registration" in flow_statuses:
            assert flow_statuses["user_registration"]["valid"]
        if "learning_session" in flow_statuses:
            assert flow_statuses["learning_session"]["valid"]

    def test_flow_validation_control(self, temp_flow_file):
        """Test flow validation enable/disable functionality."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        # Initially enabled
        assert bus.is_flow_validation_enabled()
        assert bus.is_flow_monitoring_enabled()

        # Test disable/enable validation
        assert bus.disable_flow_validation()
        assert not bus.is_flow_validation_enabled()

        assert bus.enable_flow_validation()
        assert bus.is_flow_validation_enabled()

        # Test disable/enable monitoring
        assert bus.disable_flow_monitoring()
        assert not bus.is_flow_monitoring_enabled()

        assert bus.enable_flow_monitoring()
        assert bus.is_flow_monitoring_enabled()

    @pytest.mark.asyncio
    async def test_event_metrics_accuracy(self, temp_flow_file):
        """Test accuracy of event metrics collection."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        from tests.fixtures.event_flow_demo import UserRegisteredEvent

        # Publish known number of events
        event_count = 10
        for i in range(event_count):
            await bus.publish(
                UserRegisteredEvent(user_id=i, email=f"user{i}@example.com")
            )

        # Wait for processing
        await asyncio.sleep(0.1)

        # Check metrics
        metrics = bus.get_flow_metrics()
        assert metrics is not None

        user_metrics = metrics.get("UserRegisteredEvent")
        assert user_metrics is not None
        assert user_metrics["count"] >= event_count
        assert user_metrics["avg_duration_ms"] >= 0
        assert user_metrics["min_duration_ms"] >= 0
        assert user_metrics["max_duration_ms"] >= user_metrics["min_duration_ms"]

    def test_flow_sequence_status_accuracy(self, temp_flow_file):
        """Test accuracy of flow sequence status reporting."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        # Check user registration flow status
        status = bus.get_flow_sequence_status("user_registration")
        assert status is not None
        assert "flow_name" in status
        assert status["flow_name"] == "user_registration"
        assert "sequence" in status
        assert "completion_rate" in status

        # Should have 3 events in sequence
        assert len(status["sequence"]) == 3

        # Initially, no events should have occurred
        for event_status in status["sequence"]:
            assert "event" in event_status
            assert "occurred" in event_status
            # Initially false since no events published yet

    def test_error_handling_with_invalid_flow_file(self):
        """Test error handling when flow file is invalid."""
        # Should gracefully fall back to basic functionality
        bus = EnhancedEventBus("/nonexistent/file.yaml")

        # Should work as basic event bus
        assert bus.flow_orchestrator is None
        assert not bus.is_flow_validation_enabled()
        assert not bus.is_flow_monitoring_enabled()

        # Methods should return None gracefully
        assert bus.get_flow_metrics() is None
        assert bus.get_flow_health() is None
        assert bus.get_event_history() is None
        assert bus.replay_events() is None
        assert bus.get_flow_sequence_status("any_flow") is None

    @pytest.mark.asyncio
    async def test_performance_under_load(self, temp_flow_file):
        """Test Event Flow Engine performance under load."""
        bus = EnhancedEventBus.create_with_flow_validation(temp_flow_file)

        import time

        from tests.fixtures.event_flow_demo import UserRegisteredEvent

        # Publish many events quickly
        start_time = time.perf_counter()
        event_count = 100

        for i in range(event_count):
            await bus.publish(
                UserRegisteredEvent(user_id=i, email=f"user{i}@example.com")
            )

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Wait for processing
        await asyncio.sleep(0.2)

        # Check performance metrics
        health = bus.get_flow_health()
        assert health is not None
        assert health["total_events_processed"] >= event_count

        # Average processing time should be reasonable (< 10ms per event)
        avg_time_ms = health["avg_processing_time_ms"]
        assert avg_time_ms < 10.0, f"Processing too slow: {avg_time_ms}ms per event"

        # Total time should be reasonable (< 1 second for 100 events)
        assert total_time < 1.0, f"Total publishing time too slow: {total_time}s"

        # System should still be healthy
        assert health["orchestrator_status"] in ["healthy", "degraded"]
