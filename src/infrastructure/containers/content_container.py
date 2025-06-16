"""Dependency injection container for Content Context."""

from __future__ import annotations

from src.application.workflows.build_dataset_workflow import (
    DatasetBuildWorkflow,
)
from src.domain.content.services.build_dataset import BuildDataset
from src.domain.content.services.create_image_mapping import CreateImageMapping
from src.domain.content.services.generate_answer import GenerateAnswer
from src.domain.content.services.process_image import ProcessImage
from src.infrastructure.messaging.event_bus import EventBus
from src.infrastructure.repositories.content_repository import ContentRepository


class ContentContainer:
    """Container for Content Context dependencies."""

    def __init__(self, event_bus: EventBus | None = None):
        """Initialize the content container."""
        # Use provided event bus or create new one
        self._event_bus = event_bus or EventBus()

        # Initialize repository
        self._repository = ContentRepository()

        # Initialize domain services
        self._generate_answer = GenerateAnswer(event_bus=self._event_bus)
        self._process_image = ProcessImage(event_bus=self._event_bus)
        self._create_image_mapping = CreateImageMapping(event_bus=self._event_bus)
        self._build_dataset = BuildDataset(
            event_bus=self._event_bus,
            repository=self._repository,
        )

        # Initialize application service (thin coordinator)
        self._content_builder = DatasetBuildWorkflow(
            build_dataset_service=self._build_dataset,
        )

    def get_event_bus(self) -> EventBus:
        """Get the event bus instance."""
        return self._event_bus

    def get_repository(self) -> ContentRepository:
        """Get the content repository instance."""
        return self._repository

    def get_generate_answer_service(self) -> GenerateAnswer:
        """Get the GenerateAnswer domain service."""
        return self._generate_answer

    def get_process_image_service(self) -> ProcessImage:
        """Get the ProcessImage domain service."""
        return self._process_image

    def get_create_image_mapping_service(self) -> CreateImageMapping:
        """Get the CreateImageMapping domain service."""
        return self._create_image_mapping

    def get_content_builder_service(self) -> DatasetBuildWorkflow:
        """Get the ContentBuilderService application service."""
        return self._content_builder
