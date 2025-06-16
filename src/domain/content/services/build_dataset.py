"""BuildDataset domain service for comprehensive dataset building and orchestration.

This domain service encapsulates the business logic for building complete multilingual
datasets, including image processing, question mapping, answer generation, and final
dataset compilation following the Domain-Driven Design pattern.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.infrastructure.repositories.content_repository import ContentRepository

from src.domain.content.events.content_events import (
    BatchContentProcessedEvent,
    QuestionImagesMappedEvent,
)
from src.domain.content.models.answer_models import (
    AnswerGenerationRequest,
    ImageDescription,
    MultilingualAnswer,
    QuestionImageMappingRequest,
)
from src.domain.content.services.create_image_mapping import CreateImageMapping
from src.domain.content.services.generate_answer import GenerateAnswer
from src.domain.content.services.process_image import ProcessImage
from src.domain.shared.services import (
    BusinessRuleViolationError,
    DomainService,
    ValidationError,
    log_domain_operation,
)
from src.infrastructure.messaging.event_bus import EventBus

logger = logging.getLogger(__name__)


class DatasetBuildState(str, Enum):
    """States of dataset building process."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMAGES_PROCESSING = "images_processing"
    ANSWERS_GENERATING = "answers_generating"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BuildDatasetRequest:
    """Request DTO for building a complete dataset."""

    force_rebuild: bool = False
    multilingual: bool = True
    batch_size: int = 10
    enable_image_processing: bool = True
    include_rag_sources: bool = False  # Legacy parameter, ignored

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.batch_size > 50:
            raise ValueError("batch_size must not exceed 50 to avoid API limits")


@dataclass
class DatasetBuildProgress:
    """Progress tracking for dataset building."""

    state: DatasetBuildState
    started_at: datetime | None
    completed_at: datetime | None
    total_questions: int
    questions_processed: int
    images_processed: bool
    completed_answers: int
    current_batch: int
    estimated_completion_time: datetime | None
    error_message: str | None = None


@dataclass
class BuildDatasetResult:
    """Result DTO for dataset building operation."""

    success: bool
    final_dataset_path: str | None
    build_progress: DatasetBuildProgress
    statistics: dict[str, Any]
    error_message: str | None = None


@dataclass
class GetBuildStatusRequest:
    """Request DTO for getting build status."""

    include_detailed_progress: bool = True


@dataclass
class GetBuildStatusResult:
    """Result DTO for build status query."""

    success: bool
    build_progress: DatasetBuildProgress
    detailed_status: dict[str, Any]
    error_message: str | None = None


class BuildDataset(
    DomainService[
        BuildDatasetRequest | GetBuildStatusRequest,
        BuildDatasetResult | GetBuildStatusResult,
    ]
):
    """Domain service for complete dataset building and content generation.

    This service encapsulates all business logic for:
    - Coordinating the complete dataset building pipeline
    - Processing images and creating question-image mappings
    - Generating multilingual answers for all questions
    - Managing build state and progress tracking
    - Finalizing and saving the complete dataset
    """

    def __init__(
        self,
        repository: ContentRepository,
        event_bus: EventBus,
        generate_answer: GenerateAnswer | None = None,
        process_image: ProcessImage | None = None,
        create_mapping: CreateImageMapping | None = None,
    ) -> None:
        """Initialize the dataset building domain service.

        Args:
            repository: Content repository for data persistence
            event_bus: Event bus for publishing domain events
            generate_answer: Optional GenerateAnswer service (for dependency injection)
            process_image: Optional ProcessImage service (for dependency injection)
            create_mapping: Optional CreateImageMapping service (for dependency injection)
        """
        super().__init__(event_bus)
        self.repository = repository

        # Use provided services or lazy initialization
        self._generate_answer = generate_answer
        self._process_image = process_image
        self._create_mapping = create_mapping

    @property
    def generate_answer(self) -> GenerateAnswer:
        """Get GenerateAnswer service with lazy initialization."""
        if self._generate_answer is None:
            self._generate_answer = GenerateAnswer(self.event_bus)
        return self._generate_answer

    @property
    def process_image(self) -> ProcessImage:
        """Get ProcessImage service with lazy initialization."""
        if self._process_image is None:
            self._process_image = ProcessImage(self.event_bus)
        return self._process_image

    @property
    def create_mapping(self) -> CreateImageMapping:
        """Get CreateImageMapping service with lazy initialization."""
        if self._create_mapping is None:
            self._create_mapping = CreateImageMapping(self.event_bus)
        return self._create_mapping

    @log_domain_operation
    async def call(
        self,
        request: BuildDatasetRequest | GetBuildStatusRequest,
    ) -> BuildDatasetResult | GetBuildStatusResult:
        """Execute dataset building operation based on request type.

        Args:
            request: Domain request for dataset building or status query

        Returns:
            Result of the dataset building operation

        Raises:
            ValidationError: If request validation fails
            BusinessRuleViolationError: If business rules are violated
        """
        try:
            if isinstance(request, BuildDatasetRequest):
                return await self._build_dataset(request)
            elif isinstance(request, GetBuildStatusRequest):
                return await self._get_build_status(request)
            else:
                raise ValidationError(f"Unsupported request type: {type(request)}")

        except Exception as e:
            logger.error(f"Failed to process dataset request: {e}")
            if isinstance(request, BuildDatasetRequest):
                return BuildDatasetResult(
                    success=False,
                    final_dataset_path=None,
                    build_progress=self._create_error_progress(str(e)),
                    statistics={},
                    error_message=str(e),
                )
            else:  # GetBuildStatusRequest
                return GetBuildStatusResult(
                    success=False,
                    build_progress=self._create_error_progress(str(e)),
                    detailed_status={},
                    error_message=str(e),
                )

    async def _build_dataset(self, request: BuildDatasetRequest) -> BuildDatasetResult:
        """Build a complete multilingual dataset with all components."""
        logger.info(
            f"Starting dataset build: multilingual={request.multilingual}, "
            f"batch_size={request.batch_size}, force_rebuild={request.force_rebuild}"
        )

        build_start_time = datetime.now(UTC)

        # Load or create checkpoint
        checkpoint_data = await self.repository.load_checkpoint()
        if request.force_rebuild:
            checkpoint_data = self._create_new_checkpoint()
            logger.info("Force rebuild enabled - starting fresh")

        # Step 1: Load questions from extraction checkpoint
        questions = await self.repository.load_extraction_questions()
        if not questions:
            raise BusinessRuleViolationError(
                "No extraction questions found. Run PDF extraction first."
            )

        checkpoint_data["total_questions"] = len(questions)
        checkpoint_data["state"] = DatasetBuildState.IN_PROGRESS.value
        await self.repository.save_checkpoint(checkpoint_data)

        logger.info(f"Loaded {len(questions)} questions from extraction checkpoint")

        try:
            # Step 2: Process images and create mappings
            if request.enable_image_processing and not checkpoint_data.get(
                "images_processed", False
            ):
                logger.info("Processing images and creating mappings...")
                checkpoint_data["state"] = DatasetBuildState.IMAGES_PROCESSING.value
                await self.repository.save_checkpoint(checkpoint_data)

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
            answers = []
            if request.multilingual:
                logger.info("Starting multilingual answer generation...")
                checkpoint_data["state"] = DatasetBuildState.ANSWERS_GENERATING.value
                await self.repository.save_checkpoint(checkpoint_data)

                answers = await self._generate_all_answers(
                    questions=questions,
                    question_image_mapping=question_image_mapping,
                    image_descriptions=image_descriptions,
                    checkpoint_data=checkpoint_data,
                    batch_size=request.batch_size,
                )
            else:
                logger.info("Skipping multilingual generation")

            # Step 4: Finalize and save dataset
            logger.info("Finalizing dataset...")
            checkpoint_data["state"] = DatasetBuildState.FINALIZING.value
            await self.repository.save_checkpoint(checkpoint_data)

            final_dataset_path = await self._save_final_dataset(
                questions, answers, question_image_mapping, image_descriptions
            )

            # Mark as completed
            build_end_time = datetime.now(UTC)
            checkpoint_data["state"] = DatasetBuildState.COMPLETED.value
            checkpoint_data["completed_at"] = build_end_time.isoformat()
            await self.repository.save_checkpoint(checkpoint_data)

            # Calculate final statistics
            build_duration = (build_end_time - build_start_time).total_seconds()
            statistics = {
                "total_questions": len(questions),
                "questions_with_answers": len(answers),
                "questions_with_images": len(question_image_mapping),
                "total_images_processed": len(image_descriptions),
                "build_duration_seconds": int(build_duration),
                "build_duration_minutes": round(build_duration / 60, 2),
                "completion_rate": round(len(answers) / len(questions) * 100, 1)
                if answers
                else 0,
            }

            logger.info("✓ Successfully built complete multilingual dataset")
            logger.info(
                f"Build completed in {statistics['build_duration_minutes']} minutes"
            )

            return BuildDatasetResult(
                success=True,
                final_dataset_path=final_dataset_path,
                build_progress=self._create_progress_from_checkpoint(checkpoint_data),
                statistics=statistics,
            )

        except Exception as e:
            # Mark as failed
            checkpoint_data["state"] = DatasetBuildState.FAILED.value
            checkpoint_data["error_message"] = str(e)
            await self.repository.save_checkpoint(checkpoint_data)
            raise BusinessRuleViolationError(f"Dataset build failed: {e}") from e

    async def _get_build_status(
        self, request: GetBuildStatusRequest
    ) -> GetBuildStatusResult:
        """Get current build status and progress information."""
        checkpoint = await self.repository.load_checkpoint()

        build_progress = self._create_progress_from_checkpoint(checkpoint)

        detailed_status = {}
        if request.include_detailed_progress:
            completed_count = len(checkpoint.get("completed_answers", {}))
            total_count = checkpoint.get("total_questions", 0)

            detailed_status = {
                "state": checkpoint.get("state", "unknown"),
                "started_at": checkpoint.get("started_at"),
                "completed_at": checkpoint.get("completed_at"),
                "images_processed": checkpoint.get("images_processed", False),
                "completed_answers": completed_count,
                "total_questions": total_count,
                "progress_percent": (completed_count / total_count * 100)
                if total_count > 0
                else 0,
                "estimated_completion": build_progress.estimated_completion_time.isoformat()
                if build_progress.estimated_completion_time
                else None,
            }

        return GetBuildStatusResult(
            success=True,
            build_progress=build_progress,
            detailed_status=detailed_status,
        )

    async def _process_all_images(
        self, questions: list[dict[str, Any]], checkpoint_data: dict[str, Any]
    ) -> tuple[dict[int, list[str]], dict[str, ImageDescription]]:
        """Process all images and create comprehensive mappings."""
        logger.info("Starting comprehensive image processing...")

        # Get all available images
        available_images = await self.repository.get_available_images()
        total_images = sum(len(imgs) for imgs in available_images.values())
        logger.info(f"Found {total_images} images across {len(available_images)} pages")

        # Create question-to-image mapping using domain service
        mapping_request = QuestionImageMappingRequest(
            questions=questions,
            available_images=available_images,
        )
        mapping_result = await self.create_mapping.call(mapping_request)

        if not mapping_result.success:
            raise BusinessRuleViolationError(
                f"Failed to create image mappings: {mapping_result.error_message}"
            )

        question_image_mapping = mapping_result.mappings

        # Create optimized image descriptions to avoid API timeouts
        image_descriptions = self._create_optimized_image_descriptions(available_images)

        # Save to checkpoint
        checkpoint_data["question_image_mapping"] = {
            str(k): v for k, v in question_image_mapping.items()
        }
        checkpoint_data["image_descriptions"] = {
            path: self._serialize_image_description(desc)
            for path, desc in image_descriptions.items()
        }

        # Publish mapping completion event
        await self.event_bus.publish(
            QuestionImagesMappedEvent(
                total_questions=len(questions),
                mapped_questions=len(question_image_mapping),
                total_images=total_images,
                mapped_images=len(image_descriptions),
                unmapped_images=total_images - len(image_descriptions),
            )
        )

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
        """Generate multilingual answers for all questions with batch processing."""
        logger.info("Starting multilingual answer generation...")

        completed_answers = checkpoint_data.get("completed_answers", {})
        all_answers = []

        # Process questions in batches
        total_batches = (len(questions) + batch_size - 1) // batch_size

        for i in range(0, len(questions), batch_size):
            batch = questions[i : i + batch_size]
            batch_number = i // batch_size + 1
            batch_start_time = time.time()

            # Filter out already completed questions
            new_questions = [
                q for q in batch if str(q.get("id", 0)) not in completed_answers
            ]

            if not new_questions:
                logger.info(
                    f"Skipping batch {batch_number}/{total_batches} (all completed)"
                )
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
                f"Processing batch {batch_number}/{total_batches}: "
                f"{len(new_questions)} new questions"
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
                checkpoint_data["current_batch"] = batch_number
                await self.repository.save_checkpoint(checkpoint_data)

                # Publish batch completion event
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
                    f"Completed batch {batch_number}/{total_batches}: "
                    f"{len(batch_answers)} answers generated in "
                    f"{batch_time_ms / 1000:.1f}s"
                )

            except Exception as e:
                logger.error(f"Failed to process batch {batch_number}: {e}")
                continue

        logger.info(f"Generated {len(all_answers)} multilingual answers")
        return all_answers

    async def _generate_batch_answers(
        self,
        questions: list[dict[str, Any]],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
    ) -> list[MultilingualAnswer]:
        """Generate answers for a batch of questions using domain service."""
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
                    logger.debug(f"Generated answer for question {question_id}")

                # Throttle API calls to respect rate limits
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
    ) -> str:
        """Save the final dataset in the required format."""
        # Create answer lookup for efficient access
        answer_lookup = {answer.question_id: answer for answer in answers}

        # Build final dataset structure
        final_questions = []

        for question in questions:
            question_id = question.get("id", 0)

            # Convert extraction format to final dataset format
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

                # Include RAG sources if available (legacy support)
                if hasattr(answer, "rag_sources") and answer.rag_sources:
                    final_question["rag_sources"] = answer.rag_sources

            final_questions.append(final_question)

        # Save to repository and return path
        dataset_path = await self.repository.save_final_dataset(final_questions)
        logger.info(f"Saved final dataset with {len(final_questions)} questions")

        return dataset_path

    def _format_multilingual_answers(
        self, answer: MultilingualAnswer
    ) -> dict[str, Any]:
        """Format multilingual answers for final dataset storage."""
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

    def _create_optimized_image_descriptions(
        self, available_images: dict[int, list[str]]
    ) -> dict[str, ImageDescription]:
        """Create optimized image descriptions without expensive AI calls."""
        descriptions = {}

        for page_num, images in available_images.items():
            for img_path in images:
                # Create contextual description based on page number and content
                if page_num in [9, 78, 85]:
                    desc = f"Coat of arms or official emblem from page {page_num}"
                    context = "German federal or state symbols and heraldry"
                elif page_num in range(112, 188, 5):  # State-specific pages
                    desc = f"State-specific symbol or landmark from page {page_num}"
                    context = (
                        "German federal state symbols, landmarks, or cultural elements"
                    )
                else:
                    desc = f"Official examination image from page {page_num}"
                    context = "German integration exam visual content and educational material"

                descriptions[img_path] = ImageDescription(
                    path=img_path,
                    description=desc,
                    visual_elements=["official", "educational", "governmental"],
                    context=context,
                    question_relevance="Visual content used in German integration exam questions about symbols, geography, and cultural knowledge",
                )

        return descriptions

    def _serialize_image_description(self, desc: ImageDescription) -> dict[str, Any]:
        """Serialize ImageDescription for checkpoint storage."""
        return {
            "path": desc.path,
            "description": desc.description,
            "visual_elements": desc.visual_elements,
            "context": desc.context,
            "question_relevance": desc.question_relevance,
        }

    def _create_new_checkpoint(self) -> dict[str, Any]:
        """Create a new checkpoint structure for tracking build progress."""
        return {
            "state": DatasetBuildState.NOT_STARTED.value,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "images_processed": False,
            "completed_answers": {},
            "total_questions": 0,
            "question_image_mapping": {},
            "image_descriptions": {},
            "current_batch": 0,
            "error_message": None,
        }

    def _create_progress_from_checkpoint(
        self, checkpoint: dict[str, Any]
    ) -> DatasetBuildProgress:
        """Create progress object from checkpoint data."""
        state_str = checkpoint.get("state", DatasetBuildState.NOT_STARTED.value)
        state = DatasetBuildState(state_str)

        started_at = None
        if checkpoint.get("started_at"):
            started_at = datetime.fromisoformat(checkpoint["started_at"])

        completed_at = None
        if checkpoint.get("completed_at"):
            completed_at = datetime.fromisoformat(checkpoint["completed_at"])

        completed_answers = len(checkpoint.get("completed_answers", {}))
        total_questions = checkpoint.get("total_questions", 0)

        # Estimate completion time based on progress
        estimated_completion = None
        if started_at and completed_answers > 0 and total_questions > completed_answers:
            elapsed = datetime.now(UTC) - started_at
            rate = completed_answers / elapsed.total_seconds()
            remaining_seconds = (total_questions - completed_answers) / rate
            estimated_completion = datetime.now(UTC).replace(microsecond=0) + timedelta(
                seconds=remaining_seconds
            )

        return DatasetBuildProgress(
            state=state,
            started_at=started_at,
            completed_at=completed_at,
            total_questions=total_questions,
            questions_processed=completed_answers,
            images_processed=checkpoint.get("images_processed", False),
            completed_answers=completed_answers,
            current_batch=checkpoint.get("current_batch", 0),
            estimated_completion_time=estimated_completion,
            error_message=checkpoint.get("error_message"),
        )

    def _create_error_progress(self, error_message: str) -> DatasetBuildProgress:
        """Create error progress for failed operations."""
        return DatasetBuildProgress(
            state=DatasetBuildState.FAILED,
            started_at=None,
            completed_at=None,
            total_questions=0,
            questions_processed=0,
            images_processed=False,
            completed_answers=0,
            current_batch=0,
            estimated_completion_time=None,
            error_message=error_message,
        )
