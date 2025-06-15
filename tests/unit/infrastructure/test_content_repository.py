"""Tests for ContentRepository infrastructure component."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.domain.content.models.answer_models import (
    ImageDescription,
    MultilingualAnswer,
)
from src.infrastructure.repositories.content_repository import ContentRepository


class TestContentRepository:
    """Test ContentRepository class."""

    @pytest.fixture
    def temp_data_dir(self) -> Path:
        """Create temporary data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def repository(self, temp_data_dir: Path) -> ContentRepository:
        """Create ContentRepository with temp directory."""
        return ContentRepository(data_dir=temp_data_dir)

    def test_initialization_with_default_dir(self) -> None:
        """Test repository initialization with default directory."""
        repo = ContentRepository()
        assert repo.data_dir == Path("data")
        assert repo.checkpoint_file == Path("data/dataset_checkpoint.json")
        assert repo.extraction_file == Path("data/extraction_checkpoint.json")
        assert repo.questions_file == Path("data/questions.json")
        assert repo.final_dataset_file == Path("data/final_dataset.json")

    def test_initialization_with_custom_dir(self, temp_data_dir: Path) -> None:
        """Test repository initialization with custom directory."""
        repo = ContentRepository(data_dir=temp_data_dir)
        assert repo.data_dir == temp_data_dir
        assert repo.checkpoint_file == temp_data_dir / "dataset_checkpoint.json"

    @pytest.mark.asyncio
    async def test_load_extraction_questions_success(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test successful loading of extraction questions."""
        # Create extraction checkpoint file
        extraction_data = {
            "state": "completed",
            "questions": [
                {"id": 1, "question": "Test question 1"},
                {"id": 2, "question": "Test question 2"},
            ],
        }
        extraction_file = temp_data_dir / "extraction_checkpoint.json"
        with open(extraction_file, "w") as f:
            json.dump(extraction_data, f)

        questions = await repository.load_extraction_questions()
        assert len(questions) == 2
        assert questions[0]["id"] == 1
        assert questions[1]["question"] == "Test question 2"

    @pytest.mark.asyncio
    async def test_load_extraction_questions_file_not_found(
        self, repository: ContentRepository
    ) -> None:
        """Test loading extraction questions when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Extraction checkpoint not found"):
            await repository.load_extraction_questions()

    @pytest.mark.asyncio
    async def test_load_extraction_questions_incomplete_state(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test loading extraction questions with incomplete state."""
        # Create extraction checkpoint with wrong state
        extraction_data = {"state": "in_progress", "questions": []}
        extraction_file = temp_data_dir / "extraction_checkpoint.json"
        with open(extraction_file, "w") as f:
            json.dump(extraction_data, f)

        with pytest.raises(ValueError, match="Extraction checkpoint is not completed"):
            await repository.load_extraction_questions()

    @pytest.mark.asyncio
    async def test_load_checkpoint_new_file(
        self, repository: ContentRepository
    ) -> None:
        """Test loading checkpoint creates new one if file doesn't exist."""
        checkpoint = await repository.load_checkpoint()

        assert checkpoint["state"] == "in_progress"
        assert "started_at" in checkpoint
        assert checkpoint["images_processed"] is False
        assert checkpoint["completed_answers"] == {}
        assert checkpoint["total_questions"] == 0

    @pytest.mark.asyncio
    async def test_load_checkpoint_existing_file(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test loading existing checkpoint file."""
        existing_data = {
            "state": "in_progress",
            "total_questions": 100,
            "completed_answers": {"1": "answer1"},
        }
        checkpoint_file = temp_data_dir / "dataset_checkpoint.json"
        with open(checkpoint_file, "w") as f:
            json.dump(existing_data, f)

        checkpoint = await repository.load_checkpoint()
        assert checkpoint["state"] == "in_progress"
        assert checkpoint["total_questions"] == 100
        assert checkpoint["completed_answers"] == {"1": "answer1"}

    @pytest.mark.asyncio
    async def test_save_checkpoint(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test saving checkpoint to disk."""
        checkpoint_data = {
            "state": "completed",
            "total_questions": 50,
            "completed_answers": {"1": "test"},
        }

        await repository.save_checkpoint(checkpoint_data)

        # Verify file was created and contains correct data
        checkpoint_file = temp_data_dir / "dataset_checkpoint.json"
        assert checkpoint_file.exists()

        with open(checkpoint_file) as f:
            saved_data = json.load(f)

        assert saved_data == checkpoint_data

    @pytest.mark.asyncio
    async def test_save_final_dataset(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test saving final dataset."""
        questions = [
            {"id": 1, "question": "Test 1", "correct": "A"},
            {"id": 2, "question": "Test 2", "correct": "B"},
        ]

        await repository.save_final_dataset(questions)

        # Verify file was created
        questions_file = temp_data_dir / "questions.json"
        assert questions_file.exists()

        with open(questions_file, encoding="utf-8") as f:
            saved_questions = json.load(f)

        assert len(saved_questions) == 2
        assert saved_questions[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_available_images_no_directory(
        self, repository: ContentRepository
    ) -> None:
        """Test getting available images when directory doesn't exist."""
        page_images = await repository.get_available_images()
        assert page_images == {}

    @pytest.mark.asyncio
    async def test_get_available_images_with_files(
        self, repository: ContentRepository, temp_data_dir: Path
    ) -> None:
        """Test getting available images with image files."""
        # Create images directory with test files
        images_dir = temp_data_dir / "images"
        images_dir.mkdir()

        # Create test image files
        (images_dir / "page_1_img_1.jpg").touch()
        (images_dir / "page_1_img_2.png").touch()
        (images_dir / "page_2_img_1.jpg").touch()
        (images_dir / "invalid_name.jpg").touch()  # Should be ignored

        page_images = await repository.get_available_images()

        assert 1 in page_images
        assert 2 in page_images
        assert len(page_images[1]) == 2
        assert len(page_images[2]) == 1
        assert "images/page_1_img_1.jpg" in page_images[1]
        assert "images/page_2_img_1.jpg" in page_images[2]

    @pytest.mark.asyncio
    async def test_load_image_descriptions(self, repository: ContentRepository) -> None:
        """Test loading image descriptions from checkpoint."""
        checkpoint_data = {
            "image_descriptions": {
                "test.jpg": {
                    "path": "test.jpg",
                    "description": "Test description",
                    "visual_elements": ["element1", "element2"],
                    "context": "Test context",
                    "question_relevance": "high",
                }
            }
        }

        descriptions = await repository.load_image_descriptions(checkpoint_data)

        assert "test.jpg" in descriptions
        desc = descriptions["test.jpg"]
        assert isinstance(desc, ImageDescription)
        assert desc.path == "test.jpg"
        assert desc.description == "Test description"
        assert desc.visual_elements == ["element1", "element2"]

    @pytest.mark.asyncio
    async def test_serialize_answer(self, repository: ContentRepository) -> None:
        """Test serializing MultilingualAnswer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={"en": "English explanation"},
            why_others_wrong={"en": {"B": "Wrong because..."}},
            key_concept={"en": "Key concept"},
            mnemonic={"en": "Memory aid"},
            image_context={"test.jpg": "Context"},
            rag_sources=["source1", "source2"],
        )

        serialized = await repository.serialize_answer(answer)

        assert serialized["question_id"] == 1
        assert serialized["correct_answer"] == "A"
        assert serialized["explanations"] == {"en": "English explanation"}
        assert serialized["rag_sources"] == ["source1", "source2"]

    @pytest.mark.asyncio
    async def test_deserialize_answer(self, repository: ContentRepository) -> None:
        """Test deserializing to MultilingualAnswer."""
        data = {
            "question_id": 1,
            "correct_answer": "A",
            "explanations": {"en": "English explanation"},
            "why_others_wrong": {"en": {"B": "Wrong"}},
            "key_concept": {"en": "Concept"},
            "mnemonic": {"en": "Memory aid"},
            "image_context": {"test.jpg": "Context"},
            "rag_sources": ["source1"],
        }

        answer = await repository.deserialize_answer(data)

        assert isinstance(answer, MultilingualAnswer)
        assert answer.question_id == 1
        assert answer.correct_answer == "A"
        assert answer.explanations == {"en": "English explanation"}
        assert answer.rag_sources == ["source1"]

    @pytest.mark.asyncio
    async def test_deserialize_answer_minimal_data(
        self, repository: ContentRepository
    ) -> None:
        """Test deserializing with minimal required data."""
        data = {
            "question_id": 1,
            "correct_answer": "A",
            "explanations": {"en": "Explanation"},
            "why_others_wrong": {"en": {"B": "Wrong"}},
            "key_concept": {"en": "Concept"},
        }

        answer = await repository.deserialize_answer(data)

        assert answer.question_id == 1
        assert answer.mnemonic is None
        assert answer.image_context is None
        assert answer.rag_sources == []

    def test_create_new_checkpoint_structure(
        self, repository: ContentRepository
    ) -> None:
        """Test new checkpoint structure creation."""
        checkpoint = repository._create_new_checkpoint()

        assert checkpoint["state"] == "in_progress"
        assert "started_at" in checkpoint
        assert checkpoint["images_processed"] is False
        assert checkpoint["completed_answers"] == {}
        assert checkpoint["total_questions"] == 0
        assert checkpoint["question_image_mapping"] == {}
        assert checkpoint["image_descriptions"] == {}

        # Verify started_at is a valid ISO format datetime string
        from datetime import datetime

        try:
            datetime.fromisoformat(checkpoint["started_at"])
        except ValueError:
            pytest.fail(
                f"started_at is not a valid ISO format: {checkpoint['started_at']}"
            )
