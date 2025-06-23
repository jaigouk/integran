"""Repository for user settings data access."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.shared.repositories import RepositoryError, UserRepository
from src.domain.user.models.user_models import UserSettings, UserSettingsDB
from src.infrastructure.database.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    """Repository for managing user settings persistence."""

    def __init__(self, database_manager: DatabaseManager):
        """Initialize the user settings repository."""
        self.database_manager = database_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def get_user_settings(self, user_id: int) -> UserSettings | None:
        """Load user settings from database.

        Args:
            user_id: User ID to load settings for

        Returns:
            UserSettings if found, None if not found

        Raises:
            RepositoryError: If database operation fails
        """

        def _get_user_settings() -> UserSettings | None:
            try:
                with self.database_manager.get_session() as session:
                    db_settings = (
                        session.query(UserSettingsDB)
                        .filter(UserSettingsDB.user_id == user_id)
                        .first()
                    )

                    if not db_settings:
                        self.logger.info(
                            f"No user settings found for user_id={user_id}"
                        )
                        return None

                    user_settings = UserSettings.from_database_model(db_settings)
                    self.logger.info(f"Loaded user settings for user_id={user_id}")
                    return user_settings

            except SQLAlchemyError as e:
                self.logger.error(f"Database error loading user settings: {e}")
                raise RepositoryError(f"Failed to load user settings: {e}") from e
            except Exception as e:
                self.logger.error(f"Unexpected error loading user settings: {e}")
                raise RepositoryError(
                    f"Unexpected error loading user settings: {e}"
                ) from e

        return await self._run_in_executor(_get_user_settings)

    async def save_user_settings(self, user_settings: UserSettings) -> UserSettings:
        """Save user settings to database.

        Args:
            user_settings: UserSettings aggregate to save

        Returns:
            Updated UserSettings with persistence metadata

        Raises:
            RepositoryError: If database operation fails
        """

        def _save_user_settings() -> UserSettings:
            try:
                with self.database_manager.get_session() as session:
                    # Check if settings already exist
                    existing = (
                        session.query(UserSettingsDB)
                        .filter(UserSettingsDB.user_id == user_settings.user_id)
                        .first()
                    )

                    if existing:
                        # Update existing settings
                        db_model = user_settings.to_database_model()
                        for attr, value in db_model.__dict__.items():
                            if not attr.startswith("_") and attr != "id":
                                setattr(existing, attr, value)

                        session.flush()
                        updated_settings = UserSettings.from_database_model(existing)
                        self.logger.info(
                            f"Updated user settings for user_id={user_settings.user_id}"
                        )
                        return updated_settings
                    else:
                        # Create new settings
                        db_model = user_settings.to_database_model()
                        session.add(db_model)
                        session.flush()

                        new_settings = UserSettings.from_database_model(db_model)
                        self.logger.info(
                            f"Created new user settings for user_id={user_settings.user_id}"
                        )
                        return new_settings

            except IntegrityError as e:
                self.logger.error(f"Integrity error saving user settings: {e}")
                raise RepositoryError(f"Database constraint violation: {e}") from e
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving user settings: {e}")
                raise RepositoryError(f"Failed to save user settings: {e}") from e
            except Exception as e:
                self.logger.error(f"Unexpected error saving user settings: {e}")
                raise RepositoryError(
                    f"Unexpected error saving user settings: {e}"
                ) from e

        return await self._run_in_executor(_save_user_settings)

    async def delete_user_data(self, user_id: int) -> int:
        """Delete user settings from database.

        Args:
            user_id: User ID to delete settings for

        Returns:
            True if settings were deleted, False if not found

        Raises:
            RepositoryError: If database operation fails
        """

        def _delete_user_data() -> int:
            try:
                with self.database_manager.get_session() as session:
                    deleted_count = (
                        session.query(UserSettingsDB)
                        .filter(UserSettingsDB.user_id == user_id)
                        .delete()
                    )

                    self.logger.info(
                        f"Deleted {deleted_count} user settings for user_id={user_id}"
                    )
                    return deleted_count

            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting user settings: {e}")
                raise RepositoryError(f"Failed to delete user settings: {e}") from e
            except Exception as e:
                self.logger.error(f"Unexpected error deleting user settings: {e}")
                raise RepositoryError(
                    f"Unexpected error deleting user settings: {e}"
                ) from e

        return await self._run_in_executor(_delete_user_data)

    async def user_exists(self, user_id: int) -> bool:
        """Check if user settings exist in database.

        Args:
            user_id: User ID to check

        Returns:
            True if settings exist, False otherwise

        Raises:
            RepositoryError: If database operation fails
        """

        def _user_exists() -> bool:
            try:
                with self.database_manager.get_session() as session:
                    exists = (
                        session.query(UserSettingsDB)
                        .filter(UserSettingsDB.user_id == user_id)
                        .first()
                    ) is not None

                    self.logger.debug(
                        f"User settings exist for user_id={user_id}: {exists}"
                    )
                    return exists

            except SQLAlchemyError as e:
                self.logger.error(
                    f"Database error checking user settings existence: {e}"
                )
                raise RepositoryError(
                    f"Failed to check user settings existence: {e}"
                ) from e
            except Exception as e:
                self.logger.error(
                    f"Unexpected error checking user settings existence: {e}"
                )
                raise RepositoryError(
                    f"Unexpected error checking user settings existence: {e}"
                ) from e

        return await self._run_in_executor(_user_exists)

    async def get_user_setting_value(
        self, user_id: int, setting_key: str
    ) -> Any | None:
        """Get a specific setting value.

        Args:
            user_id: User ID
            setting_key: Name of the setting to retrieve

        Returns:
            Setting value if found, None otherwise

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            user_settings = await self.get_user_settings(user_id)
            if not user_settings:
                return None

            # Map setting keys to UserSettings attributes
            setting_map = {
                "language": user_settings.language.value,
                "theme_mode": user_settings.theme_mode.value,
                "developer_mode": user_settings.developer_mode.enabled,
                "use_gemini": user_settings.developer_mode.use_gemini,
                "first_time_setup": user_settings.first_time_setup,
                "onboarding_completed": user_settings.onboarding_completed,
                "daily_goal": user_settings.preferences.daily_goal,
                "session_timeout_minutes": user_settings.preferences.session_timeout_minutes,
                "show_explanations": user_settings.preferences.show_explanations,
                "auto_advance": user_settings.preferences.auto_advance,
                "enable_notifications": user_settings.preferences.enable_notifications,
                "reminder_time": user_settings.preferences.reminder_time,
            }

            value = setting_map.get(setting_key)
            self.logger.debug(
                f"Retrieved setting {setting_key}={value} for user_id={user_id}"
            )
            return value

        except Exception as e:
            self.logger.error(f"Error retrieving setting {setting_key}: {e}")
            raise RepositoryError(
                f"Failed to retrieve setting {setting_key}: {e}"
            ) from e

    # Method aliases for backward compatibility
    async def load_user_settings(self, user_id: int) -> UserSettings | None:
        """Alias for get_user_settings."""
        return await self.get_user_settings(user_id)

    async def user_settings_exist(self, user_id: int) -> bool:
        """Alias for user_exists."""
        return await self.user_exists(user_id)


# Backward compatibility alias
UserSettingsRepository = SQLAlchemyUserRepository
