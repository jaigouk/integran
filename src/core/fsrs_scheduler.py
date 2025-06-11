"""FSRS (Free Spaced Repetition Scheduler) implementation.

This module implements the FSRS-5 algorithm for optimizing spaced repetition learning.
Based on the DSR (Difficulty/Stability/Retrievability) memory model.

References:
    - FSRS Paper: https://github.com/open-spaced-repetition/fsrs4anki/wiki/ABC-of-FSRS
    - DSR Model: https://supermemo.guru/wiki/Three_component_model_of_memory
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.core.database import DatabaseManager
from src.core.models import (
    FSRSCard,
    FSRSCardState,
    FSRSParameters,
    FSRSRating,
    FSRSState,
    ScheduleResult,
)


@dataclass
class ReviewResult:
    """Result of a single review with FSRS calculations."""

    card_id: int
    question_id: int
    rating: FSRSRating
    response_time_ms: int

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


class FSRSScheduler:
    """Main FSRS algorithm implementation for spaced repetition scheduling."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize FSRS scheduler.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._parameters: FSRSParameters | None = None

    @property
    def parameters(self) -> FSRSParameters:
        """Get FSRS parameters, loading from database if needed."""
        if self._parameters is None:
            config = self.db_manager.get_algorithm_config()
            if config:
                self._parameters = FSRSParameters()
                self._parameters.w = json.loads(config.parameters)
            else:
                self._parameters = FSRSParameters()
        return self._parameters

    def review_card(
        self,
        card_id: int,
        rating: FSRSRating,
        response_time_ms: int,
        session_id: int | None = None,
    ) -> ReviewResult:
        """Process a card review using FSRS algorithm.

        Args:
            card_id: Card ID to review
            rating: User rating (1=Again, 2=Hard, 3=Good, 4=Easy)
            response_time_ms: Time taken to answer in milliseconds
            session_id: Optional learning session ID

        Returns:
            ReviewResult with before/after states and scheduling
        """
        # Get current card state
        card = self.db_manager.get_fsrs_card_by_id(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")

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

        # Calculate new state based on rating
        schedule_result = self._schedule_card(state_before, rating)

        # Update card in database
        next_review_timestamp = schedule_result.next_review_date.timestamp()
        self.db_manager.update_fsrs_card(
            card_id=card_id,
            difficulty=schedule_result.difficulty,
            stability=schedule_result.stability,
            retrievability=schedule_result.retrievability,
            state=int(
                schedule_result.next_review_date > now
            ),  # 0=New, 1=Learning, 2=Review
            next_review_date=next_review_timestamp,
        )

        # Update lapse count if needed
        if rating == FSRSRating.AGAIN:
            self._increment_lapse_count(card_id)

        # Record review in history
        self.db_manager.record_fsrs_review(
            card_id=card_id,
            question_id=card.question_id,
            rating=int(rating),
            response_time_ms=response_time_ms,
            difficulty_before=state_before.difficulty,
            stability_before=state_before.stability,
            retrievability_before=state_before.retrievability,
            difficulty_after=schedule_result.difficulty,
            stability_after=schedule_result.stability,
            retrievability_after=schedule_result.retrievability,
            next_interval_days=schedule_result.next_interval,
            session_id=session_id,
        )

        return ReviewResult(
            card_id=card_id,
            question_id=card.question_id,
            rating=rating,
            response_time_ms=response_time_ms,
            difficulty_before=state_before.difficulty,
            stability_before=state_before.stability,
            retrievability_before=state_before.retrievability,
            state_before=state_before.state,
            difficulty_after=schedule_result.difficulty,
            stability_after=schedule_result.stability,
            retrievability_after=schedule_result.retrievability,
            state_after=FSRSState.REVIEW,  # Simplified for now
            next_review_date=schedule_result.next_review_date,
            next_interval_days=schedule_result.next_interval,
        )

    def get_due_cards(self, limit: int = 50, user_id: int = 1) -> list[FSRSCard]:
        """Get cards due for review.

        Args:
            limit: Maximum number of cards to return
            user_id: User ID

        Returns:
            List of due cards sorted by priority
        """
        return self.db_manager.get_due_fsrs_cards(user_id=user_id, limit=limit)

    def predict_retention(self, card: FSRSCard, days_ahead: int = 1) -> float:
        """Predict retention rate for a card after specified days.

        Args:
            card: FSRS card
            days_ahead: Number of days in the future to predict

        Returns:
            Predicted retention probability (0.0-1.0)
        """
        if card.stability <= 0:
            return 0.0

        # R = exp(-t/S) where t=time, S=stability
        return math.exp(-days_ahead / card.stability)

    def optimize_parameters(self, user_id: int = 1, min_reviews: int = 100) -> bool:  # noqa: ARG002
        """Optimize FSRS parameters based on user review history.

        Args:
            user_id: User ID
            min_reviews: Minimum reviews needed for optimization

        Returns:
            True if optimization was performed, False if insufficient data
        """
        # Get review history for optimization
        with self.db_manager.get_session() as session:
            from src.core.models import ReviewHistory

            reviews = session.query(ReviewHistory).count()
            if reviews < min_reviews:
                return False

        # For now, use default parameters
        # TODO: Implement parameter optimization algorithm
        return True

    def _schedule_card(
        self, state: FSRSCardState, rating: FSRSRating
    ) -> ScheduleResult:
        """Calculate new card state based on FSRS algorithm.

        Args:
            state: Current card state
            rating: User rating

        Returns:
            New card state and scheduling information
        """
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

    def _calculate_difficulty(
        self, difficulty: float, rating: FSRSRating, w: list[float]
    ) -> float:
        """Calculate new difficulty based on rating.

        Args:
            difficulty: Current difficulty
            rating: User rating
            w: FSRS parameters

        Returns:
            New difficulty value
        """
        # FSRS difficulty calculation
        if rating == FSRSRating.EASY:
            delta_d = -w[6] * (rating.value - 3)
        else:
            delta_d = w[6] * (rating.value - 3)

        new_difficulty = difficulty + delta_d
        return max(1.0, min(10.0, new_difficulty))

    def _init_stability(self, rating: FSRSRating, w: list[float]) -> float:
        """Calculate initial stability for new cards.

        Args:
            rating: User rating
            w: FSRS parameters

        Returns:
            Initial stability in days
        """
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
        """Calculate next stability for reviewed cards.

        Args:
            difficulty: Current difficulty
            stability: Current stability
            retrievability: Current retrievability
            rating: User rating
            w: FSRS parameters

        Returns:
            New stability in days
        """
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
        """Calculate success rate factor for stability calculation.

        Args:
            difficulty: Card difficulty
            stability: Current stability
            w: FSRS parameters

        Returns:
            Success rate factor
        """
        return (11 - difficulty) / (11 - w[17] * (11 - difficulty))

    def _calculate_retrievability(
        self, card: FSRSCard, current_time: datetime
    ) -> float:
        """Calculate current retrievability of a card.

        Args:
            card: FSRS card
            current_time: Current timestamp

        Returns:
            Current retrievability (0.0-1.0)
        """
        if not card.last_review_date or card.stability <= 0:
            return 1.0

        last_review = datetime.fromtimestamp(card.last_review_date, UTC)
        elapsed_days = (current_time - last_review).total_seconds() / 86400

        return math.exp(-elapsed_days / card.stability)

    def _increment_lapse_count(self, card_id: int) -> None:
        """Increment lapse count for a card.

        Args:
            card_id: Card ID
        """
        with self.db_manager.get_session() as session:
            card = session.query(FSRSCard).filter_by(card_id=card_id).first()
            if card:
                card.lapse_count += 1
                session.commit()

    def get_fsrs_card_by_id(self, card_id: int) -> FSRSCard | None:
        """Get FSRS card by ID (helper method).

        Args:
            card_id: Card ID

        Returns:
            FSRS card or None if not found
        """
        with self.db_manager.get_session() as session:
            return session.query(FSRSCard).filter_by(card_id=card_id).first()
