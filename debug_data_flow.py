#!/usr/bin/env python3
"""Debug script to trace data flow from answer submission to progress tracking."""

import asyncio
import logging
from datetime import UTC, datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

from src.domain.learning.events.card_events import CardScheduledEvent
from src.infrastructure.containers.main_container import MainContainer


async def test_data_flow():
    """Test the complete data flow from answer submission to progress tracking."""

    # Initialize container
    container = MainContainer()
    event_bus = container.get_event_bus()
    db_manager = container.get_db_manager()

    logger.info("=== Testing Data Flow ===")

    # 1. Check what event handlers are registered
    logger.info(f"Active subscriptions: {event_bus.get_active_subscriptions()}")

    # 2. Check if FSRS cards exist for questions
    question_id = 1
    fsrs_card = db_manager.get_fsrs_card(question_id, user_id=1)
    logger.info(f"FSRS card for question {question_id}: {fsrs_card}")

    if not fsrs_card:
        logger.info("Creating FSRS card for testing...")
        fsrs_card = db_manager.create_fsrs_card(question_id, user_id=1)
        logger.info(f"Created FSRS card: {fsrs_card}")

    # 3. Test CardScheduledEvent publishing (like question_view.py does)
    logger.info("Publishing CardScheduledEvent...")
    event = CardScheduledEvent(
        card_id=question_id,
        question_id=question_id,
        new_difficulty=5.0,
        new_stability=1.0,
        new_retrievability=0.9,
        next_review_date=datetime.now(UTC),
        rating=3,  # Good
        response_time_ms=1000,
        session_id=None,
    )

    await event_bus.publish(event)
    logger.info("CardScheduledEvent published")

    # 4. Check if ScheduleCard domain service should be called instead
    logger.info("Testing ScheduleCard domain service...")
    schedule_card_service = container._schedule_card

    from src.domain.learning.services.schedule_card import ScheduleCardRequest
    from src.domain.shared.models import FSRSRating

    request = ScheduleCardRequest(
        card_id=fsrs_card.card_id,
        rating=FSRSRating.GOOD,
        response_time_ms=1000,
        session_id=None
    )

    result = await schedule_card_service.call(request)
    logger.info(f"ScheduleCard result: {result}")

    # 5. Check if progress analytics work
    logger.info("Testing analytics...")
    analytics_service = container.get_analytics_service()
    insights = analytics_service.get_learning_insights(user_id=1)
    logger.info(f"Learning insights: {insights}")

    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_data_flow())
