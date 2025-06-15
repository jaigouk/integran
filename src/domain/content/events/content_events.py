"""Domain events for content context."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.messaging.event_bus import DomainEvent


@dataclass
class AnswerGeneratedEvent(DomainEvent):
    """Event raised when multilingual answer is generated."""

    question_id: int
    language_count: int
    has_images: bool
    has_mnemonic: bool
    generation_time_ms: int


@dataclass
class ImageProcessedEvent(DomainEvent):
    """Event raised when image is processed and described."""

    image_path: str
    page_number: int | None
    has_description: bool
    processing_time_ms: int


@dataclass
class QuestionImagesMappedEvent(DomainEvent):
    """Event raised when questions are mapped to images."""

    total_questions: int
    mapped_questions: int
    total_images: int
    mapped_images: int
    unmapped_images: int


@dataclass
class ContentGenerationFailedEvent(DomainEvent):
    """Event raised when content generation fails."""

    operation_type: str  # "answer_generation", "image_processing", "mapping"
    entity_id: str  # question_id or image_path
    error_message: str
    retry_count: int


@dataclass
class BatchContentProcessedEvent(DomainEvent):
    """Event raised when batch of content is processed."""

    batch_type: str  # "answers", "images"
    batch_size: int
    successful_count: int
    failed_count: int
    processing_time_ms: int
