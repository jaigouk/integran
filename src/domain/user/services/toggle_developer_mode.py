"""Toggle developer mode domain service."""

from __future__ import annotations

import logging

from src.domain.shared.services import (
    DomainService,
    ValidationError,
    log_domain_operation,
)
from src.domain.user.events.user_events import (
    ServiceAvailabilityChangedEvent,
    create_developer_mode_toggled_event,
)
from src.domain.user.models.user_models import (
    ToggleDeveloperModeRequest,
    ToggleDeveloperModeResult,
    UserSettings,
)
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import (
    RepositoryError,
    UserSettingsRepository,
)

logger = logging.getLogger(__name__)


class ToggleDeveloperMode(
    DomainService[ToggleDeveloperModeRequest, ToggleDeveloperModeResult]
):
    """Domain service to toggle developer mode following DDD patterns.

    This service handles enabling/disabling developer mode with proper
    warnings about API access and costs, and emits events for services
    that depend on developer mode access.
    """

    def __init__(
        self,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
    ):
        """Initialize the ToggleDeveloperMode domain service.

        Args:
            event_bus: Event bus for publishing domain events
            user_repository: Repository for user settings persistence
        """
        super().__init__(event_bus)
        self.user_repository = user_repository

    @log_domain_operation
    async def call(
        self, request: ToggleDeveloperModeRequest
    ) -> ToggleDeveloperModeResult:
        """Toggle developer mode with proper validation and warnings.

        Args:
            request: Toggle developer mode request

        Returns:
            ToggleDeveloperModeResult with updated settings and warnings

        Raises:
            ValidationError: If request is invalid
            DomainServiceError: If toggle operation fails
        """
        # Validate request
        self._validate_request(request)

        try:
            # Load current settings
            current_settings = await self.user_repository.load_user_settings(
                request.user_id
            )
            if not current_settings:
                # Create default settings for new user
                current_settings = UserSettings.create_default(request.user_id)

            # Determine new developer mode state
            current_state = current_settings.developer_mode.enabled
            new_state = not current_state if request.enable is None else request.enable

            # If no change needed, return current settings
            if new_state == current_state:
                return ToggleDeveloperModeResult(
                    success=True,
                    user_settings=current_settings,
                    developer_mode_enabled=current_state,
                    api_access_enabled=current_settings.developer_mode.use_gemini,
                    warning_message=None,
                )

            # Update developer mode
            updated_settings = current_settings.toggle_developer_mode()

            # Save updated settings
            saved_settings = await self.user_repository.save_user_settings(
                updated_settings
            )

            # Generate appropriate warning message
            warning_message = self._generate_warning_message(new_state, saved_settings)

            # Emit developer mode toggled event
            await self._publish_event(
                create_developer_mode_toggled_event(
                    user_id=saved_settings.user_id,
                    developer_mode_enabled=saved_settings.developer_mode.enabled,
                    api_access_enabled=saved_settings.developer_mode.use_gemini,
                    previous_state=current_state,
                    toggle_source="domain_service",
                    warning_acknowledged=False,
                )
            )

            # Emit service availability changed events
            await self._emit_service_availability_events(
                saved_settings.user_id, current_state, new_state
            )

            self.logger.info(
                f"Successfully toggled developer mode for user {saved_settings.user_id} "
                f"from {current_state} to {new_state} (API access: {saved_settings.developer_mode.use_gemini})"
            )

            return ToggleDeveloperModeResult(
                success=True,
                user_settings=saved_settings,
                developer_mode_enabled=saved_settings.developer_mode.enabled,
                api_access_enabled=saved_settings.developer_mode.use_gemini,
                warning_message=warning_message,
            )

        except RepositoryError as e:
            error_msg = f"Repository error toggling developer mode: {e}"
            self.logger.error(error_msg)

            # Try to return current settings if available
            try:
                current_settings = await self.user_repository.load_user_settings(
                    request.user_id
                )
                if current_settings:
                    return ToggleDeveloperModeResult(
                        success=False,
                        user_settings=current_settings,
                        developer_mode_enabled=current_settings.developer_mode.enabled,
                        api_access_enabled=current_settings.developer_mode.use_gemini,
                        error_message=error_msg,
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to load current settings during error handling: {e}"
                )
                # Fall through to default error handling

            # Return default settings with error
            default_settings = UserSettings.create_default(request.user_id)
            return ToggleDeveloperModeResult(
                success=False,
                user_settings=default_settings,
                developer_mode_enabled=False,
                api_access_enabled=False,
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Unexpected error toggling developer mode: {e}"
            self.logger.error(error_msg)

            # Return default settings with error
            default_settings = UserSettings.create_default(request.user_id)
            return ToggleDeveloperModeResult(
                success=False,
                user_settings=default_settings,
                developer_mode_enabled=False,
                api_access_enabled=False,
                error_message=error_msg,
            )

    def _validate_request(self, request: ToggleDeveloperModeRequest) -> None:
        """Validate the toggle developer mode request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If request is invalid
        """
        if not isinstance(request, ToggleDeveloperModeRequest):
            raise ValidationError(
                "Request must be a ToggleDeveloperModeRequest instance"
            )

        if not isinstance(request.user_id, int):
            raise ValidationError("user_id must be an integer")

        if request.user_id < 1:
            raise ValidationError("user_id must be positive")

        if request.enable is not None and not isinstance(request.enable, bool):
            raise ValidationError("enable must be None or boolean")

    def _generate_warning_message(
        self, new_state: bool, settings: UserSettings
    ) -> str | None:
        """Generate appropriate warning message for developer mode changes.

        Args:
            new_state: New developer mode state
            settings: Updated user settings

        Returns:
            Warning message if applicable, None otherwise
        """
        if new_state and settings.developer_mode.use_gemini:
            return (
                "⚠️ Developer mode enabled with API access. "
                "AI operations (dataset generation, image processing) will use "
                "Google Gemini API and may incur charges. "
                "Monitor your usage in the Google Cloud Console."
            )
        elif new_state and not settings.developer_mode.use_gemini:
            return (
                "✅ Developer mode enabled. "
                "Advanced features are now available. "
                "API access is disabled to prevent unexpected charges."
            )
        elif not new_state:
            return (
                "✅ Developer mode disabled. "
                "API access and advanced features are now restricted. "
                "Dataset generation and image processing are unavailable."
            )
        else:
            return None

    async def _emit_service_availability_events(
        self, user_id: int, old_state: bool, new_state: bool
    ) -> None:
        """Emit service availability changed events for affected services.

        Args:
            user_id: User ID
            old_state: Previous developer mode state
            new_state: New developer mode state
        """
        services_affected = [
            "BuildDataset",
            "ProcessImage",
            "GenerateAnswer",
            "DatasetGeneration",
            "ImageProcessing",
        ]

        for service_name in services_affected:
            await self._publish_event(
                ServiceAvailabilityChangedEvent(
                    user_id=user_id,
                    service_name=service_name,
                    previously_available=old_state,
                    currently_available=new_state,
                    availability_reason="developer_mode",
                )
            )
