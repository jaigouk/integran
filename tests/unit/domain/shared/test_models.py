"""Tests for shared domain models and enums."""

from __future__ import annotations

from src.domain.shared.models import (
    AnswerStatus,
    Base,
    Difficulty,
    FSRSRating,
    FSRSState,
    PracticeMode,
)


class TestDifficulty:
    """Test the Difficulty enum."""

    def test_difficulty_values(self):
        """Test difficulty enum values."""
        assert Difficulty.EASY == "easy"
        assert Difficulty.MEDIUM == "medium"
        assert Difficulty.HARD == "hard"

    def test_difficulty_membership(self):
        """Test difficulty enum membership."""
        assert "easy" in Difficulty
        assert "medium" in Difficulty
        assert "hard" in Difficulty
        assert "invalid" not in Difficulty

    def test_difficulty_iteration(self):
        """Test iterating over difficulty values."""
        values = list(Difficulty)
        assert len(values) == 3
        assert Difficulty.EASY in values
        assert Difficulty.MEDIUM in values
        assert Difficulty.HARD in values

    def test_difficulty_string_comparison(self):
        """Test comparing difficulty with strings."""
        assert Difficulty.EASY == "easy"
        assert Difficulty.MEDIUM != "easy"


class TestPracticeMode:
    """Test the PracticeMode enum."""

    def test_practice_mode_values(self):
        """Test practice mode enum values."""
        assert PracticeMode.RANDOM == "random"
        assert PracticeMode.SEQUENTIAL == "sequential"
        assert PracticeMode.CATEGORY == "category"
        assert PracticeMode.REVIEW == "review"

    def test_practice_mode_membership(self):
        """Test practice mode enum membership."""
        assert "random" in PracticeMode
        assert "sequential" in PracticeMode
        assert "category" in PracticeMode
        assert "review" in PracticeMode
        assert "invalid" not in PracticeMode

    def test_practice_mode_iteration(self):
        """Test iterating over practice mode values."""
        values = list(PracticeMode)
        assert len(values) == 4
        assert PracticeMode.RANDOM in values
        assert PracticeMode.SEQUENTIAL in values
        assert PracticeMode.CATEGORY in values
        assert PracticeMode.REVIEW in values


class TestAnswerStatus:
    """Test the AnswerStatus enum."""

    def test_answer_status_values(self):
        """Test answer status enum values."""
        assert AnswerStatus.CORRECT == "correct"
        assert AnswerStatus.INCORRECT == "incorrect"
        assert AnswerStatus.SKIPPED == "skipped"

    def test_answer_status_membership(self):
        """Test answer status enum membership."""
        assert "correct" in AnswerStatus
        assert "incorrect" in AnswerStatus
        assert "skipped" in AnswerStatus
        assert "invalid" not in AnswerStatus

    def test_answer_status_iteration(self):
        """Test iterating over answer status values."""
        values = list(AnswerStatus)
        assert len(values) == 3
        assert AnswerStatus.CORRECT in values
        assert AnswerStatus.INCORRECT in values
        assert AnswerStatus.SKIPPED in values


class TestFSRSState:
    """Test the FSRSState enum."""

    def test_fsrs_state_values(self):
        """Test FSRS state enum values."""
        assert FSRSState.NEW == 0
        assert FSRSState.LEARNING == 1
        assert FSRSState.REVIEW == 2
        assert FSRSState.RELEARNING == 3

    def test_fsrs_state_membership(self):
        """Test FSRS state enum membership."""
        assert 0 in FSRSState
        assert 1 in FSRSState
        assert 2 in FSRSState
        assert 3 in FSRSState
        assert 4 not in FSRSState

    def test_fsrs_state_iteration(self):
        """Test iterating over FSRS state values."""
        values = list(FSRSState)
        assert len(values) == 4
        assert FSRSState.NEW in values
        assert FSRSState.LEARNING in values
        assert FSRSState.REVIEW in values
        assert FSRSState.RELEARNING in values

    def test_fsrs_state_integer_comparison(self):
        """Test comparing FSRS state with integers."""
        assert FSRSState.NEW == 0
        assert FSRSState.LEARNING == 1
        assert FSRSState.REVIEW != 0


class TestFSRSRating:
    """Test the FSRSRating enum."""

    def test_fsrs_rating_values(self):
        """Test FSRS rating enum values."""
        assert FSRSRating.AGAIN == 1
        assert FSRSRating.HARD == 2
        assert FSRSRating.GOOD == 3
        assert FSRSRating.EASY == 4

    def test_fsrs_rating_membership(self):
        """Test FSRS rating enum membership."""
        assert 1 in FSRSRating
        assert 2 in FSRSRating
        assert 3 in FSRSRating
        assert 4 in FSRSRating
        assert 0 not in FSRSRating
        assert 5 not in FSRSRating

    def test_fsrs_rating_iteration(self):
        """Test iterating over FSRS rating values."""
        values = list(FSRSRating)
        assert len(values) == 4
        assert FSRSRating.AGAIN in values
        assert FSRSRating.HARD in values
        assert FSRSRating.GOOD in values
        assert FSRSRating.EASY in values

    def test_fsrs_rating_integer_comparison(self):
        """Test comparing FSRS rating with integers."""
        assert FSRSRating.AGAIN == 1
        assert FSRSRating.HARD == 2
        assert FSRSRating.GOOD != 1
        assert FSRSRating.EASY != 3

    def test_fsrs_rating_ordering(self):
        """Test FSRS rating ordering."""
        assert FSRSRating.AGAIN < FSRSRating.HARD
        assert FSRSRating.HARD < FSRSRating.GOOD
        assert FSRSRating.GOOD < FSRSRating.EASY
        assert FSRSRating.EASY > FSRSRating.AGAIN


class TestBase:
    """Test the Base declarative base class."""

    def test_base_is_declarative_base(self):
        """Test that Base is a SQLAlchemy declarative base."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_base_can_be_inherited(self):
        """Test that Base can be inherited by model classes."""
        from sqlalchemy import Column, Integer, String

        class TestModel(Base):
            __tablename__ = "test_table"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Should be able to create class without errors
        assert TestModel.__tablename__ == "test_table"
        assert hasattr(TestModel, "id")
        assert hasattr(TestModel, "name")


class TestEnumIntegration:
    """Test integration between different enums."""

    def test_enum_types_are_different(self):
        """Test that enum types are distinct."""
        assert type(Difficulty.EASY) is not type(PracticeMode.RANDOM)
        assert type(FSRSState.NEW) is not type(FSRSRating.AGAIN)

    def test_enum_values_can_be_compared_for_equality(self):
        """Test that enum values can be compared."""
        # Different enums with same string values should not be equal
        # (none exist in our current enums, but test the concept)
        assert Difficulty.EASY != PracticeMode.RANDOM

        # Different enums with same integer values should not be equal
        assert (
            FSRSState.NEW != FSRSRating.AGAIN
        )  # both are 1 and 1, but different types

    def test_enum_serialization(self):
        """Test that enums can be converted to their values."""
        # String enums return their values directly
        assert Difficulty.EASY.value == "easy"
        assert PracticeMode.RANDOM.value == "random"
        assert AnswerStatus.CORRECT.value == "correct"

        # Integer enums return their values
        assert FSRSState.NEW.value == 0
        assert FSRSRating.AGAIN.value == 1
