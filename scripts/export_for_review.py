#!/usr/bin/env python3
"""
Export final_dataset.json to CSV format for non-technical contributor review.

This script converts the nested JSON structure into reviewer-friendly CSV files
that can be imported into Google Sheets for collaborative review.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_dataset(file_path: str) -> dict[str, Any]:
    """Load the final dataset JSON file."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def export_main_content(questions: dict[str, Any], output_path: str) -> None:
    """Export main question content to CSV."""
    fieldnames = [
        "ID",
        "Question",
        "Option_A",
        "Option_B",
        "Option_C",
        "Option_D",
        "Correct_Answer",
        "Category",
        "Difficulty",
        "Is_Image_Question",
        "Explanation_EN",
        "Explanation_DE",
        "Key_Concept_EN",
        "Key_Concept_DE",
        "Mnemonic_EN",
        "Mnemonic_DE",
        "Review_Status",
        "Reviewer_Comments",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for q_id, question in questions.items():
            row = {
                "ID": question["id"],
                "Question": question["question"],
                "Option_A": question["options"][0]
                if len(question["options"]) > 0
                else "",
                "Option_B": question["options"][1]
                if len(question["options"]) > 1
                else "",
                "Option_C": question["options"][2]
                if len(question["options"]) > 2
                else "",
                "Option_D": question["options"][3]
                if len(question["options"]) > 3
                else "",
                "Correct_Answer": question["correct"],
                "Category": question["category"],
                "Difficulty": question["difficulty"],
                "Is_Image_Question": question["is_image_question"],
                "Explanation_EN": question.get("explanations", {}).get("en", ""),
                "Explanation_DE": question.get("explanations", {}).get("de", ""),
                "Key_Concept_EN": question.get("key_concept", {}).get("en", ""),
                "Key_Concept_DE": question.get("key_concept", {}).get("de", ""),
                "Mnemonic_EN": question.get("mnemonic", {}).get("en", ""),
                "Mnemonic_DE": question.get("mnemonic", {}).get("de", ""),
                "Review_Status": "",  # For reviewers to fill
                "Reviewer_Comments": "",  # For reviewers to fill
            }
            writer.writerow(row)


def export_wrong_answers(questions: dict[str, Any], output_path: str) -> None:
    """Export 'why others wrong' explanations to CSV."""
    fieldnames = [
        "ID",
        "Language",
        "Why_A_Wrong",
        "Why_B_Wrong",
        "Why_C_Wrong",
        "Review_Status",
        "Reviewer_Comments",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for q_id, question in questions.items():
            why_wrong = question.get("why_others_wrong", {})

            # Export for each language
            for lang in ["en", "de", "tr", "uk", "ar"]:
                if lang in why_wrong:
                    lang_explanations = why_wrong[lang]

                    # Handle cases where lang_explanations might be a string instead of dict
                    if isinstance(lang_explanations, str):
                        print(
                            f"Warning: Question {question['id']} has string instead of dict for {lang} why_others_wrong"
                        )
                        continue

                    if isinstance(lang_explanations, dict):
                        row = {
                            "ID": question["id"],
                            "Language": lang.upper(),
                            "Why_A_Wrong": lang_explanations.get("A", ""),
                            "Why_B_Wrong": lang_explanations.get("B", ""),
                            "Why_C_Wrong": lang_explanations.get("C", ""),
                            "Review_Status": "",
                            "Reviewer_Comments": "",
                        }
                        writer.writerow(row)


def export_multilingual_content(questions: dict[str, Any], output_path: str) -> None:
    """Export all explanations and concepts in all languages."""
    fieldnames = [
        "ID",
        "Language",
        "Explanation",
        "Key_Concept",
        "Mnemonic",
        "Review_Status",
        "Reviewer_Comments",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for q_id, question in questions.items():
            explanations = question.get("explanations", {})
            key_concepts = question.get("key_concept", {})
            mnemonics = question.get("mnemonic", {})

            # Export for each language
            for lang in ["en", "de", "tr", "uk", "ar"]:
                row = {
                    "ID": question["id"],
                    "Language": lang.upper(),
                    "Explanation": explanations.get(lang, ""),
                    "Key_Concept": key_concepts.get(lang, ""),
                    "Mnemonic": mnemonics.get(lang, ""),
                    "Review_Status": "",
                    "Reviewer_Comments": "",
                }
                writer.writerow(row)


def export_image_questions(questions: dict[str, Any], output_path: str) -> None:
    """Export image questions with their descriptions."""
    fieldnames = [
        "ID",
        "Question",
        "Image_Count",
        "Image_Descriptions",
        "Review_Status",
        "Reviewer_Comments",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for q_id, question in questions.items():
            if question.get("is_image_question", False):
                images = question.get("images", [])
                descriptions = []
                for img in images:
                    # Escape newlines and format for CSV compatibility
                    path = img.get("path", "N/A")
                    desc = (
                        img.get("description", "N/A")
                        .replace("\n", " ")
                        .replace("\r", " ")
                    )
                    context = (
                        img.get("context", "N/A").replace("\n", " ").replace("\r", " ")
                    )
                    formatted_desc = (
                        f"Path: {path} | Description: {desc} | Context: {context}"
                    )
                    descriptions.append(formatted_desc)

                # Join with semicolon separator for better CSV compatibility
                image_descriptions = " ;; ".join(descriptions)

                row = {
                    "ID": question["id"],
                    "Question": question["question"],
                    "Image_Count": len(images),
                    "Image_Descriptions": image_descriptions,
                    "Review_Status": "",
                    "Reviewer_Comments": "",
                }
                writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Export dataset for review")
    parser.add_argument(
        "--input",
        default="data/final_dataset.json",
        help="Input JSON file path (default: data/final_dataset.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/review_for_upload",
        help="Output directory for CSV files (default: data/review_for_upload)",
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load dataset
    print(f"Loading dataset from {args.input}...")
    dataset = load_dataset(args.input)
    questions = dataset["questions"]

    print(f"Found {len(questions)} questions")

    # Export different aspects
    print("Exporting main content...")
    export_main_content(questions, output_dir / "main_content.csv")

    print("Exporting wrong answer explanations...")
    export_wrong_answers(questions, output_dir / "wrong_answers.csv")

    print("Exporting multilingual content...")
    export_multilingual_content(questions, output_dir / "multilingual_content.csv")

    print("Exporting image questions...")
    export_image_questions(questions, output_dir / "image_questions.csv")

    print(f"\nExport complete! Files saved to {output_dir}/")
    print("\nGenerated files:")
    print("- main_content.csv: Questions, answers, and primary explanations")
    print("- wrong_answers.csv: Explanations for why incorrect options are wrong")
    print("- multilingual_content.csv: All content in all languages")
    print("- image_questions.csv: Questions with images and descriptions")

    print("\nNext steps:")
    print("1. Upload CSV files to Google Sheets")
    print("2. Share with reviewers")
    print("3. Use the review process documentation for guidance")


if __name__ == "__main__":
    main()
