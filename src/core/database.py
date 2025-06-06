"""Database management module for Leben in Deutschland trainer."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.models import (
    AnswerStatus,
    Base,
    CategoryProgress,
    LearningData,
    LearningStats,
    PracticeSession,
    Question,
    QuestionAttempt,
    QuestionData,
    SessionStats,
    UserProgress,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, db_path: str | Path = "data/trainer.db") -> None:
        """Initialize database manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with proper SQLite configuration
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager.

        Yields:
            Database session.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def load_questions(self, questions_file: str | Path) -> int:
        """Load questions from JSON file into database.

        Args:
            questions_file: Path to questions JSON file.

        Returns:
            Number of questions loaded.
        """
        questions_path = Path(questions_file)
        if not questions_path.exists():
            raise FileNotFoundError(f"Questions file not found: {questions_path}")

        with open(questions_path, encoding="utf-8") as f:
            data = json.load(f)

        with self.get_session() as session:
            # Clear existing questions if any
            session.query(Question).delete()

            # Load new questions
            for item in data:
                question_data = QuestionData(**item)
                question = Question(
                    id=question_data.id,
                    question=question_data.question,
                    options=json.dumps(question_data.options),
                    correct=question_data.correct,
                    category=question_data.category,
                    difficulty=question_data.difficulty.value,
                )
                session.add(question)

                # Initialize learning data
                learning = LearningData(question_id=question_data.id)
                session.add(learning)

            # Update category progress
            categories = {item["category"] for item in data}
            for category in categories:
                count = sum(1 for item in data if item["category"] == category)
                cat_progress = CategoryProgress(
                    category=category,
                    total_questions=count,
                )
                session.add(cat_progress)

            session.commit()
            logger.info(f"Loaded {len(data)} questions")
            return len(data)

    def get_question(self, question_id: int) -> Question | None:
        """Get a specific question by ID.

        Args:
            question_id: Question ID.

        Returns:
            Question object or None if not found.
        """
        with self.get_session() as session:
            return session.query(Question).filter_by(id=question_id).first()

    def get_questions_by_category(self, category: str) -> list[Question]:
        """Get all questions for a category.

        Args:
            category: Category name.

        Returns:
            List of questions.
        """
        with self.get_session() as session:
            return session.query(Question).filter_by(category=category).all()

    def get_questions_for_review(self, limit: int = 20) -> list[Question]:
        """Get questions due for review.

        Args:
            limit: Maximum number of questions to return.

        Returns:
            List of questions due for review.
        """
        with self.get_session() as session:
            # Use naive datetime for comparison since SQLite stores naive datetimes
            now = datetime.now()
            return (
                session.query(Question)
                .join(LearningData)
                .filter(LearningData.next_review <= now)
                .order_by(LearningData.next_review)
                .limit(limit)
                .all()
            )

    def record_attempt(
        self,
        session_id: int,
        question_id: int,
        status: AnswerStatus,
        user_answer: str | None = None,
        time_taken: float = 0.0,
    ) -> None:
        """Record a question attempt.

        Args:
            session_id: Practice session ID.
            question_id: Question ID.
            status: Answer status.
            user_answer: User's answer.
            time_taken: Time taken in seconds.
        """
        with self.get_session() as session:
            attempt = QuestionAttempt(
                session_id=session_id,
                question_id=question_id,
                status=status.value,
                user_answer=user_answer,
                time_taken=time_taken,
            )
            session.add(attempt)

            # Update learning data if answered
            if status != AnswerStatus.SKIPPED:
                self._update_learning_data(session, question_id, status)

            session.commit()

    def _update_learning_data(
        self, session: Session, question_id: int, status: AnswerStatus
    ) -> None:
        """Update spaced repetition data using SM-2 algorithm.

        Args:
            session: Database session.
            question_id: Question ID.
            status: Answer status.
        """
        learning = (
            session.query(LearningData).filter_by(question_id=question_id).first()
        )
        if not learning:
            return

        # SM-2 algorithm implementation
        if status == AnswerStatus.CORRECT:
            # Increase repetitions
            learning.repetitions += 1

            # Update easiness factor (minimum 1.3)
            learning.easiness_factor = max(
                1.3,
                learning.easiness_factor + 0.1 - (5 - 4) * (0.08 + (5 - 4) * 0.02),
            )

            # Calculate new interval
            if learning.repetitions == 1:
                learning.interval = 1
            elif learning.repetitions == 2:
                learning.interval = 6
            else:
                learning.interval = int(learning.interval * learning.easiness_factor)
        else:
            # Reset on incorrect answer
            learning.repetitions = 0
            learning.interval = 1
            learning.easiness_factor = max(1.3, learning.easiness_factor - 0.2)

        # Update review dates (use naive datetime for SQLite compatibility)
        now_utc = datetime.now(UTC)
        learning.last_reviewed = now_utc.replace(tzinfo=None)
        learning.next_review = (now_utc + timedelta(days=learning.interval)).replace(tzinfo=None)

    def create_session(self, mode: str) -> int:
        """Create a new practice session.

        Args:
            mode: Practice mode.

        Returns:
            Session ID.
        """
        with self.get_session() as session:
            practice_session = PracticeSession(mode=mode)
            session.add(practice_session)
            session.commit()
            return practice_session.id

    def end_session(self, session_id: int) -> SessionStats:
        """End a practice session and return statistics.

        Args:
            session_id: Session ID.

        Returns:
            Session statistics.
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if not practice_session:
                raise ValueError(f"Session {session_id} not found")

            practice_session.ended_at = datetime.now(UTC).replace(tzinfo=None)

            # Calculate statistics
            attempts = (
                session.query(QuestionAttempt).filter_by(session_id=session_id).all()
            )

            stats = SessionStats()
            stats.total_questions = len(attempts)
            stats.correct_answers = sum(
                1 for a in attempts if a.status == AnswerStatus.CORRECT.value
            )
            stats.incorrect_answers = sum(
                1 for a in attempts if a.status == AnswerStatus.INCORRECT.value
            )
            stats.skipped = sum(
                1 for a in attempts if a.status == AnswerStatus.SKIPPED.value
            )

            if stats.total_questions > 0:
                stats.accuracy = stats.correct_answers / stats.total_questions * 100
                total_time = sum(a.time_taken for a in attempts if a.time_taken)
                stats.average_time = total_time / stats.total_questions

            # Get categories practiced
            question_ids = [a.question_id for a in attempts]
            questions = (
                session.query(Question).filter(Question.id.in_(question_ids)).all()
            )
            stats.categories_practiced = list({q.category for q in questions})

            # Update session record
            practice_session.total_questions = stats.total_questions
            practice_session.correct_answers = stats.correct_answers

            # Update user progress
            self._update_user_progress(session, stats)

            session.commit()
            return stats

    def _update_user_progress(self, session: Session, stats: SessionStats) -> None:
        """Update overall user progress.

        Args:
            session: Database session.
            stats: Session statistics.
        """
        progress = session.query(UserProgress).first()
        if not progress:
            progress = UserProgress(
                total_questions_seen=0,
                total_correct=0,
                total_time_spent=0.0,
                current_streak=0,
                longest_streak=0,
                created_at=datetime.now(UTC).replace(tzinfo=None),
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(progress)

        progress.total_questions_seen += stats.total_questions
        progress.total_correct += stats.correct_answers
        progress.total_time_spent += stats.average_time * stats.total_questions

        # Update streaks
        last_practice = progress.last_practice
        progress.last_practice = datetime.now(UTC).replace(tzinfo=None)

        if last_practice:
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            days_since = (now_naive - last_practice).days
            if days_since <= 1:
                progress.current_streak += 1
            else:
                progress.current_streak = 1
        else:
            progress.current_streak = 1

        progress.longest_streak = max(progress.longest_streak, progress.current_streak)
        progress.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def get_learning_stats(self) -> LearningStats:
        """Get overall learning statistics.

        Returns:
            Learning statistics.
        """
        with self.get_session() as session:
            stats = LearningStats()

            # Count questions by learning status
            # Use naive datetime for comparison since SQLite stores naive datetimes
            now = datetime.now()
            learning_data = session.query(LearningData).all()

            for ld in learning_data:
                if ld.repetitions >= 5:
                    stats.total_mastered += 1
                elif ld.repetitions > 0:
                    stats.total_learning += 1
                else:
                    stats.total_new += 1

                if ld.next_review <= now:
                    stats.overdue_count += 1
                elif ld.next_review <= now + timedelta(days=1):
                    stats.next_review_count += 1

            # Calculate average easiness
            if learning_data:
                stats.average_easiness = sum(
                    ld.easiness_factor for ld in learning_data
                ) / len(learning_data)

            # Get current streak
            progress = session.query(UserProgress).first()
            if progress:
                stats.study_streak = progress.current_streak

            return stats

    def reset_progress(self) -> None:
        """Reset all user progress data."""
        with self.get_session() as session:
            # Delete all tracking data
            session.query(QuestionAttempt).delete()
            session.query(PracticeSession).delete()
            session.query(LearningData).delete()
            session.query(UserProgress).delete()
            session.query(CategoryProgress).update(
                {
                    CategoryProgress.questions_seen: 0,
                    CategoryProgress.correct_answers: 0,
                    CategoryProgress.average_time: 0.0,
                    CategoryProgress.last_practiced: None,
                }
            )

            # Reinitialize learning data
            questions = session.query(Question).all()
            for question in questions:
                learning = LearningData(question_id=question.id)
                session.add(learning)

            session.commit()
            logger.info("Progress reset successfully")
