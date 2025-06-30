"""Optimized dependency injection container with performance enhancements."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.domain.shared.repositories import QuestionRepository
from src.infrastructure.caching import CachedQuestionRepository, ImageCache
from src.infrastructure.containers.main_container import MainContainer
from src.infrastructure.database.optimized_database import OptimizedDatabaseManager
from src.infrastructure.monitoring import PerformanceMonitor
from src.infrastructure.repositories.question_repository import (
    SQLAlchemyQuestionRepository,
)
from src.infrastructure.services.image_loader import ImageLoader

if TYPE_CHECKING:
    from src.domain.content.models.question_models import Question
    from src.domain.shared.repositories import QuestionRepository

logger = logging.getLogger(__name__)


class OptimizedDIContainer(MainContainer):
    """Enhanced DI container with performance optimizations."""

    def __init__(
        self,
        db_path: str = "data/trainer.db",
        enable_caching: bool = True,
        enable_monitoring: bool = True,
    ):
        """Initialize optimized container.

        Args:
            db_path: Database file path
            enable_caching: Enable question and image caching
            enable_monitoring: Enable performance monitoring
        """
        # Initialize performance monitor first
        self._performance_monitor = PerformanceMonitor() if enable_monitoring else None

        # Initialize parent container first to set up base components
        super().__init__()

        # Replace with optimized database manager
        self._db_manager = OptimizedDatabaseManager(db_path)

        # Setup caching if enabled
        if enable_caching:
            self._setup_caching()

        # Setup image optimization
        self._image_cache = ImageCache(max_memory_mb=50.0, max_items=100)

        logger.info(
            f"Optimized container initialized "
            f"(caching={'enabled' if enable_caching else 'disabled'}, "
            f"monitoring={'enabled' if enable_monitoring else 'disabled'})"
        )

    def _setup_caching(self) -> None:
        """Setup caching layer for repositories."""
        # Wrap question repository with caching
        base_question_repo = SQLAlchemyQuestionRepository(self._db_manager)
        self._question_repository = CachedQuestionRepository(
            base_repository=base_question_repo,
            cache_size=500,  # Cache up to 500 questions
            cache_ttl=600.0,  # 10 minute TTL
        )

        logger.info("Question caching layer initialized")

    def get_question_repository(self) -> QuestionRepository:
        """Get optimized question repository with caching.

        Returns:
            Cached question repository
        """
        if self._performance_monitor:
            # Wrap with performance monitoring
            return MonitoredQuestionRepository(
                self._question_repository,
                self._performance_monitor,
            )
        return self._question_repository

    def get_image_loader(self) -> ImageLoader:
        """Get optimized image loader with caching.

        Returns:
            Cached image loader
        """
        base_loader = ImageLoader(base_directory=".")

        if self._image_cache:
            return CachedImageLoader(base_loader, self._image_cache)

        return base_loader

    def get_performance_monitor(self) -> PerformanceMonitor | None:
        """Get performance monitor if enabled.

        Returns:
            Performance monitor or None
        """
        return self._performance_monitor

    def optimize_database(self) -> None:
        """Run database optimization tasks."""
        if isinstance(self._db_manager, OptimizedDatabaseManager):
            logger.info("Running database optimization...")
            self._db_manager.analyze_database()
            logger.info("Database optimization complete")

    def get_performance_stats(self) -> dict[str, Any]:
        """Get comprehensive performance statistics.

        Returns:
            Performance statistics
        """
        stats = {}

        # Database stats
        if isinstance(self._db_manager, OptimizedDatabaseManager):
            stats["database"] = self._db_manager.get_database_stats()

        # Cache stats
        if hasattr(self._question_repository, "get_cache_stats"):
            stats["cache"] = self._question_repository.get_cache_stats()

        # Image cache stats
        if self._image_cache:
            stats["image_cache"] = self._image_cache.get_stats()

        # Performance monitor stats
        if self._performance_monitor:
            stats["operations"] = self._performance_monitor.get_stats()

        return stats


class MonitoredQuestionRepository(QuestionRepository):
    """Question repository wrapper with performance monitoring."""

    def __init__(
        self,
        base_repository: QuestionRepository,
        monitor: PerformanceMonitor,
    ):
        """Initialize monitored repository.

        Args:
            base_repository: Underlying repository
            monitor: Performance monitor
        """
        self.base_repository = base_repository
        self.monitor = monitor

    async def get_question_by_id(self, question_id: int) -> Question | None:
        """Get question with performance monitoring."""
        async with self.monitor.measure_async(
            "get_question_by_id", question_id=question_id
        ):
            return await self.base_repository.get_question_by_id(question_id)

    async def get_questions_by_category(self, category: str) -> list[Question]:
        """Get questions by category with monitoring."""
        async with self.monitor.measure_async(
            "get_questions_by_category", category=category
        ):
            return await self.base_repository.get_questions_by_category(category)

    async def get_questions_by_state(self, state: str | None = None) -> list[Question]:
        """Get questions by state with monitoring."""
        async with self.monitor.measure_async(
            "get_questions_by_state", state=state or "general"
        ):
            return await self.base_repository.get_questions_by_state(state)

    async def get_questions_for_review(
        self, user_id: int, limit: int = 10
    ) -> list[Question]:
        """Get review questions with monitoring."""
        async with self.monitor.measure_async(
            "get_questions_for_review", user_id=user_id, limit=limit
        ):
            return await self.base_repository.get_questions_for_review(user_id, limit)

    async def get_all_questions(self) -> list[Question]:
        """Get all questions with monitoring."""
        async with self.monitor.measure_async("get_all_questions"):
            return await self.base_repository.get_all_questions()

    async def get_image_questions(self) -> list[Question]:
        """Get image questions with monitoring."""
        async with self.monitor.measure_async("get_image_questions"):
            return await self.base_repository.get_image_questions()

    async def save_question(self, question: Question) -> Question:
        """Save question with monitoring."""
        async with self.monitor.measure_async("save_question", question_id=question.id):
            return await self.base_repository.save_question(question)

    async def get_questions_for_active_learning(
        self,
        user_id: int = 1,
        desired_retention: float = 0.90,
        stability_threshold: int = 30,
        retrievability_threshold: float = 0.9,
        include_leeches: bool = True,
        limit: int = 100,
    ) -> list[Question]:
        """Get questions for active learning with monitoring."""
        async with self.monitor.measure_async(
            "get_questions_for_active_learning", user_id=user_id, limit=limit
        ):
            return await self.base_repository.get_questions_for_active_learning(
                user_id=user_id,
                desired_retention=desired_retention,
                stability_threshold=stability_threshold,
                retrievability_threshold=retrievability_threshold,
                include_leeches=include_leeches,
                limit=limit,
            )


class CachedImageLoader(ImageLoader):
    """Image loader with caching support."""

    def __init__(self, base_loader: ImageLoader, cache: ImageCache):
        """Initialize cached image loader.

        Args:
            base_loader: Base image loader
            cache: Image cache
        """
        super().__init__(base_loader.base_directory)
        self.base_loader = base_loader
        self.cache = cache

    async def load_image(self, path: str) -> bytes | None:
        """Load image with caching."""
        return await self.cache.get_image(
            path,
            loader_func=self.base_loader.load_image,
        )

    async def get_image_info(self, path: str) -> dict[str, Any] | None:
        """Get image info with caching."""
        cached_info = await self.cache.get_image_info(path)
        if cached_info:
            return cached_info

        return await self.base_loader.get_image_info(path)
