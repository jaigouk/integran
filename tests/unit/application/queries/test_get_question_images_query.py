"""Tests for GetQuestionImagesQuery and GetAvailableImagesQuery handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.queries.get_question_images_query import (
    GetAvailableImagesQuery,
    GetAvailableImagesQueryHandler,
    GetAvailableImagesResult,
    GetQuestionImagesQuery,
    GetQuestionImagesQueryHandler,
    GetQuestionImagesResult,
    QuestionImageData,
)
from src.domain.shared.repositories import ImageRepository


class TestGetQuestionImagesQuery:
    """Test GetQuestionImagesQuery data structure."""

    def test_query_creation_with_defaults(self):
        """Test creating query with default values."""
        query = GetQuestionImagesQuery(question_id=21)

        assert query.question_id == 21
        assert query.include_metadata is True

    def test_query_creation_with_custom_values(self):
        """Test creating query with custom values."""
        query = GetQuestionImagesQuery(question_id=451, include_metadata=False)

        assert query.question_id == 451
        assert query.include_metadata is False


class TestQuestionImageData:
    """Test QuestionImageData structure."""

    def test_image_data_creation(self):
        """Test creating image data structure."""
        data = QuestionImageData(
            filename="q21_1.png",
            data=b"fake_image_data",
            metadata={"width": 400, "height": 300},
            exists=True,
        )

        assert data.filename == "q21_1.png"
        assert data.data == b"fake_image_data"
        assert data.metadata == {"width": 400, "height": 300}
        assert data.exists is True

    def test_image_data_with_defaults(self):
        """Test creating image data with default values."""
        data = QuestionImageData(filename="q21_1.png")

        assert data.filename == "q21_1.png"
        assert data.data is None
        assert data.metadata is None
        assert data.exists is False


class TestGetQuestionImagesQueryHandler:
    """Test GetQuestionImagesQueryHandler business logic."""

    @pytest.fixture
    def mock_image_repository(self) -> ImageRepository:
        """Create mock image repository."""
        mock_repo = AsyncMock(spec=ImageRepository)
        mock_repo.get_terminal_capabilities = AsyncMock(
            return_value={
                "sixel": False,
                "kitty": True,
                "iterm2": False,
                "windows_terminal": False,
                "textual_image": True,
            }
        )
        return mock_repo

    @pytest.fixture
    def query_handler(
        self, mock_image_repository: ImageRepository
    ) -> GetQuestionImagesQueryHandler:
        """Create query handler with mock repository."""
        return GetQuestionImagesQueryHandler(mock_image_repository)

    @pytest.mark.asyncio
    async def test_handle_successful_single_image(
        self, query_handler, mock_image_repository
    ):
        """Test handling query with single existing image."""
        # Setup mock responses
        mock_image_repository.validate_image_exists.side_effect = [
            True,
            False,
            False,
            False,
        ]
        mock_image_repository.get_image_data.return_value = b"fake_png_data"
        mock_image_repository.get_image_metadata.return_value = {
            "width": 400,
            "height": 300,
            "format": "PNG",
        }

        query = GetQuestionImagesQuery(question_id=21)
        result = await query_handler.handle(query)

        assert result.success is True
        assert result.images is not None
        assert len(result.images) == 4  # All 4 patterns checked

        # First image should exist
        first_image = result.images[0]
        assert first_image.filename == "q21_1.png"
        assert first_image.exists is True
        assert first_image.data == b"fake_png_data"
        assert first_image.metadata == {"width": 400, "height": 300, "format": "PNG"}

        # Other images should not exist
        for i in range(1, 4):
            assert result.images[i].exists is False
            assert result.images[i].data is None
            assert result.images[i].metadata is None

        assert result.terminal_capabilities is not None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_handle_multiple_images(self, query_handler, mock_image_repository):
        """Test handling query with multiple existing images."""
        # Setup mock responses - first two images exist
        mock_image_repository.validate_image_exists.side_effect = [
            True,
            True,
            False,
            False,
        ]
        mock_image_repository.get_image_data.return_value = b"fake_png_data"
        mock_image_repository.get_image_metadata.return_value = {
            "width": 400,
            "height": 300,
        }

        query = GetQuestionImagesQuery(question_id=451)
        result = await query_handler.handle(query)

        assert result.success is True
        assert result.images is not None
        assert len(result.images) == 4

        # First two images should exist
        assert result.images[0].exists is True
        assert result.images[1].exists is True
        assert result.images[2].exists is False
        assert result.images[3].exists is False

        # Verify correct filenames
        assert result.images[0].filename == "q451_1.png"
        assert result.images[1].filename == "q451_2.png"
        assert result.images[2].filename == "q451_3.png"
        assert result.images[3].filename == "q451_4.png"

    @pytest.mark.asyncio
    async def test_handle_no_images_found(self, query_handler, mock_image_repository):
        """Test handling query when no images exist."""
        # Setup mock responses - no images exist
        mock_image_repository.validate_image_exists.return_value = False

        query = GetQuestionImagesQuery(question_id=999)
        result = await query_handler.handle(query)

        assert result.success is False
        assert result.error_message == "No images found for question 999"
        assert result.images is not None
        assert len(result.images) == 4

        # All images should not exist
        for image in result.images:
            assert image.exists is False

    @pytest.mark.asyncio
    async def test_handle_without_metadata(self, query_handler, mock_image_repository):
        """Test handling query without requesting metadata."""
        mock_image_repository.validate_image_exists.side_effect = [
            True,
            False,
            False,
            False,
        ]
        mock_image_repository.get_image_data.return_value = b"fake_png_data"

        query = GetQuestionImagesQuery(question_id=21, include_metadata=False)
        result = await query_handler.handle(query)

        assert result.success is True
        assert result.images[0].exists is True
        assert result.images[0].metadata is None

        # Should not call get_image_metadata
        mock_image_repository.get_image_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_repository_error(self, query_handler, mock_image_repository):
        """Test handling when repository raises an exception."""
        mock_image_repository.validate_image_exists.side_effect = Exception(
            "Database error"
        )

        query = GetQuestionImagesQuery(question_id=21)
        result = await query_handler.handle(query)

        assert result.success is False
        assert "Failed to get question images" in result.error_message
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_handle_repository_without_terminal_capabilities(
        self, mock_image_repository
    ):
        """Test handling with repository that doesn't have terminal capabilities method."""
        # Remove the terminal capabilities method
        delattr(mock_image_repository, "get_terminal_capabilities")

        query_handler = GetQuestionImagesQueryHandler(mock_image_repository)
        mock_image_repository.validate_image_exists.return_value = False

        query = GetQuestionImagesQuery(question_id=21)
        result = await query_handler.handle(query)

        assert result.terminal_capabilities is None


class TestGetAvailableImagesQuery:
    """Test GetAvailableImagesQuery data structure."""

    def test_query_creation_with_default(self):
        """Test creating query with default directory."""
        query = GetAvailableImagesQuery()

        assert query.directory == "data/images"

    def test_query_creation_with_custom_directory(self):
        """Test creating query with custom directory."""
        query = GetAvailableImagesQuery(directory="custom/path")

        assert query.directory == "custom/path"


class TestGetAvailableImagesQueryHandler:
    """Test GetAvailableImagesQueryHandler business logic."""

    @pytest.fixture
    def mock_image_repository(self) -> ImageRepository:
        """Create mock image repository."""
        return AsyncMock(spec=ImageRepository)

    @pytest.fixture
    def query_handler(
        self, mock_image_repository: ImageRepository
    ) -> GetAvailableImagesQueryHandler:
        """Create query handler with mock repository."""
        return GetAvailableImagesQueryHandler(mock_image_repository)

    @pytest.mark.asyncio
    async def test_handle_successful_listing(
        self, query_handler, mock_image_repository
    ):
        """Test successful image listing."""
        expected_images = ["q21_1.png", "q21_2.png", "q451_1.png", "q451_2.png"]
        mock_image_repository.list_available_images.return_value = expected_images

        query = GetAvailableImagesQuery()
        result = await query_handler.handle(query)

        assert result.success is True
        assert result.image_files == expected_images
        assert result.total_count == 4
        assert result.error_message is None

        mock_image_repository.list_available_images.assert_called_once_with(
            "data/images"
        )

    @pytest.mark.asyncio
    async def test_handle_empty_directory(self, query_handler, mock_image_repository):
        """Test handling empty directory."""
        mock_image_repository.list_available_images.return_value = []

        query = GetAvailableImagesQuery(directory="empty/dir")
        result = await query_handler.handle(query)

        assert result.success is True
        assert result.image_files == []
        assert result.total_count == 0
        assert result.error_message is None

        mock_image_repository.list_available_images.assert_called_once_with("empty/dir")

    @pytest.mark.asyncio
    async def test_handle_repository_error(self, query_handler, mock_image_repository):
        """Test handling when repository raises an exception."""
        mock_image_repository.list_available_images.side_effect = Exception(
            "Permission denied"
        )

        query = GetAvailableImagesQuery()
        result = await query_handler.handle(query)

        assert result.success is False
        assert "Failed to list images" in result.error_message
        assert "Permission denied" in result.error_message


class TestGetQuestionImagesResult:
    """Test GetQuestionImagesResult data structure."""

    def test_result_creation_success(self):
        """Test creating successful result."""
        images = [QuestionImageData(filename="q21_1.png", exists=True)]
        terminal_caps = {"kitty": True, "sixel": False}

        result = GetQuestionImagesResult(
            success=True, images=images, terminal_capabilities=terminal_caps
        )

        assert result.success is True
        assert result.images == images
        assert result.terminal_capabilities == terminal_caps
        assert result.error_message is None

    def test_result_creation_failure(self):
        """Test creating failure result."""
        result = GetQuestionImagesResult(success=False, error_message="No images found")

        assert result.success is False
        assert result.images is None
        assert result.terminal_capabilities is None
        assert result.error_message == "No images found"


class TestGetAvailableImagesResult:
    """Test GetAvailableImagesResult data structure."""

    def test_result_creation_success(self):
        """Test creating successful result."""
        image_files = ["q21_1.png", "q451_1.png"]

        result = GetAvailableImagesResult(
            success=True, image_files=image_files, total_count=2
        )

        assert result.success is True
        assert result.image_files == image_files
        assert result.total_count == 2
        assert result.error_message is None

    def test_result_creation_failure(self):
        """Test creating failure result."""
        result = GetAvailableImagesResult(
            success=False, error_message="Directory not found"
        )

        assert result.success is False
        assert result.image_files is None
        assert result.total_count == 0
        assert result.error_message == "Directory not found"
