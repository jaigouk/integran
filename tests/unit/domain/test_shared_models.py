"""Tests for shared domain models."""

from __future__ import annotations

import pytest

from src.domain.shared.models import AnswerStatus, Base


class TestAnswerStatus:
    """Test AnswerStatus enum."""

    def test_answer_status_values(self) -> None:
        """Test AnswerStatus enum values."""
        assert AnswerStatus.CORRECT == "correct"
        assert AnswerStatus.INCORRECT == "incorrect"
        assert AnswerStatus.SKIPPED == "skipped"

    def test_answer_status_from_string(self) -> None:
        """Test creating AnswerStatus from string."""
        assert AnswerStatus("correct") == AnswerStatus.CORRECT
        assert AnswerStatus("incorrect") == AnswerStatus.INCORRECT
        assert AnswerStatus("skipped") == AnswerStatus.SKIPPED

    def test_answer_status_invalid_value(self) -> None:
        """Test invalid AnswerStatus value raises error."""
        with pytest.raises(ValueError):
            AnswerStatus("invalid")

    def test_answer_status_equality(self) -> None:
        """Test AnswerStatus equality comparison."""
        assert AnswerStatus.CORRECT == AnswerStatus.CORRECT
        assert AnswerStatus.CORRECT != AnswerStatus.INCORRECT
        assert AnswerStatus.INCORRECT != AnswerStatus.SKIPPED

    def test_answer_status_string_representation(self) -> None:
        """Test AnswerStatus string representation."""
        assert str(AnswerStatus.CORRECT) == "correct"
        assert str(AnswerStatus.INCORRECT) == "incorrect"
        assert str(AnswerStatus.SKIPPED) == "skipped"

    def test_answer_status_membership(self) -> None:
        """Test membership testing."""
        valid_statuses = [
            AnswerStatus.CORRECT,
            AnswerStatus.INCORRECT,
            AnswerStatus.SKIPPED,
        ]

        for status in valid_statuses:
            assert status in AnswerStatus

        # Test all enum members
        assert len(list(AnswerStatus)) == 3


class TestBase:
    """Test Base model class."""

    def test_base_imports(self) -> None:
        """Test that Base can be imported."""
        assert Base is not None

        # Check it has expected SQLAlchemy attributes
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_base_is_declarative_base(self) -> None:
        """Test Base is a SQLAlchemy declarative base."""
        # Base should have these declarative base attributes
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

        # Should be able to create subclasses
        from sqlalchemy import Column, Integer, String

        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        assert TestModel.__tablename__ == "test_model"
        assert hasattr(TestModel, "id")
        assert hasattr(TestModel, "name")

    def test_table_creation_metadata(self) -> None:
        """Test that tables can be created from metadata."""
        from sqlalchemy import Column, Integer, String, create_engine

        # Create test model
        class TestModel(Base):
            __tablename__ = "test_metadata_model"
            id = Column(Integer, primary_key=True)
            value = Column(String(100))

        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Should be able to create tables
        Base.metadata.create_all(engine)

        # Verify table exists in metadata
        assert "test_metadata_model" in Base.metadata.tables

    def test_multiple_model_inheritance(self) -> None:
        """Test multiple models can inherit from Base."""
        from sqlalchemy import Boolean, Column, Integer, String

        class ModelA(Base):
            __tablename__ = "model_a"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        class ModelB(Base):
            __tablename__ = "model_b"
            id = Column(Integer, primary_key=True)
            active = Column(Boolean, default=True)

        # Both should be valid models
        assert ModelA.__tablename__ == "model_a"
        assert ModelB.__tablename__ == "model_b"

        # Should have different table names
        assert ModelA.__tablename__ != ModelB.__tablename__

        # Both should inherit from Base
        assert issubclass(ModelA, Base)
        assert issubclass(ModelB, Base)

    def test_registry_access(self) -> None:
        """Test registry access on Base."""
        assert Base.registry is not None

        # Registry should have mappers
        assert hasattr(Base.registry, "_class_registry")

        # Should be able to access metadata through registry
        assert Base.registry.metadata is Base.metadata
