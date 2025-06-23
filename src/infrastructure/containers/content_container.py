"""Dependency injection container for Content Context."""

from __future__ import annotations

from src.application.workflows.build_dataset_workflow import (
    DatasetBuildWorkflow,
)
from src.domain.content.services.build_dataset import BuildDataset
from src.domain.content.services.create_image_mapping import CreateImageMapping
from src.domain.content.services.generate_answer import GenerateAnswer
from src.domain.content.services.process_image import ProcessImage
from src.infrastructure.database.database import DatabaseManager
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.repositories.content_repository import ContentRepository
from src.infrastructure.repositories.question_repository import (
    SQLAlchemyQuestionRepository,
)
from src.infrastructure.repositories.user_repository import UserSettingsRepository


class ContentContainer:
    """Container for Content Context dependencies."""

    def __init__(
        self,
        event_bus: EnhancedEventBus | None = None,
        user_repository: UserSettingsRepository | None = None,
    ):
        """Initialize the content container."""
        # Use provided event bus or create new one
        self._event_bus = event_bus or EnhancedEventBus.create_basic()

        # Initialize repositories
        self._content_repository = ContentRepository()
        self._question_repository = SQLAlchemyQuestionRepository(DatabaseManager())
        self._user_repository = user_repository or UserSettingsRepository(
            database_manager=DatabaseManager()
        )

        # Lazy initialization for Gemini-dependent services
        self._generate_answer: GenerateAnswer | None = None
        self._process_image: ProcessImage | None = None
        self._create_image_mapping: CreateImageMapping | None = None
        self._build_dataset: BuildDataset | None = None
        self._content_builder: DatasetBuildWorkflow | None = None

    def get_event_bus(self) -> EnhancedEventBus:
        """Get the event bus instance."""
        return self._event_bus

    def get_content_repository(self) -> ContentRepository:
        """Get the content repository instance."""
        return self._content_repository

    def get_question_repository(self) -> SQLAlchemyQuestionRepository:
        """Get the question repository instance."""
        return self._question_repository

    def get_generate_answer_service(self) -> GenerateAnswer:
        """Get the GenerateAnswer domain service (lazy initialization)."""
        if self._generate_answer is None:
            self._generate_answer = GenerateAnswer(
                event_bus=self._event_bus,
                user_repository=self._user_repository,
            )
        return self._generate_answer

    def get_process_image_service(self) -> ProcessImage:
        """Get the ProcessImage domain service (lazy initialization)."""
        if self._process_image is None:
            self._process_image = ProcessImage(
                event_bus=self._event_bus,
                user_repository=self._user_repository,
            )
        return self._process_image

    def get_create_image_mapping_service(self) -> CreateImageMapping:
        """Get the CreateImageMapping domain service (lazy initialization)."""
        if self._create_image_mapping is None:
            self._create_image_mapping = CreateImageMapping(event_bus=self._event_bus)
        return self._create_image_mapping

    def get_build_dataset_service(self) -> BuildDataset:
        """Get the BuildDataset domain service (lazy initialization)."""
        if self._build_dataset is None:
            # Get the services with proper user repository injection
            self._build_dataset = BuildDataset(
                question_repository=self._question_repository,
                event_bus=self._event_bus,
                generate_answer=self.get_generate_answer_service(),
                process_image=self.get_process_image_service(),
                create_mapping=self.get_create_image_mapping_service(),
                user_repository=self._user_repository,
            )
        return self._build_dataset

    def get_content_builder_service(self) -> DatasetBuildWorkflow:
        """Get the ContentBuilderService application service (lazy initialization)."""
        if self._content_builder is None:
            # Use the getter method to ensure proper lazy initialization
            build_dataset_service = self.get_build_dataset_service()
            self._content_builder = DatasetBuildWorkflow(
                build_dataset_service=build_dataset_service,
            )
        return self._content_builder
