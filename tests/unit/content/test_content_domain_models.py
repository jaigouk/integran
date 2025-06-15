"""Tests for Content Context domain models and simple functionality."""

from __future__ import annotations

from src.domain.content.events.content_events import (
    AnswerGeneratedEvent,
    BatchContentProcessedEvent,
    ContentGenerationFailedEvent,
    ImageProcessedEvent,
)
from src.domain.content.models.answer_models import (
    AnswerGenerationRequest,
    AnswerGenerationResult,
    ImageDescription,
    ImageProcessingRequest,
    ImageProcessingResult,
    MultilingualAnswer,
    QuestionImageMappingRequest,
    QuestionImageMappingResult,
)


class TestContentDomainEvents:
    """Test content domain events."""

    def test_answer_generated_event(self):
        """Test AnswerGeneratedEvent creation."""
        event = AnswerGeneratedEvent(
            question_id=1,
            language_count=5,
            has_images=True,
            has_mnemonic=True,
            generation_time_ms=1500,
        )

        assert event.question_id == 1
        assert event.language_count == 5
        assert event.has_images is True
        assert event.has_mnemonic is True
        assert event.generation_time_ms == 1500
        # Note: event_id and occurred_at are set in DomainEvent parent class
        # but are not automatically initialized in dataclass children

    def test_content_generation_failed_event(self):
        """Test ContentGenerationFailedEvent creation."""
        event = ContentGenerationFailedEvent(
            operation_type="answer_generation",
            entity_id="123",
            error_message="API timeout",
            retry_count=2,
        )

        assert event.operation_type == "answer_generation"
        assert event.entity_id == "123"
        assert event.error_message == "API timeout"
        assert event.retry_count == 2

    def test_image_processed_event(self):
        """Test ImageProcessedEvent creation."""
        event = ImageProcessedEvent(
            image_path="/path/to/image.png",
            page_number=5,
            has_description=True,
            processing_time_ms=800,
        )

        assert event.image_path == "/path/to/image.png"
        assert event.page_number == 5
        assert event.has_description is True
        assert event.processing_time_ms == 800

    def test_batch_content_processed_event(self):
        """Test BatchContentProcessedEvent creation."""
        event = BatchContentProcessedEvent(
            batch_type="answers",
            batch_size=10,
            successful_count=8,
            failed_count=2,
            processing_time_ms=5000,
        )

        assert event.batch_type == "answers"
        assert event.batch_size == 10
        assert event.successful_count == 8
        assert event.failed_count == 2
        assert event.processing_time_ms == 5000


class TestAnswerGenerationModels:
    """Test answer generation models."""

    def test_answer_generation_request_minimal(self):
        """Test minimal AnswerGenerationRequest."""
        request = AnswerGenerationRequest(
            question_id=1,
            question_text="What is the capital?",
            options={"A": "Berlin", "B": "Munich"},
            correct_answer="A",
            category="Geography",
        )

        assert request.question_id == 1
        assert request.question_text == "What is the capital?"
        assert request.options["A"] == "Berlin"
        assert request.correct_answer == "A"
        assert request.category == "Geography"
        assert request.images is None
        assert request.include_rag is False

    def test_answer_generation_request_with_images(self):
        """Test AnswerGenerationRequest with images."""
        image = ImageDescription(
            path="test.png",
            description="Test image",
            visual_elements=["red", "blue"],
            context="Test context",
            question_relevance="Relevant",
        )

        request = AnswerGenerationRequest(
            question_id=1,
            question_text="What is shown?",
            options={"A": "Flag", "B": "Map"},
            correct_answer="A",
            category="Symbols",
            images=[image],
            include_rag=True,
        )

        assert len(request.images) == 1
        assert request.images[0].path == "test.png"
        assert request.include_rag is True

    def test_answer_generation_result_success(self):
        """Test successful AnswerGenerationResult."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={"en": "Explanation"},
            why_others_wrong={},
            key_concept={},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        result = AnswerGenerationResult(
            success=True,
            answer=answer,
        )

        assert result.success is True
        assert result.answer is not None
        assert result.error_message is None

    def test_answer_generation_result_failure(self):
        """Test failed AnswerGenerationResult."""
        result = AnswerGenerationResult(
            success=False,
            answer=None,
            error_message="Generation failed",
        )

        assert result.success is False
        assert result.answer is None
        assert result.error_message == "Generation failed"


class TestImageProcessingModels:
    """Test image processing models."""

    def test_image_processing_request(self):
        """Test ImageProcessingRequest creation."""
        request = ImageProcessingRequest(
            image_path="/path/to/image.png",
            page_number=5,
            question_context="German flag colors",
        )

        assert request.image_path == "/path/to/image.png"
        assert request.page_number == 5
        assert request.question_context == "German flag colors"

    def test_image_processing_request_minimal(self):
        """Test minimal ImageProcessingRequest."""
        request = ImageProcessingRequest(
            image_path="/path/to/image.png",
        )

        assert request.image_path == "/path/to/image.png"
        assert request.page_number is None
        assert request.question_context is None

    def test_image_processing_result_success(self):
        """Test successful ImageProcessingResult."""
        description = ImageDescription(
            path="/path/to/image.png",
            description="German flag",
            visual_elements=["black", "red", "gold"],
            context="National symbol",
            question_relevance="Shows flag colors",
        )

        result = ImageProcessingResult(
            success=True,
            description=description,
        )

        assert result.success is True
        assert result.description is not None
        assert result.description.path == "/path/to/image.png"
        assert result.error_message is None

    def test_image_processing_result_failure(self):
        """Test failed ImageProcessingResult."""
        result = ImageProcessingResult(
            success=False,
            description=None,
            error_message="Image not found",
        )

        assert result.success is False
        assert result.description is None
        assert result.error_message == "Image not found"


class TestQuestionImageMappingModels:
    """Test question-image mapping models."""

    def test_question_image_mapping_request(self):
        """Test QuestionImageMappingRequest creation."""
        questions = [
            {"id": 1, "question": "What is this?"},
            {"id": 2, "question": "What color is this?"},
        ]
        available_images = {
            1: ["page1_img1.png", "page1_img2.png"],
            2: ["page2_img1.png"],
        }

        request = QuestionImageMappingRequest(
            questions=questions,
            available_images=available_images,
        )

        assert len(request.questions) == 2
        assert len(request.available_images) == 2
        assert request.questions[0]["id"] == 1
        assert "page1_img1.png" in request.available_images[1]

    def test_question_image_mapping_result_success(self):
        """Test successful QuestionImageMappingResult."""
        mappings = {
            1: ["image1.png", "image2.png"],
            2: ["image3.png"],
        }

        result = QuestionImageMappingResult(
            success=True,
            mappings=mappings,
            unmapped_images=["orphan_image.png"],
        )

        assert result.success is True
        assert len(result.mappings) == 2
        assert result.mappings[1] == ["image1.png", "image2.png"]
        assert len(result.unmapped_images) == 1
        assert result.error_message is None

    def test_question_image_mapping_result_failure(self):
        """Test failed QuestionImageMappingResult."""
        result = QuestionImageMappingResult(
            success=False,
            mappings={},
            unmapped_images=[],
            error_message="Mapping failed",
        )

        assert result.success is False
        assert len(result.mappings) == 0
        assert len(result.unmapped_images) == 0
        assert result.error_message == "Mapping failed"


class TestMultilingualAnswer:
    """Test MultilingualAnswer model."""

    def test_multilingual_answer_complete(self):
        """Test complete MultilingualAnswer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={
                "en": "English explanation",
                "de": "German explanation",
                "tr": "Turkish explanation",
            },
            why_others_wrong={
                "en": {
                    "B": "B is wrong because...",
                    "C": "C is wrong because...",
                },
                "de": {
                    "B": "B ist falsch weil...",
                    "C": "C ist falsch weil...",
                },
            },
            key_concept={
                "en": "Key concept in English",
                "de": "Schlüsselkonzept auf Deutsch",
            },
            mnemonic={
                "en": "Memory aid",
                "de": "Merkhilfe",
            },
            image_context="German flag image",
            rag_sources=["source1.pdf", "source2.txt"],
        )

        assert answer.question_id == 1
        assert answer.correct_answer == "A"
        assert len(answer.explanations) == 3
        assert "English explanation" in answer.explanations["en"]
        assert "B is wrong because" in answer.why_others_wrong["en"]["B"]
        assert answer.image_context == "German flag image"
        assert len(answer.rag_sources) == 2

    def test_multilingual_answer_minimal(self):
        """Test minimal MultilingualAnswer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={"en": "Simple explanation"},
            why_others_wrong={},
            key_concept={},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        assert answer.question_id == 1
        assert answer.correct_answer == "A"
        assert len(answer.explanations) == 1
        assert answer.why_others_wrong == {}
        assert answer.mnemonic is None
        assert answer.image_context is None
        assert answer.rag_sources == []


# ContentContainer tests temporarily disabled due to external dependencies
# (requires google-genai package which may not be available in CI)
# class TestContentContainer:
#     """Test ContentContainer dependency injection."""
#
#     def test_content_container_basic_structure(self):
#         """Test basic ContentContainer structure without external dependencies."""
#         # This would require mocking the domain services that depend on external APIs
#         pass
