#!/usr/bin/env python3
"""
Finalize Dataset Creation

This script:
1. Takes the step3_explanations_progress.json file
2. Creates the final_dataset.json with all successfully processed questions
3. Reports any missing questions
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_final_dataset():
    """Create final dataset from progress file."""

    # File paths
    progress_file = Path("data/step3_explanations_progress.json")
    final_file = Path("data/final_dataset.json")

    # Load progress file
    if not progress_file.exists():
        logger.error(f"Progress file not found: {progress_file}")
        return False

    logger.info(f"Loading progress file: {progress_file}")
    with open(progress_file, encoding="utf-8") as f:
        progress_data = json.load(f)

    # Create final dataset structure
    final_dataset = {
        "questions": progress_data.get("questions", {}),
        "metadata": {
            "step": "final_dataset",
            "description": "Complete dataset with multilingual explanations, mnemonics, and key concepts",
            "languages": ["en", "de", "tr", "uk", "ar"],
            "total_questions": len(progress_data.get("questions", {})),
            "source_files": {
                "pdf": "data/gesamtfragenkatalog-lebenindeutschland.pdf",
                "extraction": "data/direct_extraction.json",
                "images_fixed": "data/step2_answers_fixed.json",
                "explanations": "data/step3_explanations_progress.json",
            },
        },
    }

    # Check for missing questions (should be 460 total)
    expected_total = 460
    actual_total = len(final_dataset["questions"])
    missing_count = expected_total - actual_total

    if missing_count > 0:
        # Find missing question IDs
        all_ids = set(range(1, expected_total + 1))
        processed_ids = set(int(q_id) for q_id in final_dataset["questions"].keys())
        missing_ids = sorted(all_ids - processed_ids)

        final_dataset["metadata"]["missing_questions"] = missing_ids
        final_dataset["metadata"]["missing_count"] = missing_count

        logger.warning(f"Missing {missing_count} questions: {missing_ids}")
    else:
        final_dataset["metadata"]["missing_questions"] = []
        final_dataset["metadata"]["missing_count"] = 0

    # Add processing summary
    final_dataset["metadata"]["processing_summary"] = {
        "total_expected": expected_total,
        "total_processed": actual_total,
        "success_rate": round((actual_total / expected_total) * 100, 1)
        if expected_total > 0
        else 0,
        "complete": missing_count == 0,
    }

    # Save final dataset
    logger.info(f"Saving final dataset to: {final_file}")
    with open(final_file, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    # Print summary
    logger.info("=" * 60)
    logger.info("FINAL DATASET CREATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total questions expected: {expected_total}")
    logger.info(f"Total questions processed: {actual_total}")
    logger.info(f"Missing questions: {missing_count}")
    if missing_count > 0:
        logger.info(f"Missing IDs: {missing_ids}")
    logger.info(
        f"Success rate: {final_dataset['metadata']['processing_summary']['success_rate']}%"
    )
    logger.info(f"Output file: {final_file}")
    logger.info("=" * 60)

    return missing_count == 0


def main():
    """Main entry point."""
    success = create_final_dataset()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
