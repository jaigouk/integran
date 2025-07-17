"""SQLAlchemy database models for the infrastructure layer."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, relationship

from src.domain.shared.models import Base


class UserDB(Base):
    """User database model."""

    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = Column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = Column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_active: Mapped[datetime] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    study_streak: Mapped[int] = Column(Integer, default=0)
    is_active: Mapped[bool] = Column(Boolean, default=True)

    # Relationships
    learning_progress = relationship("LearningProgressDB", back_populates="user")
    sessions = relationship("SessionDB", back_populates="user")


class LearningProgressDB(Base):
    """Learning progress database model."""

    __tablename__ = "learning_progress"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = Column(Integer, nullable=False)

    # FSRS parameters
    difficulty: Mapped[float] = Column(Float, default=2.5)
    stability: Mapped[float] = Column(Float, default=1.0)
    last_reviewed: Mapped[datetime | None] = Column(
        DateTime(timezone=True), nullable=True
    )
    next_review: Mapped[datetime | None] = Column(
        DateTime(timezone=True), nullable=True
    )

    # Progress tracking
    repetitions: Mapped[int] = Column(Integer, default=0)
    lapses: Mapped[int] = Column(Integer, default=0)
    state: Mapped[str] = Column(String(20), default="New")

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user = relationship("UserDB", back_populates="learning_progress")


class SessionDB(Base):
    """Practice session database model."""

    __tablename__ = "sessions"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session info
    started_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = Column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int] = Column(Integer, default=0)

    # Performance metrics
    total_questions: Mapped[int] = Column(Integer, default=0)
    correct_answers: Mapped[int] = Column(Integer, default=0)
    incorrect_answers: Mapped[int] = Column(Integer, default=0)

    # Session type
    practice_mode: Mapped[str] = Column(String(50), default="random")
    is_completed: Mapped[bool] = Column(Boolean, default=False)

    # Relationships
    user = relationship("UserDB", back_populates="sessions")


class BookmarkModel(Base):
    """Bookmark database model."""

    __tablename__ = "bookmarks"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = Column(Integer, nullable=False)
    notes: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="_user_question_bookmark_uc"),
        Index("idx_user_bookmarks", "user_id", "created_at"),
        Index("idx_bookmark_question", "question_id"),
    )
