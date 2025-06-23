"""Read model projections for CQRS query optimization.

Projections are materialized views of domain data that are optimized
for specific query patterns. They are updated by event handlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from src.infrastructure.messaging.enhanced_event_bus import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class ReadModelProjection(ABC):
    """Base class for all read model projections."""

    @abstractmethod
    async def update(self, event: DomainEvent) -> None:
        """Update the projection based on a domain event."""
        pass

    @abstractmethod
    async def get_data(self, **filters: Any) -> Any:
        """Get projected data with optional filters."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset/rebuild the projection from scratch."""
        pass
