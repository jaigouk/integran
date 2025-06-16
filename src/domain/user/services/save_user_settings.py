"""Save user settings domain service."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.domain.shared.services import (
    DomainService,
    ValidationError,
    log_domain_operation,
)
from src.domain.user.events.user_events import (
    UserSettingsSavedEvent,
    create_user_settings_changed_event,
)
from src.domain.user.models.user_models import (
    SaveUserSettingsRequest,
    SaveUserSettingsResult,
    UserSettings,
)
from src.infrastructure.messaging.event_bus import EventBus
from src.infrastructure.repositories.user_repository import (
    RepositoryError,
    UserSettingsRepository,
)

logger = logging.getLogger(__name__)


class SaveUserSettings(DomainService[SaveUserSettingsRequest, SaveUserSettingsResult]):
    """Domain service to save user settings following DDD patterns.

    This service handles persisting user configuration changes,
    comparing old and new values, and emitting appropriate
    domain events for cross-context communication.
    """

    def __init__(
        self,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
    ):
        """Initialize the SaveUserSettings domain service.

        Args:
            event_bus: Event bus for publishing domain events
            user_repository: Repository for user settings persistence
        """
        super().__init__(event_bus)
        self.user_repository = user_repository

    @log_domain_operation
    async def call(self, request: SaveUserSettingsRequest) -> SaveUserSettingsResult:
        """Save user settings to persistence with change tracking.

        Args:
            request: Save user settings request

        Returns:
            SaveUserSettingsResult with updated settings

        Raises:
            ValidationError: If request is invalid
            DomainServiceError: If saving fails
        """
        # Validate request
        self._validate_request(request)

        start_time = datetime.now(UTC)

        try:
            # Load existing settings for comparison
            existing_settings = await self.user_repository.load_user_settings(
                request.user_settings.user_id
            )

            # Update timestamp
            updated_settings = request.user_settings._copy_with_updates(
                updated_at=datetime.now(UTC)
            )

            # Save to repository
            saved_settings = await self.user_repository.save_user_settings(
                updated_settings
            )

            # Calculate save duration
            save_duration_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            # Determine what changed
            changed_fields, old_values, new_values = self._detect_changes(
                existing_settings, saved_settings
            )

            # Emit settings changed event if there were changes
            if changed_fields:
                await self._publish_event(
                    create_user_settings_changed_event(
                        user_id=saved_settings.user_id,
                        changed_fields=changed_fields,
                        old_values=old_values,
                        new_values=new_values,
                        change_source="domain_service",
                    )
                )

            # Emit settings saved event
            await self._publish_event(
                UserSettingsSavedEvent(
                    user_id=saved_settings.user_id,
                    settings_version=f"{saved_settings.updated_at.timestamp()}",
                    save_duration_ms=save_duration_ms,
                    fields_updated=changed_fields,
                )
            )

            self.logger.info(
                f"Successfully saved user settings for user {saved_settings.user_id} "
                f"(changes: {len(changed_fields)}, duration: {save_duration_ms}ms)"
            )

            return SaveUserSettingsResult(
                success=True,
                user_settings=saved_settings,
            )

        except RepositoryError as e:
            error_msg = f"Repository error saving user settings: {e}"
            self.logger.error(error_msg)
            return SaveUserSettingsResult(
                success=False,
                user_settings=request.user_settings,
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Unexpected error saving user settings: {e}"
            self.logger.error(error_msg)
            return SaveUserSettingsResult(
                success=False,
                user_settings=request.user_settings,
                error_message=error_msg,
            )

    def _validate_request(self, request: SaveUserSettingsRequest) -> None:
        """Validate the save user settings request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If request is invalid
        """
        if not isinstance(request, SaveUserSettingsRequest):
            raise ValidationError("Request must be a SaveUserSettingsRequest instance")

        if not isinstance(request.user_settings, UserSettings):
            raise ValidationError("user_settings must be a UserSettings instance")

        if request.user_settings.user_id < 1:
            raise ValidationError("user_id must be positive")

        # Validate preferences
        preferences = request.user_settings.preferences
        if preferences.daily_goal < 1 or preferences.daily_goal > 1000:
            raise ValidationError("daily_goal must be between 1 and 1000")

        if (
            preferences.session_timeout_minutes < 5
            or preferences.session_timeout_minutes > 480
        ):
            raise ValidationError("session_timeout_minutes must be between 5 and 480")

        # Validate reminder time format (HH:MM)
        try:
            hour, minute = preferences.reminder_time.split(":")
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                raise ValueError
        except (ValueError, AttributeError) as e:
            raise ValidationError("reminder_time must be in HH:MM format") from e

    def _detect_changes(
        self,
        old_settings: UserSettings | None,
        new_settings: UserSettings,
    ) -> tuple[list[str], dict[str, str], dict[str, str]]:
        """Detect changes between old and new settings.

        Args:
            old_settings: Previous settings (None for new users)
            new_settings: New settings

        Returns:
            Tuple of (changed_fields, old_values, new_values)
        """
        if not old_settings:
            # All fields are new
            return (
                ["language", "theme_mode", "developer_mode", "preferences"],
                {},
                {
                    "language": new_settings.language.value,
                    "theme_mode": new_settings.theme_mode.value,
                    "developer_mode": str(new_settings.developer_mode.enabled),
                    "preferences": "new_user_defaults",
                },
            )

        changed_fields = []
        old_values = {}
        new_values = {}

        # Check language
        if old_settings.language != new_settings.language:
            changed_fields.append("language")
            old_values["language"] = old_settings.language.value
            new_values["language"] = new_settings.language.value

        # Check theme mode
        if old_settings.theme_mode != new_settings.theme_mode:
            changed_fields.append("theme_mode")
            old_values["theme_mode"] = old_settings.theme_mode.value
            new_values["theme_mode"] = new_settings.theme_mode.value

        # Check developer mode
        if old_settings.developer_mode.enabled != new_settings.developer_mode.enabled:
            changed_fields.append("developer_mode")
            old_values["developer_mode"] = str(old_settings.developer_mode.enabled)
            new_values["developer_mode"] = str(new_settings.developer_mode.enabled)

        # Check use_gemini
        if (
            old_settings.developer_mode.use_gemini
            != new_settings.developer_mode.use_gemini
        ):
            changed_fields.append("use_gemini")
            old_values["use_gemini"] = str(old_settings.developer_mode.use_gemini)
            new_values["use_gemini"] = str(new_settings.developer_mode.use_gemini)

        # Check first-time setup
        if old_settings.first_time_setup != new_settings.first_time_setup:
            changed_fields.append("first_time_setup")
            old_values["first_time_setup"] = str(old_settings.first_time_setup)
            new_values["first_time_setup"] = str(new_settings.first_time_setup)

        # Check onboarding completed
        if old_settings.onboarding_completed != new_settings.onboarding_completed:
            changed_fields.append("onboarding_completed")
            old_values["onboarding_completed"] = str(old_settings.onboarding_completed)
            new_values["onboarding_completed"] = str(new_settings.onboarding_completed)

        # Check preferences
        if old_settings.preferences.to_dict() != new_settings.preferences.to_dict():
            changed_fields.append("preferences")
            old_values["preferences"] = (
                f"daily_goal={old_settings.preferences.daily_goal}"
            )
            new_values["preferences"] = (
                f"daily_goal={new_settings.preferences.daily_goal}"
            )

        return changed_fields, old_values, new_values
