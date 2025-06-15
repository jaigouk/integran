#!/usr/bin/env python3
"""
Import reviewed CSV files back into final_dataset.json format.

This script takes the CSV files that were exported for review, reads the
reviewer feedback and corrections, and updates the original JSON dataset.
"""

import argparse
import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_original_dataset(file_path: str) -> dict[str, Any]:
    """Load the original dataset JSON file."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def read_csv_with_encoding(file_path: str) -> list[dict[str, str]]:
    """Read CSV file with proper encoding handling."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        # Fallback to other encodings if UTF-8 fails
        for encoding in ["utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(file_path, encoding=encoding) as f:
                    return list(csv.DictReader(f))
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not read {file_path} with any supported encoding")


def validate_review_status(status: str) -> bool:
    """Validate review status values."""
    valid_statuses = ["APPROVED", "NEEDS_REVISION", "UNCLEAR", "SKIP", ""]
    return status.upper() in valid_statuses


def import_main_content(
    csv_data: list[dict[str, str]], dataset: dict[str, Any]
) -> dict[str, list[str]]:
    """Import main content CSV and update dataset. Returns change log."""
    changes = {
        "updated_questions": [],
        "updated_explanations": [],
        "updated_concepts": [],
        "updated_mnemonics": [],
        "validation_errors": [],
    }

    for row in csv_data:
        question_id = str(row["ID"])

        if question_id not in dataset["questions"]:
            changes["validation_errors"].append(
                f"Question ID {question_id} not found in original dataset"
            )
            continue

        question = dataset["questions"][question_id]

        # Check review status
        review_status = row.get("Review_Status", "").strip().upper()

        if not validate_review_status(review_status):
            changes["validation_errors"].append(
                f"Invalid review status '{review_status}' for question {question_id}"
            )
            continue

        # Skip if not approved for changes
        if review_status in ["SKIP", "UNCLEAR", ""]:
            continue

        # Store reviewer comments in metadata
        if row.get("Reviewer_Comments", "").strip():
            if "review_metadata" not in question:
                question["review_metadata"] = {}
            question["review_metadata"]["main_content_comments"] = row[
                "Reviewer_Comments"
            ].strip()

        # Update explanations if they were modified and approved
        if review_status == "APPROVED":
            # Check for changes in explanations
            original_en = question.get("explanations", {}).get("en", "")
            original_de = question.get("explanations", {}).get("de", "")
            new_en = row.get("Explanation_EN", "").strip()
            new_de = row.get("Explanation_DE", "").strip()

            if new_en and new_en != original_en:
                question.setdefault("explanations", {})["en"] = new_en
                changes["updated_explanations"].append(
                    f"Q{question_id}: Updated EN explanation"
                )

            if new_de and new_de != original_de:
                question.setdefault("explanations", {})["de"] = new_de
                changes["updated_explanations"].append(
                    f"Q{question_id}: Updated DE explanation"
                )

            # Check for changes in key concepts
            original_concept_en = question.get("key_concept", {}).get("en", "")
            original_concept_de = question.get("key_concept", {}).get("de", "")
            new_concept_en = row.get("Key_Concept_EN", "").strip()
            new_concept_de = row.get("Key_Concept_DE", "").strip()

            if new_concept_en and new_concept_en != original_concept_en:
                question.setdefault("key_concept", {})["en"] = new_concept_en
                changes["updated_concepts"].append(
                    f"Q{question_id}: Updated EN key concept"
                )

            if new_concept_de and new_concept_de != original_concept_de:
                question.setdefault("key_concept", {})["de"] = new_concept_de
                changes["updated_concepts"].append(
                    f"Q{question_id}: Updated DE key concept"
                )

            # Check for changes in mnemonics
            original_mnemonic_en = question.get("mnemonic", {}).get("en", "")
            original_mnemonic_de = question.get("mnemonic", {}).get("de", "")
            new_mnemonic_en = row.get("Mnemonic_EN", "").strip()
            new_mnemonic_de = row.get("Mnemonic_DE", "").strip()

            if new_mnemonic_en and new_mnemonic_en != original_mnemonic_en:
                question.setdefault("mnemonic", {})["en"] = new_mnemonic_en
                changes["updated_mnemonics"].append(
                    f"Q{question_id}: Updated EN mnemonic"
                )

            if new_mnemonic_de and new_mnemonic_de != original_mnemonic_de:
                question.setdefault("mnemonic", {})["de"] = new_mnemonic_de
                changes["updated_mnemonics"].append(
                    f"Q{question_id}: Updated DE mnemonic"
                )

    return changes


def import_wrong_answers(
    csv_data: list[dict[str, str]], dataset: dict[str, Any]
) -> dict[str, list[str]]:
    """Import wrong answers CSV and update dataset. Returns change log."""
    changes = {"updated_wrong_explanations": [], "validation_errors": []}

    for row in csv_data:
        question_id = str(row["ID"])
        language = row["Language"].lower()

        if question_id not in dataset["questions"]:
            changes["validation_errors"].append(
                f"Question ID {question_id} not found in original dataset"
            )
            continue

        question = dataset["questions"][question_id]

        # Check review status
        review_status = row.get("Review_Status", "").strip().upper()

        if review_status != "APPROVED":
            continue

        # Store reviewer comments
        if row.get("Reviewer_Comments", "").strip():
            if "review_metadata" not in question:
                question["review_metadata"] = {}
            if "wrong_answers_comments" not in question["review_metadata"]:
                question["review_metadata"]["wrong_answers_comments"] = {}
            question["review_metadata"]["wrong_answers_comments"][language] = row[
                "Reviewer_Comments"
            ].strip()

        # Update wrong answer explanations
        if "why_others_wrong" not in question:
            question["why_others_wrong"] = {}
        if language not in question["why_others_wrong"]:
            question["why_others_wrong"][language] = {}

        original_wrong_answers = question["why_others_wrong"][language]
        if not isinstance(original_wrong_answers, dict):
            # Handle cases where it might be a string (data inconsistency)
            original_wrong_answers = {}
            question["why_others_wrong"][language] = original_wrong_answers

        # Update each wrong answer explanation
        for option in ["A", "B", "C"]:
            csv_key = f"Why_{option}_Wrong"
            new_explanation = row.get(csv_key, "").strip()

            if new_explanation and new_explanation != original_wrong_answers.get(
                option, ""
            ):
                original_wrong_answers[option] = new_explanation
                changes["updated_wrong_explanations"].append(
                    f"Q{question_id} {language.upper()}: Updated why {option} wrong"
                )

    return changes


def import_multilingual_content(
    csv_data: list[dict[str, str]], dataset: dict[str, Any]
) -> dict[str, list[str]]:
    """Import multilingual content CSV and update dataset. Returns change log."""
    changes = {"updated_multilingual": [], "validation_errors": []}

    for row in csv_data:
        question_id = str(row["ID"])
        language = row["Language"].lower()

        if question_id not in dataset["questions"]:
            changes["validation_errors"].append(
                f"Question ID {question_id} not found in original dataset"
            )
            continue

        question = dataset["questions"][question_id]

        # Check review status
        review_status = row.get("Review_Status", "").strip().upper()

        if review_status != "APPROVED":
            continue

        # Store reviewer comments
        if row.get("Reviewer_Comments", "").strip():
            if "review_metadata" not in question:
                question["review_metadata"] = {}
            if "multilingual_comments" not in question["review_metadata"]:
                question["review_metadata"]["multilingual_comments"] = {}
            question["review_metadata"]["multilingual_comments"][language] = row[
                "Reviewer_Comments"
            ].strip()

        # Update multilingual content
        updated_fields = []

        # Update explanation
        new_explanation = row.get("Explanation", "").strip()
        if new_explanation:
            original = question.get("explanations", {}).get(language, "")
            if new_explanation != original:
                question.setdefault("explanations", {})[language] = new_explanation
                updated_fields.append("explanation")

        # Update key concept
        new_concept = row.get("Key_Concept", "").strip()
        if new_concept:
            original = question.get("key_concept", {}).get(language, "")
            if new_concept != original:
                question.setdefault("key_concept", {})[language] = new_concept
                updated_fields.append("key_concept")

        # Update mnemonic
        new_mnemonic = row.get("Mnemonic", "").strip()
        if new_mnemonic:
            original = question.get("mnemonic", {}).get(language, "")
            if new_mnemonic != original:
                question.setdefault("mnemonic", {})[language] = new_mnemonic
                updated_fields.append("mnemonic")

        if updated_fields:
            changes["updated_multilingual"].append(
                f"Q{question_id} {language.upper()}: Updated {', '.join(updated_fields)}"
            )

    return changes


def generate_change_report(
    all_changes: dict[str, dict[str, list[str]]], output_path: str
) -> None:
    """Generate a detailed change report."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Dataset Review Import Report\n\n")
        f.write(f"Generated: {timestamp}\n\n")

        total_changes = 0
        total_errors = 0

        for file_name, changes in all_changes.items():
            f.write(f"## {file_name}\n\n")

            for change_type, change_list in changes.items():
                if change_type == "validation_errors":
                    if change_list:
                        f.write(f"### ⚠️ Validation Errors ({len(change_list)})\n")
                        for error in change_list:
                            f.write(f"- {error}\n")
                        f.write("\n")
                        total_errors += len(change_list)
                else:
                    if change_list:
                        f.write(
                            f"### ✅ {change_type.replace('_', ' ').title()} ({len(change_list)})\n"
                        )
                        for change in change_list:
                            f.write(f"- {change}\n")
                        f.write("\n")
                        total_changes += len(change_list)

        f.write("## Summary\n\n")
        f.write(f"- **Total Changes Applied**: {total_changes}\n")
        f.write(f"- **Total Validation Errors**: {total_errors}\n")

        if total_errors > 0:
            f.write(
                f"\n⚠️ **Warning**: {total_errors} validation errors were found. Please review the errors above.\n"
            )
        else:
            f.write(
                "\n✅ **Success**: All changes were applied without validation errors.\n"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Import reviewed CSV files back to JSON dataset"
    )
    parser.add_argument(
        "--input-dir",
        default="data/review_for_upload",
        help="Directory containing reviewed CSV files (default: data/review_for_upload)",
    )
    parser.add_argument(
        "--original-dataset",
        default="data/final_dataset.json",
        help="Original dataset JSON file (default: data/final_dataset.json)",
    )
    parser.add_argument(
        "--output",
        default="data/final_dataset_reviewed.json",
        help="Output file for updated dataset (default: data/final_dataset_reviewed.json)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of original dataset before updating",
    )
    parser.add_argument(
        "--report",
        default="review_import_report.md",
        help="Output file for change report (default: review_import_report.md)",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    # Check if input directory exists
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        return 1

    # Load original dataset
    print(f"Loading original dataset from {args.original_dataset}...")
    try:
        dataset = load_original_dataset(args.original_dataset)
    except FileNotFoundError:
        print(f"Error: Original dataset file {args.original_dataset} not found")
        return 1

    # Create backup if requested
    if args.backup:
        backup_path = f"{args.original_dataset}.backup.{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(args.original_dataset, backup_path)
        print(f"Created backup: {backup_path}")

    all_changes = {}

    # Import main content
    main_content_file = input_dir / "main_content.csv"
    if main_content_file.exists():
        print("Importing main content...")
        csv_data = read_csv_with_encoding(str(main_content_file))
        changes = import_main_content(csv_data, dataset)
        all_changes["main_content.csv"] = changes
    else:
        print("Warning: main_content.csv not found, skipping...")

    # Import wrong answers
    wrong_answers_file = input_dir / "wrong_answers.csv"
    if wrong_answers_file.exists():
        print("Importing wrong answers...")
        csv_data = read_csv_with_encoding(str(wrong_answers_file))
        changes = import_wrong_answers(csv_data, dataset)
        all_changes["wrong_answers.csv"] = changes
    else:
        print("Warning: wrong_answers.csv not found, skipping...")

    # Import multilingual content
    multilingual_file = input_dir / "multilingual_content.csv"
    if multilingual_file.exists():
        print("Importing multilingual content...")
        csv_data = read_csv_with_encoding(str(multilingual_file))
        changes = import_multilingual_content(csv_data, dataset)
        all_changes["multilingual_content.csv"] = changes
    else:
        print("Warning: multilingual_content.csv not found, skipping...")

    # Add review metadata to dataset
    dataset["review_metadata"] = {
        "last_review_import": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        "import_source": str(input_dir),
        "reviewer_count": len([f for f in input_dir.glob("*.csv")]),
    }

    # Save updated dataset
    print(f"Saving updated dataset to {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    # Generate change report
    print(f"Generating change report: {args.report}")
    generate_change_report(all_changes, args.report)

    # Print summary
    total_changes = sum(
        len(changes[key])
        for changes in all_changes.values()
        for key in changes
        if key != "validation_errors"
    )
    total_errors = sum(
        len(changes.get("validation_errors", [])) for changes in all_changes.values()
    )

    print("\n✅ Import complete!")
    print(f"📊 Total changes applied: {total_changes}")
    print(f"⚠️ Validation errors: {total_errors}")
    print(f"📋 Detailed report: {args.report}")

    if total_errors > 0:
        print(
            f"\n⚠️ Warning: {total_errors} validation errors found. Please review the report."
        )
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
