"""Concrete implementation of LearningRepository interface."""

from __future__ import annotations

from src.domain.learning.models.learning_models import FSRSCard, LearningSession
from src.domain.shared.repositories import LearningRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyLearningRepository(LearningRepository):
    """SQLAlchemy implementation of LearningRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def get_fsrs_card(self, question_id: int, user_id: int) -> FSRSCard | None:
        """Get FSRS card for a specific question and user."""
        return self.db_manager.get_fsrs_card(question_id, user_id)

    async def save_fsrs_card(self, card: FSRSCard) -> FSRSCard:
        """Save or update an FSRS card."""
        # Use create_fsrs_card or update_fsrs_card based on whether card exists
        if hasattr(card, "card_id") and getattr(card, "card_id", None):
            # Update existing card
            self.db_manager.update_fsrs_card(
                card.card_id,  # type: ignore[arg-type]
                card.difficulty,  # type: ignore[arg-type]
                card.stability,  # type: ignore[arg-type]
                card.retrievability,  # type: ignore[arg-type]
                card.state,  # type: ignore[arg-type]
                card.next_review_date,  # type: ignore[arg-type]
            )
            return card
        else:
            # Create new card
            return self.db_manager.create_fsrs_card(
                card.question_id,  # type: ignore[arg-type]
                card.user_id,  # type: ignore[arg-type]
            )

    async def get_due_cards(self, user_id: int, limit: int = 10) -> list[FSRSCard]:
        """Get cards due for review for a specific user."""
        return self.db_manager.get_due_fsrs_cards(user_id, limit)

    async def delete_user_learning_data(self, user_id: int) -> dict[str, int]:
        """Delete all learning data for a user and return counts."""
        # NOTE: DatabaseManager doesn't have delete_user_learning_data method
        raise NotImplementedError(
            "delete_user_learning_data not implemented in DatabaseManager"
        )

    async def get_learning_session(self, session_id: int) -> LearningSession | None:
        """Get a learning session by ID."""
        # NOTE: DatabaseManager doesn't have get_learning_session method
        raise NotImplementedError(
            "get_learning_session not implemented in DatabaseManager"
        )

    async def save_learning_session(self, session: LearningSession) -> LearningSession:
        """Save or update a learning session."""
        # NOTE: DatabaseManager doesn't have save_learning_session method
        raise NotImplementedError(
            "save_learning_session not implemented in DatabaseManager"
        )

    async def get_active_sessions(self, user_id: int) -> list[LearningSession]:
        """Get active learning sessions for a user."""
        # NOTE: DatabaseManager doesn't have get_active_sessions method
        raise NotImplementedError(
            "get_active_sessions not implemented in DatabaseManager"
        )

    async def get_fsrs_card_by_id(self, card_id: int) -> FSRSCard | None:
        """Get FSRS card by card ID."""
        return self.db_manager.get_fsrs_card_by_id(card_id)

    async def update_fsrs_card_state(
        self,
        card_id: int,
        difficulty: float,
        stability: float,
        retrievability: float,
        state: int,
        next_review_date: float,
    ) -> None:
        """Update FSRS card state after review."""
        self.db_manager.update_fsrs_card(
            card_id=card_id,
            difficulty=difficulty,
            stability=stability,
            retrievability=retrievability,
            state=state,
            next_review_date=next_review_date,
        )

    async def increment_lapse_count(self, card_id: int) -> None:
        """Increment lapse count for a card."""
        # Get current card from database
        with self.db_manager.get_session() as session:
            from src.domain.learning.models.learning_models import FSRSCard

            card = session.query(FSRSCard).filter_by(card_id=card_id).first()
            if card:
                card.lapse_count = card.lapse_count + 1  # type: ignore[assignment]
                session.commit()

    async def record_review_history(
        self,
        card_id: int,
        question_id: int,
        rating: int,
        response_time_ms: int,
        difficulty_before: float,
        stability_before: float,
        retrievability_before: float,
        difficulty_after: float,
        stability_after: float,
        retrievability_after: float,
        next_interval_days: float,
        session_id: int | None = None,
    ) -> None:
        """Record review in history."""
        self.db_manager.record_fsrs_review(
            card_id=card_id,
            question_id=question_id,
            rating=rating,
            response_time_ms=response_time_ms,
            difficulty_before=difficulty_before,
            stability_before=stability_before,
            retrievability_before=retrievability_before,
            difficulty_after=difficulty_after,
            stability_after=stability_after,
            retrievability_after=retrievability_after,
            next_interval_days=next_interval_days,
            session_id=session_id,
        )
