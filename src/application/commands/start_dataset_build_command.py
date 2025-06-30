"""Command for starting dataset build following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.content.services.build_dataset import (
    BuildDataset,
    BuildDatasetRequest,
)
from src.domain.shared.repositories import QuestionRepository, UserRepository
from src.domain.shared.services import EventBusInterface

logger = logging.getLogger(__name__)


@dataclass
class StartDatasetBuildCommand:
    """Command to start dataset build."""

    user_id: int
    use_cache: bool = True
    include_images: bool = True
    target_languages: list[str] | None = None
    force_rebuild: bool = False


@dataclass
class StartDatasetBuildCommandResult:
    """Result of start dataset build command."""

    success: bool
    build_id: str | None = None
    progress_message: str | None = None
    error_message: str | None = None


class StartDatasetBuildCommandHandler:
    """Command handler for starting dataset build using domain service."""

    def __init__(
        self,
        user_repository: UserRepository,
        question_repository: QuestionRepository,
        event_bus: EventBusInterface,
    ):
        """Initialize with repositories and event bus."""
        self.build_dataset_service = BuildDataset(
            question_repository=question_repository,
            event_bus=event_bus,
            user_repository=user_repository,
        )

    async def handle(
        self, command: StartDatasetBuildCommand
    ) -> StartDatasetBuildCommandResult:
        """Handle start dataset build command using domain service."""
        try:
            # Create domain service request
            request = BuildDatasetRequest(
                force_rebuild=command.force_rebuild,
                multilingual=bool(
                    command.target_languages and len(command.target_languages) > 1
                ),
                batch_size=10,  # Default batch size
                enable_image_processing=command.include_images,
                include_rag_sources=False,  # Legacy parameter
            )

            # Call domain service
            result = await self.build_dataset_service.call(request)

            # Convert domain result to command result
            return StartDatasetBuildCommandResult(
                success=result.success,
                build_id=result.final_dataset_path,  # Using final_dataset_path as build_id
                progress_message=f"Build completed: {result.final_dataset_path}"
                if result.success
                else None,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"Error in StartDatasetBuildCommandHandler: {e}")
            return StartDatasetBuildCommandResult(
                success=False,
                error_message=f"Failed to start dataset build: {e}",
            )
