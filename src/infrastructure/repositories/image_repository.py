"""Concrete implementation of ImageRepository interface."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.shared.repositories import ImageRepository
from src.infrastructure.services.image_loader import ImageLoader

logger = logging.getLogger(__name__)


class FileSystemImageRepository(ImageRepository):
    """File system implementation of ImageRepository interface."""

    def __init__(self, base_directory: str = "."):
        """Initialize with base directory for image loading.

        Args:
            base_directory: Base directory for resolving relative paths
        """
        self.image_loader = ImageLoader(base_directory)

    async def get_image_data(self, path: str) -> bytes | None:
        """Get image data by path.

        Args:
            path: Relative or absolute path to image file

        Returns:
            Image bytes if successful, None if error or not found
        """
        try:
            image_data = await self.image_loader.load_image(path)
            if image_data is not None:
                logger.debug(f"Successfully retrieved image data for: {path}")
            else:
                logger.debug(f"Image not found: {path}")
            return image_data

        except Exception as e:
            logger.error(f"Error getting image data for {path}: {e}")
            return None

    async def validate_image_exists(self, path: str) -> bool:
        """Check if image file exists.

        Args:
            path: Path to image file

        Returns:
            True if image exists and is accessible, False otherwise
        """
        try:
            # Use get_image_info which checks existence without loading full data
            info = await self.image_loader.get_image_info(path)
            exists = info is not None and info.get("exists", False)

            logger.debug(f"Image existence check for {path}: {exists}")
            return exists

        except Exception as e:
            logger.error(f"Error checking image existence for {path}: {e}")
            return False

    async def get_image_metadata(self, path: str) -> dict[str, Any] | None:
        """Get image metadata (size, format, etc.).

        Args:
            path: Path to image file

        Returns:
            Dictionary with image metadata or None if error
        """
        try:
            metadata = await self.image_loader.get_image_info(path)

            if metadata is not None:
                logger.debug(f"Retrieved metadata for {path}: {metadata.keys()}")
            else:
                logger.debug(f"No metadata available for: {path}")

            return metadata

        except Exception as e:
            logger.error(f"Error getting image metadata for {path}: {e}")
            return None

    async def list_available_images(self, directory: str = "data/images") -> list[str]:
        """List all available image files in directory.

        Args:
            directory: Directory to scan for images

        Returns:
            List of image filenames
        """
        try:
            images = await self.image_loader.list_images(directory)
            logger.debug(f"Found {len(images)} images in directory: {directory}")
            return images

        except Exception as e:
            logger.error(f"Error listing images in directory {directory}: {e}")
            return []

    async def get_terminal_capabilities(self) -> dict[str, bool]:
        """Get terminal image display capabilities.

        This is an additional method specific to this implementation
        that provides terminal capability information.

        Returns:
            Dictionary with terminal capability flags
        """
        try:
            capabilities = await self.image_loader.check_terminal_support()
            logger.debug(f"Terminal capabilities: {capabilities}")
            return capabilities

        except Exception as e:
            logger.error(f"Error checking terminal capabilities: {e}")
            return {
                "sixel": False,
                "kitty": False,
                "iterm2": False,
                "windows_terminal": False,
                "textual_image": False,
            }
