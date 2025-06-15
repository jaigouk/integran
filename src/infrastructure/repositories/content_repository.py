"""Repository for content-related data access."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.domain.content.models.answer_models import (
    ImageDescription,
    MultilingualAnswer,
)

logger = logging.getLogger(__name__)


class ContentRepository:
    """Repository for managing content data persistence."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize the content repository."""
        self.data_dir = data_dir or Path("data")
        self.checkpoint_file = self.data_dir / "dataset_checkpoint.json"
        self.extraction_file = self.data_dir / "extraction_checkpoint.json"
        self.questions_file = self.data_dir / "questions.json"
        self.final_dataset_file = self.data_dir / "final_dataset.json"

    async def load_extraction_questions(self) -> list[dict[str, Any]]:
        """Load questions from extraction checkpoint."""
        if not self.extraction_file.exists():
            raise FileNotFoundError(
                f"Extraction checkpoint not found: {self.extraction_file}"
            )

        with open(self.extraction_file) as f:
            data = json.load(f)

        if data.get("state") != "completed":
            raise ValueError("Extraction checkpoint is not completed")

        questions_list = data.get("questions", [])
        return questions_list  # type: ignore[no-any-return]

    async def load_checkpoint(self) -> dict[str, Any]:
        """Load dataset building checkpoint."""
        if not self.checkpoint_file.exists():
            return self._create_new_checkpoint()

        with open(self.checkpoint_file) as f:
            checkpoint_data = json.load(f)
            return checkpoint_data  # type: ignore[no-any-return]

    async def save_checkpoint(self, checkpoint_data: dict[str, Any]) -> None:
        """Save checkpoint to disk."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    async def save_final_dataset(self, questions: list[dict[str, Any]]) -> None:
        """Save the final dataset."""
        with open(self.questions_file, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(questions)} questions to {self.questions_file}")

    async def get_available_images(self) -> dict[int, list[str]]:
        """Get all available images organized by page number."""
        images_dir = self.data_dir / "images"
        page_images: dict[int, list[str]] = {}

        if not images_dir.exists():
            logger.warning("Images directory not found")
            return page_images

        for img_file in images_dir.glob("page_*_img_*"):
            try:
                page_num = int(img_file.stem.split("_")[1])
                if page_num not in page_images:
                    page_images[page_num] = []
                page_images[page_num].append(f"images/{img_file.name}")
            except (ValueError, IndexError):
                continue

        # Sort images for each page
        for page_num in page_images:
            page_images[page_num].sort()

        return page_images

    async def load_image_descriptions(
        self, checkpoint_data: dict[str, Any]
    ) -> dict[str, ImageDescription]:
        """Load image descriptions from checkpoint."""
        descriptions = {}
        for path, data in checkpoint_data.get("image_descriptions", {}).items():
            descriptions[path] = ImageDescription(
                path=data["path"],
                description=data["description"],
                visual_elements=data["visual_elements"],
                context=data["context"],
                question_relevance=data["question_relevance"],
            )
        return descriptions

    async def serialize_answer(self, answer: MultilingualAnswer) -> dict[str, Any]:
        """Serialize MultilingualAnswer for storage."""
        return {
            "question_id": answer.question_id,
            "correct_answer": answer.correct_answer,
            "explanations": answer.explanations,
            "why_others_wrong": answer.why_others_wrong,
            "key_concept": answer.key_concept,
            "mnemonic": answer.mnemonic,
            "image_context": answer.image_context,
            "rag_sources": answer.rag_sources,
        }

    async def deserialize_answer(self, data: dict[str, Any]) -> MultilingualAnswer:
        """Deserialize stored data back to MultilingualAnswer."""
        return MultilingualAnswer(
            question_id=data["question_id"],
            correct_answer=data["correct_answer"],
            explanations=data["explanations"],
            why_others_wrong=data["why_others_wrong"],
            key_concept=data["key_concept"],
            mnemonic=data.get("mnemonic"),
            image_context=data.get("image_context"),
            rag_sources=data.get("rag_sources", []),
        )

    def _create_new_checkpoint(self) -> dict[str, Any]:
        """Create a new checkpoint structure."""
        from datetime import UTC, datetime

        return {
            "state": "in_progress",
            "started_at": datetime.now(UTC).isoformat(),
            "images_processed": False,
            "completed_answers": {},
            "total_questions": 0,
            "question_image_mapping": {},
            "image_descriptions": {},
        }
