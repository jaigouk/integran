"""Event handler for card scheduled events."""

from __future__ import annotations

import logging

from src.application.events import EventHandler
from src.domain.learning.events.card_events import CardScheduledEvent
from src.infrastructure.database.database import DatabaseManager

logger = logging.getLogger(__name__)


class CardScheduledHandler(EventHandler[CardScheduledEvent]):
    """Handles CardScheduledEvent for analytics and cross-context updates."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def handle(self, event: CardScheduledEvent) -> None:
        """Handle card scheduled event for analytics tracking."""
        logger.info(f"Processing CardScheduledEvent for card {event.card_id}")

        try:
            # Update analytics data
            await self._update_performance_metrics(event)

            # Check for leech detection if rating was "Again"
            if event.rating == 1:  # Again rating
                await self._check_leech_status(event.card_id)

            # Update daily statistics
            await self._update_daily_stats(event)

        except Exception as e:
            logger.error(f"Failed to handle CardScheduledEvent: {e}")
            # Don't re-raise - event handlers should be resilient

    async def _update_performance_metrics(self, event: CardScheduledEvent) -> None:
        """Update performance analytics."""
        # This would update user analytics table with:
        # - Review completion
        # - Performance tracking
        # - Retention rate calculations
        logger.debug(f"Updating performance metrics for card {event.card_id}")

        # Example implementation:
        # self.db_manager.update_user_analytics(
        #     date=event.occurred_at.date(),
        #     reviews_completed=1,
        #     rating=event.rating
        # )

    async def _check_leech_status(self, card_id: int) -> None:
        """Check if card should be marked as leech."""
        logger.debug(f"Checking leech status for card {card_id}")

        # This would:
        # - Get card lapse count
        # - Check if it exceeds leech threshold
        # - Create leech record if needed
        # - Trigger leech management actions

    async def _update_daily_stats(self, event: CardScheduledEvent) -> None:
        """Update daily learning statistics."""
        logger.debug(f"Updating daily stats for card {event.card_id}")

        # This would update:
        # - Daily review counts
        # - Category-specific performance
        # - Study streak tracking
