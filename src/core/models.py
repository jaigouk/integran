"""Core data models for Leben in Deutschland trainer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


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


# Pydantic models for data validation
class QuestionData(BaseModel):
    """Question data model for JSON serialization."""

    id: int = Field(..., description="Unique question ID")
    question: str = Field(..., description="Question text")
    options: list[str] = Field(
        ..., description="Answer options", min_length=4, max_length=4
    )
    correct: str = Field(..., description="Correct answer")
    category: str = Field(..., description="Question category")
    difficulty: Difficulty = Field(Difficulty.MEDIUM, description="Question difficulty")

    @field_validator("correct")
    @classmethod
    def correct_in_options(cls, v: str, info) -> str:
        """Ensure correct answer is in options."""
        if (
            hasattr(info, "data")
            and "options" in info.data
            and v not in info.data["options"]
        ):
            raise ValueError("Correct answer must be one of the options")
        return v


# SQLAlchemy models for database
class Question(Base):
    """Question database model."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON serialized
    correct = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False, default=Difficulty.MEDIUM.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="question")
    learning_data = relationship(
        "LearningData", back_populates="question", uselist=False
    )


class QuestionAttempt(Base):
    """Individual question attempt tracking."""

    __tablename__ = "question_attempts"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("practice_sessions.id"), nullable=False)
    status = Column(String(20), nullable=False)
    user_answer = Column(String(500))
    time_taken = Column(Float)  # seconds
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    question = relationship("Question", back_populates="attempts")
    session = relationship("PracticeSession", back_populates="attempts")


class PracticeSession(Base):
    """Practice session tracking."""

    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True)
    mode = Column(String(20), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="session")


class LearningData(Base):
    """Spaced repetition learning data per question."""

    __tablename__ = "learning_data"

    id = Column(Integer, primary_key=True)
    question_id = Column(
        Integer, ForeignKey("questions.id"), unique=True, nullable=False
    )
    repetitions = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)  # SM-2 algorithm
    interval = Column(Integer, default=1)  # days
    next_review = Column(DateTime, default=lambda: datetime.now(UTC))
    last_reviewed = Column(DateTime)

    # Relationships
    question = relationship("Question", back_populates="learning_data")

    __table_args__ = (UniqueConstraint("question_id"),)


class UserProgress(Base):
    """Overall user progress tracking."""

    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True)
    total_questions_seen = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_time_spent = Column(Float, default=0.0)  # seconds
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_practice = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CategoryProgress(Base):
    """Progress tracking per category."""

    __tablename__ = "category_progress"

    id = Column(Integer, primary_key=True)
    category = Column(String(100), unique=True, nullable=False)
    total_questions = Column(Integer, default=0)
    questions_seen = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    average_time = Column(Float, default=0.0)
    last_practiced = Column(DateTime)

    __table_args__ = (UniqueConstraint("category"),)


# Dataclasses for business logic
@dataclass
class QuestionResult:
    """Result of a question attempt."""

    question_id: int
    status: AnswerStatus
    user_answer: str | None = None
    correct_answer: str = ""
    time_taken: float = 0.0
    category: str = ""


@dataclass
class SessionStats:
    """Statistics for a practice session."""

    total_questions: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    skipped: int = 0
    accuracy: float = 0.0
    average_time: float = 0.0
    categories_practiced: list[str] = field(default_factory=list)


@dataclass
class LearningStats:
    """Overall learning statistics."""

    total_mastered: int = 0
    total_learning: int = 0
    total_new: int = 0
    next_review_count: int = 0
    overdue_count: int = 0
    average_easiness: float = 2.5
    study_streak: int = 0
