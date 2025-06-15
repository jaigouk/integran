"""Question and content-related domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.domain.shared.models import Base, Difficulty

# ============================================================================
# Pydantic Models for Data Validation
# ============================================================================


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
    # Enhanced fields for image support and state questions
    question_type: str = Field(
        "general", description="Type: 'general' or 'state_specific'"
    )
    state: str | None = Field(
        None, description="Federal state for state-specific questions"
    )
    page_number: int | None = Field(
        None, description="PDF page number where question appears"
    )
    is_image_question: bool = Field(
        False, description="Whether question includes images"
    )

    # New Phase 1.8 format: Image descriptions with AI vision
    images: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of image objects with path, description, and context",
    )

    # New Phase 1.8 format: Multilingual answers
    answers: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Multilingual answers: {lang: {explanation, why_others_wrong, key_concept, mnemonic}}",
    )

    # RAG sources for enhanced explanations
    rag_sources: list[str] = Field(
        default_factory=list, description="Sources used from RAG system"
    )

    # Legacy fields (deprecated but kept for compatibility)
    image_paths: list[str] = Field(
        default_factory=list,
        description="DEPRECATED: Use images field instead",
    )
    image_mapping: str | None = Field(
        None, description="DEPRECATED: Use images field instead"
    )

    @field_validator("correct")
    @classmethod
    def correct_in_options(cls, v: str, info: ValidationInfo) -> str:
        """Ensure correct answer is in options."""
        if (
            hasattr(info, "data")
            and "options" in info.data
            and v not in info.data["options"]
        ):
            raise ValueError("Correct answer must be one of the options")
        return v


# ============================================================================
# SQLAlchemy Database Models
# ============================================================================


class Question(Base):
    """Question database model with Phase 1.8 multilingual support."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON serialized
    correct = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False, default=Difficulty.MEDIUM.value)

    # Enhanced fields for image support and state questions
    question_type = Column(String(20), nullable=False, default="general")
    state = Column(
        String(100), nullable=True
    )  # Federal state for state-specific questions
    page_number = Column(
        Integer, nullable=True
    )  # PDF page number where question appears
    is_image_question = Column(
        Integer, nullable=False, default=0
    )  # SQLite boolean as int

    # New Phase 1.8 fields: AI-described images
    images_data = Column(Text, nullable=True)  # JSON serialized list of image objects

    # New Phase 1.8 fields: Multilingual answers
    multilingual_answers = Column(
        Text, nullable=True
    )  # JSON serialized multilingual data
    rag_sources = Column(Text, nullable=True)  # JSON serialized list of sources

    # Legacy fields (deprecated but kept for migration compatibility)
    image_paths = Column(Text, nullable=True)  # DEPRECATED: Use images_data
    image_mapping = Column(String(50), nullable=True)  # DEPRECATED: Use images_data

    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

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
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    question = relationship("Question", back_populates="attempts")
    session = relationship("PracticeSession", back_populates="attempts")


class PracticeSession(Base):
    """Practice session tracking."""

    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True)
    mode = Column(String(20), nullable=False)
    started_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    ended_at = Column(DateTime)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    # Relationships
    attempts = relationship("QuestionAttempt", back_populates="session")


class QuestionExplanation(Base):
    """DEPRECATED: AI-generated explanations for questions.

    NOTE: This table is kept for migration compatibility.
    New multilingual explanations are stored in Question.multilingual_answers.
    """

    __tablename__ = "question_explanations"

    id = Column(Integer, primary_key=True)
    question_id = Column(
        Integer, ForeignKey("questions.id"), unique=True, nullable=False
    )
    explanation = Column(Text, nullable=False)
    why_others_wrong = Column(Text, nullable=True)  # JSON serialized dict
    key_concept = Column(Text, nullable=True)
    mnemonic = Column(Text, nullable=True)
    context_sources = Column(Text, nullable=True)  # JSON serialized list
    enhanced_with_rag = Column(
        Integer, nullable=False, default=0
    )  # SQLite boolean as int
    generated_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    __table_args__ = ({"extend_existing": True},)


class UserSettings(Base):
    """User settings and preferences."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)  # JSON serialized value
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    __table_args__ = ({"extend_existing": True},)


# ============================================================================
# Domain Data Classes
# ============================================================================


@dataclass
class ImageInfo:
    """Information about a question image."""

    path: str
    description: str
    context: str


@dataclass
class MultilingualAnswerData:
    """Multilingual answer data for a question."""

    explanation: str
    why_others_wrong: dict[str, str]  # {option: reason}
    key_concept: str
    mnemonic: str | None = None


@dataclass
class QuestionResult:
    """Result of a question attempt."""

    question_id: int
    status: str  # Using string instead of AnswerStatus to avoid circular import
    user_answer: str | None = None
    correct_answer: str = ""
    time_taken: float = 0.0
    category: str = ""
    has_images: bool = False
    selected_language: str = "en"


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
