"""Performance optimization integration tests."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from sqlalchemy import text

from src.infrastructure.caching import CachedQuestionRepository, ImageCache
from src.infrastructure.containers.optimized_container import OptimizedDIContainer
from src.infrastructure.monitoring import PerformanceMonitor

# Skip all performance tests until optimization features are integrated into main application
pytestmark = pytest.mark.skip(
    reason="Performance optimization features not yet integrated"
)


@pytest.fixture
def optimized_container(tmp_path: Path) -> OptimizedDIContainer:
    """Create optimized container for testing."""
    db_path = tmp_path / "test_performance.db"
    container = OptimizedDIContainer(
        db_path=str(db_path),
        enable_caching=True,
        enable_monitoring=True,
    )
    # Run optimization
    container.optimize_database()
    return container


@pytest.fixture
def performance_monitor() -> PerformanceMonitor:
    """Create performance monitor for testing."""
    return PerformanceMonitor(slow_threshold_ms=50.0)


class TestDatabaseOptimization:
    """Test database performance optimizations."""

    @pytest.mark.asyncio
    async def test_connection_pooling(self, optimized_container: OptimizedDIContainer):
        """Test that connection pooling improves performance."""
        db_manager = optimized_container._db_manager

        # Measure time for multiple sequential operations
        start_time = time.perf_counter()

        for _ in range(20):
            with db_manager.get_session() as session:
                session.execute(text("SELECT 1"))

        pooled_time = time.perf_counter() - start_time

        # Should complete quickly with pooling
        assert pooled_time < 0.5, f"Pooled operations too slow: {pooled_time:.3f}s"

    @pytest.mark.asyncio
    async def test_query_optimization_with_indexes(
        self, optimized_container: OptimizedDIContainer
    ):
        """Test that indexes improve query performance."""
        db_manager = optimized_container._db_manager
        question_repo = optimized_container.get_question_repository()

        # Insert test data
        with db_manager.get_session() as session:
            from src.domain.content.models.question_models import Question

            # Create test questions
            for i in range(100):
                q = Question(
                    id=i + 1,
                    question=f"Test question {i}",
                    options='["A", "B", "C", "D"]',
                    correct="A",
                    category=f"Category{i % 5}",
                    state="Bayern" if i % 3 == 0 else None,
                    is_image_question=(i % 10 == 0),
                )
                session.add(q)
            session.commit()

        # Test indexed queries
        start_time = time.perf_counter()

        # These should use indexes
        await question_repo.get_questions_by_category("Category1")
        await question_repo.get_questions_by_state("Bayern")
        await question_repo.get_image_questions()

        indexed_time = time.perf_counter() - start_time

        # Should be fast with indexes
        assert indexed_time < 0.1, f"Indexed queries too slow: {indexed_time:.3f}s"

    @pytest.mark.asyncio
    async def test_wal_mode_performance(
        self, optimized_container: OptimizedDIContainer
    ):
        """Test Write-Ahead Logging mode performance."""
        db_manager = optimized_container._db_manager

        # Check WAL mode is enabled
        with db_manager.get_session() as session:
            result = session.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
            assert mode == "wal", f"Expected WAL mode, got {mode}"

        # Test concurrent read/write performance
        async def write_operation(i: int):
            with db_manager.get_session() as session:
                session.execute(
                    text("INSERT INTO user_settings (user_id) VALUES (:id)"),
                    {"id": i},
                )
                session.commit()

        async def read_operation():
            with db_manager.get_session() as session:
                session.execute(text("SELECT COUNT(*) FROM questions"))

        # Concurrent operations should not block each other
        start_time = time.perf_counter()

        await asyncio.gather(
            *[write_operation(i) for i in range(10)],
            *[read_operation() for _ in range(10)],
        )

        concurrent_time = time.perf_counter() - start_time

        # Should complete quickly with WAL
        assert concurrent_time < 0.5, f"Concurrent ops too slow: {concurrent_time:.3f}s"


class TestQuestionCaching:
    """Test question caching performance."""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(
        self, optimized_container: OptimizedDIContainer
    ):
        """Test that cache hits are faster than database queries."""
        question_repo = optimized_container.get_question_repository()

        # Ensure we have a cached repository
        if not isinstance(question_repo.base_repository, CachedQuestionRepository):
            pytest.skip("Caching not enabled")

        # First access - cache miss
        start_time = time.perf_counter()
        questions1 = await question_repo.get_all_questions()
        miss_time = time.perf_counter() - start_time

        # Second access - cache hit
        start_time = time.perf_counter()
        questions2 = await question_repo.get_all_questions()
        hit_time = time.perf_counter() - start_time

        # Cache hit should be much faster
        assert hit_time < miss_time * 0.1, (
            f"Cache not effective: miss={miss_time:.3f}s, hit={hit_time:.3f}s"
        )
        assert questions1 == questions2, "Cached data mismatch"

        # Check cache stats
        cache_stats = question_repo.base_repository.get_cache_stats()
        assert cache_stats["categories"].hits > 0

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, optimized_container: OptimizedDIContainer):
        """Test that cache is properly invalidated on updates."""
        question_repo = optimized_container.get_question_repository()

        if not isinstance(question_repo.base_repository, CachedQuestionRepository):
            pytest.skip("Caching not enabled")

        # Get questions by category (populate cache)
        questions1 = await question_repo.get_questions_by_category("Politik")

        # Modify a question
        if questions1:
            question = questions1[0]
            question.question = "Updated question"
            await question_repo.save_question(question)

            # Get again - should reflect update
            questions2 = await question_repo.get_questions_by_category("Politik")
            updated = next((q for q in questions2 if q.id == question.id), None)
            assert updated is not None
            assert updated.question == "Updated question"

    @pytest.mark.asyncio
    async def test_lru_eviction(self, optimized_container: OptimizedDIContainer):
        """Test LRU cache eviction policy."""
        # Create small cache for testing
        from src.infrastructure.caching.question_cache import QuestionCache

        cache = QuestionCache(max_size=3, ttl_seconds=300)

        # Fill cache beyond capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add new item - should evict key2 (least recently used)
        await cache.set("key4", "value4")

        # Check eviction
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New item


class TestImageOptimization:
    """Test image loading optimizations."""

    @pytest.mark.asyncio
    async def test_image_cache_performance(
        self, optimized_container: OptimizedDIContainer, tmp_path: Path
    ):
        """Test image caching improves load times."""
        image_loader = optimized_container.get_image_loader()

        # Create test image
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"PNG" + b"\x00" * 1000)  # 1KB test image

        # First load - no cache
        start_time = time.perf_counter()
        data1 = await image_loader.load_image(str(test_image))
        load_time = time.perf_counter() - start_time

        # Second load - from cache
        start_time = time.perf_counter()
        data2 = await image_loader.load_image(str(test_image))
        cache_time = time.perf_counter() - start_time

        assert data1 == data2, "Cached data mismatch"
        assert cache_time < load_time * 0.5, "Cache not improving performance"

    @pytest.mark.asyncio
    async def test_image_preloading(
        self, optimized_container: OptimizedDIContainer, tmp_path: Path
    ):
        """Test batch image preloading."""
        image_cache = ImageCache()

        # Create test images
        image_paths = []
        for i in range(10):
            path = tmp_path / f"image{i}.png"
            path.write_bytes(b"PNG" + bytes(i) * 100)
            image_paths.append(str(path))

        # Mock loader function
        async def loader(path: str) -> bytes:
            await asyncio.sleep(0.01)  # Simulate load time
            return Path(path).read_bytes()

        # Preload images
        start_time = time.perf_counter()
        results = await image_cache.preload_images(
            image_paths, loader, max_concurrent=5
        )
        preload_time = time.perf_counter() - start_time

        # Should load concurrently
        assert all(results.values()), "Some images failed to preload"
        assert preload_time < 0.1, f"Preloading too slow: {preload_time:.3f}s"

        # Subsequent access should be instant
        for path in image_paths:
            data = await image_cache.get_image(path, loader)
            assert data is not None


class TestPerformanceMonitoring:
    """Test performance monitoring capabilities."""

    @pytest.mark.asyncio
    async def test_operation_monitoring(self, performance_monitor: PerformanceMonitor):
        """Test monitoring of operations."""
        # Monitor sync operation
        with performance_monitor.measure("test_sync", category="test"):
            time.sleep(0.01)

        # Monitor async operation
        async with performance_monitor.measure_async("test_async", category="test"):
            await asyncio.sleep(0.01)

        # Check stats
        stats = performance_monitor.get_stats()
        assert "test_sync" in stats
        assert "test_async" in stats
        assert stats["test_sync"]["count"] == 1
        assert stats["test_sync"]["avg_ms"] > 10

    @pytest.mark.asyncio
    async def test_slow_operation_detection(
        self, performance_monitor: PerformanceMonitor
    ):
        """Test detection of slow operations."""
        # Create slow operation
        async with performance_monitor.measure_async("slow_op"):
            await asyncio.sleep(0.1)  # 100ms

        # Check slow operations
        slow_ops = performance_monitor.get_slow_operations()
        assert len(slow_ops) == 1
        assert slow_ops[0]["operation"] == "slow_op"
        assert slow_ops[0]["duration_ms"] > 100

    @pytest.mark.asyncio
    async def test_performance_report(self, performance_monitor: PerformanceMonitor):
        """Test performance report generation."""
        # Generate some operations
        for i in range(5):
            with performance_monitor.measure(f"op{i % 2}"):
                time.sleep(0.001 * (i + 1))

        # Generate report
        report = performance_monitor.generate_report()
        assert "Performance Report" in report
        assert "op0" in report
        assert "op1" in report
        assert "Total Operations: 5" in report


@pytest.mark.asyncio
async def test_end_to_end_performance(optimized_container: OptimizedDIContainer):
    """Test end-to-end performance improvements."""
    # Get components
    question_repo = optimized_container.get_question_repository()
    monitor = optimized_container.get_performance_monitor()

    # Run typical operations
    start_time = time.perf_counter()

    # Simulate practice session operations
    all_questions = await question_repo.get_all_questions()
    if all_questions:
        # Get specific questions
        for i in range(min(10, len(all_questions))):
            await question_repo.get_question_by_id(all_questions[i].id)

    # Get category questions
    await question_repo.get_questions_by_category("Politik")
    await question_repo.get_questions_by_category("Geschichte")

    # Get state questions
    await question_repo.get_questions_by_state("Bayern")
    await question_repo.get_questions_by_state(None)  # General

    total_time = time.perf_counter() - start_time

    # Should complete quickly with optimizations
    assert total_time < 1.0, f"Operations too slow: {total_time:.3f}s"

    # Check performance stats
    if monitor:
        stats = optimized_container.get_performance_stats()
        assert "cache" in stats
        assert "operations" in stats

        # Generate performance report
        report = monitor.generate_report()
        print("\n" + report)  # Output for debugging
