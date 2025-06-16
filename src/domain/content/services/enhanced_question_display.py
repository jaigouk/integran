"""Enhanced question display service utilizing rich multilingual content from final_dataset.json."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.domain.shared.services import (
    DomainService,
    ValidationError,
    log_domain_operation,
)
from src.domain.user.models.user_models import Language
from src.infrastructure.messaging.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Enhanced image information with descriptions."""

    path: str
    description: str
    context: str


@dataclass
class MultilingualContent:
    """Multilingual content for a question."""

    explanation: str
    key_concept: str
    mnemonic: str | None = None


@dataclass
class WrongAnswerAnalysis:
    """Analysis of why wrong answers are incorrect."""

    option_letter: str
    option_text: str
    explanation: str


@dataclass
class EnhancedQuestionData:
    """Enhanced question data with rich multilingual content."""

    # Basic question data
    id: int
    question: str
    options: list[str]
    correct_answer: str
    correct_answer_letter: str
    category: str
    difficulty: str
    question_type: str
    state: str | None
    page_number: int | None
    is_image_question: bool

    # Rich content
    multilingual_content: MultilingualContent
    wrong_answer_analysis: list[WrongAnswerAnalysis]
    images: list[ImageInfo]
    image_context: str | None
    rag_sources: list[str]


@dataclass
class EnhancedQuestionDisplayRequest:
    """Request for enhanced question display."""

    question_id: int
    preferred_language: Language = Language.ENGLISH
    include_wrong_analysis: bool = True
    include_key_concepts: bool = True
    include_mnemonics: bool = True
    include_image_descriptions: bool = True


@dataclass
class EnhancedQuestionDisplayResult:
    """Result of enhanced question display."""

    success: bool
    question_data: EnhancedQuestionData | None = None
    error_message: str | None = None


class EnhancedQuestionDisplay(
    DomainService[EnhancedQuestionDisplayRequest, EnhancedQuestionDisplayResult]
):
    """Domain service for displaying questions with rich multilingual content.

    This service loads questions from the enhanced final_dataset.json and provides
    rich multilingual explanations, wrong answer analysis, key concepts, mnemonics,
    and image descriptions based on user preferences.
    """

    def __init__(
        self,
        event_bus: EventBus,
        dataset_path: str | Path = "data/final_dataset.json",
    ):
        """Initialize the enhanced question display service.

        Args:
            event_bus: Event bus for publishing domain events
            dataset_path: Path to the enhanced dataset JSON file
        """
        super().__init__(event_bus)
        self.dataset_path = Path(dataset_path)
        self._dataset_cache: dict[str, Any] | None = None

    @log_domain_operation
    async def call(
        self, request: EnhancedQuestionDisplayRequest
    ) -> EnhancedQuestionDisplayResult:
        """Load and display enhanced question with rich content.

        Args:
            request: Enhanced question display request

        Returns:
            Enhanced question display result with rich content

        Raises:
            ValidationError: If request is invalid
            DomainServiceError: If loading fails
        """
        # Validate request
        self._validate_request(request)

        try:
            # Load dataset if not cached
            if self._dataset_cache is None:
                self._dataset_cache = await self._load_dataset()

            # Get question data
            question_data = self._dataset_cache.get("questions", {}).get(
                str(request.question_id)
            )
            if not question_data:
                return EnhancedQuestionDisplayResult(
                    success=False,
                    error_message=f"Question {request.question_id} not found in dataset",
                )

            # Extract multilingual content
            multilingual_content = self._extract_multilingual_content(
                question_data, request.preferred_language
            )

            # Extract wrong answer analysis
            wrong_answer_analysis = []
            if request.include_wrong_analysis:
                wrong_answer_analysis = self._extract_wrong_answer_analysis(
                    question_data, request.preferred_language
                )

            # Extract image information
            images = []
            if request.include_image_descriptions and question_data.get(
                "is_image_question", False
            ):
                images = self._extract_image_info(question_data)

            # Create enhanced question data
            enhanced_question = EnhancedQuestionData(
                id=question_data["id"],
                question=question_data["question"],
                options=question_data["options"],
                correct_answer=question_data["correct"],
                correct_answer_letter=question_data.get("correct_answer_letter", ""),
                category=question_data["category"],
                difficulty=question_data.get("difficulty", "medium"),
                question_type=question_data.get("question_type", "general"),
                state=question_data.get("state"),
                page_number=question_data.get("page_number"),
                is_image_question=question_data.get("is_image_question", False),
                multilingual_content=multilingual_content,
                wrong_answer_analysis=wrong_answer_analysis,
                images=images,
                image_context=question_data.get("image_context"),
                rag_sources=question_data.get("rag_sources", []),
            )

            self.logger.info(
                f"Successfully loaded enhanced question {request.question_id} "
                f"with {request.preferred_language.value} content"
            )

            return EnhancedQuestionDisplayResult(
                success=True,
                question_data=enhanced_question,
            )

        except Exception as e:
            error_msg = f"Failed to load enhanced question {request.question_id}: {e}"
            self.logger.error(error_msg)
            return EnhancedQuestionDisplayResult(
                success=False,
                error_message=error_msg,
            )

    async def _load_dataset(self) -> dict[str, Any]:
        """Load the enhanced dataset from JSON file."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")

        try:
            with self.dataset_path.open("r", encoding="utf-8") as f:
                dataset: dict[str, Any] = json.load(f)

            self.logger.info(
                f"Loaded enhanced dataset with {len(dataset.get('questions', {}))} questions"
            )
            return dataset

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dataset file: {e}") from e

    def _extract_multilingual_content(
        self, question_data: dict[str, Any], language: Language
    ) -> MultilingualContent:
        """Extract multilingual content for the specified language."""
        lang_code = language.value

        # Get explanations
        explanations = question_data.get("explanations", {})
        explanation = explanations.get(
            lang_code, explanations.get("en", "No explanation available")
        )

        # Get key concepts
        key_concepts = question_data.get("key_concept", {})
        key_concept = key_concepts.get(
            lang_code, key_concepts.get("en", "No key concept available")
        )

        # Get mnemonics
        mnemonics = question_data.get("mnemonic", {})
        mnemonic = mnemonics.get(lang_code, mnemonics.get("en"))

        return MultilingualContent(
            explanation=explanation,
            key_concept=key_concept,
            mnemonic=mnemonic,
        )

    def _extract_wrong_answer_analysis(
        self, question_data: dict[str, Any], language: Language
    ) -> list[WrongAnswerAnalysis]:
        """Extract wrong answer analysis for incorrect options."""
        lang_code = language.value
        why_others_wrong = question_data.get("why_others_wrong", {})

        # Get wrong answer explanations for the specified language
        lang_wrong_answers = why_others_wrong.get(
            lang_code, why_others_wrong.get("en", {})
        )

        wrong_analysis = []
        options = question_data.get("options", [])
        correct_answer = question_data.get("correct", "")

        # Map option letters to explanations
        for i, option_text in enumerate(options):
            if option_text != correct_answer:  # Only wrong answers
                option_letter = chr(65 + i)  # A, B, C, D
                explanation = lang_wrong_answers.get(
                    option_letter, "No explanation available"
                )

                wrong_analysis.append(
                    WrongAnswerAnalysis(
                        option_letter=option_letter,
                        option_text=option_text,
                        explanation=explanation,
                    )
                )

        return wrong_analysis

    def _extract_image_info(self, question_data: dict[str, Any]) -> list[ImageInfo]:
        """Extract image information with descriptions."""
        images_data = question_data.get("images", [])

        images = []
        for image_data in images_data:
            if isinstance(image_data, dict):
                images.append(
                    ImageInfo(
                        path=image_data.get("path", ""),
                        description=image_data.get("description", ""),
                        context=image_data.get("context", ""),
                    )
                )

        return images

    def _validate_request(self, request: EnhancedQuestionDisplayRequest) -> None:
        """Validate the enhanced question display request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If request is invalid
        """
        if not isinstance(request, EnhancedQuestionDisplayRequest):
            raise ValidationError(
                "Request must be an EnhancedQuestionDisplayRequest instance"
            )

        if not isinstance(request.question_id, int):
            raise ValidationError("question_id must be an integer")

        if request.question_id < 1:
            raise ValidationError("question_id must be positive")

        if not isinstance(request.preferred_language, Language):
            raise ValidationError("preferred_language must be a Language enum")
