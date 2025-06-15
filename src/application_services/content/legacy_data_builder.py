"""Legacy wrapper for data building - redirects to new DDD Content Context."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.infrastructure.config.settings import has_gemini_config
from src.infrastructure.containers.content_container import ContentContainer

logger = logging.getLogger(__name__)


class DataBuilder:
    """Legacy wrapper for backward compatibility - uses new DDD Content Context."""

    def __init__(self) -> None:
        """Initialize the data builder."""
        self._container = ContentContainer()
        self._content_builder = self._container.get_content_builder_service()

    def build_complete_dataset(
        self,
        force_rebuild: bool = False,
        use_rag: bool = True,
        multilingual: bool = True,
        batch_size: int = 10,
    ) -> bool:
        """Build the complete multilingual dataset with image mappings."""
        if not has_gemini_config():
            raise ValueError("Gemini API not configured. Please set up authentication.")

        # Note: use_rag parameter is ignored as RAG was removed
        if use_rag:
            logger.info("Note: RAG functionality has been removed from the system")

        # Run async method in sync context
        result: bool = asyncio.run(
            self._content_builder.build_complete_dataset(
                force_rebuild=force_rebuild,
                multilingual=multilingual,
                batch_size=batch_size,
            )
        )
        return result

    def get_build_status(self) -> dict[str, Any]:
        """Get current build status."""
        # Run async method in sync context
        return asyncio.run(self._content_builder.get_build_status())
