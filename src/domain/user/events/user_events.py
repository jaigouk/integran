"""User configuration domain events."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.shared.events import DomainEvent
from src.domain.user.models.user_models import Language, ThemeMode

# =============================================================================
# User Configuration Events
# =============================================================================


@dataclass
class UserSettingsLoadedEvent(DomainEvent):
    """Event emitted when user settings are loaded from database."""

    user_id: int
    language: str
    theme_mode: str
    developer_mode_enabled: bool
    first_time_setup: bool
    onboarding_completed: bool

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class UserSettingsChangedEvent(DomainEvent):
    """Event emitted when user settings are modified."""

    user_id: int
    changed_fields: list[str]
    old_values: dict[str, str]
    new_values: dict[str, str]
    change_source: str  # 'ui', 'api', 'migration', 'system'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class UserSettingsSavedEvent(DomainEvent):
    """Event emitted when user settings are successfully saved."""

    user_id: int
    settings_version: str
    save_duration_ms: int
    fields_updated: list[str]

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class DeveloperModeToggledEvent(DomainEvent):
    """Event emitted when developer mode is enabled or disabled."""

    user_id: int
    developer_mode_enabled: bool
    api_access_enabled: bool
    previous_state: bool
    toggle_source: str  # 'settings', 'first_time_setup', 'admin'
    warning_acknowledged: bool = False

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class LanguageSelectedEvent(DomainEvent):
    """Event emitted when user selects interface language."""

    user_id: int
    previous_language: str
    new_language: str
    selection_source: str  # 'first_time_setup', 'settings', 'system'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class ThemeChangedEvent(DomainEvent):
    """Event emitted when UI theme is changed."""

    user_id: int
    previous_theme: str
    new_theme: str
    auto_detected: bool = False  # True if theme was auto-detected

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class FirstTimeSetupStartedEvent(DomainEvent):
    """Event emitted when first-time setup wizard is started."""

    user_id: int
    setup_version: str
    default_language: str

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class FirstTimeSetupCompletedEvent(DomainEvent):
    """Event emitted when first-time setup is completed."""

    user_id: int
    setup_duration_seconds: int
    language_selected: str
    developer_mode_enabled: bool
    completed_steps: list[str]

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class OnboardingProgressEvent(DomainEvent):
    """Event emitted during onboarding progress."""

    user_id: int
    current_step: str
    total_steps: int
    step_number: int
    step_completed: bool

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class UserPreferencesUpdatedEvent(DomainEvent):
    """Event emitted when user preferences are updated."""

    user_id: int
    preference_category: str  # 'learning', 'ui', 'notifications', 'custom'
    updated_preferences: dict[str, str]
    validation_passed: bool

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class UserFlowStateChangedEvent(DomainEvent):
    """Event emitted when user flow state changes."""

    user_id: int
    previous_screen: str
    current_screen: str
    flow_type: str  # 'navigation', 'session', 'setup'
    session_context: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class DeveloperModeRequiredEvent(DomainEvent):
    """Event emitted when an operation requires developer mode."""

    user_id: int
    requested_operation: str
    operation_category: str  # 'dataset_generation', 'image_processing', 'api_access'
    current_developer_mode: bool
    suggested_action: str

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


@dataclass
class ServiceAvailabilityChangedEvent(DomainEvent):
    """Event emitted when service availability changes due to settings."""

    user_id: int
    service_name: str
    previously_available: bool
    currently_available: bool
    availability_reason: str  # 'developer_mode', 'api_keys', 'configuration'

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()


# =============================================================================
# Event Factory Functions
# =============================================================================


def create_user_settings_loaded_event(
    user_id: int,
    language: Language,
    theme_mode: ThemeMode,
    developer_mode_enabled: bool,
    first_time_setup: bool,
    onboarding_completed: bool,
) -> UserSettingsLoadedEvent:
    """Factory function to create UserSettingsLoadedEvent."""
    return UserSettingsLoadedEvent(
        user_id=user_id,
        language=language.value,
        theme_mode=theme_mode.value,
        developer_mode_enabled=developer_mode_enabled,
        first_time_setup=first_time_setup,
        onboarding_completed=onboarding_completed,
    )


def create_developer_mode_toggled_event(
    user_id: int,
    developer_mode_enabled: bool,
    api_access_enabled: bool,
    previous_state: bool,
    toggle_source: str = "settings",
    warning_acknowledged: bool = False,
) -> DeveloperModeToggledEvent:
    """Factory function to create DeveloperModeToggledEvent."""
    return DeveloperModeToggledEvent(
        user_id=user_id,
        developer_mode_enabled=developer_mode_enabled,
        api_access_enabled=api_access_enabled,
        previous_state=previous_state,
        toggle_source=toggle_source,
        warning_acknowledged=warning_acknowledged,
    )


def create_language_selected_event(
    user_id: int,
    previous_language: Language,
    new_language: Language,
    selection_source: str = "settings",
) -> LanguageSelectedEvent:
    """Factory function to create LanguageSelectedEvent."""
    return LanguageSelectedEvent(
        user_id=user_id,
        previous_language=previous_language.value,
        new_language=new_language.value,
        selection_source=selection_source,
    )


def create_user_settings_changed_event(
    user_id: int,
    changed_fields: list[str],
    old_values: dict[str, str],
    new_values: dict[str, str],
    change_source: str = "ui",
) -> UserSettingsChangedEvent:
    """Factory function to create UserSettingsChangedEvent."""
    return UserSettingsChangedEvent(
        user_id=user_id,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values,
        change_source=change_source,
    )


def create_developer_mode_required_event(
    user_id: int,
    requested_operation: str,
    operation_category: str,
    current_developer_mode: bool,
) -> DeveloperModeRequiredEvent:
    """Factory function to create DeveloperModeRequiredEvent."""
    suggested_action = (
        "Enable developer mode in settings to access this feature"
        if not current_developer_mode
        else "Check API configuration and developer mode settings"
    )

    return DeveloperModeRequiredEvent(
        user_id=user_id,
        requested_operation=requested_operation,
        operation_category=operation_category,
        current_developer_mode=current_developer_mode,
        suggested_action=suggested_action,
    )
