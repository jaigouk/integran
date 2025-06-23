"""Command handlers for write operations in the application layer.

Commands follow CQRS pattern where each command handler is responsible
for a single write operation that changes system state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    """Base class for all commands."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate the command."""
        pass


class CommandResult(ABC):
    """Base class for all command results."""

    def __init__(self, success: bool, error_message: str | None = None):
        self.success = success
        self.error_message = error_message

    def is_success(self) -> bool:
        """Check if the command was successful."""
        return self.success

    @abstractmethod
    def get_result_data(self) -> dict[str, Any]:
        """Get result data for concrete implementations."""
        pass


class CommandHandler[T, U](ABC):
    """Base class for all command handlers."""

    @abstractmethod
    async def handle(self, command: T) -> U:
        """Handle the command and return result."""
        pass
