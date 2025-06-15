"""Tests for domain service base classes and utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.shared.services import (
    BusinessRuleViolationError,
    DomainService,
    DomainServiceError,
    ValidationError,
)
from src.infrastructure.messaging.event_bus import DomainEvent, EventBus


# Test fixtures
@dataclass
class TestRequest:
    """Test request DTO."""

    value: int
    name: str = "test"


@dataclass
class TestResponse:
    """Test response DTO."""

    result: str
    success: bool = True


class TestServiceEvent(DomainEvent):
    """Test event for domain service."""

    def __init__(self, data: str, **kwargs):
        super().__init__(**kwargs)
        self.data = data


class TestDomainService(DomainService[TestRequest, TestResponse]):
    """Test implementation of domain service."""

    async def call(self, request: TestRequest) -> TestResponse:
        """Process test request."""
        if request.value < 0:
            raise ValidationError("Value must be non-negative", "value")

        if request.value > 100:
            raise BusinessRuleViolationError(
                "Value exceeds maximum allowed", "MAX_VALUE_RULE"
            )

        # Simulate some processing
        result = f"Processed {request.name} with value {request.value}"

        # Publish event
        await self._publish_event(TestServiceEvent(data=result))

        return TestResponse(result=result)


class TestDomainServiceBase:
    """Test the DomainService base class."""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def service(self, event_bus):
        """Create test domain service."""
        return TestDomainService(event_bus)

    @pytest.mark.asyncio
    async def test_successful_call(self, service, event_bus):
        """Test successful domain service call."""
        request = TestRequest(value=42, name="test-item")
        response = await service.call(request)

        assert response.success
        assert response.result == "Processed test-item with value 42"

        # Check event was published
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, TestServiceEvent)
        assert published_event.data == response.result

    @pytest.mark.asyncio
    async def test_validation_error(self, service):
        """Test validation error handling."""
        request = TestRequest(value=-1)

        with pytest.raises(ValidationError) as exc_info:
            await service.call(request)

        assert exc_info.value.field == "value"
        assert exc_info.value.error_code == "VALIDATION_ERROR"
        assert "non-negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_business_rule_violation(self, service):
        """Test business rule violation handling."""
        request = TestRequest(value=150)

        with pytest.raises(BusinessRuleViolationError) as exc_info:
            await service.call(request)

        assert exc_info.value.rule == "MAX_VALUE_RULE"
        assert exc_info.value.error_code == "BUSINESS_RULE_VIOLATION"
        assert "exceeds maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_event_publish_failure(self, service, event_bus, caplog):
        """Test graceful handling of event publish failure."""
        event_bus.publish.side_effect = Exception("Event bus error")

        request = TestRequest(value=42)

        with caplog.at_level(logging.ERROR):
            response = await service.call(request)

        # Service should still succeed despite event failure
        assert response.success
        assert "Failed to publish event TestServiceEvent" in caplog.text

    def test_logger_initialization(self, event_bus):
        """Test that service gets its own logger."""
        service = TestDomainService(event_bus)
        assert service.logger.name == "TestDomainService"


class TestDomainServiceError:
    """Test DomainServiceError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = DomainServiceError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.error_code is None

    def test_error_with_code(self):
        """Test error with error code."""
        error = DomainServiceError("Operation failed", "OPERATION_FAILED")
        assert str(error) == "Operation failed"
        assert error.error_code == "OPERATION_FAILED"


class TestValidationError:
    """Test ValidationError exception."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field is None

    def test_validation_error_with_field(self):
        """Test validation error with field."""
        error = ValidationError("Value out of range", "age")
        assert str(error) == "Value out of range"
        assert error.field == "age"


class TestBusinessRuleViolationError:
    """Test BusinessRuleViolationError exception."""

    def test_basic_business_rule_error(self):
        """Test basic business rule error."""
        error = BusinessRuleViolationError("Rule violated")
        assert str(error) == "Rule violated"
        assert error.error_code == "BUSINESS_RULE_VIOLATION"
        assert error.rule is None

    def test_business_rule_error_with_rule(self):
        """Test business rule error with rule name."""
        error = BusinessRuleViolationError("Insufficient balance", "MIN_BALANCE_RULE")
        assert str(error) == "Insufficient balance"
        assert error.rule == "MIN_BALANCE_RULE"
