#!/usr/bin/env python3
"""Comprehensive dataset verification script for Phase 2.0.

This script validates the generated questions.json file to ensure:
1. All image questions have correct mappings
2. Multilingual content is complete
3. Data structure is valid
"""

import json
import sys
from pathlib import Path
from typing import Any


class DatasetVerifier:
    """Verify the integrity of the generated dataset."""

    # Known problematic image questions from Phase 1.7
    CRITICAL_IMAGE_QUESTIONS = {21, 22, 209, 226, 275, 294, 319, 344, 369, 394}

    # Expected languages
    REQUIRED_LANGUAGES = {"en", "de", "tr", "uk", "ar"}

    # Required answer fields for each language
    REQUIRED_ANSWER_FIELDS = {
        "explanation",
        "why_others_wrong",
        "key_concept",
        "mnemonic",
    }

    def __init__(self, dataset_path: Path = Path("data/questions.json")):
        self.dataset_path = dataset_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stats: dict[str, Any] = {
            "total_questions": 0,
            "image_questions": 0,
            "text_questions": 0,
            "multilingual_complete": 0,
            "missing_images": 0,
            "critical_issues": 0,
        }

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load the dataset from JSON file."""
        if not self.dataset_path.exists():
            self.errors.append(f"Dataset file not found: {self.dataset_path}")
            return []

        try:
            with open(self.dataset_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load dataset: {e}")
            return []

    def verify_image_question(self, question: dict[str, Any]) -> None:
        """Verify an image question has proper mappings."""
        q_id = question.get("id", "unknown")

        # Check if it's detected as image question
        if not question.get("images"):
            self.errors.append(
                f"Question {q_id}: Image question missing 'images' field"
            )
            self.stats["missing_images"] += 1
            return

        images = question["images"]
        if not isinstance(images, list) or len(images) == 0:
            self.errors.append(f"Question {q_id}: Empty or invalid images array")
            self.stats["missing_images"] += 1
            return

        # Verify each image
        for img in images:
            if not isinstance(img, dict):
                self.errors.append(f"Question {q_id}: Invalid image format")
                continue

            # Check required image fields
            if not img.get("path"):
                self.errors.append(f"Question {q_id}: Image missing 'path' field")
            else:
                # Verify image file exists
                img_path = Path("data") / img["path"]
                if not img_path.exists():
                    self.errors.append(
                        f"Question {q_id}: Image file not found: {img_path}"
                    )

            if not img.get("description"):
                self.warnings.append(f"Question {q_id}: Image missing AI description")

        # Special check for critical questions
        if q_id in self.CRITICAL_IMAGE_QUESTIONS:
            if len(images) == 0:
                self.errors.append(
                    f"CRITICAL: Question {q_id} is known problematic but has no images!"
                )
                self.stats["critical_issues"] += 1

    def verify_multilingual_answers(self, question: dict[str, Any]) -> bool:
        """Verify multilingual answers are complete."""
        q_id = question.get("id", "unknown")
        answers = question.get("answers", {})

        if not answers:
            self.errors.append(f"Question {q_id}: Missing 'answers' field")
            return False

        complete = True
        for lang in self.REQUIRED_LANGUAGES:
            if lang not in answers:
                self.errors.append(f"Question {q_id}: Missing language '{lang}'")
                complete = False
                continue

            lang_answers = answers[lang]
            if not isinstance(lang_answers, dict):
                self.errors.append(
                    f"Question {q_id}: Invalid format for language '{lang}'"
                )
                complete = False
                continue

            # Check required fields
            for field in self.REQUIRED_ANSWER_FIELDS:
                if field not in lang_answers:
                    self.errors.append(
                        f"Question {q_id}: Missing '{field}' in language '{lang}'"
                    )
                    complete = False
                elif not lang_answers[field]:
                    self.warnings.append(
                        f"Question {q_id}: Empty '{field}' in language '{lang}'"
                    )

        return complete

    def verify_question_structure(self, question: dict[str, Any]) -> None:
        """Verify basic question structure."""
        q_id = question.get("id", "unknown")

        # Required fields
        required = ["id", "question", "options", "correct", "category"]
        for field in required:
            if field not in question:
                self.errors.append(f"Question {q_id}: Missing required field '{field}'")

        # Verify options
        options = question.get("options", [])
        if not isinstance(options, list) or len(options) != 4:
            self.errors.append(f"Question {q_id}: Must have exactly 4 options")
        else:
            # Check if correct answer is in options
            correct = question.get("correct")
            if correct and correct not in options:
                self.errors.append(
                    f"Question {q_id}: Correct answer '{correct}' not in options"
                )

    def is_image_question(self, question: dict[str, Any]) -> bool:
        """Determine if a question is an image question."""
        # Check for explicit image question indicators
        if question.get("images"):
            return True

        # Check for "Bild" pattern in options
        options = question.get("options", [])
        bild_count = sum(1 for opt in options if "Bild" in str(opt))
        if bild_count >= 2:
            return True

        # Check for image keywords in question
        question_text = question.get("question", "").lower()
        image_keywords = ["wappen", "flagge", "symbol", "zeigt", "abbildung", "bild"]
        return any(keyword in question_text for keyword in image_keywords)

    def verify_dataset(self) -> bool:
        """Run comprehensive verification."""
        print("Loading dataset...")
        questions = self.load_dataset()

        if not questions:
            print("❌ Failed to load dataset")
            return False

        self.stats["total_questions"] = len(questions)
        print(f"Loaded {len(questions)} questions")

        # Track image questions
        detected_image_questions: set[int] = set()

        print("\nVerifying questions...")
        for i, question in enumerate(questions):
            # Basic structure
            self.verify_question_structure(question)

            # Check if image question
            if self.is_image_question(question):
                self.stats["image_questions"] += 1
                detected_image_questions.add(question.get("id", 0))
                self.verify_image_question(question)
            else:
                self.stats["text_questions"] += 1

            # Multilingual verification
            if self.verify_multilingual_answers(question):
                self.stats["multilingual_complete"] += 1

            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(questions)} questions...")

        # Verify critical image questions were detected
        print("\nChecking critical image questions...")
        for q_id in self.CRITICAL_IMAGE_QUESTIONS:
            if q_id not in detected_image_questions:
                self.errors.append(
                    f"CRITICAL: Known image question {q_id} not detected as image question!"
                )
                self.stats["critical_issues"] += 1

        return len(self.errors) == 0

    def print_report(self) -> None:
        """Print verification report."""
        print("\n" + "=" * 60)
        print("DATASET VERIFICATION REPORT")
        print("=" * 60)

        print("\n📊 Statistics:")
        print(f"  Total questions: {self.stats['total_questions']}")
        print(f"  Image questions: {self.stats['image_questions']}")
        print(f"  Text questions: {self.stats['text_questions']}")
        print(f"  Complete multilingual: {self.stats['multilingual_complete']}")
        print(f"  Missing images: {self.stats['missing_images']}")
        print(f"  Critical issues: {self.stats['critical_issues']}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"  - {warning}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more warnings")

        print("\n" + "=" * 60)
        if len(self.errors) == 0:
            print("✅ DATASET VALIDATION PASSED!")
        else:
            print("❌ DATASET VALIDATION FAILED!")
        print("=" * 60)


def main():
    """Main verification process."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify Integran dataset")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/questions.json"),
        help="Path to dataset file",
    )
    args = parser.parse_args()

    verifier = DatasetVerifier(args.dataset)
    success = verifier.verify_dataset()
    verifier.print_report()

    if args.strict and verifier.warnings:
        print("\n❌ Strict mode: warnings treated as errors")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
