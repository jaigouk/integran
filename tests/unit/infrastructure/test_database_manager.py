"""Tests for DatabaseManager infrastructure component."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

from src.infrastructure.database.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest.fixture
    def temp_db_file(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            yield Path(temp_file.name)

    @pytest.fixture
    def db_manager(self, temp_db_file: Path) -> DatabaseManager:
        """Create DatabaseManager with temp database."""
        return DatabaseManager(str(temp_db_file))

    @pytest.fixture
    def questions_data(self) -> list[dict]:
        """Sample questions data."""
        return [
            {
                "id": 1,
                "question": "Test question 1",
                "options": ["A", "B", "C", "D"],
                "correct": "A",
                "category": "Test",
                "difficulty": "easy",
            },
            {
                "id": 2,
                "question": "Test question 2",
                "options": ["X", "Y", "Z", "W"],
                "correct": "Y",
                "category": "Test",
                "difficulty": "medium",
            },
        ]

    def test_initialization_default_path(self) -> None:
        """Test DatabaseManager initialization with default path."""
        db = DatabaseManager()
        assert "data/trainer.db" in str(db.db_path)

    def test_initialization_custom_path(self, temp_db_file: Path) -> None:
        """Test DatabaseManager initialization with custom path."""
        db = DatabaseManager(str(temp_db_file))
        assert str(db.db_path) == str(temp_db_file)

    def test_get_session(self, db_manager: DatabaseManager) -> None:
        """Test getting database session."""
        with db_manager.get_session() as session:
            # Test that session is valid
            assert session is not None

            # Test that tables exist by trying a simple query
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';")
            )
            tables = [row[0] for row in result.fetchall()]

            # Check for some expected tables
            expected_tables = ["questions", "user_settings", "fsrs_cards"]
            for table in expected_tables:
                assert table in tables

    def test_load_questions_from_file(
        self,
        db_manager: DatabaseManager,
        questions_data: list[dict],
        temp_db_file: Path,
    ) -> None:
        """Test loading questions from JSON file."""
        # Create temporary questions file
        questions_file = temp_db_file.parent / "questions.json"
        with open(questions_file, "w") as f:
            json.dump(questions_data, f)

        count = db_manager.load_questions(questions_file)
        assert count == 2

        # Verify questions were loaded
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM questions"))
            db_count = result.fetchone()[0]
            assert db_count == 2

    def test_get_user_setting_existing(self, db_manager: DatabaseManager) -> None:
        """Test getting existing user setting."""
        # First set a setting
        db_manager.set_user_setting("test_key", "test_value")

        # Then get it
        value = db_manager.get_user_setting("test_key")
        assert value == "test_value"

    def test_get_user_setting_nonexistent(self, db_manager: DatabaseManager) -> None:
        """Test getting nonexistent user setting."""
        value = db_manager.get_user_setting("nonexistent_key")
        assert value is None

    def test_set_user_setting(self, db_manager: DatabaseManager) -> None:
        """Test setting user setting."""
        db_manager.set_user_setting("language", "de")

        # Verify it was set
        value = db_manager.get_user_setting("language")
        assert value == "de"

    def test_set_user_setting_updates_existing(
        self, db_manager: DatabaseManager
    ) -> None:
        """Test updating existing user setting."""
        # Set initial value
        db_manager.set_user_setting("theme", "light")
        assert db_manager.get_user_setting("theme") == "light"

        # Update it
        db_manager.set_user_setting("theme", "dark")
        assert db_manager.get_user_setting("theme") == "dark"

    def test_get_questions_for_review(
        self,
        db_manager: DatabaseManager,
        questions_data: list[dict],
        temp_db_file: Path,
    ) -> None:
        """Test getting questions for review."""
        # Load questions first
        questions_file = temp_db_file.parent / "questions.json"
        with open(questions_file, "w") as f:
            json.dump(questions_data, f)
        db_manager.load_questions(questions_file)

        # Get questions for review
        questions = db_manager.get_questions_for_review(limit=1)
        assert len(questions) == 1
        assert questions[0].id in [1, 2]

    def test_get_questions_by_category(
        self,
        db_manager: DatabaseManager,
        questions_data: list[dict],
        temp_db_file: Path,
    ) -> None:
        """Test getting questions by category."""
        # Load questions first
        questions_file = temp_db_file.parent / "questions.json"
        with open(questions_file, "w") as f:
            json.dump(questions_data, f)
        db_manager.load_questions(questions_file)

        # Get questions by category
        questions = db_manager.get_questions_by_category("Test")
        assert len(questions) == 2
        for question in questions:
            assert question.category == "Test"

    def test_create_tables_safe(self, db_manager: DatabaseManager) -> None:
        """Test that create_tables can be called multiple times safely."""
        # This should not raise an error even if called multiple times
        db_manager._create_tables()
        db_manager._create_tables()

    def test_load_questions_empty_list(
        self, db_manager: DatabaseManager, temp_db_file: Path
    ) -> None:
        """Test loading empty questions list."""
        # Create empty questions file
        questions_file = temp_db_file.parent / "questions.json"
        with open(questions_file, "w") as f:
            json.dump([], f)

        count = db_manager.load_questions(questions_file)
        assert count == 0

    def test_load_questions_invalid_file(self, db_manager: DatabaseManager) -> None:
        """Test loading questions from nonexistent file."""
        nonexistent_file = Path("/nonexistent/file.json")

        with pytest.raises(FileNotFoundError):
            db_manager.load_questions(nonexistent_file)

    def test_get_question_by_id(
        self,
        db_manager: DatabaseManager,
        questions_data: list[dict],
        temp_db_file: Path,
    ) -> None:
        """Test getting question by ID."""
        # Load questions first
        questions_file = temp_db_file.parent / "questions.json"
        with open(questions_file, "w") as f:
            json.dump(questions_data, f)
        db_manager.load_questions(questions_file)

        # Get specific question
        question = db_manager.get_question(1)
        assert question is not None
        assert question.id == 1
        assert question.question == "Test question 1"

        # Test nonexistent question
        question = db_manager.get_question(999)
        assert question is None
