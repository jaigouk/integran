"""Query handlers for read operations in the application layer.

Queries follow CQRS pattern where each query handler is responsible
for a single read operation that returns data without changing state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# Query and Result type variables
T = TypeVar("T")  # Query type
U = TypeVar("U")  # Result type


class Query(ABC):
    """Base class for all queries."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate the query."""
        pass


class QueryResult(ABC):
    """Base class for all query results."""

    def __init__(self, success: bool, error_message: str | None = None):
        self.success = success
        self.error_message = error_message

    def is_success(self) -> bool:
        """Check if the query was successful."""
        return self.success

    @abstractmethod
    def get_result_data(self) -> dict[str, Any]:
        """Get result data for concrete implementations."""
        pass


class QueryHandler(ABC, Generic[T, U]):
    """Base class for all query handlers."""

    @abstractmethod
    async def handle(self, query: T) -> U:
        """Handle the query and return result."""
        pass
