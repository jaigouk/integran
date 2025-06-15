"""Domain service for creating question-to-image mappings."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.content.events.content_events import QuestionImagesMappedEvent
from src.domain.content.models.answer_models import (
    QuestionImageMappingRequest,
    QuestionImageMappingResult,
)
from src.domain.shared.services import DomainService
from src.infrastructure.messaging.event_bus import EventBus

logger = logging.getLogger(__name__)


class CreateImageMapping(
    DomainService[QuestionImageMappingRequest, QuestionImageMappingResult]
):
    """Domain service for creating comprehensive question-to-image mappings."""

    def __init__(self, event_bus: EventBus):
        """Initialize the image mapping service."""
        super().__init__(event_bus)
        # Known manual corrections for specific questions
        self.known_corrections = {
            21: 9,  # German coat of arms
            29: 78,  # State coat of arms
        }

    async def call(
        self, request: QuestionImageMappingRequest
    ) -> QuestionImageMappingResult:
        """Create comprehensive mapping ensuring all images are used."""
        logger.info(
            f"Creating image mappings for {len(request.questions)} questions "
            f"and {sum(len(imgs) for imgs in request.available_images.values())} images"
        )

        try:
            question_image_mapping: dict[int, list[str]] = {}
            used_images: set[str] = set()

            # Step 1: Map questions with Bild options to images
            for question in request.questions:
                question_id = question.get("id", 0)
                options = [
                    question.get("option_a", ""),
                    question.get("option_b", ""),
                    question.get("option_c", ""),
                    question.get("option_d", ""),
                ]

                # Check if this has "Bild" options
                bild_options = [opt for opt in options if "bild" in opt.lower()]
                if len(bild_options) >= 2:  # This is an image question
                    # Find the best matching page with images
                    best_page = self._find_best_image_page_for_question(
                        question, request.available_images, used_images
                    )

                    if best_page and best_page in request.available_images:
                        images = request.available_images[best_page]
                        # Take up to 4 images for this question
                        question_images: list[str] = []
                        for img in images:
                            if img not in used_images and len(question_images) < len(
                                bild_options
                            ):
                                question_images.append(img)
                                used_images.add(img)

                        if question_images:
                            question_image_mapping[question_id] = question_images
                            logger.info(
                                f"✓ Q{question_id}: Mapped {len(question_images)} images from page {best_page}"
                            )

            # Step 2: Identify unused images
            all_images = set()
            for images in request.available_images.values():
                all_images.update(images)

            unmapped_images = list(all_images - used_images)

            # Calculate metrics
            total_images = len(all_images)
            mapped_images = len(used_images)
            mapped_questions = len(question_image_mapping)

            # Log summary
            if unmapped_images:
                logger.warning(
                    f"⚠️  {len(unmapped_images)} images not mapped to questions"
                )
                for img in sorted(unmapped_images)[:5]:  # Show first 5
                    logger.warning(f"  - {img}")
                if len(unmapped_images) > 5:
                    logger.warning(f"  ... and {len(unmapped_images) - 5} more")

            logger.info(
                f"Successfully mapped {mapped_images}/{total_images} images "
                f"to {mapped_questions} questions"
            )

            # Publish event
            await self.event_bus.publish(
                QuestionImagesMappedEvent(
                    total_questions=len(request.questions),
                    mapped_questions=mapped_questions,
                    total_images=total_images,
                    mapped_images=mapped_images,
                    unmapped_images=len(unmapped_images),
                )
            )

            return QuestionImageMappingResult(
                success=True,
                mappings=question_image_mapping,
                unmapped_images=unmapped_images,
            )

        except Exception as e:
            logger.error(f"Failed to create image mappings: {e}")
            return QuestionImageMappingResult(
                success=False,
                mappings={},
                unmapped_images=[],
                error_message=str(e),
            )

    def _find_best_image_page_for_question(
        self,
        question: dict[str, Any],
        available_images: dict[int, list[str]],
        used_images: set[str],
    ) -> int | None:
        """Find the best page with images for a given question."""
        question_id = question.get("id", 0)
        extracted_page: int = question.get("page_number", 0)
        question_text = question.get("question", "").lower()

        # Use manual corrections if available
        if question_id in self.known_corrections:
            return self.known_corrections[question_id]

        # Try extracted page first
        if extracted_page in available_images:
            available_imgs = [
                img
                for img in available_images[extracted_page]
                if img not in used_images
            ]
            if available_imgs:
                return extracted_page

        # Content-based matching for specific topics
        if "wappen" in question_text or "bundesrepublik" in question_text:
            for page in [9, 78, 85]:  # Common coat of arms pages
                if page in available_images:
                    available_imgs = [
                        img for img in available_images[page] if img not in used_images
                    ]
                    if available_imgs:
                        return page

        if "flagge" in question_text:
            for page in [9, 78, 85]:  # Common flag pages
                if page in available_images:
                    available_imgs = [
                        img for img in available_images[page] if img not in used_images
                    ]
                    if available_imgs:
                        return page

        # Find any page with available images
        for page, images in available_images.items():
            available_imgs = [img for img in images if img not in used_images]
            if available_imgs:
                return page

        return None

    def _is_image_question(self, question: dict[str, Any]) -> bool:
        """Check if a question involves images."""
        # Check for "Bild X" patterns in options
        options = [
            question.get("option_a", ""),
            question.get("option_b", ""),
            question.get("option_c", ""),
            question.get("option_d", ""),
        ]

        bild_pattern_count = sum(
            1
            for option in options
            if "bild" in option.lower() and any(char.isdigit() for char in option)
        )

        # Check for image-related keywords in question text
        question_text = question.get("question", "").lower()
        image_keywords = ["wappen", "flagge", "symbol", "bild", "abbildung", "zeigt"]

        has_image_keywords = any(keyword in question_text for keyword in image_keywords)

        return bild_pattern_count >= 2 or has_image_keywords
