"""Application service for building the complete dataset."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from src.domain.content.events.content_events import BatchContentProcessedEvent
from src.domain.content.models.answer_models import (
    AnswerGenerationRequest,
    ImageDescription,
    MultilingualAnswer,
    QuestionImageMappingRequest,
)
from src.domain.content.services.create_image_mapping import CreateImageMapping
from src.domain.content.services.generate_answer import GenerateAnswer
from src.domain.content.services.process_image import ProcessImage
from src.infrastructure.messaging.event_bus import EventBus
from src.infrastructure.repositories.content_repository import ContentRepository

logger = logging.getLogger(__name__)


class ContentBuilderService:
    """Application service that orchestrates the content building process."""

    def __init__(
        self,
        event_bus: EventBus,
        repository: ContentRepository | None = None,
    ):
        """Initialize the content builder service."""
        self.event_bus = event_bus
        self.repository = repository or ContentRepository()

        # Initialize domain services
        self.generate_answer = GenerateAnswer(event_bus)
        self.process_image = ProcessImage(event_bus)
        self.create_mapping = CreateImageMapping(event_bus)

    async def build_complete_dataset(
        self,
        force_rebuild: bool = False,
        multilingual: bool = True,
        batch_size: int = 10,
    ) -> bool:
        """Build the complete multilingual dataset with image mappings."""
        try:
            # Load or create checkpoint
            checkpoint_data = await self.repository.load_checkpoint()
            if force_rebuild:
                checkpoint_data = self._create_new_checkpoint()

            # Step 1: Load questions from extraction checkpoint
            questions = await self.repository.load_extraction_questions()
            checkpoint_data["total_questions"] = len(questions)
            logger.info(f"Loaded {len(questions)} questions from extraction checkpoint")

            # Step 2: Process images and create mappings
            if not checkpoint_data.get("images_processed", False):
                logger.info("Processing images and creating mappings...")
                (
                    question_image_mapping,
                    image_descriptions,
                ) = await self._process_all_images(questions, checkpoint_data)
                checkpoint_data["images_processed"] = True
                await self.repository.save_checkpoint(checkpoint_data)
            else:
                logger.info("Loading existing image mappings...")
                raw_mapping = checkpoint_data.get("question_image_mapping", {})
                # Convert string keys to integers for proper lookup
                question_image_mapping = {int(k): v for k, v in raw_mapping.items()}
                image_descriptions = await self.repository.load_image_descriptions(
                    checkpoint_data
                )

            # Step 3: Generate multilingual answers
            if multilingual:
                answers = await self._generate_all_answers(
                    questions=questions,
                    question_image_mapping=question_image_mapping,
                    image_descriptions=image_descriptions,
                    checkpoint_data=checkpoint_data,
                    batch_size=batch_size,
                )
            else:
                # Skip multilingual generation for testing
                answers = []

            # Step 4: Save to final dataset format
            await self._save_final_dataset(
                questions, answers, question_image_mapping, image_descriptions
            )

            # Mark as completed
            checkpoint_data["state"] = "completed"
            checkpoint_data["completed_at"] = datetime.now(UTC).isoformat()
            await self.repository.save_checkpoint(checkpoint_data)

            logger.info("✓ Successfully built complete multilingual dataset")
            return True

        except Exception as e:
            logger.error(f"Failed to build dataset: {e}")
            return False

    async def _process_all_images(
        self, questions: list[dict[str, Any]], checkpoint_data: dict[str, Any]
    ) -> tuple[dict[int, list[str]], dict[str, ImageDescription]]:
        """Process all images and create comprehensive mappings."""
        logger.info("Starting comprehensive image processing...")

        # Get all available images
        available_images = await self.repository.get_available_images()
        logger.info(
            f"Found {sum(len(imgs) for imgs in available_images.values())} images "
            f"across {len(available_images)} pages"
        )

        # Create question-to-image mapping
        mapping_request = QuestionImageMappingRequest(
            questions=questions,
            available_images=available_images,
        )
        mapping_result = await self.create_mapping.call(mapping_request)

        if not mapping_result.success:
            raise RuntimeError(
                f"Failed to create image mappings: {mapping_result.error_message}"
            )

        question_image_mapping = mapping_result.mappings

        # Create basic image descriptions to avoid API timeouts
        image_descriptions = self._create_basic_image_descriptions(available_images)

        # Save to checkpoint
        checkpoint_data["question_image_mapping"] = {
            str(k): v for k, v in question_image_mapping.items()
        }
        checkpoint_data["image_descriptions"] = {
            path: {
                "path": desc.path,
                "description": desc.description,
                "visual_elements": desc.visual_elements,
                "context": desc.context,
                "question_relevance": desc.question_relevance,
            }
            for path, desc in image_descriptions.items()
        }

        logger.info(f"Processed {len(image_descriptions)} images")
        logger.info(f"Created mappings for {len(question_image_mapping)} questions")

        return question_image_mapping, image_descriptions

    async def _generate_all_answers(
        self,
        questions: list[dict[str, Any]],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
        checkpoint_data: dict[str, Any],
        batch_size: int,
    ) -> list[MultilingualAnswer]:
        """Generate multilingual answers for all questions."""
        logger.info("Starting multilingual answer generation...")

        completed_answers = checkpoint_data.get("completed_answers", {})
        all_answers = []

        # Process questions in batches
        for i in range(0, len(questions), batch_size):
            batch = questions[i : i + batch_size]
            batch_start_time = time.time()

            # Filter out already completed questions
            new_questions = [
                q for q in batch if str(q.get("id", 0)) not in completed_answers
            ]

            if not new_questions:
                logger.info(f"Skipping batch {i // batch_size + 1} (all completed)")
                # Load existing answers
                for q in batch:
                    qid = str(q.get("id", 0))
                    if qid in completed_answers:
                        answer = await self.repository.deserialize_answer(
                            completed_answers[qid]
                        )
                        all_answers.append(answer)
                continue

            logger.info(
                f"Processing batch {i // batch_size + 1}: {len(new_questions)} new questions"
            )

            try:
                batch_answers = await self._generate_batch_answers(
                    questions=new_questions,
                    question_image_mapping=question_image_mapping,
                    image_descriptions=image_descriptions,
                )

                # Save answers to checkpoint
                for answer in batch_answers:
                    serialized = await self.repository.serialize_answer(answer)
                    completed_answers[str(answer.question_id)] = serialized
                    all_answers.append(answer)

                checkpoint_data["completed_answers"] = completed_answers
                await self.repository.save_checkpoint(checkpoint_data)

                # Publish batch processed event
                batch_time_ms = int((time.time() - batch_start_time) * 1000)
                await self.event_bus.publish(
                    BatchContentProcessedEvent(
                        batch_type="answers",
                        batch_size=len(new_questions),
                        successful_count=len(batch_answers),
                        failed_count=len(new_questions) - len(batch_answers),
                        processing_time_ms=batch_time_ms,
                    )
                )

                logger.info(
                    f"Completed batch {i // batch_size + 1}: "
                    f"{len(batch_answers)} answers generated"
                )

            except Exception as e:
                logger.error(f"Failed to process batch {i // batch_size + 1}: {e}")
                continue

        logger.info(f"Generated {len(all_answers)} multilingual answers")
        return all_answers

    async def _generate_batch_answers(
        self,
        questions: list[dict[str, Any]],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
    ) -> list[MultilingualAnswer]:
        """Generate answers for a batch of questions."""
        answers = []

        for question in questions:
            question_id = question.get("id", 0)

            # Get images for this question
            images = None
            if question_id in question_image_mapping:
                image_paths = question_image_mapping[question_id]
                images = [
                    image_descriptions[path]
                    for path in image_paths
                    if path in image_descriptions
                ]

            # Create answer generation request
            request = AnswerGenerationRequest(
                question_id=question_id,
                question_text=question.get("question", ""),
                options={
                    "A": question.get("option_a", ""),
                    "B": question.get("option_b", ""),
                    "C": question.get("option_c", ""),
                    "D": question.get("option_d", ""),
                },
                correct_answer=question.get("correct_answer", ""),
                category=question.get("category", ""),
                images=images,
            )

            try:
                result = await self.generate_answer.call(request)
                if result.success and result.answer:
                    answers.append(result.answer)
                    logger.info(
                        f"Generated multilingual answer for question {question_id}"
                    )

                # Throttle API calls
                time.sleep(1)

            except Exception as e:
                logger.error(
                    f"Failed to generate answer for question {question_id}: {e}"
                )
                continue

        return answers

    async def _save_final_dataset(
        self,
        questions: list[dict[str, Any]],
        answers: list[MultilingualAnswer],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
    ) -> None:
        """Save the final dataset."""
        # Create answer lookup
        answer_lookup = {answer.question_id: answer for answer in answers}

        # Build final dataset
        final_questions = []

        for question in questions:
            question_id = question.get("id", 0)

            # Convert extraction format to final format
            final_question = {
                "id": question_id,
                "question": question.get("question", ""),
                "options": [
                    question.get("option_a", ""),
                    question.get("option_b", ""),
                    question.get("option_c", ""),
                    question.get("option_d", ""),
                ],
                "correct": question.get("correct_answer", ""),
                "category": question.get("category", ""),
                "difficulty": question.get("difficulty", "medium"),
            }

            # Add images if available
            if question_id in question_image_mapping:
                image_paths = question_image_mapping[question_id]
                final_question["images"] = []

                for path in image_paths:
                    if path in image_descriptions:
                        desc = image_descriptions[path]
                        final_question["images"].append(
                            {
                                "path": path.replace("data/", ""),  # Relative path
                                "description": desc.description,
                                "context": desc.context,
                            }
                        )

            # Add multilingual answers if available
            if question_id in answer_lookup:
                answer = answer_lookup[question_id]
                final_question["answers"] = self._format_multilingual_answers(answer)

                if answer.rag_sources:
                    final_question["rag_sources"] = answer.rag_sources

            final_questions.append(final_question)

        # Save to file
        await self.repository.save_final_dataset(final_questions)

    def _format_multilingual_answers(
        self, answer: MultilingualAnswer
    ) -> dict[str, Any]:
        """Format multilingual answers for storage."""
        languages = ["en", "de", "tr", "uk", "ar"]
        formatted = {}

        for lang in languages:
            formatted[lang] = {
                "explanation": answer.explanations.get(lang, ""),
                "why_others_wrong": answer.why_others_wrong.get(lang, {}),
                "key_concept": answer.key_concept.get(lang, ""),
                "mnemonic": answer.mnemonic.get(lang, "") if answer.mnemonic else "",
            }

        return formatted

    def _create_basic_image_descriptions(
        self, available_images: dict[int, list[str]]
    ) -> dict[str, ImageDescription]:
        """Create basic image descriptions without AI calls to avoid timeouts."""
        descriptions = {}

        for page_num, images in available_images.items():
            for img_path in images:
                # Create basic description based on page and context
                if page_num in [9, 78, 85]:
                    desc = f"Coat of arms or emblem from page {page_num}"
                    context = "German federal or state symbols"
                elif page_num in range(112, 188, 5):  # State pages
                    desc = f"State-specific image from page {page_num}"
                    context = "German federal state symbols or landmarks"
                else:
                    desc = f"Official exam image from page {page_num}"
                    context = "German integration exam visual content"

                descriptions[img_path] = ImageDescription(
                    path=img_path,
                    description=desc,
                    visual_elements=["official", "educational"],
                    context=context,
                    question_relevance="Used in integration exam questions about German symbols and geography",
                )

        return descriptions

    def _create_new_checkpoint(self) -> dict[str, Any]:
        """Create a new checkpoint structure."""
        return {
            "state": "in_progress",
            "started_at": datetime.now(UTC).isoformat(),
            "images_processed": False,
            "completed_answers": {},
            "total_questions": 0,
            "question_image_mapping": {},
            "image_descriptions": {},
        }

    async def get_build_status(self) -> dict[str, Any]:
        """Get current build status."""
        checkpoint = await self.repository.load_checkpoint()

        if checkpoint.get("state") == "not_started":
            return checkpoint

        completed_count = len(checkpoint.get("completed_answers", {}))
        total_count = checkpoint.get("total_questions", 0)

        return {
            "state": checkpoint.get("state", "unknown"),
            "started_at": checkpoint.get("started_at"),
            "completed_at": checkpoint.get("completed_at"),
            "images_processed": checkpoint.get("images_processed", False),
            "completed_answers": completed_count,
            "total_questions": total_count,
            "progress_percent": (completed_count / total_count * 100)
            if total_count > 0
            else 0,
        }
