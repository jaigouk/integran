"""Query for getting enhanced question content following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.content.services.enhanced_question_display import (
    EnhancedQuestionData,
    EnhancedQuestionDisplay,
    EnhancedQuestionDisplayRequest,
)
from src.domain.shared.repositories import UserRepository
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import Language

logger = logging.getLogger(__name__)


@dataclass
class EnhancedQuestionContentQuery:
    """Query to get enhanced content for a question."""

    question_id: int
    preferred_language: Language = Language.ENGLISH
    user_id: int = 1


@dataclass
class EnhancedQuestionContentQueryResult:
    """Result of enhanced question content query."""

    success: bool
    enhanced_data: EnhancedQuestionData | None = None
    error_message: str | None = None


class EnhancedQuestionContentQueryHandler:
    """Query handler for getting enhanced question content using domain service."""

    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        """Initialize with user repository and event bus."""
        self.enhanced_question_service = EnhancedQuestionDisplay(event_bus)
        self.user_repository = user_repository

    async def handle(
        self, query: EnhancedQuestionContentQuery
    ) -> EnhancedQuestionContentQueryResult:
        """Handle enhanced question content query using domain service."""
        try:
            # Create domain service request
            request = EnhancedQuestionDisplayRequest(
                question_id=query.question_id,
                preferred_language=query.preferred_language,
            )

            # Call domain service
            result = await self.enhanced_question_service.call(request)

            # Convert domain result to query result
            return EnhancedQuestionContentQueryResult(
                success=result.success,
                enhanced_data=result.question_data,  # Domain service uses question_data not enhanced_data
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error in EnhancedQuestionContentQueryHandler: {e}")
            return EnhancedQuestionContentQueryResult(
                success=False,
                error_message=f"Failed to get enhanced question content: {e}",
            )
