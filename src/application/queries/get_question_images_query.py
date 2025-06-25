"""Query handler for getting question images following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.domain.shared.repositories import ImageRepository

logger = logging.getLogger(__name__)


@dataclass
class GetQuestionImagesQuery:
    """Query for getting images associated with a question."""

    question_id: int
    include_metadata: bool = True


@dataclass
class QuestionImageData:
    """Data structure for a single question image."""

    filename: str
    data: bytes | None = None
    metadata: dict[str, Any] | None = None
    exists: bool = False


@dataclass
class GetQuestionImagesResult:
    """Result of getting question images."""

    success: bool
    images: list[QuestionImageData] | None = None
    terminal_capabilities: dict[str, bool] | None = None
    error_message: str | None = None


class GetQuestionImagesQueryHandler:
    """Handler for getting question images using CQRS pattern."""

    def __init__(self, image_repository: ImageRepository):
        """Initialize with image repository."""
        self.image_repository = image_repository

    async def handle(self, query: GetQuestionImagesQuery) -> GetQuestionImagesResult:
        """Handle the query to get images for a question."""
        try:
            # Build expected image filenames for the question
            # Questions can have multiple images: q{id}_1.png, q{id}_2.png, etc.
            image_patterns = [
                f"q{query.question_id}_1.png",
                f"q{query.question_id}_2.png",
                f"q{query.question_id}_3.png",
                f"q{query.question_id}_4.png",
            ]

            images = []
            found_any = False

            for pattern in image_patterns:
                image_path = f"data/images/{pattern}"

                # Check if image exists
                exists = await self.image_repository.validate_image_exists(image_path)

                if exists:
                    found_any = True
                    # Load image data
                    image_data = await self.image_repository.get_image_data(image_path)

                    # Get metadata if requested
                    metadata = None
                    if query.include_metadata:
                        metadata = await self.image_repository.get_image_metadata(
                            image_path
                        )

                    images.append(
                        QuestionImageData(
                            filename=pattern,
                            data=image_data,
                            metadata=metadata,
                            exists=True,
                        )
                    )
                else:
                    # Still include non-existing images for completeness
                    images.append(QuestionImageData(filename=pattern, exists=False))

            # Get terminal capabilities for image display
            terminal_capabilities = None
            if hasattr(self.image_repository, "get_terminal_capabilities"):
                terminal_capabilities = (
                    await self.image_repository.get_terminal_capabilities()
                )

            if found_any:
                return GetQuestionImagesResult(
                    success=True,
                    images=images,
                    terminal_capabilities=terminal_capabilities,
                )
            else:
                return GetQuestionImagesResult(
                    success=False,
                    images=images,
                    terminal_capabilities=terminal_capabilities,
                    error_message=f"No images found for question {query.question_id}",
                )

        except Exception as e:
            logger.error(f"Error getting images for question {query.question_id}: {e}")
            return GetQuestionImagesResult(
                success=False, error_message=f"Failed to get question images: {e}"
            )


@dataclass
class GetAvailableImagesQuery:
    """Query for listing all available images."""

    directory: str = "data/images"


@dataclass
class GetAvailableImagesResult:
    """Result of listing available images."""

    success: bool
    image_files: list[str] | None = None
    total_count: int = 0
    error_message: str | None = None


class GetAvailableImagesQueryHandler:
    """Handler for listing available images using CQRS pattern."""

    def __init__(self, image_repository: ImageRepository):
        """Initialize with image repository."""
        self.image_repository = image_repository

    async def handle(self, query: GetAvailableImagesQuery) -> GetAvailableImagesResult:
        """Handle the query to list available images."""
        try:
            image_files = await self.image_repository.list_available_images(
                query.directory
            )

            return GetAvailableImagesResult(
                success=True, image_files=image_files, total_count=len(image_files)
            )

        except Exception as e:
            logger.error(f"Error listing available images in {query.directory}: {e}")
            return GetAvailableImagesResult(
                success=False, error_message=f"Failed to list images: {e}"
            )
