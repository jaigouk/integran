"""CLI command for building the complete multilingual dataset."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.domain.content.services.build_dataset import (
    BuildDataset,
    BuildDatasetRequest,
    GetBuildStatusRequest,
)
from src.infrastructure.config.settings import has_gemini_config
from src.infrastructure.messaging.enhanced_event_bus import EnhancedEventBus
from src.infrastructure.repositories.content_repository import ContentRepository

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_dataset_cli() -> None:
    """CLI entry point for building the complete dataset."""
    parser = argparse.ArgumentParser(
        description="Build complete multilingual dataset for German Integration Exam",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build complete multilingual dataset
  integran-build-dataset

  # Force rebuild everything from scratch
  integran-build-dataset --force-rebuild

  # Build without RAG enhancement (faster, less context)
  integran-build-dataset --no-rag

  # Build without multilingual support (testing only)
  integran-build-dataset --no-multilingual

  # Use larger batch size for faster processing
  integran-build-dataset --batch-size 20

  # Check current build status
  integran-build-dataset --status
        """,
    )

    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Rebuild everything from scratch, ignoring existing checkpoint",
    )

    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Disable RAG enhancement for faster processing",
    )

    parser.add_argument(
        "--no-multilingual",
        action="store_true",
        help="Skip multilingual generation (for testing)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of questions to process in each batch (default: 10)",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current build status and exit",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Initialize domain service
        event_bus = EnhancedEventBus.create_basic()
        repository = ContentRepository()
        build_service = BuildDataset(repository=repository, event_bus=event_bus)

        # Show status if requested
        if args.status:
            status_request = GetBuildStatusRequest(include_detailed_progress=True)
            status_result = asyncio.run(build_service.call(status_request))
            if status_result.success:
                print_build_status(status_result.detailed_status)
            else:
                logger.error(
                    f"Failed to get build status: {status_result.error_message}"
                )
                sys.exit(1)
            return

        # Check prerequisites
        if not has_gemini_config():
            logger.error("❌ Gemini API not configured")
            logger.error("Please set up authentication:")
            logger.error(
                "  - For Vertex AI: Set GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT_ID"
            )
            logger.error(
                "  - For API Key: Set GEMINI_API_KEY, GCP_PROJECT_ID, and USE_VERTEX_AI=false"
            )
            sys.exit(1)

        # Check if extraction checkpoint exists
        extraction_path = Path("data/extraction_checkpoint.json")
        if not extraction_path.exists():
            logger.error("❌ Extraction checkpoint not found")
            logger.error("Please run PDF extraction first:")
            logger.error("  integran-direct-extract")
            sys.exit(1)

        # Build dataset
        logger.info("🚀 Starting dataset build...")
        logger.info("Settings:")
        logger.info(f"  - Force rebuild: {args.force_rebuild}")
        logger.info(f"  - Use RAG: {not args.no_rag} (Note: RAG has been removed)")
        logger.info(f"  - Multilingual: {not args.no_multilingual}")
        logger.info(f"  - Batch size: {args.batch_size}")

        # Create build request
        build_request = BuildDatasetRequest(
            force_rebuild=args.force_rebuild,
            multilingual=not args.no_multilingual,
            batch_size=args.batch_size,
            enable_image_processing=True,
            include_rag_sources=False,  # RAG has been removed
        )

        # Execute build
        build_result = asyncio.run(build_service.call(build_request))

        if build_result.success:
            logger.info("✅ Dataset build completed successfully!")

            # Show final statistics
            stats = build_result.statistics
            logger.info("📊 Build Statistics:")
            logger.info(f"  - Total questions: {stats.get('total_questions', 0)}")
            logger.info(
                f"  - Questions with answers: {stats.get('questions_with_answers', 0)}"
            )
            logger.info(
                f"  - Questions with images: {stats.get('questions_with_images', 0)}"
            )
            logger.info(
                f"  - Build duration: {stats.get('build_duration_minutes', 0):.1f} minutes"
            )
            logger.info(f"  - Completion rate: {stats.get('completion_rate', 0):.1f}%")

            # Show final status using the new status system
            status_request = GetBuildStatusRequest(include_detailed_progress=True)
            status_result = asyncio.run(build_service.call(status_request))
            if status_result.success:
                print_build_status(status_result.detailed_status)

            logger.info("📁 Output files:")
            if build_result.final_dataset_path:
                logger.info(
                    f"  - {build_result.final_dataset_path} (Complete multilingual dataset)"
                )
            logger.info("  - data/dataset_checkpoint.json (Build progress)")

        else:
            logger.error("❌ Dataset build failed")
            if build_result.error_message:
                logger.error(f"Error: {build_result.error_message}")
            logger.error("Check logs above for details")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("⚠️ Build interrupted by user")
        logger.info("Progress has been saved. Resume with the same command.")
        sys.exit(130)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def print_build_status(status: dict) -> None:
    """Print formatted build status."""
    state = status.get("state", "unknown")

    print(f"\n📊 Build Status: {state.upper()}")

    if status.get("started_at"):
        print(f"Started: {status['started_at']}")

    if status.get("completed_at"):
        print(f"Completed: {status['completed_at']}")

    if status.get("images_processed"):
        print("✅ Images processed and mapped")
    else:
        print("⏳ Images not yet processed")

    completed = status.get("completed_answers", 0)
    total = status.get("total_questions", 0)

    if total > 0:
        progress = status.get("progress_percent", 0)
        print(f"Questions: {completed}/{total} ({progress:.1f}%)")

        if completed > 0 and completed < total:
            print("💡 Resume with: integran-build-dataset")

    print()


if __name__ == "__main__":
    build_dataset_cli()
