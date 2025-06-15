"""Domain Service base classes following DDD patterns.

This module provides the base classes and patterns for implementing domain services
in the Domain-Driven Design architecture. Each domain service encapsulates a single
business operation with a clean async interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from src.infrastructure.messaging.event_bus import EventBus

logger = logging.getLogger(__name__)

# Generic type variables for request and response
T = TypeVar("T")  # Request type
U = TypeVar("U")  # Response type


class DomainService(ABC, Generic[T, U]):
    """Base class for all domain services following DDD patterns.

    Each domain service should:
    - Use Verb + Noun naming (e.g., ScheduleCard, GenerateAnswer, ProcessImage)
    - Expose only a single `call` method as the primary operation
    - Support async/await for event-driven architecture
    - Emit domain events for cross-context communication
    - Handle errors gracefully with proper logging

    Example:
        ```python
        class ScheduleCard(DomainService[ScheduleCardRequest, ScheduleCardResult]):
            async def call(self, request: ScheduleCardRequest) -> ScheduleCardResult:
                # Business logic here
                result = await self._execute_fsrs_algorithm(request)
                await self.event_bus.publish(CardScheduledEvent(...))
                return result
        ```
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize domain service with event bus.

        Args:
            event_bus: Event bus for publishing domain events
        """
        self.event_bus = event_bus
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def call(self, request: T) -> U:
        """Single entry point for domain service execution.

        This method should contain the main business logic and emit
        appropriate domain events upon successful completion.

        Args:
            request: Typed request object containing all necessary data

        Returns:
            Typed response object with operation results

        Raises:
            DomainServiceError: When business rules are violated
            ValidationError: When request data is invalid
        """
        pass

    async def _publish_event(self, event: Any) -> None:
        """Helper method to publish domain events with error handling.

        Args:
            event: Domain event to publish
        """
        try:
            await self.event_bus.publish(event)
        except Exception as e:
            self.logger.error(f"Failed to publish event {type(event).__name__}: {e}")
            # Don't re-raise as event publishing failure shouldn't break business logic


class DomainServiceError(Exception):
    """Base exception for domain service errors.

    Used when business rules are violated or domain-specific
    errors occur during service execution.
    """

    def __init__(self, message: str, error_code: str | None = None) -> None:
        """Initialize domain service error.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
        """
        super().__init__(message)
        self.error_code = error_code


class ValidationError(DomainServiceError):
    """Exception for request validation errors.

    Used when the request data doesn't meet the required
    business constraints or format requirements.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            field: Optional field name that failed validation
        """
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class BusinessRuleViolationError(DomainServiceError):
    """Exception for business rule violations.

    Used when the requested operation violates domain-specific
    business rules or constraints.
    """

    def __init__(self, message: str, rule: str | None = None) -> None:
        """Initialize business rule violation error.

        Args:
            message: Human-readable error message
            rule: Optional name of the violated business rule
        """
        super().__init__(message, "BUSINESS_RULE_VIOLATION")
        self.rule = rule


# Utility decorators for domain services


def log_domain_operation(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to log domain service operations.

    Logs the start and completion of domain service calls
    with performance metrics.
    """
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(self: Any, request: Any) -> Any:
        operation_name = f"{self.__class__.__name__}.call"
        self.logger.info(f"Starting {operation_name}")

        start_time = time.time()
        try:
            result = await func(self, request)
            duration = time.time() - start_time
            self.logger.info(f"Completed {operation_name} in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed {operation_name} after {duration:.3f}s: {e}")
            raise

    return wrapper


def validate_request(
    validator_func: Callable[[Any], None],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to validate domain service requests.

    Args:
        validator_func: Function that validates the request and raises
                       ValidationError if invalid
    """
    import functools

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self: Any, request: Any) -> Any:
            try:
                validator_func(request)
            except Exception as e:
                raise ValidationError(f"Request validation failed: {e}") from e

            return await func(self, request)

        return wrapper

    return decorator
