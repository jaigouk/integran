"""Unit tests for Content Context domain models."""

from __future__ import annotations

from src.domain.content.models.answer_models import (
    AnswerGenerationRequest,
    AnswerGenerationResult,
    ImageDescription,
    ImageProcessingRequest,
    MultilingualAnswer,
    QuestionImageMappingRequest,
    QuestionImageMappingResult,
)


class TestMultilingualAnswer:
    """Test the MultilingualAnswer domain model."""

    def test_create_multilingual_answer(self):
        """Test creating a multilingual answer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="D",
            explanations={
                "en": "This is correct because...",
                "de": "Das ist richtig weil...",
            },
            why_others_wrong={
                "en": {
                    "A": "Option A is wrong because...",
                    "B": "Option B is wrong because...",
                },
                "de": {
                    "A": "Option A ist falsch weil...",
                    "B": "Option B ist falsch weil...",
                },
            },
            key_concept={"en": "Freedom of speech", "de": "Meinungsfreiheit"},
            mnemonic={
                "en": "Free speech = democracy",
                "de": "Freie Meinung = Demokratie",
            },
            image_context="German flag image",
            rag_sources=["constitution.pdf"],
        )

        assert answer.question_id == 1
        assert answer.correct_answer == "D"
        assert "en" in answer.explanations
        assert "de" in answer.explanations
        assert answer.mnemonic is not None
        assert answer.rag_sources == ["constitution.pdf"]


class TestAnswerGenerationRequest:
    """Test the AnswerGenerationRequest model."""

    def test_create_answer_generation_request(self):
        """Test creating an answer generation request."""
        image_desc = ImageDescription(
            path="test.png",
            description="Test image",
            visual_elements=["red", "blue"],
            context="Test context",
            question_relevance="Test relevance",
        )

        request = AnswerGenerationRequest(
            question_id=1,
            question_text="Test question?",
            options={
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D",
            },
            correct_answer="D",
            category="Test Category",
            images=[image_desc],
            include_rag=True,
        )

        assert request.question_id == 1
        assert request.question_text == "Test question?"
        assert len(request.options) == 4
        assert request.correct_answer == "D"
        assert request.category == "Test Category"
        assert request.images is not None
        assert len(request.images) == 1
        assert request.include_rag is True


class TestAnswerGenerationResult:
    """Test the AnswerGenerationResult model."""

    def test_success_result(self):
        """Test creating a successful result."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="D",
            explanations={"en": "Test explanation"},
            why_others_wrong={},
            key_concept={"en": "Test concept"},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        result = AnswerGenerationResult(
            success=True,
            answer=answer,
            error_message=None,
        )

        assert result.success is True
        assert result.answer is not None
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating a failure result."""
        result = AnswerGenerationResult(
            success=False,
            answer=None,
            error_message="Failed to generate answer",
        )

        assert result.success is False
        assert result.answer is None
        assert result.error_message == "Failed to generate answer"


class TestImageDescription:
    """Test the ImageDescription model."""

    def test_create_image_description(self):
        """Test creating an image description."""
        desc = ImageDescription(
            path="images/test.png",
            description="A coat of arms",
            visual_elements=["eagle", "shield", "colors: black, red, gold"],
            context="German federal symbol",
            question_relevance="Used in questions about German symbols",
        )

        assert desc.path == "images/test.png"
        assert desc.description == "A coat of arms"
        assert "eagle" in desc.visual_elements
        assert desc.context == "German federal symbol"
        assert "German symbols" in desc.question_relevance


class TestImageProcessingRequest:
    """Test the ImageProcessingRequest model."""

    def test_create_image_processing_request(self):
        """Test creating an image processing request."""
        request = ImageProcessingRequest(
            image_path="images/test.png",
            page_number=42,
            question_context="Question about German symbols",
        )

        assert request.image_path == "images/test.png"
        assert request.page_number == 42
        assert request.question_context == "Question about German symbols"

    def test_create_minimal_request(self):
        """Test creating a minimal request."""
        request = ImageProcessingRequest(image_path="test.png")

        assert request.image_path == "test.png"
        assert request.page_number is None
        assert request.question_context is None


class TestQuestionImageMappingRequest:
    """Test the QuestionImageMappingRequest model."""

    def test_create_mapping_request(self):
        """Test creating a question-to-image mapping request."""
        questions = [
            {"id": 1, "question": "Test question 1"},
            {"id": 2, "question": "Test question 2"},
        ]
        available_images = {
            1: ["images/page1_img1.png", "images/page1_img2.png"],
            2: ["images/page2_img1.png"],
        }

        request = QuestionImageMappingRequest(
            questions=questions,
            available_images=available_images,
        )

        assert len(request.questions) == 2
        assert len(request.available_images) == 2
        assert 1 in request.available_images
        assert len(request.available_images[1]) == 2


class TestQuestionImageMappingResult:
    """Test the QuestionImageMappingResult model."""

    def test_successful_mapping_result(self):
        """Test creating a successful mapping result."""
        mappings = {
            1: ["images/page1_img1.png"],
            2: ["images/page2_img1.png", "images/page2_img2.png"],
        }
        unmapped_images = ["images/page3_img1.png"]

        result = QuestionImageMappingResult(
            success=True,
            mappings=mappings,
            unmapped_images=unmapped_images,
        )

        assert result.success is True
        assert len(result.mappings) == 2
        assert 1 in result.mappings
        assert len(result.unmapped_images) == 1
        assert result.error_message is None

    def test_failed_mapping_result(self):
        """Test creating a failed mapping result."""
        result = QuestionImageMappingResult(
            success=False,
            mappings={},
            unmapped_images=[],
            error_message="Failed to process images",
        )

        assert result.success is False
        assert len(result.mappings) == 0
        assert len(result.unmapped_images) == 0
        assert result.error_message == "Failed to process images"
