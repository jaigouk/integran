"""ScheduleCard domain service for FSRS-based card scheduling.

This domain service encapsulates the FSRS algorithm and card scheduling logic,
following the Domain-Driven Design pattern with async operations and event publishing.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.domain.learning.events.card_events import CardScheduledEvent
from src.domain.learning.models.learning_models import (
    FSRSCard,
    FSRSCardState,
    FSRSParameters,
    ScheduleResult,
)
from src.domain.shared.models import FSRSRating, FSRSState
from src.domain.shared.repositories import LearningRepository
from src.domain.shared.services import (
    BusinessRuleViolationError,
    DomainService,
    EventBusInterface,
    ValidationError,
    log_domain_operation,
)

logger = logging.getLogger(__name__)


@dataclass
class ScheduleCardRequest:
    """Request DTO for card scheduling using FSRS algorithm."""

    card_id: int
    rating: FSRSRating
    response_time_ms: int
    session_id: int | None = None

    def __post_init__(self) -> None:
        """Validate request data."""
        if self.card_id <= 0:
            raise ValueError("card_id must be positive")
        if not isinstance(self.rating, FSRSRating):
            raise ValueError("rating must be a valid FSRSRating")
        if self.response_time_ms < 0:
            raise ValueError("response_time_ms cannot be negative")


@dataclass
class ScheduleCardResult:
    """Result DTO for card scheduling operation."""

    success: bool
    card_id: int
    question_id: int

    # State before review
    difficulty_before: float
    stability_before: float
    retrievability_before: float
    state_before: FSRSState

    # State after review
    difficulty_after: float
    stability_after: float
    retrievability_after: float
    state_after: FSRSState
    next_review_date: datetime
    next_interval_days: float

    # Additional metadata
    lapse_count_updated: bool = False
    error_message: str | None = None


class ScheduleCard(DomainService[ScheduleCardRequest, ScheduleCardResult]):
    """Domain service for FSRS card scheduling.

    This service encapsulates the complete FSRS algorithm including:
    - Card state retrieval and validation
    - FSRS difficulty/stability calculations
    - Database updates for new scheduling
    - Review history recording
    - Domain event publishing
    """

    def __init__(
        self, learning_repository: LearningRepository, event_bus: EventBusInterface
    ) -> None:
        """Initialize ScheduleCard service.

        Args:
            learning_repository: Repository for FSRS card operations
            event_bus: Event bus for publishing domain events
        """
        super().__init__(event_bus)
        self.learning_repository = learning_repository
        self._parameters: FSRSParameters | None = None

    @property
    def parameters(self) -> FSRSParameters:
        """Get FSRS parameters, loading from database if needed."""
        if self._parameters is None:
            # For now, use default parameters - algorithm config will be moved to repository
            config = None
            if config:
                import json

                self._parameters = FSRSParameters()
                self._parameters.w = json.loads(config.parameters)
            else:
                self._parameters = FSRSParameters()
        return self._parameters

    @log_domain_operation
    async def call(self, request: ScheduleCardRequest) -> ScheduleCardResult:
        """Execute FSRS card scheduling with event publishing.

        Args:
            request: Schedule card request with rating and timing data

        Returns:
            Result containing before/after states and scheduling info

        Raises:
            ValidationError: When request data is invalid
            BusinessRuleViolationError: When card cannot be scheduled
        """
        try:
            # Validate request
            await self._validate_request(request)

            # Get current card state or create new one
            card = await self.learning_repository.get_fsrs_card_by_id(request.card_id)
            if not card:
                # Card not found - this shouldn't happen if the command layer is working correctly
                self.logger.error(f"FSRS card with card_id {request.card_id} not found")
                return ScheduleCardResult(
                    success=False,
                    card_id=request.card_id,
                    question_id=None,  # We don't know the question_id from just the card_id
                    difficulty_before=0.0,
                    stability_before=0.0,
                    retrievability_before=0.0,
                    state_before=FSRSState.NEW,
                    difficulty_after=0.0,
                    stability_after=0.0,
                    retrievability_after=0.0,
                    state_after=FSRSState.NEW,
                    next_review_date=datetime.now(UTC),
                    next_interval_days=0.0,
                    error_message=f"FSRS card with card_id {request.card_id} not found",
                )

            # Calculate current retrievability
            now = datetime.now(UTC)
            retrievability = self._calculate_retrievability(card, now)

            # Store state before review
            state_before = FSRSCardState(
                difficulty=card.difficulty,
                stability=card.stability,
                retrievability=retrievability,
                state=FSRSState(card.state),
                last_review=datetime.fromtimestamp(card.last_review_date, UTC)
                if card.last_review_date
                else None,
            )

            # Calculate new state using FSRS algorithm
            schedule_result = await self._schedule_card_fsrs(
                state_before, request.rating
            )

            # Update card in database
            new_state = await self._update_card_state(
                request.card_id, schedule_result, card, request.rating
            )

            # Update lapse count if needed
            lapse_count_updated = False
            if request.rating == FSRSRating.AGAIN:
                await self._increment_lapse_count(request.card_id)
                lapse_count_updated = True

            # Record review in history
            await self._record_review_history(
                card, request, state_before, schedule_result
            )

            # Create result
            result = ScheduleCardResult(
                success=True,
                card_id=request.card_id,
                question_id=card.question_id,
                difficulty_before=state_before.difficulty,
                stability_before=state_before.stability,
                retrievability_before=state_before.retrievability,
                state_before=state_before.state,
                difficulty_after=schedule_result.difficulty,
                stability_after=schedule_result.stability,
                retrievability_after=schedule_result.retrievability,
                state_after=FSRSState(new_state),
                next_review_date=schedule_result.next_review_date,
                next_interval_days=schedule_result.next_interval,
                lapse_count_updated=lapse_count_updated,
            )

            # Publish domain event
            event = CardScheduledEvent(
                card_id=request.card_id,
                question_id=card.question_id,
                new_difficulty=schedule_result.difficulty,
                new_stability=schedule_result.stability,
                new_retrievability=schedule_result.retrievability,
                next_review_date=schedule_result.next_review_date,
                rating=int(request.rating),
                response_time_ms=request.response_time_ms,
                session_id=request.session_id,
            )
            await self._publish_event(event)

            self.logger.info(f"Successfully scheduled card {request.card_id}")
            return result

        except (ValidationError, BusinessRuleViolationError) as e:
            self.logger.error(
                f"Validation/Business rule error for card {request.card_id}: {e}"
            )
            return ScheduleCardResult(
                success=False,
                card_id=request.card_id,
                question_id=0,
                difficulty_before=0.0,
                stability_before=0.0,
                retrievability_before=0.0,
                state_before=FSRSState.NEW,
                difficulty_after=0.0,
                stability_after=0.0,
                retrievability_after=0.0,
                state_after=FSRSState.NEW,
                next_review_date=datetime.now(UTC),
                next_interval_days=0.0,
                error_message=str(e),
            )
        except Exception as e:
            self.logger.error(f"Failed to schedule card {request.card_id}: {e}")
            return ScheduleCardResult(
                success=False,
                card_id=request.card_id,
                question_id=0,
                difficulty_before=0.0,
                stability_before=0.0,
                retrievability_before=0.0,
                state_before=FSRSState.NEW,
                difficulty_after=0.0,
                stability_after=0.0,
                retrievability_after=0.0,
                state_after=FSRSState.NEW,
                next_review_date=datetime.now(UTC),
                next_interval_days=0.0,
                error_message=str(e),
            )

    async def _validate_request(self, request: ScheduleCardRequest) -> None:
        """Validate schedule card request."""
        if request.card_id <= 0:
            raise ValidationError("Card ID must be positive", "card_id")

        if not isinstance(request.rating, FSRSRating):
            raise ValidationError("Rating must be a valid FSRSRating", "rating")

        if request.response_time_ms < 0:
            raise ValidationError(
                "Response time cannot be negative", "response_time_ms"
            )

    async def _get_card_by_id(self, card_id: int) -> FSRSCard | None:
        """Get FSRS card by ID."""
        return await self.learning_repository.get_fsrs_card_by_id(card_id)

    async def _schedule_card_fsrs(
        self, state: FSRSCardState, rating: FSRSRating
    ) -> ScheduleResult:
        """Calculate new card state using FSRS algorithm."""
        from src.domain.learning.models.learning_models import ScheduleResult

        w = self.parameters.w

        # Calculate new difficulty
        new_difficulty = self._calculate_difficulty(state.difficulty, rating, w)

        # Calculate new stability based on rating and current state
        if state.state == FSRSState.NEW:
            new_stability = self._init_stability(rating, w)
        else:
            new_stability = self._next_stability(
                state.difficulty, state.stability, state.retrievability, rating, w
            )

        # Calculate retrievability after specified interval
        interval_days = max(
            1, int(new_stability * math.log(self.parameters.request_retention))
        )
        next_review = datetime.now(UTC) + timedelta(days=interval_days)
        retrievability = math.exp(-interval_days / new_stability)

        return ScheduleResult(
            difficulty=new_difficulty,
            stability=new_stability,
            retrievability=retrievability,
            next_interval=interval_days,
            next_review_date=next_review,
        )

    async def _update_card_state(
        self,
        card_id: int,
        schedule_result: ScheduleResult,
        card: FSRSCard,
        rating: FSRSRating,
    ) -> int:
        """Update card state in database with proper FSRS state transitions."""
        # Calculate new state based on FSRS algorithm
        new_state = self._calculate_new_state(card.state, rating, card.review_count)

        next_review_timestamp = schedule_result.next_review_date.timestamp()
        await self.learning_repository.update_fsrs_card_state(
            card_id=card_id,
            difficulty=schedule_result.difficulty,
            stability=schedule_result.stability,
            retrievability=schedule_result.retrievability,
            state=new_state,
            next_review_date=next_review_timestamp,
        )
        return new_state

    def _calculate_new_state(
        self, current_state: int, rating: FSRSRating, review_count: int
    ) -> int:
        """Calculate new FSRS state based on current state and rating."""
        from src.domain.shared.models import FSRSState

        # Handle failure case (AGAIN rating)
        if rating == FSRSRating.AGAIN:
            if current_state == FSRSState.REVIEW:
                return FSRSState.RELEARNING  # Review card failed -> Relearning
            else:
                return (
                    FSRSState.NEW
                )  # Learning/New card failed -> stay New or back to New

        # Handle success cases (HARD, GOOD, EASY)
        if current_state == FSRSState.NEW:
            # New card answered correctly -> move to Learning
            return FSRSState.LEARNING
        elif current_state == FSRSState.LEARNING:
            # Learning card answered correctly
            # Graduate to Review after a few successful reviews (typically 2-3)
            # Handle case where review_count might be None
            review_count_safe = review_count or 0
            if (
                review_count_safe >= 1
            ):  # Graduate after 2nd review (review_count starts at 0)
                return FSRSState.REVIEW
            else:
                return FSRSState.LEARNING  # Stay in learning
        elif current_state == FSRSState.RELEARNING:
            # Relearning card answered correctly -> back to Review
            return FSRSState.REVIEW
        else:  # current_state == FSRSState.REVIEW
            # Review card answered correctly -> stay in Review
            return FSRSState.REVIEW

    async def _increment_lapse_count(self, card_id: int) -> None:
        """Increment lapse count for a card."""
        await self.learning_repository.increment_lapse_count(card_id)

    async def _record_review_history(
        self,
        card: FSRSCard,
        request: ScheduleCardRequest,
        state_before: FSRSCardState,
        schedule_result: ScheduleResult,
    ) -> None:
        """Record review in history."""
        await self.learning_repository.record_review_history(
            card_id=card.card_id,
            question_id=card.question_id,
            rating=int(request.rating),
            response_time_ms=request.response_time_ms,
            difficulty_before=state_before.difficulty,
            stability_before=state_before.stability,
            retrievability_before=state_before.retrievability,
            difficulty_after=schedule_result.difficulty,
            stability_after=schedule_result.stability,
            retrievability_after=schedule_result.retrievability,
            next_interval_days=schedule_result.next_interval,
            session_id=request.session_id,
        )

    def _calculate_difficulty(
        self, difficulty: float, rating: FSRSRating, w: list[float]
    ) -> float:
        """Calculate new difficulty based on rating."""
        if rating == FSRSRating.EASY:
            delta_d = -w[6] * (rating.value - 3)
        else:
            delta_d = w[6] * (rating.value - 3)

        new_difficulty = difficulty + delta_d
        return max(1.0, min(10.0, new_difficulty))

    def _init_stability(self, rating: FSRSRating, w: list[float]) -> float:
        """Calculate initial stability for new cards."""
        rating_value = rating.value
        return max(0.1, w[rating_value - 1])

    def _next_stability(
        self,
        difficulty: float,
        stability: float,
        retrievability: float,
        rating: FSRSRating,
        w: list[float],
    ) -> float:
        """Calculate next stability for reviewed cards."""
        if rating == FSRSRating.AGAIN:
            # Lapse: reduce stability
            new_stability = (
                w[11]
                * pow(difficulty, -w[12])
                * (pow(stability + 1, w[13]) - 1)
                * math.exp(w[14] * (1 - retrievability))
            )
        else:
            # Successful recall: increase stability
            success_rate = self._calculate_success_rate(difficulty, stability, w)
            new_stability = stability * (
                math.exp(w[8])
                * (11 - difficulty)
                * pow(stability, -w[9])
                * (math.exp(w[10] * (1 - retrievability)) - 1)
                * success_rate
                + 1
            )

        return max(0.1, new_stability)

    def _calculate_success_rate(
        self,
        difficulty: float,
        stability: float,  # noqa: ARG002
        w: list[float],  # noqa: ARG002
    ) -> float:
        """Calculate success rate factor for stability calculation."""
        return (11 - difficulty) / (11 - w[17] * (11 - difficulty))

    def _calculate_retrievability(
        self, card: FSRSCard, current_time: datetime
    ) -> float:
        """Calculate current retrievability of a card."""
        if not card.last_review_date or card.stability <= 0:
            return 1.0

        last_review = datetime.fromtimestamp(card.last_review_date, UTC)
        elapsed_days = (current_time - last_review).total_seconds() / 86400

        return math.exp(-elapsed_days / card.stability)


# ScheduleResult is imported from learning_models at the top
