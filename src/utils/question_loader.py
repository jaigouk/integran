"""Simple utility to ensure questions file is available."""

import logging
from pathlib import Path

from src.core.settings import get_settings

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

    # Check for the direct extraction checkpoint file as a fallback
    checkpoint_path = Path("data/direct_extraction_checkpoint.json")

    # If JSON already exists, use it
    if json_path.exists():
        logger.info(f"Using existing questions file: {json_path}")
        return json_path

    # If checkpoint file exists, suggest using it
    if checkpoint_path.exists():
        raise FileNotFoundError(
            f"Questions file not found at: {json_path}\n"
            f"However, extraction checkpoint exists at: {checkpoint_path}\n"
            f"Please run 'integran-build-dataset' to build the complete dataset, or\n"
            f"Copy the checkpoint file to {json_path} to use raw extracted data."
        )

    # If nothing exists, provide helpful error message
    raise FileNotFoundError(
        f"Questions file not found. Please ensure one of the following:\n"
        f"1. {json_path} exists (processed questions)\n"
        f"2. Run 'integran-direct-extract' to extract questions from PDF\n"
        f"3. Run 'integran-build-dataset' to build complete multilingual dataset"
    )
