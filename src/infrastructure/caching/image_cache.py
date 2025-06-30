"""Image caching and optimization for performance."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

from src.infrastructure.caching.question_cache import QuestionCache

logger = logging.getLogger(__name__)


class ImageCache:
    """Optimized image caching with memory management."""

    def __init__(
        self,
        max_memory_mb: float = 100.0,  # 100MB default
        max_items: int = 200,
    ):
        """Initialize image cache with memory limits.

        Args:
            max_memory_mb: Maximum memory usage in megabytes
            max_items: Maximum number of cached images
        """
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.max_items = max_items
        self._cache = QuestionCache(max_size=max_items, ttl_seconds=3600.0)  # 1 hour
        self._memory_usage = 0
        self._file_stats: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_image(
        self,
        path: str,
        loader_func: Any,
        thumbnail: bool = False,
    ) -> bytes | None:
        """Get image from cache or load it.

        Args:
            path: Image file path
            loader_func: Async function to load image if not cached
            thumbnail: Whether to load thumbnail version

        Returns:
            Image bytes or None if not found
        """
        # Generate cache key
        cache_key = self._generate_cache_key(path, thumbnail)

        # Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Image cache hit: {path} (thumbnail={thumbnail})")
            return cached

        # Load image
        logger.debug(f"Image cache miss: {path} (thumbnail={thumbnail})")
        image_data = await loader_func(path)

        if image_data:
            # Check memory usage before caching
            if await self._can_cache(len(image_data)):
                await self._cache_image(cache_key, image_data)
            else:
                logger.warning(
                    f"Image too large to cache: {path} ({len(image_data)} bytes)"
                )

        return image_data

    async def preload_images(
        self,
        paths: list[str],
        loader_func: Any,
        max_concurrent: int = 5,
    ) -> dict[str, bool]:
        """Preload multiple images concurrently.

        Args:
            paths: List of image paths to preload
            loader_func: Async function to load images
            max_concurrent: Maximum concurrent loads

        Returns:
            Dictionary of path -> success status
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def load_one(path: str) -> tuple[str, bool]:
            async with semaphore:
                try:
                    data = await self.get_image(path, loader_func)
                    return (path, data is not None)
                except Exception as e:
                    logger.error(f"Error preloading image {path}: {e}")
                    return (path, False)

        # Load all images concurrently
        tasks = [load_one(path) for path in paths]
        completed = await asyncio.gather(*tasks)

        for path, success in completed:
            results[path] = success

        logger.info(
            f"Preloaded {sum(results.values())}/{len(paths)} images successfully"
        )
        return results

    async def get_image_info(self, path: str) -> dict[str, Any] | None:
        """Get cached image metadata without loading full image.

        Args:
            path: Image file path

        Returns:
            Image metadata or None
        """
        cache_key = f"info:{path}"

        # Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Check file stats
        try:
            file_path = Path(path)
            if file_path.exists():
                stat = file_path.stat()
                info = {
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                }
                await self._cache.set(cache_key, info)
                return info
        except Exception as e:
            logger.error(f"Error getting image info for {path}: {e}")

        return None

    async def optimize_for_display(
        self,
        image_data: bytes,
        max_width: int = 800,
        max_height: int = 600,
        quality: int = 85,
    ) -> bytes:
        """Optimize image for terminal display.

        Args:
            image_data: Original image bytes
            max_width: Maximum display width
            max_height: Maximum display height
            quality: JPEG quality (1-100)

        Returns:
            Optimized image bytes
        """
        try:
            import io

            from PIL import Image

            # Load image
            img = Image.open(io.BytesIO(image_data))

            # Convert RGBA to RGB if needed (for JPEG)
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background

            # Resize if needed
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Save optimized
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()

        except ImportError:
            logger.warning("PIL not available, returning original image")
            return image_data
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return image_data

    async def _can_cache(self, size_bytes: int) -> bool:
        """Check if image can be cached based on memory constraints.

        Args:
            size_bytes: Size of image in bytes

        Returns:
            True if can be cached
        """
        async with self._lock:
            # Check if adding this would exceed memory limit
            if self._memory_usage + size_bytes > self.max_memory_bytes:
                # Try to free some memory
                freed = await self._evict_to_fit(size_bytes)
                if not freed:
                    return False

            return True

    async def _cache_image(self, key: str, data: bytes) -> None:
        """Cache image data with memory tracking.

        Args:
            key: Cache key
            data: Image data
        """
        async with self._lock:
            size = len(data)
            await self._cache.set(key, data)
            self._memory_usage += size
            logger.debug(
                f"Cached image {key}: {size} bytes "
                f"(total: {self._memory_usage / 1024 / 1024:.1f}MB)"
            )

    async def _evict_to_fit(self, required_bytes: int) -> bool:
        """Evict entries to fit required bytes.

        Args:
            required_bytes: Bytes needed

        Returns:
            True if enough space was freed
        """
        # Simple implementation: clear cache if needed
        # In production, implement smarter LRU eviction
        if self._memory_usage + required_bytes > self.max_memory_bytes:
            logger.info("Clearing image cache to free memory")
            await self._cache.clear()
            self._memory_usage = 0
            return True

        return False

    def _generate_cache_key(self, path: str, thumbnail: bool) -> str:
        """Generate unique cache key for image.

        Args:
            path: Image path
            thumbnail: Whether thumbnail version

        Returns:
            Cache key
        """
        key_parts = [path]
        if thumbnail:
            key_parts.append("thumb")

        key_str = ":".join(key_parts)
        return f"img:{hashlib.sha256(key_str.encode()).hexdigest()}"

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        cache_stats = self._cache.get_stats()
        return {
            "items": len(self._cache._cache),
            "memory_mb": round(self._memory_usage / 1024 / 1024, 2),
            "max_memory_mb": round(self.max_memory_bytes / 1024 / 1024, 2),
            "hit_rate": cache_stats.hit_rate,
            "hits": cache_stats.hits,
            "misses": cache_stats.misses,
        }
