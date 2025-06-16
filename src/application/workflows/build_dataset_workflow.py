"""Thin workflow coordinator for dataset building following CQRS and DDD patterns."""

from __future__ import annotations

from typing import Any

from src.domain.content.services.build_dataset import BuildDataset, BuildDatasetRequest


class DatasetBuildWorkflow:
    """Thin coordinator - delegates all operations to BuildDataset domain service."""

    def __init__(self, build_dataset_service: BuildDataset) -> None:
        self.build_dataset_service = build_dataset_service

    async def build_complete_dataset(
        self,
        force_rebuild: bool = False,
        multilingual: bool = True,
        batch_size: int = 10,
    ) -> dict[str, Any]:
        """Build complete dataset - validate input and delegate to domain service."""
        request = BuildDatasetRequest(force_rebuild, multilingual, batch_size)
        result = await self.build_dataset_service.call(request)
        return {
            "success": result.success,
            "dataset_path": result.final_dataset_path,
            "statistics": result.statistics,
            "progress": result.build_progress,
            "error": result.error_message,
        }

    async def get_build_status(self) -> dict[str, Any]:
        """Get current build status - delegate to domain service."""
        request = BuildDatasetRequest()  # Empty request for status check
        result = await self.build_dataset_service.call(request)
        return {"progress": result.build_progress, "statistics": result.statistics}
