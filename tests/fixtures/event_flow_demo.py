#!/usr/bin/env python3
"""Test fixture for demonstrating Event Flow Engine capabilities.

This module provides test fixtures and utilities for validating
the EventFlowOrchestrator and EnhancedEventBus functionality.
"""

import asyncio
import logging

from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.messaging.event_bus import DomainEvent

# Setup logging
logger = logging.getLogger(__name__)


class UserRegisteredEvent(DomainEvent):
    """Test event: User registered."""

    def __init__(self, user_id: int, email: str):
        super().__init__()
        self.user_id = user_id
        self.email = email


class ProfileCreatedEvent(DomainEvent):
    """Test event: User profile created."""

    def __init__(self, user_id: int, profile_data: dict):
        super().__init__()
        self.user_id = user_id
        self.profile_data = profile_data


class WelcomeEmailSentEvent(DomainEvent):
    """Test event: Welcome email sent."""

    def __init__(self, user_id: int, email: str):
        super().__init__()
        self.user_id = user_id
        self.email = email


class SessionStartedEvent(DomainEvent):
    """Test event: Learning session started."""

    def __init__(self, session_id: int, user_id: int):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id


class QuestionAnsweredEvent(DomainEvent):
    """Test event: Question answered."""

    def __init__(self, session_id: int, question_id: int, correct: bool):
        super().__init__()
        self.session_id = session_id
        self.question_id = question_id
        self.correct = correct


async def simulate_user_registration_flow(event_bus: EnhancedEventBus):
    """Test fixture: Simulate a user registration flow."""
    await event_bus.publish(UserRegisteredEvent(user_id=123, email="user@example.com"))
    await asyncio.sleep(0.01)

    await event_bus.publish(
        ProfileCreatedEvent(
            user_id=123, profile_data={"name": "John Doe", "language": "en"}
        )
    )
    await asyncio.sleep(0.01)

    await event_bus.publish(
        WelcomeEmailSentEvent(user_id=123, email="user@example.com")
    )
    await asyncio.sleep(0.01)


async def simulate_learning_session_flow(event_bus: EnhancedEventBus):
    """Test fixture: Simulate a learning session flow."""
    await event_bus.publish(SessionStartedEvent(session_id=456, user_id=123))
    await asyncio.sleep(0.01)

    for question_id in range(1, 6):
        correct = question_id % 2 == 0
        await event_bus.publish(
            QuestionAnsweredEvent(
                session_id=456, question_id=question_id, correct=correct
            )
        )
        await asyncio.sleep(0.005)


def validate_flow_capabilities(event_bus: EnhancedEventBus) -> dict:
    """Test fixture: Validate flow validation capabilities."""
    results = {
        "validation_enabled": event_bus.is_flow_validation_enabled(),
        "monitoring_enabled": event_bus.is_flow_monitoring_enabled(),
        "orchestrator_available": event_bus.flow_orchestrator is not None,
    }

    if event_bus.flow_orchestrator and event_bus.flow_orchestrator.flow_definition:
        results["flows_available"] = list(
            event_bus.flow_orchestrator.flow_definition.flows.keys()
        )

    return results


def get_monitoring_data(event_bus: EnhancedEventBus) -> dict:
    """Test fixture: Get monitoring and metrics data."""
    return {
        "health": event_bus.get_flow_health(),
        "metrics": event_bus.get_flow_metrics(),
        "history": event_bus.get_event_history(limit=10),
        "debug_info": event_bus.get_debug_info(),
    }


def debugging_features_test(event_bus: EnhancedEventBus) -> dict:
    """Test fixture: Test debugging and replay capabilities."""
    results = {}

    # Event replay tests
    all_events = event_bus.replay_events()
    results["total_events_replay"] = len(all_events) if all_events else 0

    user_events = event_bus.replay_events(
        event_names=["UserRegisteredEvent", "ProfileCreatedEvent"]
    )
    results["user_events_replay"] = len(user_events) if user_events else 0

    # Flow sequence status tests
    test_flows = ["first_time_setup", "learning_session", "user_registration"]
    results["flow_statuses"] = {}

    for flow_name in test_flows:
        status = event_bus.get_flow_sequence_status(flow_name)
        if status:
            if "error" not in status:
                results["flow_statuses"][flow_name] = {
                    "completion_rate": status.get("completion_rate", 0),
                    "valid": True,
                }
            else:
                results["flow_statuses"][flow_name] = {
                    "error": status["error"],
                    "valid": False,
                }

    return results


async def run_comprehensive_test(event_bus: EnhancedEventBus) -> dict:
    """Test fixture: Run comprehensive test of Event Flow Engine."""
    test_results = {}

    # Setup handlers
    events_received = []

    def universal_handler(event):
        events_received.append(event.event_name)

    # Subscribe to all test events
    event_bus.subscribe(UserRegisteredEvent, universal_handler)
    event_bus.subscribe(ProfileCreatedEvent, universal_handler)
    event_bus.subscribe(WelcomeEmailSentEvent, universal_handler)
    event_bus.subscribe(SessionStartedEvent, universal_handler)
    event_bus.subscribe(QuestionAnsweredEvent, universal_handler)

    # Validate initial state
    test_results["initial_validation"] = validate_flow_capabilities(event_bus)

    # Run event flows
    await simulate_user_registration_flow(event_bus)
    await simulate_learning_session_flow(event_bus)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Collect monitoring data
    test_results["monitoring_data"] = get_monitoring_data(event_bus)

    # Test debugging features
    test_results["debugging_features"] = debugging_features_test(event_bus)

    # Record events received
    test_results["events_received"] = events_received
    test_results["total_events_received"] = len(events_received)

    return test_results
