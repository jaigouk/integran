"""Shared models and base classes for all bounded contexts."""

from __future__ import annotations

from enum import Enum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Difficulty(str, Enum):
    """Question difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PracticeMode(str, Enum):
    """Practice mode types."""

    RANDOM = "random"
    SEQUENTIAL = "sequential"
    CATEGORY = "category"
    REVIEW = "review"


class AnswerStatus(str, Enum):
    """Answer status types."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


class FSRSState(int, Enum):
    """FSRS card learning states."""

    NEW = 0
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3


class FSRSRating(int, Enum):
    """FSRS difficulty ratings."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4
