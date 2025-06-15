"""Domain models for multilingual answers and explanations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MultilingualAnswer:
    """Multilingual answer with explanations in multiple languages."""

    question_id: int
    correct_answer: str
    explanations: dict[
        str, str
    ]  # {"en": "...", "de": "...", "tr": "...", "uk": "...", "ar": "..."}
    why_others_wrong: dict[str, dict[str, str]]  # Per language
    key_concept: dict[str, str]  # Per language
    mnemonic: dict[str, str] | None  # Per language
    image_context: str | None  # If question has images
    rag_sources: list[str]  # Sources used from RAG


@dataclass
class AnswerGenerationRequest:
    """Request to generate multilingual answer for a question."""

    question_id: int
    question_text: str
    options: dict[str, str]  # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer: str
    category: str
    images: list[ImageDescription] | None = None
    include_rag: bool = False


@dataclass
class AnswerGenerationResult:
    """Result of answer generation."""

    success: bool
    answer: MultilingualAnswer | None
    error_message: str | None = None


@dataclass
class ImageDescription:
    """Metadata for an extracted image."""

    path: str
    description: str  # What the image shows
    visual_elements: list[str]  # Colors, symbols, text
    context: str  # Historical/political context
    question_relevance: str  # How this relates to integration exam


@dataclass
class ImageProcessingRequest:
    """Request to process and describe an image."""

    image_path: str
    page_number: int | None = None
    question_context: str | None = None


@dataclass
class ImageProcessingResult:
    """Result of image processing."""

    success: bool
    description: ImageDescription | None
    error_message: str | None = None


@dataclass
class QuestionImageMappingRequest:
    """Request to create question-to-image mappings."""

    questions: list[dict[str, Any]]
    available_images: dict[int, list[str]]  # page_number -> [image_paths]


@dataclass
class QuestionImageMappingResult:
    """Result of question-to-image mapping."""

    success: bool
    mappings: dict[int, list[str]]  # question_id -> [image_paths]
    unmapped_images: list[str]
    error_message: str | None = None
