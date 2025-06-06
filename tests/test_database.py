"""Tests for database module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from src.core.database import DatabaseManager
from src.core.models import (
    AnswerStatus,
    CategoryProgress,
    LearningData,
    PracticeMode,
    Question,
    QuestionAttempt,
    UserProgress,
)


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
            assert learning.next_review > datetime.utcnow()

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
                learning.next_review = datetime.utcnow() + timedelta(days=7)
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
