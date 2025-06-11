"""CLI command for building the complete multilingual dataset."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.core.data_builder import DataBuilder
from src.core.settings import has_gemini_config

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
        builder = DataBuilder()

        # Show status if requested
        if args.status:
            status = builder.get_build_status()
            print_build_status(status)
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
        logger.info(f"  - Use RAG: {not args.no_rag}")
        logger.info(f"  - Multilingual: {not args.no_multilingual}")
        logger.info(f"  - Batch size: {args.batch_size}")

        success = builder.build_complete_dataset(
            force_rebuild=args.force_rebuild,
            use_rag=not args.no_rag,
            multilingual=not args.no_multilingual,
            batch_size=args.batch_size,
        )

        if success:
            logger.info("✅ Dataset build completed successfully!")

            # Show final status
            status = builder.get_build_status()
            print_build_status(status)

            logger.info("📁 Output files:")
            logger.info("  - data/questions.json (Complete multilingual dataset)")
            logger.info("  - data/dataset_checkpoint.json (Build progress)")

        else:
            logger.error("❌ Dataset build failed")
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
