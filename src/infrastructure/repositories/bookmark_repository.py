"""SQLite implementation of bookmark repository."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.shared.repositories import BookmarkRepository, RepositoryError
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection
from src.infrastructure.database.models import BookmarkModel

if TYPE_CHECKING:
    from src.infrastructure.database.database import DatabaseManager


class BookmarkRepositoryImpl(BookmarkRepository):
    """SQLite implementation of bookmark repository."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager."""
        self.db = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def add_bookmark(
        self, user_id: int, question_id: int, notes: str | None = None
    ) -> Bookmark:
        """Add a new bookmark for a user and question."""

        def _add_bookmark() -> Bookmark:
            try:
                with self.db.get_session() as session:
                    # Check for existing bookmark
                    existing_query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    existing_result = session.execute(existing_query)
                    existing_bookmark = existing_result.scalar_one_or_none()

                    if existing_bookmark:
                        raise RepositoryError(
                            f"Bookmark already exists for user {user_id} and question {question_id}",
                            "DUPLICATE_BOOKMARK",
                        )

                    # Create new bookmark
                    bookmark_model = BookmarkModel(
                        user_id=user_id, question_id=question_id, notes=notes
                    )
                    session.add(bookmark_model)
                    session.commit()

                    return self._model_to_entity(bookmark_model)

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except IntegrityError as e:
                raise RepositoryError(
                    f"Integrity constraint violation: {e}", "INTEGRITY_ERROR"
                ) from e
            except ConnectionError as e:
                raise RepositoryError(
                    f"Database connection error: {e}", "CONNECTION_ERROR"
                ) from e
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_add_bookmark)

    async def remove_bookmark(self, user_id: int, question_id: int) -> bool:
        """Remove a bookmark for a user and question."""

        def _remove_bookmark() -> bool:
            try:
                with self.db.get_session() as session:
                    # Find existing bookmark
                    query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    result = session.execute(query)
                    bookmark = result.scalar_one_or_none()

                    if bookmark is None:
                        return False

                    # Delete bookmark
                    session.delete(bookmark)
                    session.commit()
                    return True

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_remove_bookmark)

    async def get_bookmarks(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> BookmarkCollection:
        """Get user's bookmarks with optional pagination."""

        def _get_bookmarks() -> BookmarkCollection:
            try:
                with self.db.get_session() as session:
                    # Build query for bookmarks
                    query = (
                        select(BookmarkModel)
                        .where(BookmarkModel.user_id == user_id)
                        .order_by(BookmarkModel.created_at.desc())
                    )

                    # Apply pagination
                    if limit is not None:
                        query = query.limit(limit)
                    if offset > 0:
                        query = query.offset(offset)

                    # Execute query
                    result = session.execute(query)
                    bookmark_models = result.scalars().all()

                    # Get total count
                    count_query = select(func.count(BookmarkModel.id)).where(
                        BookmarkModel.user_id == user_id
                    )
                    count_result = session.execute(count_query)
                    total_count = count_result.scalar() or 0

                    # Convert to entities
                    bookmarks = [
                        self._model_to_entity(model) for model in bookmark_models
                    ]

                    return BookmarkCollection(
                        user_id=user_id, bookmarks=bookmarks, total_count=total_count
                    )

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_get_bookmarks)

    async def is_bookmarked(self, user_id: int, question_id: int) -> bool:
        """Check if a question is bookmarked by user."""

        def _is_bookmarked() -> bool:
            try:
                with self.db.get_session() as session:
                    query = select(BookmarkModel.id).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    result = session.execute(query)
                    bookmark = result.scalar_one_or_none()
                    return bookmark is not None

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except ConnectionError as e:
                raise RepositoryError(
                    f"Database connection error: {e}", "CONNECTION_ERROR"
                ) from e
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_is_bookmarked)

    async def get_bookmark_by_question(
        self, user_id: int, question_id: int
    ) -> Bookmark | None:
        """Get bookmark for a specific question."""

        def _get_bookmark_by_question() -> Bookmark | None:
            try:
                with self.db.get_session() as session:
                    query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    result = session.execute(query)
                    bookmark_model = result.scalar_one_or_none()

                    if bookmark_model is None:
                        return None

                    return self._model_to_entity(bookmark_model)

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_get_bookmark_by_question)

    async def get_bookmark_count(self, user_id: int) -> int:
        """Get total number of bookmarks for a user."""

        def _get_bookmark_count() -> int:
            try:
                with self.db.get_session() as session:
                    query = select(func.count(BookmarkModel.id)).where(
                        BookmarkModel.user_id == user_id
                    )
                    result = session.execute(query)
                    return result.scalar() or 0

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_get_bookmark_count)

    async def get_bookmarks_by_question_ids(
        self, user_id: int, question_ids: list[int]
    ) -> list[Bookmark]:
        """Get bookmarks for specific questions."""
        if not question_ids:
            return []

        def _get_bookmarks_by_question_ids() -> list[Bookmark]:
            try:
                with self.db.get_session() as session:
                    query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id.in_(question_ids),
                    )
                    result = session.execute(query)
                    bookmark_models = result.scalars().all()

                    return [self._model_to_entity(model) for model in bookmark_models]

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_get_bookmarks_by_question_ids)

    async def update_bookmark_notes(
        self, user_id: int, question_id: int, notes: str | None
    ) -> bool:
        """Update notes for an existing bookmark."""

        def _update_bookmark_notes() -> bool:
            try:
                with self.db.get_session() as session:
                    # Find existing bookmark
                    query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    result = session.execute(query)
                    bookmark = result.scalar_one_or_none()

                    if bookmark is None:
                        return False

                    # Update notes
                    bookmark.notes = notes
                    session.commit()
                    return True

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_update_bookmark_notes)

    async def delete_user_bookmarks(self, user_id: int) -> int:
        """Delete all bookmarks for a user."""

        def _delete_user_bookmarks() -> int:
            try:
                with self.db.get_session() as session:
                    query = delete(BookmarkModel).where(
                        BookmarkModel.user_id == user_id
                    )
                    result = session.execute(query)
                    session.commit()
                    return result.rowcount

            except RepositoryError:
                # Re-raise RepositoryError as-is (for domain validation errors)
                raise
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_delete_user_bookmarks)

    def _model_to_entity(self, model: BookmarkModel) -> Bookmark:
        """Convert SQLAlchemy model to domain entity."""
        # Handle timezone for created_at
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        return Bookmark(
            id=model.id,
            user_id=model.user_id,
            question_id=model.question_id,
            notes=model.notes,
            created_at=created_at,
        )
