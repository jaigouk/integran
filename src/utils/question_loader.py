"""Simple utility to ensure questions file is available."""

import logging
from pathlib import Path

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


def ensure_questions_available() -> Path:
    """Ensure questions are available for the application.

    Returns:
        Path to the questions JSON file.

    Raises:
        FileNotFoundError: If questions file doesn't exist.
    """
    settings = get_settings()
    json_path = Path(settings.questions_json_path)

    # Check for fallback files in order of preference
    fallback_paths = [
        Path("data/final_dataset.json"),  # Current format
        Path("data/direct_extraction_checkpoint.json"),  # Raw extraction
    ]

    # If primary JSON already exists, use it
    if json_path.exists():
        logger.info(f"Using existing questions file: {json_path}")
        return json_path

    # Try fallback files
    for fallback_path in fallback_paths:
        if fallback_path.exists():
            logger.info(f"Primary file not found, using fallback: {fallback_path}")
            return fallback_path

    # If nothing exists, provide helpful error message
    raise FileNotFoundError(
        f"Questions file not found. Please ensure one of the following:\n"
        f"1. {json_path} exists (processed questions)\n"
        f"2. Run 'integran-direct-extract' to extract questions from PDF\n"
        f"3. Run 'integran-build-dataset' to build complete multilingual dataset"
    )
