"""Tests for database module."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from src.domain.analytics.models.analytics_models import (
    CategoryProgress,
    UserProgress,
)
from src.domain.content.models.question_models import Question, QuestionAttempt
from src.domain.learning.models.learning_models import (
    FSRSCard,
    LearningData,
    LearningSession,
    ReviewHistory,
)
from src.domain.shared.models import AnswerStatus, PracticeMode
from src.infrastructure.database.database import DatabaseManager


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def db_manager(temp_db: Path) -> DatabaseManager:
    """Create a database manager with temporary database."""
    return DatabaseManager(temp_db)


@pytest.fixture
def sample_questions() -> list[dict]:
    """Sample questions for testing."""
    return [
        {
            "id": 1,
            "question": "What is the capital of Germany?",
            "options": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
            "correct": "Berlin",
            "category": "Geography",
            "difficulty": "easy",
        },
        {
            "id": 2,
            "question": "When was Germany reunified?",
            "options": ["1989", "1990", "1991", "1992"],
            "correct": "1990",
            "category": "History",
            "difficulty": "medium",
        },
        {
            "id": 3,
            "question": "What is the German word for 'freedom'?",
            "options": ["Freiheit", "Einheit", "Gerechtigkeit", "Gleichheit"],
            "correct": "Freiheit",
            "category": "Language",
            "difficulty": "easy",
        },
    ]


class TestDatabaseManager:
    """Test DatabaseManager class."""

    def test_initialization(self, db_manager: DatabaseManager) -> None:
        """Test database manager initialization."""
        assert db_manager.db_path.exists()
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

    def test_tables_created(self, db_manager: DatabaseManager) -> None:
        """Test all tables are created."""
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "questions",
            "question_attempts",
            "practice_sessions",
            "learning_data",
            "user_progress",
            "category_progress",
        ]

        for table in expected_tables:
            assert table in tables

    def test_load_questions(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test loading questions from JSON file."""
        # Create questions file
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)

        # Load questions
        count = db_manager.load_questions(questions_file)
        assert count == 3

        # Verify questions in database
        with db_manager.get_session() as session:
            questions = session.query(Question).all()
            assert len(questions) == 3

            # Check first question
            q1 = session.query(Question).filter_by(id=1).first()
            assert q1 is not None
            assert q1.question == "What is the capital of Germany?"
            assert json.loads(q1.options) == [
                "Berlin",
                "Munich",
                "Hamburg",
                "Frankfurt",
            ]
            assert q1.correct == "Berlin"
            assert q1.category == "Geography"
            assert q1.difficulty == "easy"

            # Check learning data created
            learning_data = session.query(LearningData).all()
            assert len(learning_data) == 3

            # Check category progress created
            categories = session.query(CategoryProgress).all()
            assert len(categories) == 3
            assert {c.category for c in categories} == {
                "Geography",
                "History",
                "Language",
            }

    def test_load_questions_file_not_found(self, db_manager: DatabaseManager) -> None:
        """Test loading questions with non-existent file."""
        with pytest.raises(FileNotFoundError):
            db_manager.load_questions("non_existent.json")

    def test_get_question(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test getting a specific question."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Get specific question
        question = db_manager.get_question(1)
        assert question is not None
        assert question.id == 1
        assert question.question == "What is the capital of Germany?"

        # Get non-existent question
        question = db_manager.get_question(999)
        assert question is None

    def test_get_questions_by_category(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test getting questions by category."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Get questions by category
        history_questions = db_manager.get_questions_by_category("History")
        assert len(history_questions) == 1
        assert history_questions[0].category == "History"

        # Get questions from non-existent category
        empty_questions = db_manager.get_questions_by_category("NonExistent")
        assert len(empty_questions) == 0

    def test_create_and_end_session(self, db_manager: DatabaseManager) -> None:
        """Test creating and ending a practice session."""
        # Create session
        session_id = db_manager.create_session(PracticeMode.RANDOM.value)
        assert isinstance(session_id, int)
        assert session_id > 0

        # End session without attempts
        stats = db_manager.end_session(session_id)
        assert stats.total_questions == 0
        assert stats.correct_answers == 0
        assert stats.accuracy == 0.0

    def test_record_attempt(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test recording question attempts."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Create session
        session_id = db_manager.create_session(PracticeMode.RANDOM.value)

        # Record attempts
        db_manager.record_attempt(session_id, 1, AnswerStatus.CORRECT, "Berlin", 3.5)
        db_manager.record_attempt(session_id, 2, AnswerStatus.INCORRECT, "1989", 5.0)
        db_manager.record_attempt(session_id, 3, AnswerStatus.SKIPPED, None, 0.0)

        # Verify attempts
        with db_manager.get_session() as session:
            attempts = (
                session.query(QuestionAttempt).filter_by(session_id=session_id).all()
            )
            assert len(attempts) == 3

            # Check first attempt
            attempt1 = attempts[0]
            assert attempt1.question_id == 1
            assert attempt1.status == AnswerStatus.CORRECT.value
            assert attempt1.user_answer == "Berlin"
            assert attempt1.time_taken == 3.5

    def test_learning_data_update(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test spaced repetition learning data updates."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Create session and record correct answer
        session_id = db_manager.create_session(PracticeMode.RANDOM.value)
        db_manager.record_attempt(session_id, 1, AnswerStatus.CORRECT, "Berlin", 3.5)

        # Check learning data updated
        with db_manager.get_session() as session:
            learning = session.query(LearningData).filter_by(question_id=1).first()
            assert learning is not None
            assert learning.repetitions == 1
            assert learning.interval == 1
            assert learning.last_reviewed is not None
            # Compare with a naive datetime since SQLite may store as naive
            now_naive = datetime.now()
            if learning.next_review.tzinfo is None:
                assert learning.next_review > now_naive
            else:
                assert learning.next_review > datetime.now(UTC)

    def test_get_questions_for_review(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test getting questions due for review."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Initially all questions should be due for review
        due_questions = db_manager.get_questions_for_review()
        assert len(due_questions) == 3

        # Update one question's review date to future
        with db_manager.get_session() as session:
            learning = session.query(LearningData).filter_by(question_id=1).first()
            if learning:
                # Use naive datetime since SQLite stores naive datetimes
                learning.next_review = datetime.now() + timedelta(days=7)
                session.commit()

        # Now only 2 questions should be due
        due_questions = db_manager.get_questions_for_review()
        assert len(due_questions) == 2

    def test_session_statistics(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test session statistics calculation."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Create session and record attempts
        session_id = db_manager.create_session(PracticeMode.CATEGORY.value)
        db_manager.record_attempt(session_id, 1, AnswerStatus.CORRECT, "Berlin", 3.5)
        db_manager.record_attempt(session_id, 2, AnswerStatus.CORRECT, "1990", 4.0)
        db_manager.record_attempt(session_id, 3, AnswerStatus.INCORRECT, "Einheit", 6.0)

        # End session and check statistics
        stats = db_manager.end_session(session_id)
        assert stats.total_questions == 3
        assert stats.correct_answers == 2
        assert stats.incorrect_answers == 1
        assert stats.skipped == 0
        assert stats.accuracy == pytest.approx(66.67, 0.1)
        assert stats.average_time == pytest.approx(4.5, 0.1)
        assert set(stats.categories_practiced) == {"Geography", "History", "Language"}

    def test_reset_progress(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test resetting user progress."""
        # Load questions and create some progress
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        session_id = db_manager.create_session(PracticeMode.RANDOM.value)
        db_manager.record_attempt(session_id, 1, AnswerStatus.CORRECT, "Berlin", 3.5)
        db_manager.end_session(session_id)

        # Verify progress exists
        with db_manager.get_session() as session:
            attempts = session.query(QuestionAttempt).all()
            assert len(attempts) > 0

            progress = session.query(UserProgress).first()
            assert progress is not None
            assert progress.total_questions_seen > 0

        # Reset progress
        db_manager.reset_progress()

        # Verify progress cleared
        with db_manager.get_session() as session:
            attempts = session.query(QuestionAttempt).all()
            assert len(attempts) == 0

            progress = session.query(UserProgress).first()
            assert progress is None

            # Learning data should be reinitialized
            learning_data = session.query(LearningData).all()
            assert len(learning_data) == 3
            for ld in learning_data:
                assert ld.repetitions == 0
                assert ld.easiness_factor == 2.5

    def test_get_learning_stats(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test getting overall learning statistics."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Initial stats
        stats = db_manager.get_learning_stats()
        assert stats.total_new == 3
        assert stats.total_learning == 0
        assert stats.total_mastered == 0
        assert stats.overdue_count == 3  # All new questions are due

        # Record some attempts
        session_id = db_manager.create_session(PracticeMode.RANDOM.value)
        db_manager.record_attempt(session_id, 1, AnswerStatus.CORRECT, "Berlin", 3.5)
        db_manager.record_attempt(session_id, 2, AnswerStatus.INCORRECT, "1989", 5.0)

        # Updated stats
        stats = db_manager.get_learning_stats()
        assert (
            stats.total_new == 2
        )  # Question 3 still new, question 2 reset to 0 repetitions
        assert stats.total_learning == 1  # Question 1 only
        assert stats.total_mastered == 0  # None mastered yet

    # ============================================================================
    # FSRS Tests (Phase 3.0)
    # ============================================================================

    def test_migrate_to_fsrs_schema(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test FSRS schema migration."""
        # Load questions first
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)

        # Migrate to FSRS schema
        db_manager.migrate_to_fsrs_schema()

        # Verify FSRS tables exist
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        assert "fsrs_cards" in tables
        assert "review_history" in tables
        assert "learning_sessions" in tables
        assert "algorithm_config" in tables
        assert "categories" in tables

        # Verify algorithm config was created
        config = db_manager.get_algorithm_config()
        assert config is not None
        assert config.target_retention == 0.9

        # Verify categories were populated
        with db_manager.get_session() as session:
            from src.domain.analytics.models.analytics_models import Category

            categories = session.query(Category).all()
            assert len(categories) >= 3  # Geography, History, Language

    def test_fsrs_card_operations(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test FSRS card creation and retrieval."""
        # Load questions and migrate
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create FSRS card
        card = db_manager.create_fsrs_card(question_id=1)
        assert card is not None
        assert card.question_id == 1
        # Note: difficulty may be converted from existing learning data during migration
        assert card.difficulty >= 1.0 and card.difficulty <= 10.0
        assert card.stability >= 0.1
        assert card.retrievability >= 0.0 and card.retrievability <= 1.0

        # Retrieve the same card
        retrieved_card = db_manager.get_fsrs_card(question_id=1)
        assert retrieved_card is not None
        assert retrieved_card.card_id == card.card_id

        # Try to create duplicate (should return existing)
        duplicate_card = db_manager.create_fsrs_card(question_id=1)
        assert duplicate_card.card_id == card.card_id

    def test_fsrs_card_updates(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test FSRS card state updates."""
        # Setup
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create card
        card = db_manager.create_fsrs_card(question_id=1)

        # Update card state
        new_difficulty = 4.5
        new_stability = 2.5
        new_retrievability = 0.9
        new_state = 2  # Review state
        next_review = datetime.now(UTC).timestamp() + 86400  # Tomorrow

        db_manager.update_fsrs_card(
            card.card_id,
            new_difficulty,
            new_stability,
            new_retrievability,
            new_state,
            next_review,
        )

        # Verify updates
        updated_card = db_manager.get_fsrs_card(question_id=1)
        assert updated_card.difficulty == new_difficulty
        assert updated_card.stability == new_stability
        assert updated_card.retrievability == new_retrievability
        assert updated_card.state == new_state
        assert updated_card.next_review_date == next_review
        assert updated_card.review_count == 1

    def test_get_due_fsrs_cards(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test getting due FSRS cards."""
        # Setup
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create cards with different review dates
        card1 = db_manager.create_fsrs_card(question_id=1)
        card2 = db_manager.create_fsrs_card(question_id=2)
        card3 = db_manager.create_fsrs_card(question_id=3)

        now = datetime.now(UTC).timestamp()

        # Set card1 as due, card2 as future, card3 as overdue
        db_manager.update_fsrs_card(card1.card_id, 5.0, 1.0, 1.0, 0, now - 100)  # Due
        db_manager.update_fsrs_card(
            card2.card_id, 5.0, 1.0, 1.0, 0, now + 86400
        )  # Future
        db_manager.update_fsrs_card(
            card3.card_id, 5.0, 1.0, 1.0, 0, now - 86400
        )  # Overdue

        # Get due cards
        due_cards = db_manager.get_due_fsrs_cards(limit=10)
        due_question_ids = [card.question_id for card in due_cards]

        assert 1 in due_question_ids
        assert 3 in due_question_ids
        assert 2 not in due_question_ids

    def test_learning_session_lifecycle(self, db_manager: DatabaseManager) -> None:
        """Test learning session creation and management."""
        db_manager.migrate_to_fsrs_schema()

        # Create learning session
        session_id = db_manager.create_learning_session(
            session_type="review", target_retention=0.85, max_reviews=25
        )
        assert session_id > 0

        # End session
        db_manager.end_learning_session(session_id)

        # Verify session was updated
        with db_manager.get_session() as session:
            learning_session = (
                session.query(LearningSession).filter_by(session_id=session_id).first()
            )
            assert learning_session is not None
            assert learning_session.end_time is not None
            assert learning_session.duration_seconds is not None

    def test_fsrs_review_recording(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test recording FSRS reviews."""
        # Setup
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create card and session
        card = db_manager.create_fsrs_card(question_id=1)
        session_id = db_manager.create_learning_session("review")

        # Record review
        db_manager.record_fsrs_review(
            card_id=card.card_id,
            question_id=1,
            rating=3,  # Good
            response_time_ms=5000,
            difficulty_before=5.0,
            stability_before=1.0,
            retrievability_before=1.0,
            difficulty_after=4.8,
            stability_after=2.5,
            retrievability_after=0.95,
            next_interval_days=2.5,
            session_id=session_id,
        )

        # Verify review was recorded
        with db_manager.get_session() as session:
            review = (
                session.query(ReviewHistory).filter_by(card_id=card.card_id).first()
            )
            assert review is not None
            assert review.rating == 3
            assert review.response_time_ms == 5000
            assert review.difficulty_after == 4.8
            assert review.stability_after == 2.5

    def test_algorithm_config_management(self, db_manager: DatabaseManager) -> None:
        """Test algorithm configuration management."""
        db_manager.migrate_to_fsrs_schema()

        # Update config
        new_parameters = [1.0, 2.0, 3.0] * 7  # 21 parameters (more than needed)
        new_parameters = new_parameters[:19]  # Take only 19
        db_manager.update_algorithm_config(
            user_id=1, parameters=new_parameters, target_retention=0.85
        )

        # Retrieve config
        config = db_manager.get_algorithm_config(user_id=1)
        assert config is not None
        assert config.target_retention == 0.85

        import json

        stored_params = json.loads(config.parameters)
        assert len(stored_params) == 19
        assert stored_params[0] == 1.0

    def test_leech_detection(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test leech card detection."""
        # Setup
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create card with high lapse count
        card = db_manager.create_fsrs_card(question_id=1)

        # Simulate multiple lapses by updating directly
        with db_manager.get_session() as session:
            fsrs_card = session.query(FSRSCard).filter_by(card_id=card.card_id).first()
            fsrs_card.lapse_count = 10  # Above default threshold of 8
            session.commit()

        # Detect leeches
        leeches = db_manager.detect_leech_cards(threshold=8)
        assert len(leeches) == 1
        assert leeches[0].question_id == 1
        assert leeches[0].lapse_count == 10

        # Second detection should not create duplicate
        leeches2 = db_manager.detect_leech_cards(threshold=8)
        assert len(leeches2) == 0  # No new leeches

    def test_fsrs_learning_stats(
        self, db_manager: DatabaseManager, sample_questions: list[dict], tmp_path: Path
    ) -> None:
        """Test FSRS learning statistics."""
        # Setup
        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f)
        db_manager.load_questions(questions_file)
        db_manager.migrate_to_fsrs_schema()

        # Create cards in different states
        db_manager.create_fsrs_card(question_id=1)  # New
        card2 = db_manager.create_fsrs_card(question_id=2)  # Learning
        card3 = db_manager.create_fsrs_card(question_id=3)  # Review

        # Update states
        now = datetime.now(UTC).timestamp()
        db_manager.update_fsrs_card(
            card2.card_id, 5.0, 1.0, 1.0, 1, now + 86400
        )  # Learning
        db_manager.update_fsrs_card(
            card3.card_id, 5.0, 1.0, 1.0, 2, now - 100
        )  # Review (due)

        # Get stats
        stats = db_manager.get_fsrs_learning_stats()
        assert stats["total_cards"] == 3
        assert stats["new_cards"] == 1
        assert stats["learning_cards"] == 1
        assert stats["review_cards"] == 1
        assert stats["due_cards"] == 2  # new card + review card
        assert stats["retention_rate"] == 0.0  # No reviews yet

    def test_get_question_with_multilingual_answers(
        self, db_manager: DatabaseManager, tmp_path: Path
    ) -> None:
        """Test getting questions with multilingual answers."""
        # Create question with multilingual data
        multilingual_question = {
            "id": 1,
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct": "A",
            "category": "Test",
            "answers": {
                "en": {
                    "explanation": "English explanation",
                    "key_concept": "English concept",
                },
                "de": {
                    "explanation": "German explanation",
                    "key_concept": "German concept",
                },
            },
        }

        questions_file = tmp_path / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump([multilingual_question], f)
        db_manager.load_questions(questions_file)

        # Test English (default)
        question_data = db_manager.get_question_with_multilingual_answers(1, "en")
        assert question_data is not None
        assert question_data["answers"]["explanation"] == "English explanation"
        assert "en" in question_data["available_languages"]
        assert "de" in question_data["available_languages"]

        # Test German
        question_data = db_manager.get_question_with_multilingual_answers(1, "de")
        assert question_data["answers"]["explanation"] == "German explanation"

        # Test fallback to English for unsupported language
        question_data = db_manager.get_question_with_multilingual_answers(1, "fr")
        assert question_data["answers"]["explanation"] == "English explanation"
