"""Tests for bookmark repository implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.domain.shared.repositories import RepositoryError
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.database.models import BookmarkModel
from src.infrastructure.repositories.bookmark_repository import BookmarkRepositoryImpl


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    return MagicMock(spec=DatabaseManager)


@pytest.fixture
def mock_session():
    """Mock sync session."""
    return MagicMock(spec=Session)


@pytest.fixture
def repository(mock_db_manager):
    """Create repository instance."""
    return BookmarkRepositoryImpl(mock_db_manager)


@pytest.fixture
def sample_bookmark_model():
    """Create sample bookmark model."""
    return BookmarkModel(
        id=1,
        user_id=100,
        question_id=42,
        notes="Test notes",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )


@pytest.fixture
def sample_bookmark_entity():
    """Create sample bookmark entity."""
    return Bookmark(
        id=1,
        user_id=100,
        question_id=42,
        notes="Test notes",
        created_at=datetime.now(UTC),
    )


class TestBookmarkRepositoryImpl:
    """Test bookmark repository implementation."""

    pass


class TestAddBookmark:
    """Test add_bookmark method."""

    @pytest.mark.asyncio
    async def test_add_bookmark_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test successful bookmark addition."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock no existing bookmark
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Mock bookmark creation
        _created_bookmark = BookmarkModel(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test notes",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

        with patch.object(repository, "_model_to_entity") as mock_convert:
            expected_entity = Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes="Test notes",
                created_at=datetime.now(UTC),
            )
            mock_convert.return_value = expected_entity

            # Act
            result = await repository.add_bookmark(100, 42, "Test notes")

            # Assert
            assert result == expected_entity
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_bookmark_duplicate_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test adding duplicate bookmark raises error."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock existing bookmark
        existing_bookmark = BookmarkModel(
            id=1,
            user_id=100,
            question_id=42,
            notes="Existing",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            existing_bookmark
        )

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.add_bookmark(100, 42, "Test notes")

        assert "already exists" in str(exc_info.value)
        assert exc_info.value.error_code == "DUPLICATE_BOOKMARK"
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_bookmark_database_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test database error during bookmark addition."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.add_bookmark(100, 42, "Test notes")

        assert "Database error" in str(exc_info.value)
        assert exc_info.value.error_code == "DATABASE_ERROR"

    @pytest.mark.asyncio
    async def test_add_bookmark_without_notes(
        self, repository, mock_db_manager, mock_session
    ):
        """Test adding bookmark without notes."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch.object(repository, "_model_to_entity") as mock_convert:
            expected_entity = Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes=None,
                created_at=datetime.now(UTC),
            )
            mock_convert.return_value = expected_entity

            # Act
            result = await repository.add_bookmark(100, 42)

            # Assert
            assert result == expected_entity
            # Verify the created model has None notes
            call_args = mock_session.add.call_args[0][0]
            assert call_args.notes is None


class TestRemoveBookmark:
    """Test remove_bookmark method."""

    @pytest.mark.asyncio
    async def test_remove_bookmark_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test successful bookmark removal."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock finding existing bookmark
        existing_bookmark = BookmarkModel(id=1, user_id=100, question_id=42)
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            existing_bookmark
        )

        # Act
        result = await repository.remove_bookmark(100, 42)

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(existing_bookmark)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_bookmark_not_found(
        self, repository, mock_db_manager, mock_session
    ):
        """Test removing non-existent bookmark."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Act
        result = await repository.remove_bookmark(100, 42)

        # Assert
        assert result is False
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_bookmark_database_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test database error during bookmark removal."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.side_effect = (
            SQLAlchemyError("Database error")
        )

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.remove_bookmark(100, 42)

        assert "Database error" in str(exc_info.value)
        assert exc_info.value.error_code == "DATABASE_ERROR"


class TestGetBookmarks:
    """Test get_bookmarks method."""

    @pytest.mark.asyncio
    async def test_get_bookmarks_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test successful bookmark retrieval."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock bookmarks and count
        bookmark_models = [
            BookmarkModel(
                id=1,
                user_id=100,
                question_id=42,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
            BookmarkModel(
                id=2,
                user_id=100,
                question_id=43,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
        ]

        # Mock query results
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            bookmark_models
        )
        # Mock count query
        mock_session.execute.return_value.scalar.return_value = 2

        with patch.object(repository, "_model_to_entity") as mock_convert:
            bookmark_entities = [
                Bookmark(
                    id=1, user_id=100, question_id=42, created_at=datetime.now(UTC)
                ),
                Bookmark(
                    id=2, user_id=100, question_id=43, created_at=datetime.now(UTC)
                ),
            ]
            mock_convert.side_effect = bookmark_entities

            # Act
            result = await repository.get_bookmarks(100, limit=10, offset=0)

            # Assert
            assert isinstance(result, BookmarkCollection)
            assert result.user_id == 100
            assert len(result.bookmarks) == 2
            assert result.total_count == 2
            assert result.bookmarks == bookmark_entities

    @pytest.mark.asyncio
    async def test_get_bookmarks_with_pagination(
        self, repository, mock_db_manager, mock_session
    ):
        """Test bookmark retrieval with pagination."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock one bookmark for page 2
        bookmark_models = [
            BookmarkModel(
                id=3,
                user_id=100,
                question_id=44,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            bookmark_models
        )
        mock_session.execute.return_value.scalar.return_value = 25  # Total count

        with patch.object(repository, "_model_to_entity") as mock_convert:
            bookmark_entity = Bookmark(
                id=3, user_id=100, question_id=44, created_at=datetime.now(UTC)
            )
            mock_convert.return_value = bookmark_entity

            # Act
            result = await repository.get_bookmarks(100, limit=10, offset=20)

            # Assert
            assert len(result.bookmarks) == 1
            assert result.total_count == 25
            assert result.bookmarks[0] == bookmark_entity

    @pytest.mark.asyncio
    async def test_get_bookmarks_empty_result(
        self, repository, mock_db_manager, mock_session
    ):
        """Test bookmark retrieval with no results."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0

        # Act
        result = await repository.get_bookmarks(100)

        # Assert
        assert isinstance(result, BookmarkCollection)
        assert result.user_id == 100
        assert len(result.bookmarks) == 0
        assert result.total_count == 0
        assert result.is_empty is True

    @pytest.mark.asyncio
    async def test_get_bookmarks_no_limit(
        self, repository, mock_db_manager, mock_session
    ):
        """Test bookmark retrieval without limit."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        bookmark_models = [
            BookmarkModel(
                id=i,
                user_id=100,
                question_id=40 + i,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            for i in range(1, 6)  # 5 bookmarks
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            bookmark_models
        )
        mock_session.execute.return_value.scalar.return_value = 5

        with patch.object(repository, "_model_to_entity") as mock_convert:
            mock_convert.side_effect = [
                Bookmark(
                    id=i, user_id=100, question_id=40 + i, created_at=datetime.now(UTC)
                )
                for i in range(1, 6)
            ]

            # Act
            result = await repository.get_bookmarks(100, limit=None)

            # Assert
            assert len(result.bookmarks) == 5
            assert result.total_count == 5


class TestIsBookmarked:
    """Test is_bookmarked method."""

    @pytest.mark.asyncio
    async def test_is_bookmarked_true(self, repository, mock_db_manager, mock_session):
        """Test checking bookmark status when bookmarked."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock existing bookmark
        existing_bookmark = BookmarkModel(id=1, user_id=100, question_id=42)
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            existing_bookmark
        )

        # Act
        result = await repository.is_bookmarked(100, 42)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_is_bookmarked_false(self, repository, mock_db_manager, mock_session):
        """Test checking bookmark status when not bookmarked."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Act
        result = await repository.is_bookmarked(100, 42)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_is_bookmarked_database_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test database error during bookmark check."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            await repository.is_bookmarked(100, 42)


class TestGetBookmarkByQuestion:
    """Test get_bookmark_by_question method."""

    @pytest.mark.asyncio
    async def test_get_bookmark_by_question_found(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmark by question when found."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        bookmark_model = BookmarkModel(
            id=1,
            user_id=100,
            question_id=42,
            notes="Test notes",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            bookmark_model
        )

        with patch.object(repository, "_model_to_entity") as mock_convert:
            expected_entity = Bookmark(
                id=1,
                user_id=100,
                question_id=42,
                notes="Test notes",
                created_at=datetime.now(UTC),
            )
            mock_convert.return_value = expected_entity

            # Act
            result = await repository.get_bookmark_by_question(100, 42)

            # Assert
            assert result == expected_entity

    @pytest.mark.asyncio
    async def test_get_bookmark_by_question_not_found(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmark by question when not found."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Act
        result = await repository.get_bookmark_by_question(100, 42)

        # Assert
        assert result is None


class TestGetBookmarkCount:
    """Test get_bookmark_count method."""

    @pytest.mark.asyncio
    async def test_get_bookmark_count_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmark count."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 15

        # Act
        result = await repository.get_bookmark_count(100)

        # Assert
        assert result == 15

    @pytest.mark.asyncio
    async def test_get_bookmark_count_zero(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmark count when zero."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        # Act
        result = await repository.get_bookmark_count(100)

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_bookmark_count_database_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test database error during bookmark count."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            await repository.get_bookmark_count(100)


class TestGetBookmarksByQuestionIds:
    """Test get_bookmarks_by_question_ids method."""

    @pytest.mark.asyncio
    async def test_get_bookmarks_by_question_ids_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmarks by question IDs."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        bookmark_models = [
            BookmarkModel(
                id=1,
                user_id=100,
                question_id=42,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
            BookmarkModel(
                id=2,
                user_id=100,
                question_id=43,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            bookmark_models
        )

        with patch.object(repository, "_model_to_entity") as mock_convert:
            bookmark_entities = [
                Bookmark(
                    id=1, user_id=100, question_id=42, created_at=datetime.now(UTC)
                ),
                Bookmark(
                    id=2, user_id=100, question_id=43, created_at=datetime.now(UTC)
                ),
            ]
            mock_convert.side_effect = bookmark_entities

            # Act
            result = await repository.get_bookmarks_by_question_ids(100, [42, 43, 44])

            # Assert
            assert len(result) == 2
            assert result == bookmark_entities

    @pytest.mark.asyncio
    async def test_get_bookmarks_by_question_ids_empty_list(
        self, repository, mock_db_manager, mock_session
    ):
        """Test getting bookmarks with empty question ID list."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Act
        result = await repository.get_bookmarks_by_question_ids(100, [])

        # Assert
        assert result == []
        mock_session.execute.assert_not_called()


class TestDeleteUserBookmarks:
    """Test delete_user_bookmarks method."""

    @pytest.mark.asyncio
    async def test_delete_user_bookmarks_success(
        self, repository, mock_db_manager, mock_session
    ):
        """Test deleting all user bookmarks."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.rowcount = 5

        # Act
        result = await repository.delete_user_bookmarks(100)

        # Assert
        assert result == 5
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_bookmarks_none_found(
        self, repository, mock_db_manager, mock_session
    ):
        """Test deleting user bookmarks when none exist."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.rowcount = 0

        # Act
        result = await repository.delete_user_bookmarks(100)

        # Assert
        assert result == 0
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_bookmarks_database_error(
        self, repository, mock_db_manager, mock_session
    ):
        """Test database error during user bookmark deletion."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            await repository.delete_user_bookmarks(100)


class TestModelToEntityConversion:
    """Test model to entity conversion methods."""

    def test_model_to_entity_conversion(self, repository):
        """Test converting SQLAlchemy model to domain entity."""
        # Arrange
        created_at = datetime.now(UTC).replace(tzinfo=None)
        model = BookmarkModel(
            id=1, user_id=100, question_id=42, notes="Test notes", created_at=created_at
        )

        # Act
        entity = repository._model_to_entity(model)

        # Assert
        assert isinstance(entity, Bookmark)
        assert entity.id == 1
        assert entity.user_id == 100
        assert entity.question_id == 42
        assert entity.notes == "Test notes"
        assert entity.created_at == created_at.replace(tzinfo=UTC)

    def test_model_to_entity_conversion_no_notes(self, repository):
        """Test converting model without notes."""
        # Arrange
        created_at = datetime.now(UTC).replace(tzinfo=None)
        model = BookmarkModel(
            id=1, user_id=100, question_id=42, notes=None, created_at=created_at
        )

        # Act
        entity = repository._model_to_entity(model)

        # Assert
        assert entity.notes is None
        assert entity.created_at == created_at.replace(tzinfo=UTC)


class TestRepositoryErrorHandling:
    """Test repository error handling patterns."""

    @pytest.mark.asyncio
    async def test_integrity_error_handling(
        self, repository, mock_db_manager, mock_session
    ):
        """Test handling of integrity constraint violations."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.commit.side_effect = IntegrityError(
            "Integrity constraint", None, None
        )

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.add_bookmark(100, 42)

        assert "Integrity constraint" in str(exc_info.value)
        assert exc_info.value.error_code == "INTEGRITY_ERROR"

    @pytest.mark.asyncio
    async def test_connection_error_handling(
        self, repository, mock_db_manager, mock_session
    ):
        """Test handling of connection errors."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.side_effect = ConnectionError("Connection failed")

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.is_bookmarked(100, 42)

        assert "Connection failed" in str(exc_info.value)
        assert exc_info.value.error_code == "CONNECTION_ERROR"

    @pytest.mark.asyncio
    async def test_generic_exception_handling(
        self, repository, mock_db_manager, mock_session
    ):
        """Test handling of generic exceptions."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await repository.get_bookmark_count(100)

        assert "Unexpected error" in str(exc_info.value)
        assert exc_info.value.error_code == "UNKNOWN_ERROR"


class TestRepositoryPerformance:
    """Test repository performance considerations."""

    @pytest.mark.asyncio
    async def test_large_bookmark_collection_performance(
        self, repository, mock_db_manager, mock_session
    ):
        """Test performance with large bookmark collections."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock large collection
        large_collection = [
            BookmarkModel(
                id=i,
                user_id=100,
                question_id=i,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            for i in range(1, 1001)  # Start from 1 to avoid validation error
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            large_collection
        )
        mock_session.execute.return_value.scalar.return_value = 1000

        with patch.object(repository, "_model_to_entity") as mock_convert:
            mock_convert.side_effect = [
                Bookmark(id=i, user_id=100, question_id=i, created_at=datetime.now(UTC))
                for i in range(1, 1001)  # Start from 1 to avoid validation error
            ]

            # Act
            result = await repository.get_bookmarks(100, limit=100, offset=0)

            # Assert
            assert len(result.bookmarks) == 1000  # All items converted
            assert result.total_count == 1000
            # Verify pagination was attempted (limit/offset should be in query)

    @pytest.mark.asyncio
    async def test_concurrent_bookmark_operations(
        self, repository, mock_db_manager, mock_session
    ):
        """Test concurrent bookmark operations."""
        # Arrange
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock successful operations
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch.object(repository, "_model_to_entity") as mock_convert:
            mock_convert.return_value = Bookmark(
                id=1, user_id=100, question_id=42, created_at=datetime.now(UTC)
            )

            # Act - simulate concurrent operations
            import asyncio

            tasks = [
                repository.add_bookmark(100, 42 + i, f"Notes {i}") for i in range(5)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Assert
            assert len(results) == 5
            # All operations should succeed (in this mock scenario)
            assert all(isinstance(r, Bookmark) for r in results)
