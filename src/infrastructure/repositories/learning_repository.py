"""Concrete implementation of LearningRepository interface."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from src.domain.learning.models.learning_models import FSRSCard, LearningSession
from src.domain.shared.repositories import LearningRepository
from src.infrastructure.database.database import DatabaseManager


class SQLAlchemyLearningRepository(LearningRepository):
    """SQLAlchemy implementation of LearningRepository interface."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def get_fsrs_card(self, question_id: int, user_id: int) -> FSRSCard | None:
        """Get FSRS card for a specific question and user."""
        return self.db_manager.get_fsrs_card(question_id, user_id)

    async def save_fsrs_card(self, card: FSRSCard) -> FSRSCard:
        """Save or update an FSRS card."""
        # Use create_fsrs_card or update_fsrs_card based on whether card exists
        if hasattr(card, "card_id") and getattr(card, "card_id", None):
            # Update existing card
            self.db_manager.update_fsrs_card(
                card.card_id,
                card.difficulty,
                card.stability,
                card.retrievability,
                card.state,
                card.next_review_date,
            )
            return card
        else:
            # Create new card
            return self.db_manager.create_fsrs_card(
                card.question_id,
                card.user_id,
            )

    async def get_due_cards(self, user_id: int, limit: int = 10) -> list[FSRSCard]:
        """Get cards due for review for a specific user."""
        return self.db_manager.get_due_fsrs_cards(user_id, limit)

    async def count_due_cards(self, user_id: int) -> int:
        """Count cards due for review for a specific user."""
        return await self._run_in_executor(
            lambda: self.db_manager.count_due_fsrs_cards(user_id)
        )

    async def delete_user_learning_data(self, user_id: int) -> dict[str, int]:
        """Delete all learning data for a user and return counts."""

        def _delete_user_learning_data() -> dict[str, int]:
            with self.db_manager.get_session() as session:
                from src.domain.learning.models.learning_models import (
                    FSRSCard,
                    LearningSession,
                    ReviewHistory,
                )

                # Count items before deletion
                fsrs_cards_count = (
                    session.query(FSRSCard).filter_by(user_id=user_id).count()
                )
                review_history_count = (
                    session.query(ReviewHistory)
                    .join(FSRSCard)
                    .filter(FSRSCard.user_id == user_id)
                    .count()
                )
                sessions_count = (
                    session.query(LearningSession).filter_by(user_id=user_id).count()
                )

                # Delete data in proper order (respecting foreign keys)
                # First get review history IDs for this user's cards
                review_history_ids = [
                    result[0]
                    for result in session.query(ReviewHistory.review_id)
                    .join(FSRSCard)
                    .filter(FSRSCard.user_id == user_id)
                    .all()
                ]
                # Delete review history by IDs
                if review_history_ids:
                    session.query(ReviewHistory).filter(
                        ReviewHistory.review_id.in_(review_history_ids)
                    ).delete(synchronize_session=False)
                session.query(FSRSCard).filter_by(user_id=user_id).delete()
                session.query(LearningSession).filter_by(user_id=user_id).delete()

                session.commit()

                return {
                    "fsrs_cards": fsrs_cards_count,
                    "review_history": review_history_count,
                    "learning_sessions": sessions_count,
                }

        return await self._run_in_executor(_delete_user_learning_data)

    async def get_learning_session(self, session_id: int) -> LearningSession | None:
        """Get a learning session by ID."""

        def _get_learning_session() -> LearningSession | None:
            with self.db_manager.get_session() as session:
                return (
                    session.query(LearningSession)
                    .filter_by(session_id=session_id)
                    .first()
                )

        return await self._run_in_executor(_get_learning_session)

    async def save_learning_session(self, session: LearningSession) -> LearningSession:
        """Save or update a learning session."""

        def _save_learning_session() -> LearningSession:
            with self.db_manager.get_session() as db_session:
                # Check if session exists (has session_id)
                if hasattr(session, "session_id") and session.session_id:
                    # Update existing session
                    existing = (
                        db_session.query(LearningSession)
                        .filter_by(session_id=session.session_id)
                        .first()
                    )
                    if existing:
                        # Update fields
                        for field in [
                            "user_id",
                            "start_time",
                            "end_time",
                            "duration_seconds",
                            "questions_reviewed",
                            "questions_correct",
                            "new_cards_learned",
                            "session_type",
                            "target_retention",
                            "max_reviews",
                            "average_response_time_ms",
                            "retention_rate",
                        ]:
                            if hasattr(session, field):
                                setattr(existing, field, getattr(session, field))
                        db_session.commit()
                        return existing
                    else:
                        # Add as new session
                        db_session.add(session)
                        db_session.commit()
                        return session
                else:
                    # Add as new session
                    db_session.add(session)
                    db_session.commit()
                    return session

        return await self._run_in_executor(_save_learning_session)

    async def get_active_sessions(self, user_id: int) -> list[LearningSession]:
        """Get active learning sessions for a user."""

        def _get_active_sessions() -> list[LearningSession]:
            with self.db_manager.get_session() as session:
                # Active sessions are those without an end_time
                return (
                    session.query(LearningSession)
                    .filter_by(user_id=user_id)
                    .filter(LearningSession.end_time.is_(None))
                    .all()
                )

        return await self._run_in_executor(_get_active_sessions)

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

        def _increment_lapse_count() -> None:
            # Get current card from database
            with self.db_manager.get_session() as session:
                from src.domain.learning.models.learning_models import FSRSCard

                card = session.query(FSRSCard).filter_by(card_id=card_id).first()
                if card:
                    card.lapse_count = card.lapse_count + 1
                    session.commit()

        await self._run_in_executor(_increment_lapse_count)

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
