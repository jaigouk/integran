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
    AlgorithmConfig,
    AnswerStatus,
    Base,
    Category,
    CategoryProgress,
    # FSRS Models (Phase 3.0)
    FSRSCard,
    LearningData,
    LearningSession,
    LearningStats,
    LeechCard,
    PracticeSession,
    Question,
    QuestionAttempt,
    QuestionData,
    ReviewHistory,
    SessionStats,
    UserProgress,
    UserSettings,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for Phase 1.8 multilingual support."""

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
        """Load questions from JSON file into database (Phase 1.8 format).

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

            # Load new questions with Phase 1.8 multilingual format
            for item in data:
                # Handle both legacy and new format
                if "answers" in item:  # New Phase 1.8 format
                    question = Question(
                        id=item["id"],
                        question=item["question"],
                        options=json.dumps(item["options"]),
                        correct=item["correct"],
                        category=item["category"],
                        difficulty=item.get("difficulty", "medium"),
                        question_type=item.get("question_type", "general"),
                        state=item.get("state"),
                        page_number=item.get("page_number"),
                        is_image_question=1 if item.get("images") else 0,
                        images_data=json.dumps(item.get("images", [])),
                        multilingual_answers=json.dumps(item.get("answers", {})),
                        rag_sources=json.dumps(item.get("rag_sources", [])),
                    )
                else:  # Legacy format
                    question_data = QuestionData(**item)
                    question = Question(
                        id=question_data.id,
                        question=question_data.question,
                        options=json.dumps(question_data.options),
                        correct=question_data.correct,
                        category=question_data.category,
                        difficulty=question_data.difficulty.value,
                        question_type=question_data.question_type,
                        state=question_data.state,
                        page_number=question_data.page_number,
                        is_image_question=1 if question_data.is_image_question else 0,
                        # Convert legacy image_paths to new format if needed
                        images_data=json.dumps(
                            [
                                {"path": path, "description": "", "context": ""}
                                for path in question_data.image_paths
                            ]
                        )
                        if question_data.image_paths
                        else None,
                        image_paths=json.dumps(question_data.image_paths),
                        image_mapping=question_data.image_mapping,
                    )

                session.add(question)

                # Initialize learning data
                learning = LearningData(question_id=item["id"])
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
        learning.next_review = (now_utc + timedelta(days=learning.interval)).replace(
            tzinfo=None
        )

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

            # Phase 1.8: Count image questions completed
            completed_image_attempts = (
                session.query(QuestionAttempt)
                .join(Question)
                .filter(
                    Question.is_image_question == 1,
                    QuestionAttempt.status == AnswerStatus.CORRECT.value,
                )
                .count()
            )
            stats.image_questions_completed = completed_image_attempts

            # Get preferred language from settings
            preferred_lang = self.get_user_setting("preferred_language")
            stats.preferred_language = preferred_lang if preferred_lang else "en"

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

    def get_user_setting(self, key: str, default: Any = None) -> Any:
        """Get a user setting value.

        Args:
            key: Setting key.
            default: Default value if setting not found.

        Returns:
            Setting value or default.
        """
        with self.get_session() as session:
            setting = session.query(UserSettings).filter_by(setting_key=key).first()
            if setting:
                try:
                    return json.loads(setting.setting_value)
                except json.JSONDecodeError:
                    return setting.setting_value
            return default

    def set_user_setting(self, key: str, value: Any) -> None:
        """Set a user setting value.

        Args:
            key: Setting key.
            value: Setting value.
        """
        with self.get_session() as session:
            setting = session.query(UserSettings).filter_by(setting_key=key).first()

            if setting:
                setting.setting_value = json.dumps(value)
                setting.updated_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                setting = UserSettings(setting_key=key, setting_value=json.dumps(value))
                session.add(setting)

            session.commit()

    def get_question_with_multilingual_answers(
        self, question_id: int, language: str = "en"
    ) -> dict[str, Any] | None:
        """Get a question with its multilingual answers.

        Args:
            question_id: Question ID.
            language: Preferred language for answers.

        Returns:
            Question data with answers in specified language, or None if not found.
        """
        with self.get_session() as session:
            question = session.query(Question).filter_by(id=question_id).first()
            if not question:
                return None

            # Parse JSON data
            options = json.loads(question.options)
            images = json.loads(question.images_data) if question.images_data else []
            multilingual_answers = (
                json.loads(question.multilingual_answers)
                if question.multilingual_answers
                else {}
            )
            rag_sources = (
                json.loads(question.rag_sources) if question.rag_sources else []
            )

            # Get answers for specified language (fallback to English)
            answers = multilingual_answers.get(
                language, multilingual_answers.get("en", {})
            )

            return {
                "id": question.id,
                "question": question.question,
                "options": options,
                "correct": question.correct,
                "category": question.category,
                "difficulty": question.difficulty,
                "has_images": bool(question.is_image_question),
                "images": images,
                "answers": answers,
                "available_languages": list(multilingual_answers.keys()),
                "rag_sources": rag_sources,
            }

    def migrate_to_phase_18_schema(self) -> None:
        """Migrate database schema to Phase 1.8 format.

        This adds the new columns for multilingual support.
        """
        import contextlib

        with self.get_session() as session:
            # Add new columns if they don't exist
            with contextlib.suppress(Exception):
                session.execute("ALTER TABLE questions ADD COLUMN images_data TEXT")

            with contextlib.suppress(Exception):
                session.execute(
                    "ALTER TABLE questions ADD COLUMN multilingual_answers TEXT"
                )

            with contextlib.suppress(Exception):
                session.execute("ALTER TABLE questions ADD COLUMN rag_sources TEXT")

            with contextlib.suppress(Exception):
                session.execute("ALTER TABLE questions ADD COLUMN updated_at DATETIME")

            session.commit()
            logger.info("Phase 1.8 schema migration completed")

    # ============================================================================
    # FSRS Database Operations (Phase 3.0)
    # ============================================================================

    def migrate_to_fsrs_schema(self) -> None:
        """Migrate database schema to Phase 3.0 FSRS format.

        This creates all FSRS tables and migrates existing learning data.
        """
        with self.get_session() as session:
            # Create FSRS tables (they'll be created automatically by SQLAlchemy)
            # but we need to migrate existing learning data
            logger.info("Creating FSRS schema...")

            # Migrate existing learning data to FSRS cards
            existing_learning = session.query(LearningData).all()
            for ld in existing_learning:
                # Check if FSRS card already exists
                existing_card = (
                    session.query(FSRSCard)
                    .filter_by(question_id=ld.question_id)
                    .first()
                )

                if not existing_card:
                    # Convert SM-2 to initial FSRS state
                    fsrs_card = FSRSCard(
                        question_id=ld.question_id,
                        user_id=1,
                        difficulty=max(
                            1.0, min(10.0, 11 - ld.easiness_factor)
                        ),  # Convert EF to difficulty
                        stability=max(
                            0.1, float(ld.interval)
                        ),  # Use interval as initial stability
                        retrievability=0.9 if ld.repetitions > 0 else 1.0,
                        state=2
                        if ld.repetitions >= 2
                        else (1 if ld.repetitions > 0 else 0),
                        review_count=ld.repetitions,
                        last_review_date=ld.last_reviewed.timestamp()
                        if ld.last_reviewed
                        else None,
                        next_review_date=ld.next_review.timestamp()
                        if ld.next_review
                        else datetime.now(UTC).timestamp(),
                    )
                    session.add(fsrs_card)

            # Initialize default algorithm config if it doesn't exist
            config = session.query(AlgorithmConfig).filter_by(user_id=1).first()
            if not config:
                from src.core.models import FSRSParameters

                params = FSRSParameters()
                config = AlgorithmConfig(
                    user_id=1,
                    parameters=json.dumps(params.w),
                    target_retention=params.request_retention,
                    maximum_interval_days=365,
                )
                session.add(config)

            # Populate categories table from existing questions
            existing_categories = session.query(Question.category).distinct().all()
            for (category_name,) in existing_categories:
                existing_cat = (
                    session.query(Category).filter_by(name=category_name).first()
                )
                if not existing_cat:
                    question_count = (
                        session.query(Question)
                        .filter_by(category=category_name)
                        .count()
                    )
                    category = Category(
                        name=category_name,
                        description=f"Questions about {category_name}",
                        total_questions=question_count,
                    )
                    session.add(category)

            session.commit()
            logger.info("FSRS schema migration completed")

    def create_fsrs_card(self, question_id: int, user_id: int = 1) -> FSRSCard:
        """Create a new FSRS card for a question.

        Args:
            question_id: Question ID
            user_id: User ID (default 1)

        Returns:
            Created FSRS card
        """
        with self.get_session() as session:
            # Check if card already exists
            existing_card = (
                session.query(FSRSCard)
                .filter_by(question_id=question_id, user_id=user_id)
                .first()
            )

            if existing_card:
                return existing_card

            # Create new card with initial FSRS state
            card = FSRSCard(
                question_id=question_id,
                user_id=user_id,
                difficulty=5.0,  # Initial difficulty
                stability=1.0,  # Initial stability (1 day)
                retrievability=1.0,  # Perfect retrievability for new cards
                state=0,  # New state
            )

            session.add(card)
            session.commit()
            return card

    def get_fsrs_card(self, question_id: int, user_id: int = 1) -> FSRSCard | None:
        """Get FSRS card for a question.

        Args:
            question_id: Question ID
            user_id: User ID

        Returns:
            FSRS card or None if not found
        """
        with self.get_session() as session:
            return (
                session.query(FSRSCard)
                .filter_by(question_id=question_id, user_id=user_id)
                .first()
            )

    def get_due_fsrs_cards(self, user_id: int = 1, limit: int = 50) -> list[FSRSCard]:
        """Get FSRS cards due for review.

        Args:
            user_id: User ID
            limit: Maximum number of cards to return

        Returns:
            List of due cards
        """
        now = datetime.now(UTC).timestamp()

        with self.get_session() as session:
            return (
                session.query(FSRSCard)
                .filter(FSRSCard.user_id == user_id, FSRSCard.next_review_date <= now)
                .order_by(FSRSCard.next_review_date)
                .limit(limit)
                .all()
            )

    def update_fsrs_card(
        self,
        card_id: int,
        difficulty: float,
        stability: float,
        retrievability: float,
        state: int,
        next_review_date: float,
    ) -> None:
        """Update FSRS card state after review.

        Args:
            card_id: Card ID
            difficulty: New difficulty value
            stability: New stability value
            retrievability: New retrievability value
            state: New learning state
            next_review_date: Next review timestamp
        """
        with self.get_session() as session:
            card = session.query(FSRSCard).filter_by(card_id=card_id).first()
            if card:
                card.difficulty = difficulty
                card.stability = stability
                card.retrievability = retrievability
                card.state = state
                card.next_review_date = next_review_date
                card.last_review_date = datetime.now(UTC).timestamp()
                card.updated_at = datetime.now(UTC).timestamp()
                card.review_count += 1
                session.commit()

    def record_fsrs_review(
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
        """Record an FSRS review in history.

        Args:
            card_id: Card ID
            question_id: Question ID
            rating: User rating (1-4)
            response_time_ms: Response time in milliseconds
            difficulty_before: Difficulty before review
            stability_before: Stability before review
            retrievability_before: Retrievability before review
            difficulty_after: Difficulty after review
            stability_after: Stability after review
            retrievability_after: Retrievability after review
            next_interval_days: Next interval in days
            session_id: Learning session ID
        """
        with self.get_session() as session:
            review = ReviewHistory(
                card_id=card_id,
                question_id=question_id,
                review_date=datetime.now(UTC).timestamp(),
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
                review_type="review",
            )
            session.add(review)
            session.commit()

    def create_learning_session(
        self,
        session_type: str,
        user_id: int = 1,
        target_retention: float = 0.9,
        max_reviews: int = 50,
    ) -> int:
        """Create a new FSRS learning session.

        Args:
            session_type: Type of session ('review', 'learn', 'weak_focus', 'quiz')
            user_id: User ID
            target_retention: Target retention rate
            max_reviews: Maximum number of reviews

        Returns:
            Session ID
        """
        with self.get_session() as session:
            learning_session = LearningSession(
                user_id=user_id,
                start_time=datetime.now(UTC).timestamp(),
                session_type=session_type,
                target_retention=target_retention,
                max_reviews=max_reviews,
            )
            session.add(learning_session)
            session.commit()
            return learning_session.session_id

    def end_learning_session(self, session_id: int) -> None:
        """End a learning session and update statistics.

        Args:
            session_id: Session ID
        """
        with self.get_session() as session:
            learning_session = (
                session.query(LearningSession).filter_by(session_id=session_id).first()
            )

            if learning_session:
                end_time = datetime.now(UTC).timestamp()
                learning_session.end_time = end_time
                learning_session.duration_seconds = int(
                    end_time - learning_session.start_time
                )

                # Calculate session statistics
                reviews = (
                    session.query(ReviewHistory).filter_by(session_id=session_id).all()
                )
                learning_session.questions_reviewed = len(reviews)
                learning_session.questions_correct = sum(
                    1 for r in reviews if r.rating >= 3
                )

                if reviews:
                    learning_session.average_response_time_ms = int(
                        sum(r.response_time_ms or 0 for r in reviews) / len(reviews)
                    )
                    learning_session.retention_rate = (
                        learning_session.questions_correct / len(reviews)
                    )

                session.commit()

    def get_algorithm_config(self, user_id: int = 1) -> AlgorithmConfig | None:
        """Get algorithm configuration for user.

        Args:
            user_id: User ID

        Returns:
            Algorithm config or None
        """
        with self.get_session() as session:
            return session.query(AlgorithmConfig).filter_by(user_id=user_id).first()

    def update_algorithm_config(
        self, user_id: int, parameters: list[float], target_retention: float = 0.9
    ) -> None:
        """Update algorithm configuration.

        Args:
            user_id: User ID
            parameters: FSRS parameters
            target_retention: Target retention rate
        """
        with self.get_session() as session:
            config = session.query(AlgorithmConfig).filter_by(user_id=user_id).first()

            if config:
                config.parameters = json.dumps(parameters)
                config.target_retention = target_retention
                config.updated_at = datetime.now(UTC).timestamp()
            else:
                config = AlgorithmConfig(
                    user_id=user_id,
                    parameters=json.dumps(parameters),
                    target_retention=target_retention,
                )
                session.add(config)

            session.commit()

    def detect_leech_cards(
        self, user_id: int = 1, threshold: int = 8
    ) -> list[LeechCard]:
        """Detect cards that qualify as leeches.

        Args:
            user_id: User ID
            threshold: Lapse threshold for leech detection

        Returns:
            List of leech cards
        """
        with self.get_session() as session:
            # Find cards with high lapse count that aren't already marked as leeches
            cards = (
                session.query(FSRSCard)
                .filter(FSRSCard.user_id == user_id, FSRSCard.lapse_count >= threshold)
                .all()
            )

            leeches = []
            for card in cards:
                existing_leech = (
                    session.query(LeechCard).filter_by(card_id=card.card_id).first()
                )
                if not existing_leech:
                    leech = LeechCard(
                        card_id=card.card_id,
                        question_id=card.question_id,
                        lapse_count=card.lapse_count,
                        leech_threshold=threshold,
                        detected_at=datetime.now(UTC).timestamp(),
                    )
                    session.add(leech)
                    leeches.append(leech)

            session.commit()
            return leeches

    def get_fsrs_learning_stats(self, user_id: int = 1) -> dict[str, Any]:
        """Get comprehensive FSRS learning statistics.

        Args:
            user_id: User ID

        Returns:
            Dictionary of learning statistics
        """
        now = datetime.now(UTC).timestamp()

        with self.get_session() as session:
            cards = session.query(FSRSCard).filter_by(user_id=user_id).all()

            stats = {
                "total_cards": len(cards),
                "new_cards": sum(1 for c in cards if c.state == 0),
                "learning_cards": sum(1 for c in cards if c.state == 1),
                "review_cards": sum(1 for c in cards if c.state == 2),
                "relearning_cards": sum(1 for c in cards if c.state == 3),
                "due_cards": sum(
                    1 for c in cards if c.next_review_date and c.next_review_date <= now
                ),
                "overdue_cards": sum(
                    1
                    for c in cards
                    if c.next_review_date and c.next_review_date < now - 86400
                ),  # 1 day
                "average_difficulty": sum(c.difficulty for c in cards) / len(cards)
                if cards
                else 0,
                "average_stability": sum(c.stability for c in cards) / len(cards)
                if cards
                else 0,
                "leech_count": session.query(LeechCard)
                .filter(LeechCard.card_id.in_([c.card_id for c in cards]))
                .count(),
            }

            # Calculate retention rate from recent reviews
            recent_reviews = (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    ReviewHistory.review_date >= now - 2592000,  # 30 days
                )
                .all()
            )

            if recent_reviews:
                successful_reviews = sum(1 for r in recent_reviews if r.rating >= 3)
                stats["retention_rate"] = successful_reviews / len(recent_reviews)
            else:
                stats["retention_rate"] = 0.0

            return stats
