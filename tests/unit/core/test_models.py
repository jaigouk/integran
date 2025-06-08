"""Tests for core data models."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.core.models import (
    AnswerStatus,
    Difficulty,
    PracticeMode,
    Question,
    QuestionData,
    QuestionResult,
    SessionStats,
)


class TestEnums:
    """Test enum types."""

    def test_difficulty_values(self) -> None:
        """Test difficulty enum values."""
        assert Difficulty.EASY.value == "easy"
        assert Difficulty.MEDIUM.value == "medium"
        assert Difficulty.HARD.value == "hard"

    def test_practice_mode_values(self) -> None:
        """Test practice mode enum values."""
        assert PracticeMode.RANDOM.value == "random"
        assert PracticeMode.SEQUENTIAL.value == "sequential"
        assert PracticeMode.CATEGORY.value == "category"
        assert PracticeMode.REVIEW.value == "review"

    def test_answer_status_values(self) -> None:
        """Test answer status enum values."""
        assert AnswerStatus.CORRECT.value == "correct"
        assert AnswerStatus.INCORRECT.value == "incorrect"
        assert AnswerStatus.SKIPPED.value == "skipped"


class TestQuestionData:
    """Test QuestionData pydantic model."""

    def test_valid_question_data(self) -> None:
        """Test creating valid question data."""
        data = {
            "id": 1,
            "question": "What is the capital of Germany?",
            "options": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
            "correct": "Berlin",
            "category": "Geography",
            "difficulty": "easy",
        }
        question = QuestionData(**data)
        assert question.id == 1
        assert question.question == "What is the capital of Germany?"
        assert len(question.options) == 4
        assert question.correct == "Berlin"
        assert question.category == "Geography"
        assert question.difficulty == Difficulty.EASY

    def test_default_difficulty(self) -> None:
        """Test default difficulty is medium."""
        data = {
            "id": 1,
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct": "A",
            "category": "Test",
        }
        question = QuestionData(**data)
        assert question.difficulty == Difficulty.MEDIUM

    def test_invalid_options_count(self) -> None:
        """Test validation fails with wrong number of options."""
        data = {
            "id": 1,
            "question": "Test question",
            "options": ["A", "B", "C"],  # Only 3 options
            "correct": "A",
            "category": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            QuestionData(**data)
        assert "at least 4 items" in str(exc_info.value) or "too_short" in str(
            exc_info.value
        )

    def test_correct_not_in_options(self) -> None:
        """Test validation fails when correct answer not in options."""
        data = {
            "id": 1,
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct": "E",  # Not in options
            "category": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            QuestionData(**data)
        assert "Correct answer must be one of the options" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        """Test validation fails with missing required fields."""
        data = {
            "id": 1,
            "question": "Test question",
            # Missing options, correct, category
        }
        with pytest.raises(ValidationError):
            QuestionData(**data)


class TestQuestionModel:
    """Test Question SQLAlchemy model."""

    def test_question_creation(self) -> None:
        """Test creating a question instance."""
        question = Question(
            id=1,
            question="Test question",
            options=json.dumps(["A", "B", "C", "D"]),
            correct="A",
            category="Test",
            difficulty="medium",
        )
        assert question.id == 1
        assert question.question == "Test question"
        assert json.loads(question.options) == ["A", "B", "C", "D"]
        assert question.correct == "A"
        assert question.category == "Test"
        assert question.difficulty == "medium"


class TestDataClasses:
    """Test dataclass models."""

    def test_question_result_creation(self) -> None:
        """Test creating a question result."""
        result = QuestionResult(
            question_id=1,
            status=AnswerStatus.CORRECT,
            user_answer="Berlin",
            correct_answer="Berlin",
            time_taken=5.5,
            category="Geography",
        )
        assert result.question_id == 1
        assert result.status == AnswerStatus.CORRECT
        assert result.user_answer == "Berlin"
        assert result.correct_answer == "Berlin"
        assert result.time_taken == 5.5
        assert result.category == "Geography"

    def test_question_result_defaults(self) -> None:
        """Test question result default values."""
        result = QuestionResult(
            question_id=1,
            status=AnswerStatus.SKIPPED,
        )
        assert result.user_answer is None
        assert result.correct_answer == ""
        assert result.time_taken == 0.0
        assert result.category == ""

    def test_session_stats_creation(self) -> None:
        """Test creating session statistics."""
        stats = SessionStats(
            total_questions=10,
            correct_answers=7,
            incorrect_answers=2,
            skipped=1,
            accuracy=70.0,
            average_time=4.5,
            categories_practiced=["Geography", "History"],
        )
        assert stats.total_questions == 10
        assert stats.correct_answers == 7
        assert stats.incorrect_answers == 2
        assert stats.skipped == 1
        assert stats.accuracy == 70.0
        assert stats.average_time == 4.5
        assert len(stats.categories_practiced) == 2

    def test_session_stats_defaults(self) -> None:
        """Test session stats default values."""
        stats = SessionStats()
        assert stats.total_questions == 0
        assert stats.correct_answers == 0
        assert stats.incorrect_answers == 0
        assert stats.skipped == 0
        assert stats.accuracy == 0.0
        assert stats.average_time == 0.0
        assert stats.categories_practiced == []
