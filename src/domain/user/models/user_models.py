"""User configuration domain models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from src.domain.shared.models import Base


class Language(str, Enum):
    """Supported interface languages."""

    ENGLISH = "en"
    GERMAN = "de"
    TURKISH = "tr"
    UKRAINIAN = "uk"
    ARABIC = "ar"


class ThemeMode(str, Enum):
    """UI theme modes."""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


# ============================================================================
# SQLAlchemy Database Models
# ============================================================================


class UserSettingsDB(Base):
    """User settings database model with enhanced configuration."""

    __tablename__ = "user_configuration"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1, nullable=False)  # Single user for now

    # Core Configuration
    language = Column(String(5), default=Language.ENGLISH.value, nullable=False)
    theme_mode = Column(String(10), default=ThemeMode.AUTO.value, nullable=False)

    # Developer Mode Control
    developer_mode = Column(Boolean, default=False, nullable=False)
    use_gemini = Column(Boolean, default=False, nullable=False)

    # First-time Setup
    first_time_setup = Column(Boolean, default=True, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # User Preferences (JSON)
    user_preferences = Column(Text, default="{}", nullable=False)  # JSON serialized
    user_flow_state = Column(
        Text, default="{}", nullable=False
    )  # JSON for resume state

    # Learning Preferences
    daily_goal = Column(Integer, default=20, nullable=False)  # Questions per day
    session_timeout_minutes = Column(Integer, default=60, nullable=False)
    show_explanations = Column(Boolean, default=True, nullable=False)
    auto_advance = Column(Boolean, default=False, nullable=False)

    # Notifications
    enable_notifications = Column(Boolean, default=True, nullable=False)
    reminder_time = Column(String(10), default="19:00", nullable=False)  # HH:MM format

    # Metadata
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    __table_args__ = ({"extend_existing": True},)


# ============================================================================
# Domain Aggregates and Value Objects
# ============================================================================


@dataclass
class DeveloperMode:
    """Developer mode value object."""

    enabled: bool = False
    use_gemini: bool = False
    api_usage_warnings: bool = True

    def enable(self) -> DeveloperMode:
        """Enable developer mode with API access."""
        return DeveloperMode(
            enabled=True, use_gemini=True, api_usage_warnings=self.api_usage_warnings
        )

    def disable(self) -> DeveloperMode:
        """Disable developer mode and API access."""
        return DeveloperMode(
            enabled=False, use_gemini=False, api_usage_warnings=self.api_usage_warnings
        )

    def requires_api_access(self) -> bool:
        """Check if current settings require API access."""
        return self.enabled and self.use_gemini


@dataclass
class UserPreferences:
    """User preferences value object."""

    # Learning preferences
    daily_goal: int = 20
    session_timeout_minutes: int = 60
    show_explanations: bool = True
    auto_advance: bool = False

    # UI preferences
    theme_mode: ThemeMode = ThemeMode.AUTO
    language: Language = Language.ENGLISH

    # Notification preferences
    enable_notifications: bool = True
    reminder_time: str = "19:00"  # HH:MM format

    # Custom preferences (extensible)
    custom_settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "daily_goal": self.daily_goal,
            "session_timeout_minutes": self.session_timeout_minutes,
            "show_explanations": self.show_explanations,
            "auto_advance": self.auto_advance,
            "theme_mode": self.theme_mode.value,
            "language": self.language.value,
            "enable_notifications": self.enable_notifications,
            "reminder_time": self.reminder_time,
            "custom_settings": self.custom_settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreferences:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            daily_goal=data.get("daily_goal", 20),
            session_timeout_minutes=data.get("session_timeout_minutes", 60),
            show_explanations=data.get("show_explanations", True),
            auto_advance=data.get("auto_advance", False),
            theme_mode=ThemeMode(data.get("theme_mode", ThemeMode.AUTO.value)),
            language=Language(data.get("language", Language.ENGLISH.value)),
            enable_notifications=data.get("enable_notifications", True),
            reminder_time=data.get("reminder_time", "19:00"),
            custom_settings=data.get("custom_settings", {}),
        )


@dataclass
class UserFlowState:
    """User flow state for resume capabilities."""

    current_screen: str = "main_menu"
    session_in_progress: bool = False
    current_session_id: int | None = None
    last_question_id: int | None = None
    setup_step: str | None = None  # For first-time setup
    flow_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_screen": self.current_screen,
            "session_in_progress": self.session_in_progress,
            "current_session_id": self.current_session_id,
            "last_question_id": self.last_question_id,
            "setup_step": self.setup_step,
            "flow_data": self.flow_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserFlowState:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            current_screen=data.get("current_screen", "main_menu"),
            session_in_progress=data.get("session_in_progress", False),
            current_session_id=data.get("current_session_id"),
            last_question_id=data.get("last_question_id"),
            setup_step=data.get("setup_step"),
            flow_data=data.get("flow_data", {}),
        )


@dataclass
class UserSettings:
    """User settings aggregate root following DDD patterns."""

    user_id: int
    language: Language
    theme_mode: ThemeMode
    developer_mode: DeveloperMode
    first_time_setup: bool
    onboarding_completed: bool
    preferences: UserPreferences
    flow_state: UserFlowState
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_default(cls, user_id: int = 1) -> UserSettings:
        """Create default user settings for new users."""
        now = datetime.now(UTC)
        return cls(
            user_id=user_id,
            language=Language.ENGLISH,
            theme_mode=ThemeMode.AUTO,
            developer_mode=DeveloperMode(enabled=False, use_gemini=False),
            first_time_setup=True,
            onboarding_completed=False,
            preferences=UserPreferences(),
            flow_state=UserFlowState(),
            created_at=now,
            updated_at=now,
        )

    def update_language(self, language: Language) -> UserSettings:
        """Update interface language."""
        updated_prefs_dict = self.preferences.to_dict()
        updated_prefs_dict["language"] = language.value
        return self._copy_with_updates(
            language=language, preferences=UserPreferences.from_dict(updated_prefs_dict)
        )

    def toggle_developer_mode(self) -> UserSettings:
        """Toggle developer mode and API access."""
        new_developer_mode = (
            self.developer_mode.disable()
            if self.developer_mode.enabled
            else self.developer_mode.enable()
        )
        return self._copy_with_updates(developer_mode=new_developer_mode)

    def complete_first_time_setup(self) -> UserSettings:
        """Mark first-time setup as complete."""
        return self._copy_with_updates(
            first_time_setup=False,
            onboarding_completed=True,
        )

    def update_preferences(self, preferences: UserPreferences) -> UserSettings:
        """Update user preferences."""
        return self._copy_with_updates(preferences=preferences)

    def update_flow_state(self, flow_state: UserFlowState) -> UserSettings:
        """Update user flow state."""
        return self._copy_with_updates(flow_state=flow_state)

    def requires_developer_mode_for_api(self) -> bool:
        """Check if developer mode is required for API operations."""
        return not self.developer_mode.requires_api_access()

    def to_database_model(self) -> UserSettingsDB:
        """Convert to database model for persistence."""
        return UserSettingsDB(
            id=None,  # Auto-generated
            user_id=self.user_id,
            language=self.language.value,
            theme_mode=self.theme_mode.value,
            developer_mode=self.developer_mode.enabled,
            use_gemini=self.developer_mode.use_gemini,
            first_time_setup=self.first_time_setup,
            onboarding_completed=self.onboarding_completed,
            user_preferences=json.dumps(self.preferences.to_dict()),
            user_flow_state=json.dumps(self.flow_state.to_dict()),
            daily_goal=self.preferences.daily_goal,
            session_timeout_minutes=self.preferences.session_timeout_minutes,
            show_explanations=self.preferences.show_explanations,
            auto_advance=self.preferences.auto_advance,
            enable_notifications=self.preferences.enable_notifications,
            reminder_time=self.preferences.reminder_time,
            created_at=self.created_at.replace(tzinfo=None),
            updated_at=self.updated_at.replace(tzinfo=None),
        )

    @classmethod
    def from_database_model(cls, db_model: UserSettingsDB) -> UserSettings:
        """Create from database model."""
        preferences_data = json.loads(str(db_model.user_preferences or "{}"))
        flow_state_data = json.loads(str(db_model.user_flow_state or "{}"))

        return cls(
            user_id=int(db_model.user_id),
            language=Language(str(db_model.language)),
            theme_mode=ThemeMode(str(db_model.theme_mode)),
            developer_mode=DeveloperMode(
                enabled=bool(db_model.developer_mode),
                use_gemini=bool(db_model.use_gemini),
            ),
            first_time_setup=bool(db_model.first_time_setup),
            onboarding_completed=bool(db_model.onboarding_completed),
            preferences=UserPreferences.from_dict(preferences_data),
            flow_state=UserFlowState.from_dict(flow_state_data),
            created_at=db_model.created_at.replace(tzinfo=UTC)
            if db_model.created_at
            else datetime.now(UTC),
            updated_at=db_model.updated_at.replace(tzinfo=UTC)
            if db_model.updated_at
            else datetime.now(UTC),
        )

    def _copy_with_updates(self, **updates: Any) -> UserSettings:
        """Create a copy with updates and refresh timestamp."""
        return UserSettings(
            user_id=updates.get("user_id", self.user_id),
            language=updates.get("language", self.language),
            theme_mode=updates.get("theme_mode", self.theme_mode),
            developer_mode=updates.get("developer_mode", self.developer_mode),
            first_time_setup=updates.get("first_time_setup", self.first_time_setup),
            onboarding_completed=updates.get(
                "onboarding_completed", self.onboarding_completed
            ),
            preferences=updates.get("preferences", self.preferences),
            flow_state=updates.get("flow_state", self.flow_state),
            created_at=updates.get("created_at", self.created_at),
            updated_at=updates.get("updated_at", datetime.now(UTC)),
        )


# ============================================================================
# Request/Response DTOs for Domain Services
# ============================================================================


@dataclass
class SaveUserSettingsRequest:
    """Request to save user settings."""

    user_settings: UserSettings


@dataclass
class SaveUserSettingsResult:
    """Result of saving user settings."""

    success: bool
    user_settings: UserSettings
    error_message: str | None = None


@dataclass
class LoadUserSettingsRequest:
    """Request to load user settings."""

    user_id: int = 1


@dataclass
class LoadUserSettingsResult:
    """Result of loading user settings."""

    success: bool
    user_settings: UserSettings | None = None
    is_first_time: bool = False
    error_message: str | None = None


@dataclass
class ToggleDeveloperModeRequest:
    """Request to toggle developer mode."""

    user_id: int = 1
    enable: bool | None = (
        None  # None = toggle, True = force enable, False = force disable
    )


@dataclass
class ToggleDeveloperModeResult:
    """Result of toggling developer mode."""

    success: bool
    user_settings: UserSettings
    developer_mode_enabled: bool
    api_access_enabled: bool
    warning_message: str | None = None
    error_message: str | None = None
