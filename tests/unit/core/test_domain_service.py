"""Tests for Domain Service base classes."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.shared.services import (
    BusinessRuleViolationError,
    DomainService,
    DomainServiceError,
    ValidationError,
    log_domain_operation,
    validate_request,
)
from src.infrastructure.messaging.event_bus import DomainEvent, EventBus


@dataclass
class TestRequest:
    """Test request for domain service testing."""

    user_id: int
    data: str
    valid: bool = True


@dataclass
class TestResponse:
    """Test response for domain service testing."""

    success: bool
    message: str
    processed_data: str | None = None


@dataclass
class TestEvent(DomainEvent):
    """Test event for domain service testing."""

    user_id: int
    message: str

    def __post_init__(self) -> None:
        # Initialize parent DomainEvent with auto-generated values
        DomainEvent.__init__(self)


class ConcreteDomainService(DomainService[TestRequest, TestResponse]):
    """Concrete implementation for testing."""

    async def call(self, request: TestRequest) -> TestResponse:
        """Test implementation of call method."""
        if not request.valid:
            raise ValidationError("Invalid request", field="valid")

        # Simulate some processing
        processed_data = f"processed_{request.data}"

        # Publish event
        event = TestEvent(user_id=request.user_id, message="Test operation completed")
        await self._publish_event(event)

        return TestResponse(
            success=True,
            message="Operation completed successfully",
            processed_data=processed_data,
        )


class FailingDomainService(DomainService[TestRequest, TestResponse]):
    """Domain service that fails for testing error scenarios."""

    async def call(self, request: TestRequest) -> TestResponse:
        """Test implementation that raises exceptions."""
        if request.data == "business_error":
            raise BusinessRuleViolationError("Business rule violated", rule="test_rule")
        elif request.data == "domain_error":
            raise DomainServiceError("Domain error occurred", error_code="TEST_ERROR")
        elif request.data == "generic_error":
            raise Exception("Generic error")

        return TestResponse(success=True, message="Success")


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def domain_service(mock_event_bus):
    """Create concrete domain service for testing."""
    return ConcreteDomainService(mock_event_bus)


@pytest.fixture
def failing_service(mock_event_bus):
    """Create failing domain service for testing."""
    return FailingDomainService(mock_event_bus)


class TestDomainService:
    """Test DomainService base class."""

    def test_init(self, mock_event_bus):
        """Test domain service initialization."""
        service = ConcreteDomainService(mock_event_bus)

        assert service.event_bus is mock_event_bus
        assert service.logger is not None
        assert service.logger.name == "ConcreteDomainService"

    @pytest.mark.asyncio
    async def test_call_success(self, domain_service, mock_event_bus):
        """Test successful domain service call."""
        request = TestRequest(user_id=1, data="test_data")

        result = await domain_service.call(request)

        assert result.success is True
        assert result.message == "Operation completed successfully"
        assert result.processed_data == "processed_test_data"

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, TestEvent)
        assert published_event.user_id == 1
        assert published_event.message == "Test operation completed"

    @pytest.mark.asyncio
    async def test_call_validation_error(self, domain_service):
        """Test domain service call with validation error."""
        request = TestRequest(user_id=1, data="test_data", valid=False)

        with pytest.raises(ValidationError) as exc_info:
            await domain_service.call(request)

        assert exc_info.value.field == "valid"
        assert "Invalid request" in str(exc_info.value)
        assert exc_info.value.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_publish_event_success(self, domain_service, mock_event_bus):
        """Test successful event publishing."""
        event = TestEvent(user_id=1, message="Test event")

        await domain_service._publish_event(event)

        mock_event_bus.publish.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_event_failure(self, domain_service, mock_event_bus):
        """Test event publishing failure handling."""
        mock_event_bus.publish.side_effect = Exception("Event bus error")
        event = TestEvent(user_id=1, message="Test event")

        # Should not raise exception
        await domain_service._publish_event(event)

        mock_event_bus.publish.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_event_failure_logging(self, domain_service, mock_event_bus):
        """Test that event publishing failures are logged."""
        mock_event_bus.publish.side_effect = Exception("Event bus error")
        event = TestEvent(user_id=1, message="Test event")

        with patch.object(domain_service.logger, "error") as mock_logger:
            await domain_service._publish_event(event)

            mock_logger.assert_called_once()
            call_args = mock_logger.call_args[0][0]
            assert "Failed to publish event TestEvent" in call_args
            assert "Event bus error" in call_args


class TestDomainServiceError:
    """Test DomainServiceError exception."""

    def test_init_with_message_only(self):
        """Test DomainServiceError with message only."""
        error = DomainServiceError("Test error")

        assert str(error) == "Test error"
        assert error.error_code is None

    def test_init_with_error_code(self):
        """Test DomainServiceError with error code."""
        error = DomainServiceError("Test error", error_code="TEST_CODE")

        assert str(error) == "Test error"
        assert error.error_code == "TEST_CODE"


class TestValidationError:
    """Test ValidationError exception."""

    def test_init_with_message_only(self):
        """Test ValidationError with message only."""
        error = ValidationError("Validation failed")

        assert str(error) == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field is None

    def test_init_with_field(self):
        """Test ValidationError with field."""
        error = ValidationError("Field is invalid", field="username")

        assert str(error) == "Field is invalid"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field == "username"

    def test_inheritance(self):
        """Test ValidationError inherits from DomainServiceError."""
        error = ValidationError("Test error")
        assert isinstance(error, DomainServiceError)


class TestBusinessRuleViolationError:
    """Test BusinessRuleViolationError exception."""

    def test_init_with_message_only(self):
        """Test BusinessRuleViolationError with message only."""
        error = BusinessRuleViolationError("Rule violated")

        assert str(error) == "Rule violated"
        assert error.error_code == "BUSINESS_RULE_VIOLATION"
        assert error.rule is None

    def test_init_with_rule(self):
        """Test BusinessRuleViolationError with rule."""
        error = BusinessRuleViolationError("Rule violated", rule="max_attempts")

        assert str(error) == "Rule violated"
        assert error.error_code == "BUSINESS_RULE_VIOLATION"
        assert error.rule == "max_attempts"

    def test_inheritance(self):
        """Test BusinessRuleViolationError inherits from DomainServiceError."""
        error = BusinessRuleViolationError("Test error")
        assert isinstance(error, DomainServiceError)


class TestFailingDomainService:
    """Test domain service error scenarios."""

    @pytest.mark.asyncio
    async def test_business_rule_violation(self, failing_service):
        """Test business rule violation error."""
        request = TestRequest(user_id=1, data="business_error")

        with pytest.raises(BusinessRuleViolationError) as exc_info:
            await failing_service.call(request)

        assert exc_info.value.rule == "test_rule"
        assert "Business rule violated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_domain_service_error(self, failing_service):
        """Test domain service error."""
        request = TestRequest(user_id=1, data="domain_error")

        with pytest.raises(DomainServiceError) as exc_info:
            await failing_service.call(request)

        assert exc_info.value.error_code == "TEST_ERROR"
        assert "Domain error occurred" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generic_error(self, failing_service):
        """Test generic exception handling."""
        request = TestRequest(user_id=1, data="generic_error")

        with pytest.raises(Exception) as exc_info:
            await failing_service.call(request)

        assert "Generic error" in str(exc_info.value)


class TestLogDomainOperation:
    """Test log_domain_operation decorator."""

    @pytest.mark.asyncio
    async def test_successful_operation_logging(self, mock_event_bus):
        """Test successful operation logging."""

        class LoggedService(DomainService[TestRequest, TestResponse]):
            @log_domain_operation
            async def call(self, _request: TestRequest) -> TestResponse:
                return TestResponse(success=True, message="Success")

        service = LoggedService(mock_event_bus)
        request = TestRequest(user_id=1, data="test")

        with patch.object(service.logger, "info") as mock_info:
            result = await service.call(request)

            assert result.success is True
            assert mock_info.call_count == 2

            # Check start log
            start_call = mock_info.call_args_list[0][0][0]
            assert "Starting LoggedService.call" in start_call

            # Check completion log
            completion_call = mock_info.call_args_list[1][0][0]
            assert "Completed LoggedService.call" in completion_call
            assert "in" in completion_call  # Duration should be logged

    @pytest.mark.asyncio
    async def test_failed_operation_logging(self, mock_event_bus):
        """Test failed operation logging."""

        class LoggedFailingService(DomainService[TestRequest, TestResponse]):
            @log_domain_operation
            async def call(self, _request: TestRequest) -> TestResponse:
                raise Exception("Test error")

        service = LoggedFailingService(mock_event_bus)
        request = TestRequest(user_id=1, data="test")

        with (
            patch.object(service.logger, "info") as mock_info,
            patch.object(service.logger, "error") as mock_error,
        ):
            with pytest.raises(Exception):  # noqa: B017
                await service.call(request)

            # Check start log
            mock_info.assert_called_once()
            start_call = mock_info.call_args[0][0]
            assert "Starting LoggedFailingService.call" in start_call

            # Check error log
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0][0]
            assert "Failed LoggedFailingService.call" in error_call
            assert "Test error" in error_call


class TestValidateRequest:
    """Test validate_request decorator."""

    def test_successful_validation(self, mock_event_bus):
        """Test successful request validation."""

        def test_validator(request: TestRequest) -> None:
            if not request.valid:
                raise ValueError("Request is invalid")

        class ValidatedService(DomainService[TestRequest, TestResponse]):
            @validate_request(test_validator)
            async def call(self, _request: TestRequest) -> TestResponse:
                return TestResponse(success=True, message="Success")

        service = ValidatedService(mock_event_bus)
        request = TestRequest(user_id=1, data="test", valid=True)

        # Should not raise exception
        import asyncio

        result = asyncio.run(service.call(request))
        assert result.success is True

    def test_failed_validation(self, mock_event_bus):
        """Test failed request validation."""

        def test_validator(request: TestRequest) -> None:
            if not request.valid:
                raise ValueError("Request is invalid")

        class ValidatedService(DomainService[TestRequest, TestResponse]):
            @validate_request(test_validator)
            async def call(self, _request: TestRequest) -> TestResponse:
                return TestResponse(success=True, message="Success")

        service = ValidatedService(mock_event_bus)
        request = TestRequest(user_id=1, data="test", valid=False)

        import asyncio

        with pytest.raises(ValidationError) as exc_info:
            asyncio.run(service.call(request))

        assert "Request validation failed" in str(exc_info.value)
        assert exc_info.value.error_code == "VALIDATION_ERROR"


class TestDomainServiceIntegration:
    """Test domain service integration scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, mock_event_bus):
        """Test complete end-to-end domain service flow."""

        def request_validator(request: TestRequest) -> None:
            if request.user_id <= 0:
                raise ValueError("User ID must be positive")

        class IntegratedService(DomainService[TestRequest, TestResponse]):
            @log_domain_operation
            @validate_request(request_validator)
            async def call(self, request: TestRequest) -> TestResponse:
                # Simulate business logic
                if request.data == "special":
                    raise BusinessRuleViolationError("Special data not allowed")

                # Publish event
                event = TestEvent(user_id=request.user_id, message="Integration test")
                await self._publish_event(event)

                return TestResponse(
                    success=True,
                    message="Integration successful",
                    processed_data=f"integrated_{request.data}",
                )

        service = IntegratedService(mock_event_bus)
        request = TestRequest(user_id=1, data="test_data")

        with patch.object(service.logger, "info") as mock_info:
            result = await service.call(request)

            assert result.success is True
            assert result.message == "Integration successful"
            assert result.processed_data == "integrated_test_data"

            # Verify logging occurred
            assert mock_info.call_count == 2

            # Verify event was published
            mock_event_bus.publish.assert_called_once()
