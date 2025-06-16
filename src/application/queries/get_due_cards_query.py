"""Query for getting cards due for review - thin query handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.queries import Query, QueryHandler, QueryResult
from src.domain.learning.models.learning_models import FSRSCard
from src.infrastructure.database.database import DatabaseManager


@dataclass
class GetDueCardsQuery(Query):
    """Query to get cards due for review."""

    user_id: int = 1
    limit: int = 50

    def validate(self) -> bool:
        return self.user_id > 0 and self.limit > 0


@dataclass
class GetDueCardsResult(QueryResult):
    """Result of getting due cards."""

    success: bool = False
    error_message: str | None = None
    cards: list[FSRSCard] | None = None
    total_due: int = 0

    def __post_init__(self) -> None:
        if self.cards is None:
            self.cards = []

    def get_result_data(self) -> dict[str, Any]:
        return {
            "card_count": len(self.cards) if self.cards else 0,
            "total_due": self.total_due,
        }


class GetDueCardsQueryHandler(QueryHandler[GetDueCardsQuery, GetDueCardsResult]):
    """Handler for getting due cards - direct DB access for performance."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def handle(self, query: GetDueCardsQuery) -> GetDueCardsResult:
        """Handle get due cards query."""
        try:
            # Get due cards from database
            due_cards = self.db_manager.get_due_fsrs_cards(
                user_id=query.user_id, limit=query.limit
            )
            # Get total count (for pagination)
            total_due = self.db_manager.count_due_fsrs_cards(user_id=query.user_id)
            return GetDueCardsResult(success=True, cards=due_cards, total_due=total_due)
        except Exception as e:
            return GetDueCardsResult(
                success=False, error_message=f"Failed to get due cards: {str(e)}"
            )
