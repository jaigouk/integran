#!/usr/bin/env python3
"""
Fix Image Question Answers

This script analyzes extracted images using AI vision to verify and fix incorrect answers
for image questions in the German Integration Exam dataset.
"""

import base64
import json
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types

from src.core.settings import get_settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ImageAnswerValidator:
    """Analyze images with AI to validate and fix incorrect answers."""

    def __init__(self):
        """Initialize with Gemini client for image analysis."""
        settings = get_settings()

        # Use Vertex AI client with service account credentials
        self.client = genai.Client(
            vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region
        )
        self.model_id = settings.gemini_model

    def load_image_as_base64(self, image_path: Path) -> str:
        """Load image file as base64 string."""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            raise

    def analyze_single_image_question(
        self, question_data: dict, images_dir: Path
    ) -> dict | None:
        """Analyze a question with 1 image that contains multiple options."""
        question_id = question_data.get("id")
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        current_answer = question_data.get("correct", "")
        current_letter = question_data.get("correct_answer_letter", "")

        # Find the image file
        image_path = images_dir / f"q{question_id}_1.png"
        if not image_path.exists():
            logger.warning(f"Image not found for question {question_id}: {image_path}")
            return None

        logger.info(f"Analyzing single image for question {question_id}")

        try:
            # Load image
            image_base64 = self.load_image_as_base64(image_path)

            # Create analysis prompt
            prompt = f"""Analyze this image for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Current Answer: {current_answer} (Letter: {current_letter})

TASK: Look carefully at the image and determine which option (A, B, C, or D) is correct based on what you see. 

The image may show:
- Multiple marked/highlighted areas corresponding to different options
- A single correct example among incorrect ones
- Visual elements that match one of the text options

Respond in JSON format:
{{
    "analysis": "Detailed description of what you see in the image",
    "correct_option_letter": "A/B/C/D",
    "correct_option_text": "Full text of the correct option",
    "confidence": "high/medium/low",
    "reasoning": "Why this option is correct based on the image",
    "current_answer_validation": "correct/incorrect"
}}"""

            # Create image part
            image_part = types.Part.from_bytes(
                data=base64.b64decode(image_base64), mime_type="image/png"
            )

            # Create text part
            text_part = types.Part.from_text(text=prompt)

            # Create content
            contents = [types.Content(role="user", parts=[text_part, image_part])]

            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=2048,
            )

            # Make request
            response = self.client.models.generate_content(
                model=self.model_id, contents=contents, config=config
            )

            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            analysis_result = json.loads(response_text)

            logger.info(
                f"Q{question_id} Analysis: {analysis_result.get('current_answer_validation', 'unknown')}"
            )
            return analysis_result

        except Exception as e:
            logger.error(f"Failed to analyze question {question_id}: {e}")
            return None

    def analyze_multiple_image_question(
        self, question_data: dict, images_dir: Path
    ) -> dict | None:
        """Analyze a question with 4 separate images for each option."""
        question_id = question_data.get("id")
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        current_answer = question_data.get("correct", "")
        current_letter = question_data.get("correct_answer_letter", "")

        # Find all image files for this question
        image_paths = []
        for i in range(1, 5):
            image_path = images_dir / f"q{question_id}_{i}.png"
            if image_path.exists():
                image_paths.append(image_path)

        if len(image_paths) != 4:
            logger.warning(
                f"Expected 4 images for question {question_id}, found {len(image_paths)}"
            )
            return None

        logger.info(f"Analyzing 4 images for question {question_id}")

        try:
            # Load all images
            image_parts = []
            for i, image_path in enumerate(image_paths):
                image_base64 = self.load_image_as_base64(image_path)
                image_part = types.Part.from_bytes(
                    data=base64.b64decode(image_base64), mime_type="image/png"
                )
                image_parts.append(image_part)

            # Create analysis prompt
            prompt = f"""Analyze these 4 images for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]} (Image 1)
B) {options[1]} (Image 2)
C) {options[2]} (Image 3)  
D) {options[3]} (Image 4)

Current Answer: {current_answer} (Letter: {current_letter})

TASK: Look at each image and determine which one correctly answers the question. The images are provided in order A, B, C, D.

Image 1 = Option A: {options[0]}
Image 2 = Option B: {options[1]}
Image 3 = Option C: {options[2]}
Image 4 = Option D: {options[3]}

Respond in JSON format:
{{
    "analysis": "Description of what you see in each image",
    "image_descriptions": [
        "Description of Image 1 (Option A)",
        "Description of Image 2 (Option B)",
        "Description of Image 3 (Option C)",
        "Description of Image 4 (Option D)"
    ],
    "correct_option_letter": "A/B/C/D",
    "correct_option_text": "Full text of the correct option",
    "confidence": "high/medium/low",
    "reasoning": "Why this image/option is correct",
    "current_answer_validation": "correct/incorrect"
}}"""

            # Create text part
            text_part = types.Part.from_text(text=prompt)

            # Create content with all images
            all_parts = [text_part] + image_parts
            contents = [types.Content(role="user", parts=all_parts)]

            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=4096,
            )

            # Make request
            response = self.client.models.generate_content(
                model=self.model_id, contents=contents, config=config
            )

            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            analysis_result = json.loads(response_text)

            logger.info(
                f"Q{question_id} Analysis: {analysis_result.get('current_answer_validation', 'unknown')}"
            )
            return analysis_result

        except Exception as e:
            logger.error(f"Failed to analyze question {question_id}: {e}")
            return None


class ImageAnswerFixer:
    """Fix incorrect answers based on AI image analysis."""

    def __init__(self, dataset_path: Path, images_dir: Path):
        self.dataset_path = dataset_path
        self.images_dir = images_dir
        self.validator = ImageAnswerValidator()
        self.dataset = self._load_dataset()

    def _load_dataset(self) -> dict:
        """Load the step1 dataset."""
        try:
            with open(self.dataset_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(
                f"Loaded dataset with {len(data.get('questions', {}))} questions"
            )
            return data
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise

    def get_image_questions(self) -> list[tuple[int, dict, str]]:
        """Get list of image questions with their type (single/multiple)."""
        image_questions = []

        for q_id_str, question in self.dataset.get("questions", {}).items():
            if not question.get("is_image_question", False):
                continue

            q_id = int(q_id_str)

            # Determine image type based on actual files
            single_image = (self.images_dir / f"q{q_id}_1.png").exists()
            multiple_images = all(
                (self.images_dir / f"q{q_id}_{i}.png").exists() for i in range(1, 5)
            )

            if multiple_images:
                image_type = "multiple"
            elif single_image:
                image_type = "single"
            else:
                logger.warning(f"No images found for question {q_id}")
                continue

            image_questions.append((q_id, question, image_type))

        logger.info(f"Found {len(image_questions)} image questions to analyze")
        return image_questions

    def fix_question_answer(self, question_data: dict, analysis: dict) -> dict:
        """Fix a question's answer based on AI analysis."""
        if analysis.get("current_answer_validation") == "correct":
            # No changes needed
            return question_data

        # Create corrected question
        corrected_question = question_data.copy()

        # Update the correct answer
        correct_letter = analysis.get("correct_option_letter", "")
        correct_text = analysis.get("correct_option_text", "")

        if correct_letter and correct_text:
            corrected_question["correct"] = correct_text
            corrected_question["correct_answer_letter"] = correct_letter

            # Add analysis metadata
            corrected_question["answer_correction"] = {
                "original_answer": question_data.get("correct", ""),
                "original_letter": question_data.get("correct_answer_letter", ""),
                "corrected_answer": correct_text,
                "corrected_letter": correct_letter,
                "ai_analysis": analysis.get("analysis", ""),
                "reasoning": analysis.get("reasoning", ""),
                "confidence": analysis.get("confidence", "unknown"),
            }

            logger.info(
                f"Fixed Q{question_data.get('id')}: {question_data.get('correct_answer_letter')} → {correct_letter}"
            )

        return corrected_question

    def analyze_and_fix_all(self) -> dict:
        """Analyze all image questions and fix incorrect answers."""
        image_questions = self.get_image_questions()

        corrected_dataset = {
            "questions": self.dataset.get("questions", {}).copy(),
            "metadata": self.dataset.get("metadata", {}).copy(),
        }

        # Update metadata
        corrected_dataset["metadata"]["step"] = "step2_answers_fixed"
        corrected_dataset["metadata"]["description"] = (
            "Dataset with corrected answers for image questions"
        )

        corrections_made = 0
        total_analyzed = 0

        for q_id, question_data, image_type in image_questions:
            logger.info(f"Analyzing question {q_id} ({image_type} image)")

            try:
                # Analyze based on image type
                if image_type == "single":
                    analysis = self.validator.analyze_single_image_question(
                        question_data, self.images_dir
                    )
                else:  # multiple
                    analysis = self.validator.analyze_multiple_image_question(
                        question_data, self.images_dir
                    )

                if analysis:
                    total_analyzed += 1

                    # Fix if needed
                    if analysis.get("current_answer_validation") == "incorrect":
                        corrected_question = self.fix_question_answer(
                            question_data, analysis
                        )
                        corrected_dataset["questions"][str(q_id)] = corrected_question
                        corrections_made += 1
                    else:
                        logger.info(f"Q{q_id}: Answer already correct")

                # Add small delay to avoid rate limits
                import time

                time.sleep(1)

            except Exception as e:
                logger.error(f"Failed to process question {q_id}: {e}")
                continue

        # Update metadata with results
        corrected_dataset["metadata"]["analysis_results"] = {
            "total_image_questions": len(image_questions),
            "questions_analyzed": total_analyzed,
            "corrections_made": corrections_made,
            "accuracy_rate": round(
                (total_analyzed - corrections_made) / total_analyzed * 100, 1
            )
            if total_analyzed > 0
            else 0,
        }

        logger.info(
            f"Analysis complete: {corrections_made}/{total_analyzed} corrections made"
        )
        return corrected_dataset


def main():
    """Main function to fix image question answers."""
    # File paths
    input_dataset_path = Path("data/step1_images_extracted.json")
    output_dataset_path = Path("data/step2_answers_fixed.json")
    images_dir = Path("data/images")

    # Validate inputs
    if not input_dataset_path.exists():
        logger.error(f"Input dataset not found: {input_dataset_path}")
        return 1

    if not images_dir.exists():
        logger.error(f"Images directory not found: {images_dir}")
        return 1

    # Initialize fixer
    fixer = ImageAnswerFixer(input_dataset_path, images_dir)

    # Analyze and fix answers
    logger.info("Starting AI analysis of image questions...")
    corrected_dataset = fixer.analyze_and_fix_all()

    # Save results
    logger.info(f"Saving corrected dataset to {output_dataset_path}")
    with open(output_dataset_path, "w", encoding="utf-8") as f:
        json.dump(corrected_dataset, f, ensure_ascii=False, indent=2)

    # Print summary
    results = corrected_dataset["metadata"]["analysis_results"]
    logger.info("=" * 50)
    logger.info("STEP 2 ANSWER CORRECTION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total image questions: {results['total_image_questions']}")
    logger.info(f"Questions analyzed: {results['questions_analyzed']}")
    logger.info(f"Corrections made: {results['corrections_made']}")
    logger.info(f"Original accuracy rate: {results['accuracy_rate']}%")
    logger.info(f"Output file: {output_dataset_path}")
    logger.info("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
