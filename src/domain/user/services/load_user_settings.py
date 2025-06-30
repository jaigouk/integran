"""Load user settings domain service."""

from __future__ import annotations

import logging

from src.domain.shared.repositories import RepositoryError, UserRepository
from src.domain.shared.services import (
    DomainService,
    EventBusInterface,
    ValidationError,
    log_domain_operation,
)
from src.domain.user.events.user_events import (
    FirstTimeSetupStartedEvent,
    create_user_settings_loaded_event,
)
from src.domain.user.models.user_models import (
    LoadUserSettingsRequest,
    LoadUserSettingsResult,
    UserSettings,
)

logger = logging.getLogger(__name__)


class LoadUserSettings(DomainService[LoadUserSettingsRequest, LoadUserSettingsResult]):
    """Domain service to load user settings following DDD patterns.

    This service handles loading user configuration from persistence,
    creating default settings for first-time users, and emitting
    appropriate domain events.
    """

    def __init__(
        self,
        event_bus: EventBusInterface,
        user_repository: UserRepository,
    ):
        """Initialize the LoadUserSettings domain service.

        Args:
            event_bus: Event bus for publishing domain events
            user_repository: Repository for user settings persistence
        """
        super().__init__(event_bus)
        self.user_repository = user_repository

    @log_domain_operation
    async def call(self, request: LoadUserSettingsRequest) -> LoadUserSettingsResult:
        """Load user settings from persistence or create defaults.

        Args:
            request: Load user settings request

        Returns:
            LoadUserSettingsResult with settings and first-time flag

        Raises:
            ValidationError: If request is invalid
            DomainServiceError: If loading fails
        """
        # Validate request
        self._validate_request(request)

        try:
            # Try to load existing settings
            user_settings = await self.user_repository.get_user_settings(
                request.user_id
            )

            if user_settings:
                # User settings exist
                is_first_time = user_settings.first_time_setup
            else:
                # Create default settings for first-time user
                user_settings = UserSettings.create_default(request.user_id)
                is_first_time = True

                # Emit first-time setup event
                await self._publish_event(
                    FirstTimeSetupStartedEvent(
                        user_id=request.user_id,
                        setup_version="1.0",
                        default_language=user_settings.language.value,
                    )
                )

            # Emit settings loaded event
            await self._publish_event(
                create_user_settings_loaded_event(
                    user_id=user_settings.user_id,
                    language=user_settings.language,
                    theme_mode=user_settings.theme_mode,
                    developer_mode_enabled=user_settings.developer_mode.enabled,
                    first_time_setup=user_settings.first_time_setup,
                    onboarding_completed=user_settings.onboarding_completed,
                )
            )

            self.logger.info(
                f"Successfully loaded user settings for user {request.user_id} "
                f"(first_time: {is_first_time}, developer_mode: {user_settings.developer_mode.enabled})"
            )

            return LoadUserSettingsResult(
                success=True,
                user_settings=user_settings,
                is_first_time=is_first_time,
            )

        except RepositoryError as e:
            error_msg = f"Repository error loading user settings: {e}"
            self.logger.error(error_msg)
            return LoadUserSettingsResult(
                success=False,
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Unexpected error loading user settings: {e}"
            self.logger.error(error_msg)
            return LoadUserSettingsResult(
                success=False,
                error_message=error_msg,
            )

    def _validate_request(self, request: LoadUserSettingsRequest) -> None:
        """Validate the load user settings request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If request is invalid
        """
        if not isinstance(request, LoadUserSettingsRequest):
            raise ValidationError("Request must be a LoadUserSettingsRequest instance")

        if not isinstance(request.user_id, int):
            raise ValidationError("user_id must be an integer")

        if request.user_id < 1:
            raise ValidationError("user_id must be positive")
