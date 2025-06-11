#!/usr/bin/env python3
"""
Generate Multilingual Explanations - Single Question Processing

Processes one question at a time with immediate JSON saving, like step1 and step2.
Handles all three image question types with proper AI analysis.
"""

import base64
import json
import logging
import sys
import time
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


class SingleQuestionExplanationGenerator:
    """Generate comprehensive multilingual explanations for one question at a time."""

    def __init__(self):
        """Initialize with Gemini client for content generation."""
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

    def determine_question_type(self, question_data: dict, images_dir: Path) -> str:
        """Determine the type of question based on images."""
        if not question_data.get("is_image_question", False):
            return "text_only"

        question_id = question_data.get("id")

        # Check for multiple images (4 images = one per option)
        multiple_images = all(
            (images_dir / f"q{question_id}_{i}.png").exists() for i in range(1, 5)
        )

        if multiple_images:
            return "multiple_images"

        # Check for single image
        single_image = (images_dir / f"q{question_id}_1.png").exists()

        if single_image:
            return "single_image"

        logger.warning(
            f"No images found for question {question_id}, treating as text-only"
        )
        return "text_only"

    def generate_text_only_explanation(self, question_data: dict) -> dict | None:
        """Generate explanation for text-only questions (no images)."""
        question_id = question_data.get("id")
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        correct_answer = question_data.get("correct", "")
        correct_letter = question_data.get("correct_answer_letter", "")
        category = question_data.get("category", "")

        logger.info(f"Generating explanations for text question {question_id}")

        try:
            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

Generate detailed explanations in 5 languages (English, German, Turkish, Ukrainian, Arabic) that help learners understand:
1. WHY the correct answer is right (with cultural/legal context and background)
2. WHY each incorrect option is wrong (specific detailed reasons)
3. KEY CONCEPT that this question tests (core principle being examined)
4. MNEMONIC device to remember the answer (memory aid technique)

Requirements:
- Explanations should be comprehensive and educational, not just stating facts
- Include cultural and legal context for German integration
- Reference specific laws, institutions, or historical context when relevant
- Make explanations accessible to language learners
- Ensure mnemonics are practical and memorable

Respond in JSON format:
{{
    "explanations": {{
        "en": "Comprehensive explanation of why {correct_answer} is correct, including background context, cultural significance, and legal framework...",
        "de": "Umfassende deutsche Erklärung mit kulturellem und rechtlichem Hintergrund...",
        "tr": "Türkçe kapsamlı açıklama, kültürel ve yasal bağlam dahil...",
        "uk": "Детальне пояснення українською з культурним та правовим контекстом...",
        "ar": "شرح شامل باللغة العربية مع السياق الثقافي والقانوني..."
    }},
    "why_others_wrong": {{
        "en": {{
            "A": "Detailed explanation of why option A is incorrect, with specific reasoning...",
            "B": "Detailed explanation of why option B is incorrect, with specific reasoning...",
            "C": "Detailed explanation of why option C is incorrect, with specific reasoning...",
            "D": "Detailed explanation of why option D is incorrect, with specific reasoning..."
        }},
        "de": {{
            "A": "Detaillierte Erklärung warum Option A falsch ist...",
            "B": "Detaillierte Erklärung warum Option B falsch ist...",
            "C": "Detaillierte Erklärung warum Option C falsch ist...",
            "D": "Detaillierte Erklärung warum Option D falsch ist..."
        }},
        "tr": {{
            "A": "A seçeneği neden yanlış, detaylı açıklama...",
            "B": "B seçeneği neden yanlış, detaylı açıklama...",
            "C": "C seçeneği neden yanlış, detaylı açıklama...",
            "D": "D seçeneği neden yanlış, detaylı açıklama..."
        }},
        "uk": {{
            "A": "Детальне пояснення чому варіант A неправильний...",
            "B": "Детальне пояснення чому варіант B неправильний...",
            "C": "Детальне пояснення чому варіант C неправильний...",
            "D": "Детальне пояснення чому варіант D неправильний..."
        }},
        "ar": {{
            "A": "توضيح مفصل لماذا الخيار A خاطئ...",
            "B": "توضيح مفصل لماذا الخيار B خاطئ...",
            "C": "توضيح مفصل لماذا الخيار C خاطئ...",
            "D": "توضيح مفصل لماذا الخيار D خاطئ..."
        }}
    }},
    "key_concept": {{
        "en": "Core concept/principle this question tests (1-2 sentences explaining the fundamental idea)...",
        "de": "Kernkonzept das diese Frage testet...",
        "tr": "Bu sorunun test ettiği temel kavram...",
        "uk": "Основна концепція цього питання...",
        "ar": "المفهوم الأساسي لهذا السؤال..."
    }},
    "mnemonic": {{
        "en": "Practical memory device to remember this answer (creative but functional)...",
        "de": "Praktische Gedächtnisstütze für diese Antwort...",
        "tr": "Bu cevabı hatırlamak için pratik hafıza yardımcısı...",
        "uk": "Практичний мнемонічний прийом для запам'ятовування...",
        "ar": "وسيلة عملية للتذكر لهذه الإجابة..."
    }}
}}

IMPORTANT: Remove the correct answer letter from why_others_wrong explanations (don't explain why the correct answer is wrong)."""

            # Create text content
            contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]

            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192,
            )

            # Make request
            response = self.client.models.generate_content(
                model=self.model_id, contents=contents, config=config
            )

            # Parse response - handle Gemini's markdown JSON wrapping
            response_text = response.text.strip()

            # Clean markdown formatting that Gemini sometimes adds
            response_text = response_text.replace("```json", "").replace("```", "")

            # Remove any extra text before JSON (Gemini 2.5 Pro issue)
            # Find the first occurrence of '{' which should be the start of JSON
            json_start = response_text.find("{")
            if json_start > 0:
                response_text = response_text[json_start:]

            # Find the last occurrence of '}' which should be the end of JSON
            json_end = response_text.rfind("}")
            if json_end >= 0:
                response_text = response_text[: json_end + 1]

            response_text = response_text.strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response text preview: {response_text[:500]}...")
                raise

            # Remove the correct answer from why_others_wrong
            if "why_others_wrong" in result and isinstance(
                result["why_others_wrong"], dict
            ):
                for lang in result["why_others_wrong"]:
                    if (
                        isinstance(result["why_others_wrong"][lang], dict)
                        and correct_letter in result["why_others_wrong"][lang]
                    ):
                        del result["why_others_wrong"][lang][correct_letter]

            logger.info(f"Q{question_id}: Generated text-only explanations")
            return result

        except Exception as e:
            logger.error(
                f"Failed to generate explanation for question {question_id}: {e}"
            )
            return None

    def generate_single_image_explanation(
        self, question_data: dict, images_dir: Path
    ) -> dict | None:
        """Generate explanation for questions with 1 image (may contain marked options)."""
        question_id = question_data.get("id")
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        correct_answer = question_data.get("correct", "")
        correct_letter = question_data.get("correct_answer_letter", "")
        category = question_data.get("category", "")

        # Find the image file
        image_path = images_dir / f"q{question_id}_1.png"
        if not image_path.exists():
            logger.warning(f"Image not found for question {question_id}: {image_path}")
            return self.generate_text_only_explanation(question_data)

        logger.info(f"Generating explanations for single-image question {question_id}")

        try:
            # Load image
            image_base64 = self.load_image_as_base64(image_path)

            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

IMPORTANT: Analyze the provided image carefully. The image may:
- Show marked/highlighted options corresponding to A, B, C, D (like ballot papers with marked choices)
- Contain visual elements that directly relate to the correct answer
- Provide context that explains why the correct answer is right
- Show a single contextual scene that supports the question

Generate detailed explanations in 5 languages that:
1. Reference the visual content when relevant
2. Explain what can be seen in the image and how it relates to the answer
3. Provide cultural/legal context for German integration
4. Include specific visual details that support the correct choice

Use the same JSON structure as text-only questions, but include visual references in explanations:
{{
    "explanations": {{
        "en": "Based on the image, the correct answer is {correct_answer} because [visual analysis]... [cultural context]...",
        "de": "Basierend auf dem Bild ist {correct_answer} richtig, weil [visuelle Analyse]... [kultureller Kontext]...",
        "tr": "Görsel temelinde {correct_answer} doğrudur çünkü [görsel analiz]... [kültürel bağlam]...",
        "uk": "На основі зображення {correct_answer} правильна, тому що [візуальний аналіз]... [культурний контекст]...",
        "ar": "بناءً على الصورة، {correct_answer} صحيح لأن [التحليل البصري]... [السياق الثقافي]..."
    }},
    "why_others_wrong": {{
        // Same multilingual structure, referencing image when relevant
    }},
    "key_concept": {{
        // Same multilingual structure
    }},
    "mnemonic": {{
        // Same multilingual structure
    }},
    "image_description": "Detailed description of what the image shows and how it relates to the question and correct answer"
}}

IMPORTANT: Remove the correct answer letter from why_others_wrong explanations."""

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
                max_output_tokens=8192,
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

            # Remove any extra text before/after JSON
            json_start = response_text.find("{")
            if json_start > 0:
                response_text = response_text[json_start:]
            json_end = response_text.rfind("}")
            if json_end >= 0:
                response_text = response_text[: json_end + 1]

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response text preview: {response_text[:500]}...")
                raise

            # Remove the correct answer from why_others_wrong
            if "why_others_wrong" in result and isinstance(
                result["why_others_wrong"], dict
            ):
                for lang in result["why_others_wrong"]:
                    if (
                        isinstance(result["why_others_wrong"][lang], dict)
                        and correct_letter in result["why_others_wrong"][lang]
                    ):
                        del result["why_others_wrong"][lang][correct_letter]

            logger.info(f"Q{question_id}: Generated single-image explanations")
            return result

        except Exception as e:
            logger.error(
                f"Failed to generate explanation for question {question_id}: {e}"
            )
            return None

    def generate_multiple_image_explanation(
        self, question_data: dict, images_dir: Path
    ) -> dict | None:
        """Generate explanation for questions with 4 images (one per option)."""
        question_id = question_data.get("id")
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        correct_answer = question_data.get("correct", "")
        correct_letter = question_data.get("correct_answer_letter", "")
        category = question_data.get("category", "")

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
            return self.generate_text_only_explanation(question_data)

        logger.info(
            f"Generating explanations for multiple-image question {question_id}"
        )

        try:
            # Load all images
            image_parts = []
            for i, image_path in enumerate(image_paths):
                image_base64 = self.load_image_as_base64(image_path)
                image_part = types.Part.from_bytes(
                    data=base64.b64decode(image_base64), mime_type="image/png"
                )
                image_parts.append(image_part)

            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options with corresponding images:
A) {options[0]} (Image 1)
B) {options[1]} (Image 2)
C) {options[2]} (Image 3)
D) {options[3]} (Image 4)

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

IMPORTANT: Analyze all 4 provided images carefully. Each image corresponds to an option:
- Image 1 = Option A: {options[0]}
- Image 2 = Option B: {options[1]}
- Image 3 = Option C: {options[2]}
- Image 4 = Option D: {options[3]}

Generate detailed explanations that:
1. Describe what each image shows specifically
2. Explain why the correct image/option is right based on visual content
3. Explain why other images are incorrect based on what they show
4. Provide cultural/legal context for German integration
5. Reference visual details that distinguish correct from incorrect options

Respond in JSON format:
{{
    "explanations": {{
        "en": "Image {correct_letter} correctly shows {correct_answer} because [detailed visual analysis of correct image]... [cultural/legal context]...",
        "de": "Bild {correct_letter} zeigt korrekt {correct_answer} weil [detaillierte visuelle Analyse]... [kultureller/rechtlicher Kontext]...",
        "tr": "Resim {correct_letter} doğru bir şekilde {correct_answer} gösteriyor çünkü [detaylı görsel analiz]... [kültürel/yasal bağlam]...",
        "uk": "Зображення {correct_letter} правильно показує {correct_answer} тому що [детальний візуальний аналіз]... [культурний/правовий контекст]...",
        "ar": "الصورة {correct_letter} تُظهر بشكل صحيح {correct_answer} لأن [التحليل البصري المفصل]... [السياق الثقافي/القانوني]..."
    }},
    "why_others_wrong": {{
        "en": {{
            "A": "Image 1 shows [specific visual description] which is incorrect because [detailed reasoning]...",
            "B": "Image 2 shows [specific visual description] which is incorrect because [detailed reasoning]...",
            "C": "Image 3 shows [specific visual description] which is incorrect because [detailed reasoning]...",
            "D": "Image 4 shows [specific visual description] which is incorrect because [detailed reasoning]..."
        }},
        // Same structure for other languages
    }},
    "key_concept": {{
        // Same multilingual structure
    }},
    "mnemonic": {{
        // Same multilingual structure  
    }},
    "image_descriptions": [
        "Detailed description of what Image 1 (Option A) shows",
        "Detailed description of what Image 2 (Option B) shows", 
        "Detailed description of what Image 3 (Option C) shows",
        "Detailed description of what Image 4 (Option D) shows"
    ]
}}

IMPORTANT: Remove the correct answer letter from why_others_wrong explanations."""

            # Create text part
            text_part = types.Part.from_text(text=prompt)

            # Create content with all images
            all_parts = [text_part] + image_parts
            contents = [types.Content(role="user", parts=all_parts)]

            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192,
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

            result = json.loads(response_text)

            # Remove the correct answer from why_others_wrong
            if "why_others_wrong" in result:
                for lang in result["why_others_wrong"]:
                    if correct_letter in result["why_others_wrong"][lang]:
                        del result["why_others_wrong"][lang][correct_letter]

            logger.info(f"Q{question_id}: Generated multiple-image explanations")
            return result

        except Exception as e:
            logger.error(
                f"Failed to generate explanation for question {question_id}: {e}"
            )
            return None


def process_single_question(question_id: int):
    """Process a single question and save results immediately."""

    # File paths
    input_dataset_path = Path("data/step2_answers_fixed.json")
    output_dataset_path = Path("data/step3_explanations_progress.json")
    images_dir = Path("data/images")

    # Validate inputs
    if not input_dataset_path.exists():
        logger.error(f"Input dataset not found: {input_dataset_path}")
        return False

    # Load input dataset
    with open(input_dataset_path, encoding="utf-8") as f:
        input_dataset = json.load(f)

    # Load or create output dataset
    if output_dataset_path.exists():
        with open(output_dataset_path, encoding="utf-8") as f:
            output_dataset = json.load(f)
    else:
        output_dataset = {
            "questions": {},
            "metadata": {
                "step": "step3_multilingual_explanations_progress",
                "description": "Progressive multilingual explanation generation",
                "languages": ["en", "de", "tr", "uk", "ar"],
                "processed_questions": [],
                "total_questions": len(input_dataset.get("questions", {})),
                "processing_started": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    # Check if question exists and hasn't been processed
    question_id_str = str(question_id)
    if question_id_str not in input_dataset.get("questions", {}):
        logger.error(f"Question {question_id} not found in dataset")
        return False

    if question_id_str in output_dataset.get("questions", {}):
        logger.info(f"Question {question_id} already processed, skipping")
        return True

    # Get question data
    question_data = input_dataset["questions"][question_id_str]

    # Initialize generator
    generator = SingleQuestionExplanationGenerator()

    # Determine question type and generate explanations
    question_type = generator.determine_question_type(question_data, images_dir)
    logger.info(f"Processing question {question_id} (type: {question_type})")

    try:
        # Generate explanations based on question type
        if question_type == "multiple_images":
            explanations = generator.generate_multiple_image_explanation(
                question_data, images_dir
            )
        elif question_type == "single_image":
            explanations = generator.generate_single_image_explanation(
                question_data, images_dir
            )
        else:  # text_only
            explanations = generator.generate_text_only_explanation(question_data)

        if not explanations:
            logger.error(f"Failed to generate explanations for question {question_id}")
            return False

        # Create enhanced question with full target format
        enhanced_question = question_data.copy()

        # Add core explanation fields
        enhanced_question.update(
            {
                "question_id": question_id,
                "correct_answer": enhanced_question.get("correct_answer_letter", ""),
                "explanations": explanations.get("explanations", {}),
                "why_others_wrong": explanations.get("why_others_wrong", {}),
                "key_concept": explanations.get("key_concept", {}),
                "mnemonic": explanations.get("mnemonic", {}),
            }
        )

        # Add image-specific fields
        if "image_description" in explanations:
            enhanced_question["image_description"] = explanations["image_description"]
        if "image_descriptions" in explanations:
            enhanced_question["image_descriptions"] = explanations["image_descriptions"]

        # Add image metadata for image questions
        if question_data.get("is_image_question", False):
            enhanced_question["images"] = question_data.get("images", [])
        else:
            enhanced_question["image_context"] = None
            enhanced_question["rag_sources"] = []

        # Save to output dataset
        output_dataset["questions"][question_id_str] = enhanced_question
        output_dataset["metadata"]["processed_questions"].append(question_id)
        output_dataset["metadata"]["last_processed"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        output_dataset["metadata"]["progress"] = (
            f"{len(output_dataset['metadata']['processed_questions'])}/{output_dataset['metadata']['total_questions']}"
        )

        # Save immediately
        with open(output_dataset_path, "w", encoding="utf-8") as f:
            json.dump(output_dataset, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Question {question_id} processed and saved successfully")
        logger.info(f"Progress: {output_dataset['metadata']['progress']}")

        return True

    except Exception as e:
        logger.error(f"Error processing question {question_id}: {e}")
        return False


def main():
    """Process a single question (default: question 1)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate multilingual explanations for a single question"
    )
    parser.add_argument(
        "--question-id", type=int, default=1, help="Question ID to process (default: 1)"
    )
    args = parser.parse_args()

    logger.info(f"Starting explanation generation for question {args.question_id}")
    success = process_single_question(args.question_id)

    if success:
        logger.info(f"✅ Successfully processed question {args.question_id}")
        return 0
    else:
        logger.error(f"❌ Failed to process question {args.question_id}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
