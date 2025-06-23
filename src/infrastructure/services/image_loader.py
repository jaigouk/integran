"""Image loading service for handling file system operations."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ImageLoader:
    """Service for loading images from the file system."""

    def __init__(self, base_directory: str = "."):
        """Initialize with base directory for image loading.

        Args:
            base_directory: Base directory for resolving relative paths
        """
        self.base_directory = Path(base_directory).resolve()

    async def load_image(self, path: str) -> bytes | None:
        """Load image file from disk.

        Args:
            path: Relative or absolute path to image file

        Returns:
            Image bytes if successful, None if file not found or error
        """
        try:
            image_path = self._resolve_path(path)

            if not image_path.exists():
                logger.debug(f"Image file not found: {image_path}")
                return None

            if not image_path.is_file():
                logger.warning(f"Path is not a file: {image_path}")
                return None

            # Use executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            image_data = await loop.run_in_executor(None, image_path.read_bytes)

            logger.debug(
                f"Successfully loaded image: {image_path} ({len(image_data)} bytes)"
            )
            return image_data

        except PermissionError:
            logger.error(f"Permission denied reading image: {path}")
            return None
        except OSError as e:
            logger.error(f"OS error reading image {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading image {path}: {e}")
            return None

    async def check_terminal_support(self) -> dict[str, bool]:
        """Check terminal capabilities for image display.

        Returns:
            Dictionary with capability flags
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            capabilities = await loop.run_in_executor(
                None, self._detect_terminal_capabilities
            )

            logger.debug(f"Terminal capabilities detected: {capabilities}")
            return capabilities

        except Exception as e:
            logger.error(f"Error detecting terminal capabilities: {e}")
            return {
                "sixel": False,
                "kitty": False,
                "iterm2": False,
                "windows_terminal": False,
                "textual_image": False,
            }

    async def get_image_info(self, path: str) -> dict[str, Any] | None:
        """Get image metadata without loading full image data.

        Args:
            path: Path to image file

        Returns:
            Image metadata dict or None if error
        """
        try:
            image_path = self._resolve_path(path)

            if not image_path.exists():
                return None

            # Get basic file info
            stat = image_path.stat()

            info = {
                "path": str(image_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "exists": True,
            }

            # Try to get image-specific metadata using PIL if available
            try:
                loop = asyncio.get_event_loop()
                with_pil = await loop.run_in_executor(
                    None, self._get_pil_metadata, image_path
                )
                info.update(with_pil)

            except ImportError:
                logger.debug("PIL not available, using basic file info only")
            except Exception as e:
                logger.debug(f"Error getting PIL metadata for {path}: {e}")

            return info

        except Exception as e:
            logger.error(f"Error getting image info for {path}: {e}")
            return None

    async def list_images(self, directory: str = "data/images") -> list[str]:
        """List available image files in directory.

        Args:
            directory: Directory to scan for images

        Returns:
            List of image filenames
        """
        try:
            dir_path = self._resolve_path(directory)

            if not dir_path.exists() or not dir_path.is_dir():
                logger.debug(f"Directory not found: {dir_path}")
                return []

            # Common image extensions
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

            # Use executor for file system operations
            loop = asyncio.get_event_loop()
            image_files = await loop.run_in_executor(
                None, self._scan_directory_for_images, dir_path, image_extensions
            )

            logger.debug(f"Found {len(image_files)} images in {dir_path}")
            return sorted(image_files)

        except Exception as e:
            logger.error(f"Error listing images in {directory}: {e}")
            return []

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base directory with security checks.

        Args:
            path: Input path (relative or absolute)

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path tries to escape base directory
        """
        path_obj = Path(path)

        # If absolute path, use as-is but check it's within allowed area
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            # Resolve relative to base directory
            resolved = (self.base_directory / path_obj).resolve()

        # Security check: ensure resolved path is within base directory
        # This prevents path traversal attacks
        try:
            resolved.relative_to(self.base_directory)
        except ValueError as e:
            # Path is outside base directory
            logger.warning(f"Path traversal attempt blocked: {path} -> {resolved}")
            raise ValueError(f"Path outside allowed directory: {path}") from e

        return resolved

    def _detect_terminal_capabilities(self) -> dict[str, bool]:
        """Detect terminal image display capabilities (blocking operation).

        Returns:
            Dictionary with capability flags
        """
        capabilities = {
            "sixel": False,
            "kitty": False,
            "iterm2": False,
            "windows_terminal": False,
            "textual_image": False,
        }

        # Check environment variables for terminal type
        term = os.environ.get("TERM", "").lower()
        term_program = os.environ.get("TERM_PROGRAM", "")

        # Kitty terminal
        if "kitty" in term:
            capabilities["kitty"] = True

        # iTerm2
        if term_program == "iTerm.app":
            capabilities["iterm2"] = True

        # Windows Terminal (version 1.22+ supports Sixel)
        if os.environ.get("WT_SESSION"):
            capabilities["windows_terminal"] = True
            capabilities["sixel"] = True

        # Sixel support detection
        if any(x in term for x in ["xterm", "screen", "tmux"]) and "sixel" in term:
            capabilities["sixel"] = True

        # Check if textual-image is available
        try:
            import textual_image  # noqa: F401  # type: ignore

            capabilities["textual_image"] = True
        except ImportError:
            pass

        return capabilities

    def _get_pil_metadata(self, image_path: Path) -> dict[str, Any]:
        """Get image metadata using PIL (blocking operation).

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with PIL metadata
        """
        from PIL import Image

        try:
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ("RGBA", "LA")
                    or "transparency" in img.info,
                }
        except Exception as e:
            logger.debug(f"PIL error for {image_path}: {e}")
            return {"error": str(e)}

    def _scan_directory_for_images(
        self, dir_path: Path, extensions: set[str]
    ) -> list[str]:
        """Scan directory for image files (blocking operation).

        Args:
            dir_path: Directory to scan
            extensions: Set of allowed file extensions

        Returns:
            List of image filenames
        """
        image_files = []

        try:
            for file_path in dir_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    image_files.append(file_path.name)
        except PermissionError:
            logger.warning(f"Permission denied scanning directory: {dir_path}")
        except OSError as e:
            logger.warning(f"OS error scanning directory {dir_path}: {e}")

        return image_files
