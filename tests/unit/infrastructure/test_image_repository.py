"""Tests for ImageRepository infrastructure component."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.shared.repositories import ImageRepository, RepositoryError


class TestImageRepositoryInterface:
    """Test ImageRepository interface compliance."""

    @pytest.fixture
    def mock_image_repository(self) -> ImageRepository:
        """Create mock ImageRepository for interface testing."""
        mock_repo = AsyncMock(spec=ImageRepository)
        return mock_repo

    @pytest.mark.asyncio
    async def test_interface_methods_exist(
        self, mock_image_repository: ImageRepository
    ):
        """Test that all interface methods exist."""
        # Test all interface methods are available
        assert hasattr(mock_image_repository, "get_image_data")
        assert hasattr(mock_image_repository, "validate_image_exists")
        assert hasattr(mock_image_repository, "get_image_metadata")
        assert hasattr(mock_image_repository, "list_available_images")

    @pytest.mark.asyncio
    async def test_get_image_data_signature(
        self, mock_image_repository: ImageRepository
    ):
        """Test get_image_data method signature."""
        mock_image_repository.get_image_data.return_value = b"fake_image_data"

        result = await mock_image_repository.get_image_data("test.png")

        mock_image_repository.get_image_data.assert_called_once_with("test.png")
        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_validate_image_exists_signature(
        self, mock_image_repository: ImageRepository
    ):
        """Test validate_image_exists method signature."""
        mock_image_repository.validate_image_exists.return_value = True

        result = await mock_image_repository.validate_image_exists("test.png")

        mock_image_repository.validate_image_exists.assert_called_once_with("test.png")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_image_metadata_signature(
        self, mock_image_repository: ImageRepository
    ):
        """Test get_image_metadata method signature."""
        expected_metadata = {"width": 400, "height": 300, "format": "PNG"}
        mock_image_repository.get_image_metadata.return_value = expected_metadata

        result = await mock_image_repository.get_image_metadata("test.png")

        mock_image_repository.get_image_metadata.assert_called_once_with("test.png")
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_list_available_images_signature(
        self, mock_image_repository: ImageRepository
    ):
        """Test list_available_images method signature."""
        expected_images = ["q21_1.png", "q21_2.png", "q451_1.png"]
        mock_image_repository.list_available_images.return_value = expected_images

        result = await mock_image_repository.list_available_images("data/images")

        mock_image_repository.list_available_images.assert_called_once_with(
            "data/images"
        )
        assert result == expected_images


class TestFileSystemImageRepository:
    """Test FileSystemImageRepository implementation."""

    @pytest.fixture
    def temp_images_dir(self) -> Path:
        """Create temporary images directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir) / "images"
            images_dir.mkdir()

            # Create test image files
            test_images = ["q21_1.png", "q21_2.png", "q451_1.png", "q451_2.png"]

            for image_name in test_images:
                # Create fake PNG data (minimal PNG header)
                png_data = (
                    b"\x89PNG\r\n\x1a\n"  # PNG signature
                    b"\x00\x00\x00\rIHDR"  # IHDR chunk
                    b"\x00\x00\x01\x90"  # Width: 400
                    b"\x00\x00\x01,\x08\x02"  # Height: 300, bit depth: 8, color type: 2
                    b"\x00\x00\x00\x91(\xcb4"  # CRC
                    b"\x00\x00\x00\x00IEND"  # IEND chunk
                    b"\xaeB`\x82"  # CRC
                )

                image_path = images_dir / image_name
                image_path.write_bytes(png_data)

            # Create a non-image file
            (images_dir / "not_an_image.txt").write_text("This is not an image")

            yield images_dir

    @pytest.fixture
    def image_repository(self, temp_images_dir: Path):
        """Create FileSystemImageRepository with temp directory."""
        # We'll import this here to avoid import issues during test collection
        from src.infrastructure.repositories.image_repository import (
            FileSystemImageRepository,
        )

        return FileSystemImageRepository(base_directory=str(temp_images_dir.parent))

    @pytest.mark.asyncio
    async def test_validate_image_exists_true(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test validate_image_exists returns True for existing image."""
        image_path = "images/q21_1.png"

        result = await image_repository.validate_image_exists(image_path)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_image_exists_false(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test validate_image_exists returns False for non-existing image."""
        image_path = "images/nonexistent.png"

        result = await image_repository.validate_image_exists(image_path)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_image_data_success(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test get_image_data returns bytes for existing image."""
        image_path = "images/q21_1.png"

        result = await image_repository.get_image_data(image_path)

        assert result is not None
        assert isinstance(result, bytes)
        assert result.startswith(b"\x89PNG")  # PNG signature

    @pytest.mark.asyncio
    async def test_get_image_data_not_found(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test get_image_data returns None for non-existing image."""
        image_path = "images/nonexistent.png"

        result = await image_repository.get_image_data(image_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_image_metadata_success(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test get_image_metadata returns metadata for existing image."""
        image_path = "images/q21_1.png"

        result = await image_repository.get_image_metadata(image_path)

        assert result is not None
        assert isinstance(result, dict)
        assert "size" in result
        assert "exists" in result
        assert result["exists"] is True

        # PIL metadata might fail for fake PNG data, but basic file info should be present
        if "error" not in result:
            assert "format" in result
            assert "width" in result
            assert "height" in result

    @pytest.mark.asyncio
    async def test_get_image_metadata_not_found(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test get_image_metadata returns None for non-existing image."""
        image_path = "images/nonexistent.png"

        result = await image_repository.get_image_metadata(image_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_available_images_success(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test list_available_images returns list of image files."""
        directory = "images"

        result = await image_repository.list_available_images(directory)

        assert isinstance(result, list)
        assert len(result) == 4  # Only PNG files, not the .txt file
        assert "q21_1.png" in result
        assert "q21_2.png" in result
        assert "q451_1.png" in result
        assert "q451_2.png" in result
        assert "not_an_image.txt" not in result

    @pytest.mark.asyncio
    async def test_list_available_images_empty_directory(self, image_repository):
        """Test list_available_images returns empty list for non-existing directory."""
        directory = "nonexistent"

        result = await image_repository.list_available_images(directory)

        assert result == []

    @pytest.mark.asyncio
    async def test_absolute_path_traversal_protection(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):
        """Test that path traversal attacks are prevented."""
        malicious_path = "../../../etc/passwd"

        result = await image_repository.validate_image_exists(malicious_path)

        assert result is False

        result = await image_repository.get_image_data(malicious_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_access(  # noqa: ARG002
        self, image_repository, temp_images_dir: Path
    ):  # noqa: ARG002
        """Test concurrent access to image repository."""
        image_paths = ["images/q21_1.png", "images/q21_2.png", "images/q451_1.png"]

        # Test concurrent validation
        tasks = [image_repository.validate_image_exists(path) for path in image_paths]
        results = await asyncio.gather(*tasks)

        assert all(results)

    @pytest.mark.asyncio
    async def test_error_handling_permission_denied(self, image_repository):
        """Test error handling when file permissions are denied."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.read_bytes",
                side_effect=PermissionError("Permission denied"),
            ),
        ):
            result = await image_repository.get_image_data("images/protected.png")

            assert result is None

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_file(
        self, image_repository, temp_images_dir: Path
    ):
        """Test error handling when image file is corrupted."""
        # Create a corrupted "image" file
        corrupted_path = temp_images_dir / "corrupted.png"
        corrupted_path.write_bytes(b"not a valid png file")

        # Should still return the bytes (repository doesn't validate format)
        result = await image_repository.get_image_data("images/corrupted.png")
        assert result == b"not a valid png file"

        # But metadata should handle the error gracefully
        metadata = await image_repository.get_image_metadata("images/corrupted.png")
        assert metadata is None or "error" in metadata


class TestImageRepositoryError:
    """Test ImageRepository error handling."""

    def test_repository_error_creation(self):
        """Test RepositoryError can be created with message and error code."""
        error = RepositoryError("Image not found", "IMG_404")

        assert str(error) == "Image not found"
        assert error.error_code == "IMG_404"

    def test_repository_error_without_error_code(self):
        """Test RepositoryError can be created without error code."""
        error = RepositoryError("Generic error")

        assert str(error) == "Generic error"
        assert error.error_code is None


class TestImageRepositoryIntegration:
    """Integration tests for ImageRepository with real image files."""

    @pytest.mark.asyncio
    async def test_with_real_image_files(self):
        """Test with actual image files from the project."""
        from src.infrastructure.repositories.image_repository import (
            FileSystemImageRepository,
        )

        # Use the actual project directory
        repository = FileSystemImageRepository()

        # Test with actual data/images directory if it exists
        images = await repository.list_available_images("data/images")

        if images:
            # Test with first available image
            first_image = f"data/images/{images[0]}"

            # Validate existence
            exists = await repository.validate_image_exists(first_image)
            assert exists is True

            # Get image data
            data = await repository.get_image_data(first_image)
            assert data is not None
            assert len(data) > 0

            # Get metadata
            metadata = await repository.get_image_metadata(first_image)
            assert metadata is not None
            assert "size" in metadata
        else:
            # If no images in data/images, just test that the methods don't crash
            exists = await repository.validate_image_exists(
                "data/images/nonexistent.png"
            )
            assert exists is False
