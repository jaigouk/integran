"""Question caching layer for performance optimization."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import QuestionRepository

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""

    value: Any
    timestamp: float
    hits: int = 0


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        return self.hits / self.total_requests if self.total_requests > 0 else 0.0


class QuestionCache:
    """LRU cache for question data with TTL support."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 300.0,  # 5 minutes default
    ):
        """Initialize cache with size and TTL limits.

        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []
        self._stats = CacheStats()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            self._stats.total_requests += 1

            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Check if entry expired
            if current_time - entry.timestamp > self.ttl_seconds:
                self._evict(key)
                self._stats.misses += 1
                return None

            # Update access order (LRU)
            self._access_order.remove(key)
            self._access_order.append(key)

            # Update stats
            entry.hits += 1
            self._stats.hits += 1

            return entry.value

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Evict least recently used
                lru_key = self._access_order[0]
                self._evict(lru_key)

            # Add or update entry
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
            )

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    async def invalidate(self, key: str) -> None:
        """Invalidate specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        async with self._lock:
            self._evict(key)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info(f"Cache cleared. Stats: {self.get_stats()}")

    def _evict(self, key: str) -> None:
        """Evict entry from cache (internal, not thread-safe).

        Args:
            key: Key to evict
        """
        if key in self._cache:
            del self._cache[key]
            self._access_order.remove(key)
            self._stats.evictions += 1

    def get_stats(self) -> CacheStats:
        """Get cache performance statistics.

        Returns:
            Cache statistics
        """
        return self._stats

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if current_time - entry.timestamp > self.ttl_seconds
            ]

            for key in expired_keys:
                self._evict(key)

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)


class CachedQuestionRepository(QuestionRepository):
    """Question repository with caching layer for performance."""

    def __init__(
        self,
        base_repository: QuestionRepository,
        cache_size: int = 1000,
        cache_ttl: float = 300.0,
    ):
        """Initialize cached repository.

        Args:
            base_repository: Underlying repository implementation
            cache_size: Maximum cache size
            cache_ttl: Cache TTL in seconds
        """
        self.base_repository = base_repository
        self.cache = QuestionCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self._category_cache = QuestionCache(max_size=100, ttl_seconds=600.0)  # 10 min
        self._state_cache = QuestionCache(max_size=50, ttl_seconds=600.0)  # 10 min

        # Start periodic cleanup task
        asyncio.create_task(self._periodic_cleanup())

    async def get_question_by_id(self, question_id: int) -> Question | None:
        """Get a single question by ID with caching."""
        cache_key = f"question:{question_id}"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Load from base repository
        question = await self.base_repository.get_question_by_id(question_id)

        # Cache if found
        if question:
            await self.cache.set(cache_key, question)

        return question

    async def get_questions_by_category(self, category: str) -> list[Question]:
        """Get all questions in a specific category with caching."""
        cache_key = f"category:{category}"

        # Try cache first
        cached = await self._category_cache.get(cache_key)
        if cached is not None:
            return cached

        # Load from base repository
        questions = await self.base_repository.get_questions_by_category(category)

        # Cache result
        await self._category_cache.set(cache_key, questions)

        # Also cache individual questions
        for question in questions:
            await self.cache.set(f"question:{question.id}", question)

        return questions

    async def get_questions_by_state(self, state: str | None = None) -> list[Question]:
        """Get questions filtered by federal state with caching."""
        cache_key = f"state:{state or 'general'}"

        # Try cache first
        cached = await self._state_cache.get(cache_key)
        if cached is not None:
            return cached

        # Load from base repository
        questions = await self.base_repository.get_questions_by_state(state)

        # Cache result
        await self._state_cache.set(cache_key, questions)

        # Also cache individual questions
        for question in questions:
            await self.cache.set(f"question:{question.id}", question)

        return questions

    async def get_questions_for_review(
        self, user_id: int, limit: int = 10
    ) -> list[Question]:
        """Get questions due for review - not cached due to user-specific nature."""
        return await self.base_repository.get_questions_for_review(user_id, limit)

    async def get_all_questions(self) -> list[Question]:
        """Get all questions - cached with longer TTL."""
        cache_key = "all_questions"

        # Try cache first
        cached = await self._category_cache.get(cache_key)
        if cached is not None:
            return cached

        # Load from base repository
        questions = await self.base_repository.get_all_questions()

        # Cache result with longer TTL
        await self._category_cache.set(cache_key, questions)

        # Also cache individual questions
        for question in questions:
            await self.cache.set(f"question:{question.id}", question)

        return questions

    async def get_image_questions(self) -> list[Question]:
        """Get all questions that have images with caching."""
        cache_key = "image_questions"

        # Try cache first
        cached = await self._category_cache.get(cache_key)
        if cached is not None:
            return cached

        # Load from base repository
        questions = await self.base_repository.get_image_questions()

        # Cache result
        await self._category_cache.set(cache_key, questions)

        # Also cache individual questions
        for question in questions:
            await self.cache.set(f"question:{question.id}", question)

        return questions

    async def save_question(self, question: Question) -> Question:
        """Save or update a question - invalidates relevant caches."""
        # Save through base repository
        saved = await self.base_repository.save_question(question)

        # Invalidate caches
        await self.cache.invalidate(f"question:{saved.id}")
        await self._category_cache.invalidate(f"category:{saved.category}")
        await self._category_cache.invalidate("all_questions")

        if saved.is_image_question:
            await self._category_cache.invalidate("image_questions")

        if saved.state:
            await self._state_cache.invalidate(f"state:{saved.state}")
        await self._state_cache.invalidate("state:general")

        return saved

    async def get_questions_for_active_learning(
        self,
        user_id: int = 1,
        desired_retention: float = 0.90,
        stability_threshold: int = 30,
        retrievability_threshold: float = 0.9,
        include_leeches: bool = True,
        limit: int = 100,
    ) -> list[Question]:
        """Get questions for active learning - not cached due to user-specific FSRS state."""
        return await self.base_repository.get_questions_for_active_learning(
            user_id=user_id,
            desired_retention=desired_retention,
            stability_threshold=stability_threshold,
            retrievability_threshold=retrievability_threshold,
            include_leeches=include_leeches,
            limit=limit,
        )

    def get_cache_stats(self) -> dict[str, CacheStats]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary of cache statistics by cache type
        """
        return {
            "questions": self.cache.get_stats(),
            "categories": self._category_cache.get_stats(),
            "states": self._state_cache.get_stats(),
        }

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self.cache.cleanup_expired()
                await self._category_cache.cleanup_expired()
                await self._state_cache.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
