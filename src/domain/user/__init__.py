"""User configuration bounded context.

This module contains the User bounded context for managing user settings,
preferences, developer mode configuration, and user flow state following
Domain-Driven Design patterns.
"""

from src.domain.user.events.user_events import (
    DeveloperModeRequiredEvent,
    DeveloperModeToggledEvent,
    FirstTimeSetupCompletedEvent,
    FirstTimeSetupStartedEvent,
    LanguageSelectedEvent,
    OnboardingProgressEvent,
    ServiceAvailabilityChangedEvent,
    ThemeChangedEvent,
    UserFlowStateChangedEvent,
    UserPreferencesUpdatedEvent,
    UserSettingsChangedEvent,
    UserSettingsLoadedEvent,
    UserSettingsSavedEvent,
    create_developer_mode_required_event,
    create_developer_mode_toggled_event,
    create_language_selected_event,
    create_user_settings_changed_event,
    create_user_settings_loaded_event,
)
from src.domain.user.models.user_models import (
    DeveloperMode,
    Language,
    LoadUserSettingsRequest,
    LoadUserSettingsResult,
    SaveUserSettingsRequest,
    SaveUserSettingsResult,
    ThemeMode,
    ToggleDeveloperModeRequest,
    ToggleDeveloperModeResult,
    UserFlowState,
    UserPreferences,
    UserSettings,
    UserSettingsDB,
)
from src.domain.user.services.load_user_settings import LoadUserSettings
from src.domain.user.services.save_user_settings import SaveUserSettings
from src.domain.user.services.toggle_developer_mode import ToggleDeveloperMode

__all__ = [
    # Models
    "DeveloperMode",
    "Language",
    "ThemeMode",
    "UserFlowState",
    "UserPreferences",
    "UserSettings",
    "UserSettingsDB",
    # Request/Response DTOs
    "LoadUserSettingsRequest",
    "LoadUserSettingsResult",
    "SaveUserSettingsRequest",
    "SaveUserSettingsResult",
    "ToggleDeveloperModeRequest",
    "ToggleDeveloperModeResult",
    # Events
    "DeveloperModeRequiredEvent",
    "DeveloperModeToggledEvent",
    "FirstTimeSetupCompletedEvent",
    "FirstTimeSetupStartedEvent",
    "LanguageSelectedEvent",
    "OnboardingProgressEvent",
    "ServiceAvailabilityChangedEvent",
    "ThemeChangedEvent",
    "UserFlowStateChangedEvent",
    "UserPreferencesUpdatedEvent",
    "UserSettingsChangedEvent",
    "UserSettingsLoadedEvent",
    "UserSettingsSavedEvent",
    # Event factories
    "create_developer_mode_required_event",
    "create_developer_mode_toggled_event",
    "create_language_selected_event",
    "create_user_settings_changed_event",
    "create_user_settings_loaded_event",
    # Domain services
    "LoadUserSettings",
    "SaveUserSettings",
    "ToggleDeveloperMode",
]
