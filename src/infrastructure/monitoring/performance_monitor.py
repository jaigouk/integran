"""Performance monitoring and profiling utilities."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric for a single operation."""

    name: str
    start_time: float
    end_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def is_slow(self) -> bool:
        """Check if operation is considered slow (>100ms)."""
        return self.duration_ms > 100


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""

    operation: str
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    slow_count: int = 0

    @property
    def avg_ms(self) -> float:
        """Get average duration in milliseconds."""
        return self.total_ms / self.count if self.count > 0 else 0.0

    def update(self, duration_ms: float) -> None:
        """Update statistics with new measurement."""
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
        if duration_ms > 100:  # Slow threshold
            self.slow_count += 1


class PerformanceMonitor:
    """Monitor and track application performance metrics."""

    def __init__(self, slow_threshold_ms: float = 100.0):
        """Initialize performance monitor.

        Args:
            slow_threshold_ms: Threshold for slow operation warnings
        """
        self.slow_threshold_ms = slow_threshold_ms
        self._metrics: list[PerformanceMetric] = []
        self._stats: dict[str, PerformanceStats] = defaultdict(
            lambda: PerformanceStats("")
        )
        self._active_operations: dict[str, PerformanceMetric] = {}
        self._lock = asyncio.Lock()

    @contextmanager
    def measure(self, operation: str, **metadata: Any) -> Iterator[PerformanceMetric]:
        """Measure synchronous operation performance.

        Args:
            operation: Operation name
            **metadata: Additional metadata

        Yields:
            Performance metric
        """
        metric = PerformanceMetric(
            name=operation,
            start_time=time.perf_counter(),
            metadata=metadata,
        )

        try:
            yield metric
        finally:
            metric.end_time = time.perf_counter()
            self._record_metric(metric)

    @asynccontextmanager
    async def measure_async(
        self, operation: str, **metadata: Any
    ) -> AsyncIterator[PerformanceMetric]:
        """Measure asynchronous operation performance.

        Args:
            operation: Operation name
            **metadata: Additional metadata

        Yields:
            Performance metric
        """
        metric = PerformanceMetric(
            name=operation,
            start_time=time.perf_counter(),
            metadata=metadata,
        )

        async with self._lock:
            self._active_operations[operation] = metric

        try:
            yield metric
        finally:
            metric.end_time = time.perf_counter()

            async with self._lock:
                self._active_operations.pop(operation, None)
                self._record_metric(metric)

    def _record_metric(self, metric: PerformanceMetric) -> None:
        """Record completed metric.

        Args:
            metric: Performance metric to record
        """
        self._metrics.append(metric)

        # Update statistics
        stats = self._stats[metric.name]
        stats.operation = metric.name
        stats.update(metric.duration_ms)

        # Log slow operations
        if metric.is_slow:
            logger.warning(
                f"Slow operation detected: {metric.name} "
                f"took {metric.duration_ms:.1f}ms "
                f"(metadata: {metric.metadata})"
            )

        # Limit metrics storage
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-5000:]  # Keep last 5000

    def get_stats(self, operation: str | None = None) -> dict[str, Any]:
        """Get performance statistics.

        Args:
            operation: Specific operation or None for all

        Returns:
            Performance statistics
        """
        if operation:
            stats = self._stats.get(operation)
            if stats:
                return self._format_stats(stats)
            return {}

        # Return all statistics
        return {
            op: self._format_stats(stats) for op, stats in sorted(self._stats.items())
        }

    def _format_stats(self, stats: PerformanceStats) -> dict[str, Any]:
        """Format statistics for output.

        Args:
            stats: Performance statistics

        Returns:
            Formatted statistics
        """
        return {
            "count": stats.count,
            "avg_ms": round(stats.avg_ms, 2),
            "min_ms": round(stats.min_ms, 2),
            "max_ms": round(stats.max_ms, 2),
            "total_ms": round(stats.total_ms, 2),
            "slow_count": stats.slow_count,
            "slow_percentage": round(
                (stats.slow_count / stats.count * 100) if stats.count > 0 else 0, 1
            ),
        }

    def get_slow_operations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get slowest operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of slow operations
        """
        # Get recent slow operations
        slow_ops = [m for m in self._metrics if m.is_slow]
        slow_ops.sort(key=lambda m: m.duration_ms, reverse=True)

        return [
            {
                "operation": m.name,
                "duration_ms": round(m.duration_ms, 2),
                "timestamp": datetime.fromtimestamp(m.start_time, UTC).isoformat(),
                "metadata": m.metadata,
            }
            for m in slow_ops[:limit]
        ]

    async def get_active_operations(self) -> list[dict[str, Any]]:
        """Get currently active operations.

        Returns:
            List of active operations
        """
        async with self._lock:
            return [
                {
                    "operation": metric.name,
                    "elapsed_ms": round(
                        (time.perf_counter() - metric.start_time) * 1000, 2
                    ),
                    "metadata": metric.metadata,
                }
                for metric in self._active_operations.values()
            ]

    def reset(self) -> None:
        """Reset all metrics and statistics."""
        self._metrics.clear()
        self._stats.clear()
        self._active_operations.clear()
        logger.info("Performance monitor reset")

    def generate_report(self) -> str:
        """Generate performance report.

        Returns:
            Formatted performance report
        """
        lines = ["=== Performance Report ===\n"]

        # Overall statistics
        total_ops = sum(s.count for s in self._stats.values())
        total_time = sum(s.total_ms for s in self._stats.values())
        slow_ops = sum(s.slow_count for s in self._stats.values())

        lines.append(f"Total Operations: {total_ops}")
        lines.append(f"Total Time: {total_time:.1f}ms")
        lines.append(
            f"Slow Operations: {slow_ops} ({slow_ops / total_ops * 100:.1f}%)\n"
        )

        # Per-operation statistics
        lines.append("Operation Statistics:")
        lines.append("-" * 80)
        lines.append(
            f"{'Operation':<30} {'Count':>8} {'Avg(ms)':>10} "
            f"{'Min(ms)':>10} {'Max(ms)':>10} {'Slow%':>8}"
        )
        lines.append("-" * 80)

        for op, stats in sorted(
            self._stats.items(), key=lambda x: x[1].total_ms, reverse=True
        ):
            slow_pct = (stats.slow_count / stats.count * 100) if stats.count > 0 else 0
            lines.append(
                f"{op:<30} {stats.count:>8} {stats.avg_ms:>10.1f} "
                f"{stats.min_ms:>10.1f} {stats.max_ms:>10.1f} {slow_pct:>7.1f}%"
            )

        # Slowest operations
        lines.append("\n\nSlowest Operations:")
        lines.append("-" * 80)

        slow_ops = self.get_slow_operations(10)
        for op in slow_ops:
            lines.append(
                f"{op['operation']}: {op['duration_ms']}ms "
                f"at {op['timestamp']} {op['metadata']}"
            )

        return "\n".join(lines)
