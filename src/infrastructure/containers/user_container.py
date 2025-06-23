"""Dependency injection container for User Context."""

from __future__ import annotations

from src.domain.user.services.load_user_settings import LoadUserSettings
from src.domain.user.services.save_user_settings import SaveUserSettings
from src.domain.user.services.toggle_developer_mode import ToggleDeveloperMode
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository


class UserContainer:
    """Container for User Context dependencies."""

    def __init__(
        self,
        event_bus: EnhancedEventBus | None = None,
        database_manager: DatabaseManager | None = None,
    ):
        """Initialize the user container."""
        # Use provided event bus or create new one
        self._event_bus = event_bus or EnhancedEventBus.create_basic()

        # Use provided database manager or create new one
        self._database_manager = database_manager or DatabaseManager()

        # Initialize repository
        self._repository = UserSettingsRepository(
            database_manager=self._database_manager
        )

        # Initialize domain services
        self._load_user_settings = LoadUserSettings(
            event_bus=self._event_bus,
            user_repository=self._repository,
        )
        self._save_user_settings = SaveUserSettings(
            event_bus=self._event_bus,
            user_repository=self._repository,
        )
        self._toggle_developer_mode = ToggleDeveloperMode(
            event_bus=self._event_bus,
            user_repository=self._repository,
        )

    def get_event_bus(self) -> EnhancedEventBus:
        """Get the event bus instance."""
        return self._event_bus

    def get_repository(self) -> UserSettingsRepository:
        """Get the user settings repository instance."""
        return self._repository

    def get_load_user_settings_service(self) -> LoadUserSettings:
        """Get the LoadUserSettings domain service."""
        return self._load_user_settings

    def get_save_user_settings_service(self) -> SaveUserSettings:
        """Get the SaveUserSettings domain service."""
        return self._save_user_settings

    def get_toggle_developer_mode_service(self) -> ToggleDeveloperMode:
        """Get the ToggleDeveloperMode domain service."""
        return self._toggle_developer_mode
