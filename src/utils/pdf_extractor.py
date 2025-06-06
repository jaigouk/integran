"""PDF extraction utility for Leben in Deutschland questions using Gemini Pro 2.5."""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.settings import get_settings, has_gemini_config

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)


class ExtractedQuestion(BaseModel):
    """Model for extracted question data."""

    id: int = Field(description="Unique question number/ID from the document")
    question: str = Field(description="The complete question text in German")
    option_a: str = Field(description="Answer option A text")
    option_b: str = Field(description="Answer option B text")
    option_c: str = Field(description="Answer option C text")
    option_d: str = Field(description="Answer option D text")
    correct_answer: str = Field(description="The correct answer letter (A, B, C, or D)")
    category: str = Field(
        description="Question category/topic (e.g., Grundrechte, Geschichte, etc.)"
    )
    difficulty: str = Field(
        description="Estimated difficulty level: easy, medium, or hard"
    )


class QuestionList(BaseModel):
    """Model for the complete list of extracted questions."""

    questions: list[ExtractedQuestion] = Field(
        description="List of all extracted questions"
    )


class GeminiPDFExtractor:
    """Extracts questions from PDF using Gemini Pro 2.5."""

    def __init__(self) -> None:
        """Initialize the PDF extractor with Gemini API."""
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for PDF extraction. "
                "Install with: pip install google-genai"
            )

        settings = get_settings()
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region
        self.model_id = settings.gemini_model
        self.use_vertex_ai = settings.use_vertex_ai

        # Initialize Gemini client based on authentication method
        if self.use_vertex_ai:
            # Use Vertex AI client with service account credentials
            if not self.project_id:
                raise ValueError("GCP_PROJECT_ID is required for Vertex AI")

            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location="global",
            )
        else:
            # Use API key authentication (legacy)
            self.api_key = settings.gemini_api_key
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is required for PDF extraction")

            self.client = genai.Client(api_key=self.api_key)

    def extract_questions_from_pdf(self, pdf_path: str | Path) -> list[dict[str, Any]]:
        """Extract questions from PDF using Gemini Pro 2.5.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of extracted question dictionaries.

        Raises:
            FileNotFoundError: If PDF file doesn't exist.
            Exception: If API call fails.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Extracting questions from {pdf_path} using Gemini Pro 2.5")

        try:
            # Read PDF data
            with open(pdf_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()

            # Create the prompt for question extraction
            prompt = self._create_extraction_prompt()

            # Prepare the request with PDF data using new types format
            pdf_part = types.Part.from_bytes(data=pdf_data, mime_type="application/pdf")
            text_part = types.Part.from_text(text=prompt)

            contents = [types.Content(role="user", parts=[pdf_part, text_part])]

            # Configure generation with structured output
            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuestionList.model_json_schema(),
                temperature=0.1,  # Low temperature for consistent extraction
                max_output_tokens=65535,
            )

            # Make API call to Gemini with retry logic
            max_retries = 3
            retry_delay = 30  # seconds

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Attempting API call (attempt {attempt + 1}/{max_retries})"
                    )
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=contents,
                        config=generate_config,
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if (
                        "overloaded" in str(e).lower()
                        or "unavailable" in str(e).lower()
                    ):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"API overloaded, retrying in {retry_delay} seconds..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            logger.error("API still overloaded after all retries")
                            raise
                    else:
                        # Different error, don't retry
                        raise

            # Parse the response - handle potential markdown wrapping
            response_text = response.text.strip()

            # Remove markdown code block wrapping if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove closing ```

            response_text = response_text.strip()

            try:
                result = json.loads(response_text)
                questions = result.get("questions", [])
                logger.info(f"Successfully extracted {len(questions)} questions")
                return questions
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                logger.error(f"Response text (last 500 chars): {response_text[-500:]}")
                raise

        except Exception as e:
            logger.error(f"Failed to extract questions using Gemini API: {e}")
            raise

    def _create_extraction_prompt(self) -> str:
        """Create a comprehensive prompt for question extraction.

        Returns:
            Detailed prompt for Gemini API.
        """
        return """
You are an expert document processor specializing in extracting German integration exam questions from official documents.

CRITICAL: Your response must be ONLY a valid JSON object that matches the provided schema. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.

TASK: Analyze the provided PDF document "Gesamtfragenkatalog Leben in Deutschland" and extract ALL questions with their answer options.

REQUIREMENTS:

1. EXTRACT ALL QUESTIONS: This document contains exactly 310 questions for the German integration exam (Leben in Deutschland Test). You must extract every single question.

2. QUESTION STRUCTURE: Each question follows this format:
   - Question number (1-310)
   - Question text in German
   - Four answer options labeled A), B), C), D)
   - Correct answer is typically marked or can be inferred

3. CATEGORIZATION: Classify each question into one of these categories based on content:
   - "Grundrechte" (Basic rights and constitution)
   - "Demokratie und Wahlen" (Democracy and elections)
   - "Geschichte" (German history)
   - "Geografie" (Geography of Germany)
   - "Kultur und Gesellschaft" (Culture and society)
   - "Rechtssystem" (Legal system)
   - "Föderalismus" (Federalism)
   - "Allgemein" (General knowledge)

4. DIFFICULTY ASSESSMENT: Evaluate difficulty based on:
   - "easy": Simple factual questions, basic vocabulary
   - "medium": Requires understanding of concepts, moderate complexity
   - "hard": Complex topics, detailed knowledge required, long texts

5. QUALITY ASSURANCE:
   - Ensure question text is complete and readable
   - All four options (A, B, C, D) must be extracted
   - Correct answer must be identified (A, B, C, or D)
   - Remove any page numbers or formatting artifacts
   - Preserve German special characters (ä, ö, ü, ß)
   - Escape any quotes or special characters properly in JSON

6. OUTPUT FORMAT:
   - Return ONLY a valid JSON object matching the provided schema
   - Do not wrap the JSON in markdown code blocks
   - Do not include any text before or after the JSON
   - Ensure all strings are properly escaped for JSON parsing

EXAMPLE FORMAT:
{
  "questions": [
    {
      "id": 1,
      "question": "Question text in German",
      "option_a": "First option",
      "option_b": "Second option",
      "option_c": "Third option",
      "option_d": "Fourth option",
      "correct_answer": "A",
      "category": "Grundrechte",
      "difficulty": "medium"
    }
  ]
}

Process the entire document systematically and extract all 310 questions. Return ONLY the JSON object.
"""

    def save_questions_to_csv(
        self, questions: list[dict[str, Any]], csv_path: str | Path
    ) -> None:
        """Save extracted questions to CSV file.

        Args:
            questions: List of question dictionaries.
            csv_path: Path to save CSV file.
        """
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to CSV format matching our data model
        csv_data = []
        for q in questions:
            row = {
                "id": q["id"],
                "question": q["question"],
                "options": json.dumps(
                    [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
                ),
                "correct": q[f"option_{q['correct_answer'].lower()}"],
                "category": q["category"],
                "difficulty": q["difficulty"],
            }
            csv_data.append(row)

        # Write to CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "id",
                "question",
                "options",
                "correct",
                "category",
                "difficulty",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        logger.info(f"Saved {len(csv_data)} questions to {csv_path}")

    def convert_csv_to_json(self, csv_path: str | Path, json_path: str | Path) -> int:
        """Convert CSV file to JSON format for the application.

        Args:
            csv_path: Path to CSV file.
            json_path: Path to save JSON file.

        Returns:
            Number of questions converted.
        """
        csv_path = Path(csv_path)
        json_path = Path(json_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        questions = []
        with open(csv_path, encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                question = {
                    "id": int(row["id"]),
                    "question": row["question"],
                    "options": json.loads(row["options"]),
                    "correct": row["correct"],
                    "category": row["category"],
                    "difficulty": row["difficulty"],
                }
                questions.append(question)

        # Save to JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(questions, jsonfile, ensure_ascii=False, indent=2)

        logger.info(f"Converted {len(questions)} questions from CSV to JSON")
        return len(questions)


def _convert_csv_to_json_standalone(csv_path: str | Path, json_path: str | Path) -> int:
    """Convert CSV to JSON without requiring Gemini API.

    Args:
        csv_path: Path to CSV file.
        json_path: Path to save JSON file.

    Returns:
        Number of questions converted.
    """
    import csv

    csv_path = Path(csv_path)
    json_path = Path(json_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    questions = []
    with open(csv_path, encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            question = {
                "id": int(row["id"]),
                "question": row["question"],
                "options": json.loads(row["options"]),
                "correct": row["correct"],
                "category": row["category"],
                "difficulty": row["difficulty"],
            }
            questions.append(question)

    # Save to JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jsonfile:
        json.dump(questions, jsonfile, ensure_ascii=False, indent=2)

    logger.info(f"Converted {len(questions)} questions from CSV to JSON")
    return len(questions)


def extract_questions_to_csv(
    pdf_path: str | Path | None = None,
    csv_path: str | Path | None = None,
) -> bool:
    """Extract questions from PDF to CSV using Gemini Pro 2.5.

    This function is intended for generating the CSV file during development.
    Normal users don't need to run this as the CSV should be pre-generated.

    Args:
        pdf_path: Path to the PDF file. Uses settings default if None.
        csv_path: Path to save CSV file. Uses settings default if None.

    Returns:
        True if extraction successful, False otherwise.
    """
    try:
        settings = get_settings()

        # Use defaults from settings if not provided
        if pdf_path is None:
            pdf_path = settings.pdf_path
        if csv_path is None:
            csv_path = settings.questions_csv_path

        # Check if Gemini API is available
        if not GENAI_AVAILABLE:
            logger.warning("google-genai package not available")
            logger.info("CSV extraction skipped - google-genai not installed")
            return False

        # Check if Gemini configuration is available
        if not has_gemini_config():
            logger.warning("Gemini API configuration not available")
            logger.info("CSV extraction skipped - Gemini API not configured")
            return False

        extractor = GeminiPDFExtractor()
        questions = extractor.extract_questions_from_pdf(pdf_path)
        extractor.save_questions_to_csv(questions, csv_path)

        logger.info(f"Successfully extracted {len(questions)} questions to CSV")
        return True

    except Exception as e:
        logger.error(f"Failed to extract questions to CSV: {e}")
        return False


def ensure_questions_available() -> str | Path:
    """Ensure questions are available, either from CSV or by extracting from PDF.

    Returns:
        Path to the questions JSON file.

    Raises:
        FileNotFoundError: If neither CSV exists nor can be generated.
    """
    settings = get_settings()
    json_path = Path(settings.questions_json_path)
    csv_path = Path(settings.questions_csv_path)
    pdf_path = Path(settings.pdf_path)

    # If JSON already exists, use it
    if json_path.exists():
        logger.info(f"Using existing questions file: {json_path}")
        return json_path

    # If CSV exists, convert to JSON
    if csv_path.exists():
        logger.info(f"Converting CSV to JSON: {csv_path} -> {json_path}")
        _convert_csv_to_json_standalone(csv_path, json_path)
        return json_path

    # Try to extract from PDF if environment is configured
    if pdf_path.exists():
        logger.info("Attempting to extract questions from PDF")
        if extract_questions_to_csv(pdf_path, csv_path):
            # Convert newly created CSV to JSON
            _convert_csv_to_json_standalone(csv_path, json_path)
            return json_path

    # If all else fails, suggest manual steps
    raise FileNotFoundError(
        f"Questions file not found. Please ensure one of the following exists:\n"
        f"1. {json_path} (processed questions)\n"
        f"2. {csv_path} (extracted from PDF)\n"
        f"3. {pdf_path} with GEMINI_API_KEY configured for extraction"
    )
