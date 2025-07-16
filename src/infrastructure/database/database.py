"""Database management module for Leben in Deutschland trainer."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Import domain-specific models
from src.domain.analytics.models.analytics_models import (
    Category,
    CategoryProgress,
    UserProgress,
)
from src.domain.content.models.question_models import (
    PracticeSession,
    Question,
    QuestionAttempt,
    QuestionData,
    SessionStats,
)
from src.domain.learning.models.learning_models import (
    AlgorithmConfig,
    FSRSCard,
    LearningSession,
    LearningStats,
    LeechCard,
    ReviewHistory,
)
from src.domain.shared.models import AnswerStatus, Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations with performance optimizations."""

    def __init__(
        self,
        db_path: str | Path = "data/trainer.db",
        enable_optimizations: bool = True,
        enable_async: bool = True,
        enable_indexing: bool = True,
        pool_size: int = 10,
        max_overflow: int = 20,
        timeout: int = 30,
    ) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to the SQLite database file.
            enable_optimizations: Enable SQLite performance optimizations.
            enable_async: Enable async database operations.
            enable_indexing: Enable database indexing for better query performance.
            pool_size: Number of connections to maintain in pool.
            max_overflow: Maximum overflow connections.
            timeout: Connection timeout in seconds.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_optimizations = enable_optimizations
        self.enable_async = enable_async
        self.enable_indexing = enable_indexing

        # Create engine with proper SQLite configuration
        engine_kwargs = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": timeout,
            },
            "echo": False,
        }

        if enable_optimizations:
            engine_kwargs.update(
                {
                    "poolclass": pool.QueuePool,
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                    "pool_pre_ping": True,
                }
            )
        else:
            engine_kwargs["poolclass"] = pool.StaticPool

        self.engine = create_engine(f"sqlite:///{self.db_path}", **engine_kwargs)

        # Enable foreign keys and performance optimizations for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            if enable_optimizations:
                # Performance optimizations
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
                cursor.execute("PRAGMA cache_size=10000")  # Larger cache (10MB)
                cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O

            cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create async engine if enabled
        if enable_async:
            self.async_engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.db_path}",
                connect_args={
                    "check_same_thread": False,
                    "timeout": timeout,
                },
                pool_pre_ping=True,
                echo=False,
            )
            self.async_session_maker = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        else:
            self.async_engine = None
            self.async_session_maker = None

        self._create_tables()
        self._ensure_default_user()

        if enable_indexing:
            self._create_indexes()

    def _create_tables(self) -> None:
        """Create all database tables."""
        # Import User domain models to register them with SQLAlchemy metadata
        try:
            from src.domain.user.models.user_models import UserSettingsDB  # noqa: F401
            from src.infrastructure.database.models import UserDB  # noqa: F401

            # This import registers the model with Base.metadata
            logger.debug(
                f"Successfully imported UserSettingsDB model: {UserSettingsDB.__name__}"
            )
        except ImportError as e:
            logger.warning(f"Could not import User domain models: {e}")

        Base.metadata.create_all(bind=self.engine)

        # Run schema migrations for existing databases
        self.migrate_practice_sessions_schema()
        self.migrate_user_configuration_schema()

        logger.info(f"Database initialized at {self.db_path}")

    def _ensure_default_user(self) -> None:
        """Ensure a default user exists with ID=1."""
        with self.get_session() as session:
            from src.infrastructure.database.models import UserDB

            # Check if user with ID=1 exists
            user = session.query(UserDB).filter_by(id=1).first()
            if not user:
                # Create default user
                default_user = UserDB(
                    id=1,
                    username="default",
                    email=None,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    last_active=datetime.now(UTC).replace(tzinfo=None),
                    study_streak=0,
                    is_active=True,
                )
                session.add(default_user)
                session.commit()
                logger.info("Created default user with ID=1")

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

        # Handle different JSON formats
        if isinstance(data, dict) and "questions" in data:
            # Final dataset format: {"questions": {"1": {...}, "2": {...}}}
            questions_data = list(data["questions"].values())
        elif isinstance(data, list):
            # Legacy format: [{"id": 1, ...}, {"id": 2, ...}]
            questions_data = data
        else:
            raise ValueError(f"Unsupported questions file format in {questions_path}")

        with self.get_session() as session:
            # Clear existing questions if any
            session.query(Question).delete()

            # Load new questions with Phase 1.8 multilingual format
            for item in questions_data:
                # Handle different data formats
                if "explanations" in item:  # Final dataset format
                    # Convert final dataset format to standard multilingual answers format
                    multilingual_answers = {}

                    # Get available languages from explanations
                    languages = set(item.get("explanations", {}).keys())
                    if item.get("why_others_wrong"):
                        languages.update(item["why_others_wrong"].keys())
                    if item.get("key_concept"):
                        languages.update(item["key_concept"].keys())
                    if item.get("mnemonic"):
                        languages.update(item["mnemonic"].keys())

                    # Build answers for each language
                    for lang in languages:
                        multilingual_answers[lang] = {
                            "explanation": item.get("explanations", {}).get(lang, ""),
                            "why_others_wrong": item.get("why_others_wrong", {}).get(
                                lang, {}
                            ),
                            "key_concept": item.get("key_concept", {}).get(lang, ""),
                            "mnemonic": item.get("mnemonic", {}).get(lang, ""),
                        }

                    question = Question(
                        id=item["id"],
                        question=item["question"],
                        options=json.dumps(item["options"])
                        if isinstance(item["options"], list)
                        else item["options"],
                        correct=item["correct"],
                        category=item["category"],
                        difficulty=item.get("difficulty", "medium"),
                        question_type=item.get("question_type", "general"),
                        state=item.get("state"),
                        page_number=item.get("page_number")[0]
                        if isinstance(item.get("page_number"), list)
                        and item.get("page_number")
                        else item.get("page_number"),
                        is_image_question=1
                        if bool(item.get("is_image_question"))
                        else 0,
                        images_data=json.dumps(item.get("images", [])),
                        multilingual_answers=json.dumps(multilingual_answers),
                        rag_sources=json.dumps(item.get("rag_sources", [])),
                    )
                elif "answers" in item:  # New Phase 1.8 format
                    question = Question(
                        id=item["id"],
                        question=item["question"],
                        options=json.dumps(item["options"])
                        if isinstance(item["options"], list)
                        else item["options"],
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
                session.flush()  # Force the question to be written before learning data

                # Initialize FSRS card for new question
                now = datetime.now(UTC).timestamp()
                fsrs_card = FSRSCard(
                    question_id=item["id"],
                    user_id=1,
                    difficulty=5.0,  # Default initial difficulty
                    stability=1.0,  # Default initial stability
                    retrievability=1.0,  # Perfect initial retrievability
                    state=0,  # New card state
                    next_review_date=now,  # New cards are immediately available for study
                )
                session.add(fsrs_card)

            # Update category progress
            categories = {item["category"] for item in questions_data}
            for category in categories:
                count = sum(
                    1 for item in questions_data if item["category"] == category
                )
                cat_progress = CategoryProgress(
                    category=category,
                    total_questions=count,
                )
                session.add(cat_progress)

            session.commit()
            logger.info(f"Loaded {len(questions_data)} questions")
            return len(questions_data)

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
        """Get questions that have failed and need review.

        This method finds questions that the user has answered incorrectly
        and need to be reviewed again. It looks for:
        - Questions with lapse_count > 0 (have been failed)
        - Questions in RELEARNING state (failed from review state)

        Args:
            limit: Maximum number of questions to return.

        Returns:
            List of questions that have failed and need review.
        """
        with self.get_session() as session:
            from sqlalchemy import or_

            from src.domain.shared.models import FSRSState

            return (
                session.query(Question)
                .join(FSRSCard)
                .filter(
                    or_(
                        FSRSCard.lapse_count > 0,  # Questions that have been failed
                        FSRSCard.state
                        == FSRSState.RELEARNING.value,  # Questions currently relearning
                    )
                )
                .order_by(FSRSCard.lapse_count.desc())  # Most failed questions first
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
            session.commit()

    def create_session(self, mode: str, user_id: int = 1) -> int:
        """Create a new practice session.

        Args:
            mode: Practice mode.
            user_id: User ID for multi-user support.

        Returns:
            Session ID.
        """
        with self.get_session() as session:
            practice_session = PracticeSession(
                mode=mode, user_id=user_id, status="active"
            )
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

            # Count questions by learning status using FSRS cards
            now = datetime.now(UTC).timestamp()
            fsrs_cards = session.query(FSRSCard).all()

            for card in fsrs_cards:
                # Map FSRS states to learning statistics
                if card.state == 0:  # New
                    stats.total_new += 1
                elif card.state == 1:  # Learning
                    stats.total_learning += 1
                elif card.state == 2:  # Review (mastered)
                    stats.total_mastered += 1

                # Check if card is due for review
                if card.next_review_date and card.next_review_date <= now:
                    stats.overdue_count += 1
                elif (
                    card.next_review_date and card.next_review_date <= now + 86400
                ):  # 24 hours
                    stats.next_review_count += 1

            # Calculate average easiness from FSRS difficulty
            if fsrs_cards:
                avg_difficulty = sum(card.difficulty for card in fsrs_cards) / len(
                    fsrs_cards
                )
                # Convert difficulty (1-10) to easiness factor equivalent
                stats.average_easiness = max(
                    1.3, float(3.5 - (avg_difficulty - 5.0) * 0.2)
                )

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
            session.query(
                FSRSCard
            ).delete()  # Use FSRS cards instead of legacy LearningData
            session.query(ReviewHistory).delete()  # Clear FSRS review history
            session.query(UserProgress).delete()
            session.query(CategoryProgress).update(
                {
                    CategoryProgress.questions_seen: 0,
                    CategoryProgress.correct_answers: 0,
                    CategoryProgress.average_time: 0.0,
                    CategoryProgress.last_practiced: None,
                }
            )

            # Reinitialize FSRS cards for all questions
            questions = session.query(Question).all()
            now = datetime.now(UTC).timestamp()
            for question in questions:
                fsrs_card = FSRSCard(
                    question_id=question.id,
                    user_id=1,
                    difficulty=5.0,  # Default initial difficulty
                    stability=1.0,  # Default initial stability
                    retrievability=1.0,  # Perfect initial retrievability
                    state=0,  # New card state
                    next_review_date=now,  # New cards are immediately available for study
                )
                session.add(fsrs_card)

            session.commit()
            logger.info("Progress reset successfully")

    def get_user_setting(self, key: str, default: Any = None) -> Any:
        """Get a user setting value (legacy compatibility method).

        Args:
            key: Setting key.
            default: Default value if setting not found.

        Returns:
            Default value (for backward compatibility during migration).

        Note:
            This method is deprecated. Use User domain services for new code.
            During migration, this returns sensible defaults.
        """
        # Provide backward compatibility with reasonable defaults
        defaults = {
            "preferred_language": "en",
            "show_explanations": True,
            "multilingual_mode": True,
            "image_descriptions": True,
        }

        if key in defaults:
            return defaults[key]

        logger.info(
            f"get_user_setting called for unknown key: {key}, returning default: {default}"
        )
        return default

    def set_user_setting(self, key: str, value: Any) -> None:
        """Set a user setting value using new User domain.

        Args:
            key: Setting key.
            value: Setting value.

        Note:
            This method provides backward compatibility with the old API.
            For new code, use the User domain services directly.
        """
        logger.warning(
            f"set_user_setting is deprecated. Use User domain services instead. "
            f"Attempted to set {key}={value}"
        )
        # For backward compatibility during migration, we'll just log and skip
        # The proper way is to use SaveUserSettings domain service

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

            # Initialize FSRS cards for questions without cards
            questions_without_cards = (
                session.query(Question)
                .outerjoin(FSRSCard, Question.id == FSRSCard.question_id)
                .filter(FSRSCard.question_id.is_(None))
                .all()
            )

            for question in questions_without_cards:
                # Create new FSRS card with default initial state
                fsrs_card = FSRSCard(
                    question_id=question.id,
                    user_id=1,
                    difficulty=5.0,  # Default initial difficulty
                    stability=1.0,  # Default initial stability
                    retrievability=1.0,  # Perfect initial retrievability
                    state=0,  # New card state
                )
                session.add(fsrs_card)

            # Initialize default algorithm config if it doesn't exist
            config = session.query(AlgorithmConfig).filter_by(user_id=1).first()
            if not config:
                from src.domain.learning.models.learning_models import FSRSParameters

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

    def migrate_practice_sessions_schema(self) -> None:
        """Migrate practice_sessions table to include missing columns.

        This method adds missing columns that were added in later versions:
        - user_id: for multi-user support
        - status: session status (active, paused, completed)
        - pause_start_time: when session was paused
        - total_pause_duration: total pause time in seconds
        - new_cards_count: count of new cards in session
        - review_cards_count: count of review cards in session
        """
        logger.info("Starting practice_sessions schema migration")

        # Use raw SQL for schema changes
        with self.engine.connect() as conn:
            # Check which columns are missing
            from sqlalchemy import text

            result = conn.execute(text("PRAGMA table_info(practice_sessions)"))
            existing_columns = {row[1] for row in result}

            required_columns = {
                "user_id": "INTEGER NOT NULL DEFAULT 1",
                "status": 'VARCHAR(20) NOT NULL DEFAULT "active"',
                "pause_start_time": "DATETIME",
                "total_pause_duration": "INTEGER DEFAULT 0",
                "new_cards_count": "INTEGER DEFAULT 0",
                "review_cards_count": "INTEGER DEFAULT 0",
            }

            # Add missing columns one by one
            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE practice_sessions ADD COLUMN {column_name} {column_def}"
                            )
                        )
                        logger.info(
                            f"Added column {column_name} to practice_sessions table"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add column {column_name}: {e}")

            conn.commit()

        logger.info("Practice sessions schema migration completed")

    def migrate_user_configuration_schema(self) -> None:
        """Migrate user_configuration table to include missing columns.

        This method adds missing columns that were added in later versions:
        - federal_state: user's federal state preference for questions
        """
        logger.info("Starting user_configuration schema migration")

        # Use raw SQL for schema changes
        with self.engine.connect() as conn:
            # Check which columns are missing
            from sqlalchemy import text

            result = conn.execute(text("PRAGMA table_info(user_configuration)"))
            existing_columns = {row[1] for row in result}

            required_columns = {
                "federal_state": 'VARCHAR(50) NOT NULL DEFAULT "general"',
            }

            # Add missing columns one by one
            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE user_configuration ADD COLUMN {column_name} {column_def}"
                            )
                        )
                        logger.info(
                            f"Added column {column_name} to user_configuration table"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add column {column_name}: {e}")

            conn.commit()

        logger.info("User configuration schema migration completed")

    def ensure_all_questions_have_fsrs_cards(self) -> int:
        """Ensure all questions have corresponding FSRS cards.

        This is a helper method to fix databases where FSRS cards are missing.

        Returns:
            Number of FSRS cards created
        """
        with self.get_session() as session:
            # Find questions without FSRS cards
            questions_without_cards = (
                session.query(Question)
                .outerjoin(FSRSCard, Question.id == FSRSCard.question_id)
                .filter(FSRSCard.question_id.is_(None))
                .all()
            )

            created_count = 0
            now = datetime.now(UTC).timestamp()

            for question in questions_without_cards:
                # Create new FSRS card
                fsrs_card = FSRSCard(
                    question_id=question.id,
                    user_id=1,
                    difficulty=5.0,  # Default initial difficulty
                    stability=1.0,  # Default initial stability
                    retrievability=1.0,  # Perfect initial retrievability
                    state=0,  # New card state
                    next_review_date=now,  # Immediately available
                    created_at=now,
                    updated_at=now,
                    last_review_date=None,
                    review_count=0,
                    lapse_count=0,
                )
                session.add(fsrs_card)
                created_count += 1

            if created_count > 0:
                session.commit()
                logger.info(
                    f"Created {created_count} FSRS cards for existing questions"
                )

            return created_count

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
                review_count=0,  # Initial review count
                lapse_count=0,  # Initial lapse count
                success_count=0,  # Initial success count
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

    def count_due_fsrs_cards(self, user_id: int = 1) -> int:
        """Count FSRS cards due for review.

        Args:
            user_id: User ID

        Returns:
            Number of due cards
        """
        now = datetime.now(UTC).timestamp()

        with self.get_session() as session:
            return (
                session.query(FSRSCard)
                .filter(FSRSCard.user_id == user_id, FSRSCard.next_review_date <= now)
                .count()
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

    def get_cards_by_lapse_threshold(
        self, user_id: int = 1, threshold: int = 8
    ) -> list[FSRSCard]:
        """Get cards that meet a lapse threshold (pure data access).

        Args:
            user_id: User ID
            threshold: Lapse threshold

        Returns:
            List of cards meeting threshold
        """
        with self.get_session() as session:
            return (
                session.query(FSRSCard)
                .filter(FSRSCard.user_id == user_id, FSRSCard.lapse_count >= threshold)
                .all()
            )

    def save_leech_card(self, leech_card: LeechCard) -> None:
        """Save a leech card to database (pure data access).

        Args:
            leech_card: Leech card to save
        """
        with self.get_session() as session:
            session.add(leech_card)
            session.commit()

    def get_existing_leech_card(self, card_id: int) -> LeechCard | None:
        """Get existing leech card by card ID (pure data access).

        Args:
            card_id: Card ID

        Returns:
            Existing leech card if found
        """
        with self.get_session() as session:
            return session.query(LeechCard).filter_by(card_id=card_id).first()

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

            # Note: Retention rate calculation moved to analytics domain service
            stats["retention_rate"] = (
                0.0  # Default value, should be calculated in domain service
            )

            return stats

    def get_recent_review_history(
        self, user_id: int = 1, days: int = 30
    ) -> list[ReviewHistory]:
        """Get recent review history for analytics (pure data access).

        Args:
            user_id: User ID
            days: Number of days back to retrieve

        Returns:
            List of recent review history records
        """
        with self.get_session() as session:
            now = datetime.now(UTC).timestamp()
            cutoff_date = now - (days * 24 * 60 * 60)  # Convert days to seconds

            return (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    ReviewHistory.review_date >= cutoff_date,
                )
                .all()
            )

    def get_fsrs_card_by_id(self, card_id: int) -> FSRSCard | None:
        """Get FSRS card by ID.

        Args:
            card_id: Card ID

        Returns:
            FSRS card or None if not found
        """
        with self.get_session() as session:
            return session.query(FSRSCard).filter_by(card_id=card_id).first()

    def get_session_count(self, user_id: int = 1) -> int:  # noqa: ARG002
        """Get total number of completed practice sessions.

        Args:
            user_id: User ID (currently unused, for future multi-user support)

        Returns:
            Total number of completed sessions
        """
        with self.get_session() as session:
            return (
                session.query(PracticeSession)
                .filter(PracticeSession.ended_at.isnot(None))
                .count()
            )

    def get_session_statistics(self, user_id: int = 1) -> dict[str, Any]:  # noqa: ARG002
        """Get comprehensive session statistics.

        Args:
            user_id: User ID (currently unused, for future multi-user support)

        Returns:
            Session statistics including count, average duration, total time
        """
        with self.get_session() as session:
            # Get all completed sessions
            completed_sessions = (
                session.query(PracticeSession)
                .filter(PracticeSession.ended_at.isnot(None))
                .all()
            )

            if not completed_sessions:
                return {
                    "total_sessions": 0,
                    "avg_duration": 0,
                    "total_time": 0,
                    "total_questions": 0,
                    "total_correct": 0,
                }

            # Calculate statistics
            total_sessions = len(completed_sessions)
            total_duration = 0
            total_questions = 0
            total_correct = 0

            for session in completed_sessions:
                if session.started_at and session.ended_at:
                    duration = (session.ended_at - session.started_at).total_seconds()
                    total_duration += duration

                if session.total_questions:
                    total_questions += session.total_questions
                if session.correct_answers:
                    total_correct += session.correct_answers

            avg_duration = total_duration / total_sessions if total_sessions > 0 else 0

            return {
                "total_sessions": total_sessions,
                "avg_duration": avg_duration,  # seconds
                "total_time": total_duration,  # seconds
                "total_questions": total_questions,
                "total_correct": total_correct,
            }

    def update_session_status(self, session_id: int, status: str) -> None:
        """Update the status of a session.

        Args:
            session_id: Session ID to update
            status: New status (active, paused, completed)
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if practice_session:
                practice_session.status = status
                session.commit()

    def start_session_pause(self, session_id: int) -> None:
        """Start pause tracking for a session.

        Args:
            session_id: Session ID to pause
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if practice_session:
                practice_session.status = "paused"
                practice_session.pause_start_time = datetime.now(UTC).replace(
                    tzinfo=None
                )
                session.commit()

    def end_session_pause(self, session_id: int) -> int:
        """End pause tracking for a session and return pause duration.

        Args:
            session_id: Session ID to resume

        Returns:
            Pause duration in seconds
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if practice_session and practice_session.pause_start_time:
                pause_duration = int(
                    (
                        datetime.now(UTC).replace(tzinfo=None)
                        - practice_session.pause_start_time
                    ).total_seconds()
                )
                practice_session.total_pause_duration += pause_duration
                practice_session.status = "active"
                practice_session.pause_start_time = None
                session.commit()
                return pause_duration
            return 0

    def get_session_pause_duration(self, session_id: int) -> int:
        """Get total pause duration for a session.

        Args:
            session_id: Session ID

        Returns:
            Total pause duration in seconds
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if practice_session:
                return practice_session.total_pause_duration or 0
            return 0

    def update_session_card_counts(
        self, session_id: int, new_cards: int, review_cards: int
    ) -> None:
        """Update new and review card counts for a session.

        Args:
            session_id: Session ID
            new_cards: Number of new cards learned
            review_cards: Number of review cards completed
        """
        with self.get_session() as session:
            practice_session = (
                session.query(PracticeSession).filter_by(id=session_id).first()
            )
            if practice_session:
                practice_session.new_cards_count = new_cards
                practice_session.review_cards_count = review_cards
                session.commit()

    # ============================================================================
    # Performance Optimization Methods
    # ============================================================================

    def _create_indexes(self) -> None:
        """Create database indexes for better query performance."""
        with self.engine.begin() as conn:
            indexes = [
                # Question indexes
                ("idx_questions_category", "questions", "category"),
                ("idx_questions_state", "questions", "state"),
                ("idx_questions_type_state", "questions", "question_type, state"),
                ("idx_questions_image", "questions", "is_image_question"),
                # FSRS card indexes
                (
                    "idx_fsrs_cards_user_review",
                    "fsrs_cards",
                    "user_id, next_review_date",
                ),
                ("idx_fsrs_cards_question_user", "fsrs_cards", "question_id, user_id"),
                # Session indexes
                ("idx_sessions_user_status", "practice_sessions", "user_id, status"),
                ("idx_sessions_started", "practice_sessions", "started_at"),
                # Question attempts index
                ("idx_attempts_session", "question_attempts", "session_id"),
                ("idx_attempts_question", "question_attempts", "question_id"),
                # User settings index
                ("idx_user_settings_user", "user_settings", "user_id"),
            ]

            for index_name, table_name, columns in indexes:
                try:
                    conn.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
                        )
                    )
                except Exception as e:
                    # Table might not exist yet, which is fine
                    logger.debug(f"Could not create index {index_name}: {e}")

            logger.info("Database indexes created/verified")

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session for high-performance operations.

        Yields:
            Async database session
        """
        if not self.async_session_maker:
            raise RuntimeError(
                "Async support not enabled. Initialize with enable_async=True"
            )

        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def analyze_database(self) -> None:
        """Run ANALYZE to update SQLite query planner statistics."""
        with self.engine.begin() as conn:
            conn.execute(text("ANALYZE"))
            logger.info("Database statistics updated")

    def vacuum_database(self) -> None:
        """Vacuum database to reclaim space and optimize structure."""
        # Note: VACUUM cannot be run within a transaction
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
            logger.info("Database vacuumed")

    def get_database_stats(self) -> dict[str, Any]:
        """Get database performance statistics.

        Returns:
            Dictionary of database statistics
        """
        stats = {}

        with self.engine.begin() as conn:
            # Get page count and size
            result = conn.execute(text("PRAGMA page_count"))
            page_count = result.scalar()

            result = conn.execute(text("PRAGMA page_size"))
            page_size = result.scalar()

            # Get cache statistics
            result = conn.execute(text("PRAGMA cache_size"))
            cache_size = result.scalar()

            # Get table sizes
            result = conn.execute(
                text(
                    """
                    SELECT
                        name as table_name,
                        SUM(pgsize) as size_bytes
                    FROM dbstat
                    GROUP BY name
                    ORDER BY size_bytes DESC
                    """
                )
            )
            table_sizes = {row[0]: row[1] for row in result}

            stats.update(
                {
                    "database_size_mb": round(
                        (page_count * page_size) / 1024 / 1024, 2
                    ),
                    "page_count": page_count,
                    "page_size": page_size,
                    "cache_pages": abs(cache_size),  # Negative means KB
                    "table_sizes": table_sizes,
                }
            )

        return stats

    def optimize_query(self, query: str) -> list[dict[str, Any]]:
        """Analyze query execution plan for optimization.

        Args:
            query: SQL query to analyze

        Returns:
            Query execution plan
        """
        with self.engine.begin() as conn:
            result = conn.execute(text(f"EXPLAIN QUERY PLAN {query}"))
            plan = [dict(row._mapping) for row in result]
            return plan
