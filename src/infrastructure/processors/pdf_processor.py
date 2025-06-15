"""Direct PDF processor - Upload PDF to Gemini File API and process with structured output."""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.infrastructure.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageData(BaseModel):
    """Image data matching models.py ImageInfo."""

    path: str = Field(description="Image file path")
    description: str = Field(description="AI-generated description of image")
    context: str = Field(description="Context about what the image represents")


class QuestionSchema(BaseModel):
    """Schema matching models.py QuestionData format."""

    id: int = Field(description="Sequential question number (1-460)")
    question: str = Field(description="Full German question text")
    options: list[str] = Field(description="Four answer options as list")
    correct: str = Field(description="Full text of the correct answer")
    category: str = Field(description="Question category")
    difficulty: str = Field(description="easy, medium, or hard")
    question_type: str = Field(description="general or state_specific")
    state: str | None = Field(
        description="State name for state-specific questions", default=None
    )
    page_number: int = Field(description="PDF page number where question appears")
    is_image_question: bool = Field(description="Whether question includes images")
    images: list[ImageData] = Field(
        description="Image data for image questions", default_factory=list
    )
    # Legacy compatibility
    correct_answer_letter: str | None = Field(
        description="Answer letter A/B/C/D", default=None
    )


class DatasetSchema(BaseModel):
    """Schema for the complete dataset."""

    questions: dict[str, QuestionSchema] = Field(description="Questions indexed by ID")
    metadata: dict[str, Any] = Field(description="Extraction metadata")


class DirectPDFProcessor:
    """Upload PDF to Gemini File API and process with structured output."""

    def __init__(self) -> None:
        """Initialize with Gemini client using service account credentials."""
        settings = get_settings()

        # Use Vertex AI client with service account credentials
        self.client = genai.Client(
            vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region
        )
        # Use a stable model that's available in all regions
        self.model_id = "gemini-1.5-pro"

    def load_pdf_as_base64(self, pdf_path: Path) -> str:
        """Load PDF as base64 for direct embedding."""

        logger.info(f"Loading PDF for direct processing: {pdf_path}")

        try:
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")
            logger.info(f"PDF loaded successfully: {len(pdf_base64)} characters")

            return pdf_base64

        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            raise

    def process_pdf_with_structured_output(
        self, pdf_base64: str, batch_start: int = 1, batch_end: int = 460
    ) -> list[dict[str, Any]]:
        """Process PDF with structured JSON output and proper error handling."""

        logger.info(
            f"Processing questions {batch_start}-{batch_end} with structured output"
        )

        # Create a comprehensive prompt with proper PDF structure understanding
        prompt = f"""Extract question {batch_start} from the German Integration Exam PDF (Leben in Deutschland Test).

PDF STRUCTURE UNDERSTANDING:
- Teil I (Pages 1-111): General questions 1-300 (Aufgabe 1, Aufgabe 2, ..., Aufgabe 300)
- Teil II (Pages 112-191): State-specific questions, each state has 10 questions numbered 1-10
  * Each state section starts fresh with "Aufgabe 1" through "Aufgabe 10"
  * State sections: Baden-Württemberg, Bayern, Berlin, Brandenburg, Bremen, Hamburg, Hessen, Mecklenburg-Vorpommern, Niedersachsen, Nordrhein-Westfalen, Rheinland-Pfalz, Saarland, Sachsen, Sachsen-Anhalt, Schleswig-Holstein, Thüringen

TASK: Find the correct "Aufgabe {batch_start if batch_start <= 300 else (batch_start - 300) % 10 if (batch_start - 300) % 10 != 0 else 10}" in the appropriate section.

IMAGE QUESTIONS (CRITICAL):
Questions WITH images:
- Teil I: 21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235
- Teil II: Questions 1 and 8 for each state (total 32 image questions)

For question {batch_start}:
{"- This is an IMAGE QUESTION! Set is_image_question=true" if batch_start in [21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235] or (batch_start > 300 and ((batch_start - 300 - 1) % 10 + 1) in [1, 8]) else "- This is a TEXT-ONLY question, set is_image_question=false"}

EXTRACTION REQUIREMENTS:
1. GERMAN CHARACTER HANDLING: Preserve ä, ö, ü, ß correctly (NO escape sequences like \\n)

2. QUESTION LOCATION:
   {"- Look for 'Aufgabe " + str(batch_start) + "' in Teil I (pages 1-111)" if batch_start <= 300 else f"- Look for 'Aufgabe {(batch_start - 300 - 1) % 10 + 1}' in Teil II state section (pages 112-191)"}

3. ANSWER OPTIONS: Extract A), B), C), D) with proper German characters

4. CORRECT ANSWER: Find answer key (usually at document end) and match to option text

5. IMAGE HANDLING:
   {"- Must include 4 images in images array with descriptions" if batch_start in [21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235] or (batch_start > 300 and ((batch_start - 300 - 1) % 10 + 1) in [1, 8]) else "- No images needed (empty array)"}

6. STATE DETECTION:
   {"- question_type='general', state=null" if batch_start <= 300 else "- question_type='state_specific', extract state name from section header"}

Return JSON with proper German characters:
{{
  "questions": {{
    "{batch_start}": {{
      "id": {batch_start},
      "question": "German text with ä, ö, ü, ß preserved",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct": "Full correct option text",
      "category": "Category",
      "difficulty": "easy/medium/hard",
      "question_type": "{"general" if batch_start <= 300 else "state_specific"}",
      "state": {"null" if batch_start <= 300 else '"State name"'},
      "page_number": actual_page,
      "is_image_question": {"true" if batch_start in [21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235] or (batch_start > 300 and ((batch_start - 300 - 1) % 10 + 1) in [1, 8]) else "false"},
      "images": [{"4 image objects" if batch_start in [21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235] or (batch_start > 300 and ((batch_start - 300 - 1) % 10 + 1) in [1, 8]) else "empty array"}],
      "correct_answer_letter": "A/B/C/D"
    }}
  }},
  "metadata": {{
    "total_questions": 1,
    "extraction_method": "direct_pdf_single",
    "has_images_count": {"1" if batch_start in [21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235] or (batch_start > 300 and ((batch_start - 300 - 1) % 10 + 1) in [1, 8]) else "0"},
    "state_questions_count": {"1" if batch_start > 300 else "0"}
  }}
}}"""

        try:
            # Create PDF part from base64 data
            pdf_part = types.Part.from_bytes(
                data=base64.b64decode(pdf_base64), mime_type="application/pdf"
            )

            # Create text part with prompt
            text_part = types.Part.from_text(text=prompt)

            # Create content
            contents = [types.Content(role="user", parts=[text_part, pdf_part])]

            # Configure generation with structured output
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DatasetSchema.model_json_schema(),
                temperature=0.1,
                max_output_tokens=8192,
            )

            logger.info("Generating structured output from PDF...")

            # Make the request with retry logic
            max_retries = 3
            retry_delay = 30

            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=contents,  # type: ignore[arg-type]
                        config=config,
                    )

                    # Parse and validate JSON response
                    if not response or not response.text:
                        raise ValueError("Empty response from API")
                    response_text = response.text.strip()

                    # Clean up response if needed
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()

                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.error(
                            f"Response text (first 500 chars): {response_text[:500]}"
                        )
                        raise ValueError(f"Invalid JSON response: {e}") from e

                    # Validate response structure
                    if not isinstance(result, dict) or "questions" not in result:
                        raise ValueError("Response missing 'questions' field")

                    questions_dict = result.get("questions", {})
                    if not questions_dict:
                        logger.warning("No questions found in response")
                        return []

                    questions = list(questions_dict.values())

                    # Validate question structure
                    for q in questions:
                        if not isinstance(q, dict) or "id" not in q:
                            logger.error(f"Invalid question structure: {q}")
                            continue

                        # Ensure required fields exist
                        required_fields = [
                            "id",
                            "question",
                            "options",
                            "correct",
                            "category",
                        ]
                        missing_fields = [f for f in required_fields if f not in q]
                        if missing_fields:
                            logger.error(
                                f"Question {q.get('id')} missing fields: {missing_fields}"
                            )

                    logger.info(
                        f"Successfully extracted and validated {len(questions)} questions"
                    )

                    # Validate critical questions
                    self._validate_batch(questions, batch_start, batch_end)

                    return questions

                except Exception as e:
                    if "timeout" in str(e).lower() or "overloaded" in str(e).lower():
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"API timeout/overload, retrying in {retry_delay} seconds..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error("API still unavailable after all retries")
                            raise
                    else:
                        raise

        except Exception as e:
            logger.error(f"Failed to process batch {batch_start}-{batch_end}: {e}")
            raise

        # This should never be reached, but mypy needs it
        return []

    def load_checkpoint(
        self, checkpoint_path: Path
    ) -> tuple[list[dict[str, Any]], int]:
        """Load existing checkpoint and return questions and last processed ID."""
        if not checkpoint_path.exists():
            return [], 0

        try:
            with open(checkpoint_path, encoding="utf-8") as f:
                data = json.load(f)

            questions = list(data.get("questions", {}).values())
            last_processed = data.get("metadata", {}).get("last_processed", 0)

            logger.info(
                f"✓ Loaded checkpoint: {len(questions)} questions, last processed: {last_processed}"
            )
            return questions, last_processed

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return [], 0

    def process_full_pdf_in_batches(
        self,
        pdf_path: Path,
        checkpoint_path: Path,
        batch_size: int = 50,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Process the full PDF with transparent checkpoint progress."""

        # Load existing checkpoint
        all_questions, last_processed = self.load_checkpoint(checkpoint_path)
        start_from = last_processed + 1

        if start_from > 460:
            logger.info("✓ All questions already extracted!")
            return all_questions

        logger.info(f"Starting extraction from question {start_from}/460")

        # Load PDF as base64 once
        pdf_base64 = self.load_pdf_as_base64(pdf_path)

        # Process one question at a time starting from checkpoint
        for question_id in range(start_from, 461):
            progress_pct = (question_id / 460) * 100
            logger.info(f"[{progress_pct:.1f}%] Processing question {question_id}/460")

            try:
                # Process single question
                batch_questions = self.process_pdf_with_structured_output(
                    pdf_base64, question_id, question_id
                )
                if batch_questions:
                    all_questions.extend(batch_questions)
                    logger.info(f"✓ Successfully extracted question {question_id}")

                # Save checkpoint after every question for transparency
                self._save_checkpoint(
                    all_questions, start_from, question_id, checkpoint_path
                )

                # Progress summary every 10 questions
                if question_id % 10 == 0:
                    completed = question_id
                    remaining = 460 - question_id
                    logger.info(
                        f"📊 Progress: {completed}/460 completed, {remaining} remaining ({progress_pct:.1f}%)"
                    )

                # Throttle to avoid rate limits (2 seconds between questions)
                if question_id < 460:
                    time.sleep(2)

            except Exception as e:
                logger.error(f"❌ Question {question_id} failed: {e}")
                # Save progress even on failure
                self._save_checkpoint(
                    all_questions, start_from, question_id - 1, checkpoint_path
                )
                # Continue with next question instead of failing completely
                continue

        logger.info(f"🎉 Extraction completed! Total questions: {len(all_questions)}")
        return all_questions

    def _validate_batch(
        self, questions: list[dict[str, Any]], batch_start: int, batch_end: int
    ) -> None:
        """Validate that critical questions are correctly extracted."""

        # Check if Question 130 is in this batch
        if batch_start <= 130 and batch_end >= 130:
            q130 = next((q for q in questions if q.get("id") == 130), None)

            if q130:
                if not q130.get("is_image_question"):
                    logger.error("Question 130 not marked as image question!")
                else:
                    logger.info("✓ Question 130 correctly marked as image question")

                # Check if it has image data
                images = q130.get("images", [])
                if not images:
                    logger.warning("Question 130 has no image data")
                else:
                    logger.info(f"✓ Question 130 has {len(images)} images")
            else:
                logger.error("Question 130 not found in batch!")

        # Validate batch completeness
        expected_count = batch_end - batch_start + 1
        if len(questions) != expected_count:
            logger.warning(f"Expected {expected_count} questions, got {len(questions)}")

        # Check image questions in batch
        image_questions = [q for q in questions if q.get("has_images")]
        logger.info(
            f"Found {len(image_questions)} image questions in batch {batch_start}-{batch_end}"
        )

    def _save_checkpoint(
        self,
        questions: list[dict[str, Any]],
        batch_start: int,
        batch_end: int,
        checkpoint_path: Path,
    ) -> None:
        """Save incremental progress with detailed metadata."""
        # Convert list to dictionary format
        questions_dict = {}
        for question in questions:
            question_id = str(question.get("id", question.get("question_id", 0)))
            questions_dict[question_id] = question

        # Calculate detailed statistics
        image_questions = [
            q for q in questions if q.get("is_image_question") or q.get("has_images")
        ]
        state_questions = [
            q for q in questions if q.get("question_type") == "state_specific"
        ]

        # Save as checkpoint format
        checkpoint_data = {
            "questions": questions_dict,
            "metadata": {
                "total_questions": len(questions),
                "extraction_method": "direct_pdf_checkpoint",
                "has_images_count": len(image_questions),
                "state_questions_count": len(state_questions),
                "last_processed": batch_end,
                "progress_percentage": round((batch_end / 460) * 100, 1),
                "status": "completed" if batch_end >= 460 else "in_progress",
                "range_start": batch_start,
                "range_end": batch_end,
                "timestamp": time.time(),
            },
        }

        # Save checkpoint
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        progress_pct = checkpoint_data["metadata"]["progress_percentage"]  # type: ignore[index]
        logger.info(
            f"💾 Checkpoint saved: {len(questions)} questions ({progress_pct}% complete)"
        )


def main() -> None:
    """Run direct PDF extraction with batching."""
    processor = DirectPDFProcessor()

    pdf_path = Path("data/gesamtfragenkatalog-lebenindeutschland.pdf")
    output_path = Path("data/direct_extraction.json")

    # Process PDF in batches
    checkpoint_path = Path("data/extraction_checkpoint.json")
    questions = processor.process_full_pdf_in_batches(
        pdf_path, checkpoint_path, batch_size=50
    )

    # Save final results
    final_dataset: dict[str, Any] = {
        "questions": questions,
        "metadata": {
            "total_questions": len(questions),
            "extraction_method": "direct_pdf_file_api",
            "has_images_count": len([q for q in questions if q.get("has_images")]),
            "state_questions_count": len(
                [q for q in questions if q.get("question_type") == "state_specific"]
            ),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ Saved {len(questions)} questions to {output_path}")
    logger.info(f"✓ Image questions: {final_dataset['metadata']['has_images_count']}")
    logger.info(
        f"✓ State questions: {final_dataset['metadata']['state_questions_count']}"
    )


if __name__ == "__main__":
    main()
