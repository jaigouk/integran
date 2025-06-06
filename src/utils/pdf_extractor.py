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

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

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
    # Enhanced fields for image support and state questions
    question_type: str = Field(
        "general", description="Type: 'general' or 'state_specific'"
    )
    state: str | None = Field(
        None, description="Federal state for state-specific questions"
    )
    page_number: int | None = Field(
        None, description="PDF page number where question appears"
    )
    is_image_question: bool = Field(
        False, description="Whether question includes images"
    )
    image_paths: list[str] = Field(
        default_factory=list,
        description="List of image paths for multi-image questions",
    )
    image_mapping: str | None = Field(
        None, description="How images map to options: 'single' or 'option_images'"
    )


class QuestionList(BaseModel):
    """Model for the complete list of extracted questions."""

    questions: list[ExtractedQuestion] = Field(
        description="List of all extracted questions"
    )


class GeminiPDFExtractor:
    """Extracts questions from PDF using Gemini Pro 2.5 with image support."""

    def __init__(self) -> None:
        """Initialize the PDF extractor with Gemini API."""
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for PDF extraction. "
                "Install with: pip install google-genai"
            )

        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF (fitz) and Pillow are required for image extraction. "
                "Install with: pip install pymupdf pillow"
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

    def extract_images_from_pdf(
        self, pdf_path: str | Path, output_dir: str | Path
    ) -> dict[int, list[str]]:
        """Extract images from PDF pages and save them.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save extracted images

        Returns:
            Dictionary mapping page numbers to lists of image file paths
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        page_images = {}

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                if image_list:
                    page_images[page_num] = []

                    for img_index, img in enumerate(image_list):
                        # Get image metadata
                        xref = img[0]

                        # Extract image
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        width = base_image["width"]
                        height = base_image["height"]

                        # Filter out header logos (634x434) and very small/large images
                        # Header logos appear on every page and should be skipped
                        if (
                            100 <= width <= 800
                            and 100 <= height <= 600
                            and not (
                                width == 634 and height == 434
                            )  # Skip header logos
                        ):
                            # Save image with question-friendly naming
                            image_filename = (
                                f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                            )
                            image_path = output_dir / image_filename

                            with open(image_path, "wb") as f:
                                f.write(image_bytes)

                            # Store relative path for easier use in the app
                            relative_path = f"images/{image_filename}"
                            page_images[page_num].append(relative_path)
                            logger.info(
                                f"Extracted image: {image_filename} ({width}x{height})"
                            )

            doc.close()
            logger.info(f"Extracted images from {len(page_images)} pages")
            return page_images

        except Exception as e:
            logger.error(f"Failed to extract images: {e}")
            return {}

    def match_images_to_questions(
        self,
        questions: list[dict[str, Any]],
        page_images: dict[int, list[str]],
        pdf_path: str | Path,
    ) -> list[dict[str, Any]]:
        """Match extracted images to questions using precise PDF text analysis.

        Args:
            questions: List of extracted questions
            page_images: Dictionary mapping page numbers to image paths
            pdf_path: Path to the PDF file for page text analysis

        Returns:
            Updated questions list with image paths added
        """
        try:
            doc = fitz.open(pdf_path)

            # Build a comprehensive map of question locations and their contexts
            question_locations = {}

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()

                # Find all "Aufgabe X" patterns on this page
                import re

                aufgabe_matches = re.finditer(r"Aufgabe\s+(\d+)", page_text)

                for match in aufgabe_matches:
                    question_id = int(match.group(1))
                    start_pos = match.start()

                    # Get the text context around this question (next 1000 chars)
                    context_text = page_text[start_pos : start_pos + 1000]

                    question_locations[question_id] = {
                        "page": page_num,
                        "position": start_pos,
                        "context": context_text,
                        "full_page_text": page_text,
                    }

            # Now match each question to its images using precise context
            for question in questions:
                question_id = question.get("id", 0)

                # Initialize image fields
                question["image_paths"] = []
                question["image_mapping"] = None
                question["is_image_question"] = False
                question["page_number"] = None

                if question_id not in question_locations:
                    continue

                location = question_locations[question_id]
                page_num = location["page"]
                context = location["context"].lower()
                question["page_number"] = page_num + 1  # Store 1-based page number

                # Check if this page has images
                if page_num not in page_images or not page_images[page_num]:
                    continue

                # Filter out header logos (typically img_1 with specific dimensions)
                available_images = [
                    img
                    for img in page_images[page_num]
                    if not img.endswith("img_1.png") and not img.endswith("img_1.jpeg")
                ]

                if not available_images:
                    continue

                # Check question options to determine image type
                options = [
                    question.get("option_a", ""),
                    question.get("option_b", ""),
                    question.get("option_c", ""),
                    question.get("option_d", ""),
                ]

                # Type 1: Multi-image questions where images ARE the answer options
                is_image_options = all(
                    opt.strip().startswith("Bild ") for opt in options if opt.strip()
                )

                if is_image_options:
                    # This is a "Bild 1, Bild 2, Bild 3, Bild 4" type question
                    # We need to find the correct group of 4 images for this specific question

                    # If multiple questions on same page, we need to be more precise
                    same_page_questions = [
                        qid
                        for qid, loc in question_locations.items()
                        if loc["page"] == page_num and qid != question_id
                    ]

                    if same_page_questions:
                        # Multiple questions on same page - use position-based assignment
                        questions_on_page = sorted([question_id] + same_page_questions)
                        question_index = questions_on_page.index(question_id)

                        # Divide images among questions (assuming 4 images per question)
                        images_per_question = 4
                        start_idx = question_index * images_per_question
                        end_idx = start_idx + images_per_question

                        if start_idx < len(available_images):
                            assigned_images = available_images[start_idx:end_idx]
                            if assigned_images:
                                question["image_paths"] = assigned_images
                                question["image_mapping"] = "option_images"
                                question["is_image_question"] = True
                                logger.info(
                                    f"Multi-question page: Assigned images {start_idx}-{end_idx-1} to question {question_id}"
                                )
                    else:
                        # Single question on page - assign all available images
                        question["image_paths"] = available_images[
                            :4
                        ]  # Take up to 4 images
                        question["image_mapping"] = "option_images"
                        question["is_image_question"] = True
                        logger.info(
                            f"Single question: Assigned {len(question['image_paths'])} images to question {question_id}"
                        )

                # Type 2: Single image questions with image in question text
                elif any(
                    phrase in context
                    for phrase in [
                        "bild zeigt",
                        "welches bild",
                        "abbildung",
                        "wappen",
                        "flagge",
                        "karte zeigt",
                        "foto zeigt",
                    ]
                ):
                    # Single image that illustrates the question
                    question["image_paths"] = [available_images[0]]
                    question["image_mapping"] = "single"
                    question["is_image_question"] = True
                    logger.info(
                        f"Single image question: Assigned {available_images[0]} to question {question_id}"
                    )

                # Type 3: Questions that reference images in options but aren't pure image questions
                elif any("bild" in opt.lower() for opt in options):
                    # Options reference images but aren't pure "Bild X" format
                    num_image_refs = sum(1 for opt in options if "bild" in opt.lower())
                    if num_image_refs <= len(available_images):
                        question["image_paths"] = available_images[:num_image_refs]
                        question["image_mapping"] = "referenced"
                        question["is_image_question"] = True
                        logger.info(
                            f"Image-referenced question: Assigned {len(question['image_paths'])} images to question {question_id}"
                        )

            doc.close()
            return questions

        except Exception as e:
            logger.error(f"Failed to match images to questions: {e}")
            return questions

    def detect_image_questions(self, pdf_path: str | Path) -> dict[int, bool]:
        """Detect which pages contain image-based questions.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary mapping page numbers to whether they contain image questions
        """
        image_question_indicators = [
            "bild zeigt",
            "welches bild",
            "was zeigt",
            "abbildung",
            "foto zeigt",
            "darstellung",
            "wappen",
            "flagge",
            "karte zeigt",
            "dieses bild",
        ]

        try:
            doc = fitz.open(pdf_path)
            page_has_images = {}

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().lower()

                # Check for image-related text
                has_image_text = any(
                    indicator in text for indicator in image_question_indicators
                )

                # Check for actual images on the page
                image_list = page.get_images(full=True)
                has_images = len(image_list) > 0

                page_has_images[page_num] = has_image_text and has_images

            doc.close()
            return page_has_images

        except Exception as e:
            logger.error(f"Failed to detect image questions: {e}")
            return {}

    def extract_questions_from_pdf(self, pdf_path: str | Path) -> list[dict[str, Any]]:
        """Extract all 460 questions from PDF using Gemini Pro 2.5 with image support.

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

        logger.info(
            f"Extracting all 460 questions from {pdf_path} using Gemini Pro 2.5"
        )

        try:
            # Step 1: Extract images from PDF
            output_dir = pdf_path.parent / "images"
            page_images = self.extract_images_from_pdf(pdf_path, output_dir)

            # Step 2: Process the PDF in batches for better handling
            all_questions = []

            # Process Teil I (General questions 1-300) in smaller batches
            logger.info("Processing Teil I (General questions 1-300)")
            batch_size = 20  # Process 20 pages at a time to avoid timeouts

            for start_page in range(1, 112, batch_size):
                end_page = min(start_page + batch_size - 1, 111)
                logger.info(f"Processing Teil I batch: pages {start_page}-{end_page}")

                teil1_batch = self._extract_questions_batch(
                    pdf_path,
                    start_page=start_page,
                    end_page=end_page,
                    question_type="general",
                    page_images=page_images,
                )
                all_questions.extend(teil1_batch)

                # Throttle between batches to avoid rate limits
                logger.info(
                    f"Extracted {len(teil1_batch)} questions, sleeping 1 second..."
                )
                time.sleep(1)

            # Process Teil II (State-specific questions) in smaller batches
            logger.info("Processing Teil II (State-specific questions)")

            for start_page in range(112, 192, batch_size):
                end_page = min(start_page + batch_size - 1, 191)
                logger.info(f"Processing Teil II batch: pages {start_page}-{end_page}")

                teil2_batch = self._extract_questions_batch(
                    pdf_path,
                    start_page=start_page,
                    end_page=end_page,
                    question_type="state_specific",
                    page_images=page_images,
                )
                all_questions.extend(teil2_batch)

                # Throttle between batches to avoid rate limits
                logger.info(
                    f"Extracted {len(teil2_batch)} questions, sleeping 1 second..."
                )
                time.sleep(1)

            # Step 3: Match images to questions
            logger.info("Matching images to questions...")
            all_questions = self.match_images_to_questions(
                all_questions, page_images, pdf_path
            )

            logger.info(f"Successfully extracted {len(all_questions)} total questions")
            return all_questions

        except Exception as e:
            logger.error(f"Failed to extract questions using Gemini API: {e}")
            raise

    def _extract_questions_batch(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        question_type: str,
        page_images: dict[int, list[str]],
    ) -> list[dict[str, Any]]:
        """Extract questions from a specific page range of the PDF.

        Args:
            pdf_path: Path to the PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed)
            question_type: "general" or "state_specific"
            page_images: Dictionary of page numbers to image paths

        Returns:
            List of extracted questions from the specified pages
        """
        try:
            # Read specific pages from PDF
            doc = fitz.open(pdf_path)

            # Extract text from specified page range
            extracted_text = ""
            for page_num in range(start_page - 1, min(end_page, len(doc))):
                page = doc[page_num]
                page_text = page.get_text()

                # Add page marker for context
                extracted_text += f"\n=== PAGE {page_num + 1} ===\n"
                extracted_text += page_text

                # Add image context if this page has images
                if page_num in page_images and page_images[page_num]:
                    extracted_text += (
                        f"\n[IMAGES ON THIS PAGE: {', '.join(page_images[page_num])}]\n"
                    )

            doc.close()

            # Create the prompt for this batch
            prompt = self._create_enhanced_extraction_prompt(
                question_type=question_type, start_page=start_page, end_page=end_page
            )

            # Prepare the request
            text_part = types.Part.from_text(text=f"{prompt}\n\n{extracted_text}")
            contents = [types.Content(role="user", parts=[text_part])]

            # Configure generation with structured output
            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuestionList.model_json_schema(),
                temperature=0.1,
                max_output_tokens=65535,
            )

            # Make API call with retry logic
            max_retries = 3
            retry_delay = 30

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Extracting {question_type} questions from pages {start_page}-{end_page} "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )

                    # Add throttling to avoid rate limits
                    if attempt > 0:
                        time.sleep(2)  # Wait 2 seconds between retries

                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=contents,
                        config=generate_config,
                    )
                    break
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
                            retry_delay *= 2
                            continue
                        else:
                            logger.error("API still overloaded after all retries")
                            raise
                    else:
                        raise

            # Parse the response
            response_text = response.text.strip()

            # Remove markdown wrapping if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            try:
                result = json.loads(response_text)
                questions = result.get("questions", [])

                # Post-process questions to add metadata
                for question in questions:
                    question["question_type"] = question_type

                    # Detect if this is an image question
                    question_text = question.get("question", "").lower()
                    is_image_question = any(
                        indicator in question_text
                        for indicator in [
                            "bild zeigt",
                            "welches bild",
                            "abbildung",
                            "wappen",
                            "flagge",
                        ]
                    )
                    question["is_image_question"] = is_image_question

                    # For state-specific questions, try to determine the state
                    if question_type == "state_specific":
                        # This would need to be enhanced based on the actual PDF structure
                        question["state"] = (
                            "Unknown"  # TODO: Parse state from page content
                        )

                logger.info(
                    f"Extracted {len(questions)} {question_type} questions from pages {start_page}-{end_page}"
                )
                return questions

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                raise

        except Exception as e:
            logger.error(
                f"Failed to extract questions from pages {start_page}-{end_page}: {e}"
            )
            raise

    def _create_enhanced_extraction_prompt(
        self, question_type: str, start_page: int, end_page: int
    ) -> str:
        """Create enhanced prompt for batch extraction with image support.

        Args:
            question_type: "general" or "state_specific"
            start_page: Starting page number
            end_page: Ending page number

        Returns:
            Detailed prompt for Gemini API
        """
        if question_type == "general":
            intro = f"""
You are extracting GENERAL questions (Teil I) from pages {start_page}-{end_page} of the German integration exam catalog.
These are questions numbered from Aufgabe 1 to Aufgabe 300 that apply to all German federal states.
"""
        else:
            intro = f"""
You are extracting STATE-SPECIFIC questions (Teil II) from pages {start_page}-{end_page} of the German integration exam catalog.
These are questions that are specific to individual German federal states (Bundesländer).
Each state has 10 unique questions, for a total of 160 state-specific questions.
"""

        return f"""{intro}

CRITICAL: Your response must be ONLY a valid JSON object that matches the provided schema. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.

TASK: Extract ALL questions from the provided text with their answer options, including IMAGE-BASED questions.

REQUIREMENTS:

1. QUESTION DETECTION: Look for questions starting with "Aufgabe" followed by a number.
   - Filter out page numbers like "Seite X von Y"
   - Skip headers, footers, and navigation elements
   - Each question has a question text and four options A), B), C), D)

2. IMAGE QUESTIONS: Special attention to questions with images:
   - Questions containing phrases like "Bild zeigt", "Welches Bild", "Abbildung", "Wappen", "Flagge"
   - Mark these as image questions (is_image_question: true)
   - Include image context where available [IMAGES ON THIS PAGE: ...]

3. CATEGORIZATION: Classify each question into one of these categories:
   - "Grundrechte" (Basic rights and constitution)
   - "Demokratie und Wahlen" (Democracy and elections)
   - "Geschichte" (German history)
   - "Geografie" (Geography of Germany)
   - "Kultur und Gesellschaft" (Culture and society)
   - "Rechtssystem" (Legal system)
   - "Föderalismus" (Federalism)
   - "Allgemein" (General knowledge)

4. DIFFICULTY ASSESSMENT:
   - "easy": Simple factual questions, basic vocabulary
   - "medium": Requires understanding of concepts, moderate complexity
   - "hard": Complex topics, detailed knowledge, long texts

5. QUALITY ASSURANCE:
   - Extract complete question text and all four options
   - Preserve German characters (ä, ö, ü, ß)
   - Identify correct answer (A, B, C, or D)
   - Remove page artifacts and formatting issues

6. OUTPUT FORMAT: Return ONLY valid JSON matching the schema:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text in German",
      "option_a": "First option",
      "option_b": "Second option",
      "option_c": "Third option",
      "option_d": "Fourth option",
      "correct_answer": "A",
      "category": "Grundrechte",
      "difficulty": "medium",
      "question_type": "{question_type}",
      "state": null,
      "is_image_question": false,
      "image_path": null
    }}
  ]
}}

Extract ALL questions from the provided pages. Return ONLY the JSON object.
"""

    def _create_extraction_prompt(self) -> str:
        """Create a comprehensive prompt for question extraction (legacy method)."""
        return self._create_enhanced_extraction_prompt("general", 1, 191)

    def save_questions_to_csv(
        self, questions: list[dict[str, Any]], csv_path: str | Path
    ) -> None:
        """Save extracted questions to CSV file with enhanced fields.

        Args:
            questions: List of question dictionaries.
            csv_path: Path to save CSV file.
        """
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to CSV format matching our enhanced data model
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
                # Enhanced fields
                "question_type": q.get("question_type", "general"),
                "state": q.get("state", ""),
                "page_number": q.get("page_number", ""),
                "is_image_question": q.get("is_image_question", False),
                "image_paths": json.dumps(q.get("image_paths", [])),
                "image_mapping": q.get("image_mapping", ""),
            }
            csv_data.append(row)

        # Write to CSV with enhanced fields
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "id",
                "question",
                "options",
                "correct",
                "category",
                "difficulty",
                "question_type",
                "state",
                "page_number",
                "is_image_question",
                "image_paths",
                "image_mapping",
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
                    # Enhanced fields with defaults for backward compatibility
                    "question_type": row.get("question_type", "general"),
                    "state": row.get("state", "") or None,
                    "page_number": int(row.get("page_number", 0))
                    if row.get("page_number") and str(row.get("page_number")).isdigit()
                    else None,
                    "is_image_question": str(
                        row.get("is_image_question", "False")
                    ).lower()
                    == "true",
                    "image_paths": json.loads(row.get("image_paths", "[]"))
                    if row.get("image_paths")
                    else [],
                    "image_mapping": row.get("image_mapping", "") or None,
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
                # Enhanced fields with defaults for backward compatibility
                "question_type": row.get("question_type", "general"),
                "state": row.get("state", "") or None,
                "is_image_question": str(row.get("is_image_question", "False")).lower()
                == "true",
                "image_path": row.get("image_path", "") or None,
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


def extract_with_enhanced_checkpoint(
    pdf_path: str | Path | None = None,
    csv_path: str | Path | None = None,
) -> tuple[bool, int]:
    """Extract questions with checkpoint support and enhanced multi-image handling.

    Args:
        pdf_path: Path to the PDF file. Uses settings default if None.
        csv_path: Path to save CSV file. Uses settings default if None.

    Returns:
        Tuple of (success, total_questions_extracted)
    """
    import time
    from datetime import datetime

    try:
        settings = get_settings()

        # Use defaults from settings if not provided
        if pdf_path is None:
            pdf_path = settings.pdf_path
        if csv_path is None:
            csv_path = settings.questions_csv_path

        pdf_path = Path(pdf_path)
        csv_path = Path(csv_path)

        # Check if Gemini API is available
        if not GENAI_AVAILABLE or not has_gemini_config():
            logger.warning("Gemini API not available or configured")
            return False, 0

        # Initialize checkpoint
        checkpoint_file = Path("data/extraction_checkpoint.json")
        checkpoint_data = load_checkpoint(checkpoint_file)

        extractor = GeminiPDFExtractor()

        # Build page images mapping
        images_dir = Path("data/images")
        page_images = {}
        for img_file in images_dir.glob("page_*"):
            parts = img_file.stem.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                page_num = int(parts[1]) - 1  # 0-based
                if page_num not in page_images:
                    page_images[page_num] = []
                page_images[page_num].append(f"images/{img_file.name}")

        # Sort images to ensure correct order
        for page_num in page_images:
            page_images[page_num].sort()

        logger.info(f"Found images for {len(page_images)} pages")

        # Process with continuous ID numbering
        current_id = max(1, len(checkpoint_data.get("questions", [])) + 1)
        batch_size = 10

        # Teil I: Pages 1-111 (300 general questions)
        logger.info("Processing Teil I (General questions)")
        for start_page in range(1, 112, batch_size):
            end_page = min(start_page + batch_size - 1, 111)

            if should_skip_batch(checkpoint_data, start_page, end_page):
                logger.info(
                    f"Skipping already processed batch: pages {start_page}-{end_page}"
                )
                continue

            try:
                logger.info(f"Extracting Teil I pages {start_page}-{end_page}")

                questions = extractor._extract_questions_batch(
                    pdf_path=pdf_path,
                    start_page=start_page,
                    end_page=end_page,
                    question_type="general",
                    page_images=page_images,
                )

                # Fix IDs and add enhanced metadata
                for q in questions:
                    q["id"] = current_id
                    q["question_type"] = "general"
                    q["state"] = None
                    q["page_number"] = estimate_page_number(current_id)

                    # Image handling is now done in match_images_to_questions

                    current_id += 1

                if questions:
                    add_batch_to_checkpoint(
                        checkpoint_data, start_page, end_page, questions
                    )
                    save_checkpoint(checkpoint_file, checkpoint_data)
                    logger.info(
                        f"Batch complete: {len(questions)} questions. Total: {len(checkpoint_data['questions'])}"
                    )

                time.sleep(2)  # Throttle

            except Exception as e:
                logger.error(f"Batch {start_page}-{end_page} failed: {e}")
                continue

        # Teil II: Pages 112-191 (160 state-specific questions)
        logger.info("Processing Teil II (State-specific questions)")

        state_ranges = [
            ("Baden-Württemberg", 112, 116),
            ("Bayern", 117, 121),
            ("Berlin", 122, 126),
            ("Brandenburg", 127, 131),
            ("Bremen", 132, 136),
            ("Hamburg", 137, 141),
            ("Hessen", 142, 146),
            ("Mecklenburg-Vorpommern", 147, 151),
            ("Niedersachsen", 152, 156),
            ("Nordrhein-Westfalen", 157, 161),
            ("Rheinland-Pfalz", 162, 166),
            ("Saarland", 167, 171),
            ("Sachsen", 172, 176),
            ("Sachsen-Anhalt", 177, 181),
            ("Schleswig-Holstein", 182, 186),
            ("Thüringen", 187, 191),
        ]

        for start_page in range(112, 192, batch_size):
            end_page = min(start_page + batch_size - 1, 191)

            if should_skip_batch(checkpoint_data, start_page, end_page):
                logger.info(
                    f"Skipping already processed batch: pages {start_page}-{end_page}"
                )
                continue

            # Find current state
            current_state = None
            for state, state_start, state_end in state_ranges:
                if start_page >= state_start and start_page <= state_end:
                    current_state = state
                    break

            try:
                logger.info(
                    f"Extracting Teil II pages {start_page}-{end_page} ({current_state})"
                )

                questions = extractor._extract_questions_batch(
                    pdf_path=pdf_path,
                    start_page=start_page,
                    end_page=end_page,
                    question_type="state_specific",
                    page_images=page_images,
                )

                # Fix IDs and add enhanced metadata
                for q in questions:
                    q["id"] = current_id
                    q["question_type"] = "state_specific"
                    q["state"] = current_state
                    q["page_number"] = estimate_state_page_number(
                        current_id - 300, state_ranges
                    )

                    # Image handling is now done in match_images_to_questions

                    current_id += 1

                if questions:
                    add_batch_to_checkpoint(
                        checkpoint_data, start_page, end_page, questions
                    )
                    save_checkpoint(checkpoint_file, checkpoint_data)
                    logger.info(
                        f"Batch complete: {len(questions)} questions. Total: {len(checkpoint_data['questions'])}"
                    )

                time.sleep(2)  # Throttle

            except Exception as e:
                logger.error(f"Batch {start_page}-{end_page} failed: {e}")
                continue

        # Save final results
        all_questions = checkpoint_data.get("questions", [])
        if all_questions:
            extractor.save_questions_to_csv(all_questions, csv_path)

            # Convert to JSON
            json_path = csv_path.with_suffix(".json")
            extractor.convert_csv_to_json(csv_path, json_path)

            # Mark checkpoint as complete
            checkpoint_data["state"] = "completed"
            checkpoint_data["completed_at"] = datetime.now().isoformat()
            save_checkpoint(checkpoint_file, checkpoint_data)

            logger.info(f"Successfully extracted {len(all_questions)} questions")
            return True, len(all_questions)

        return False, 0

    except Exception as e:
        logger.error(f"Enhanced extraction failed: {e}")
        return False, 0


def load_checkpoint(checkpoint_file: Path) -> dict:
    """Load existing checkpoint or create new one."""
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            return json.load(f)
    from datetime import datetime

    return {
        "completed_batches": [],
        "questions": [],
        "state": "in_progress",
        "started_at": datetime.now().isoformat(),
    }


def save_checkpoint(checkpoint_file: Path, checkpoint_data: dict):
    """Save checkpoint to disk."""
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f, indent=2)


def should_skip_batch(checkpoint_data: dict, start_page: int, end_page: int) -> bool:
    """Check if batch was already processed."""
    for batch in checkpoint_data.get("completed_batches", []):
        if batch["start"] == start_page and batch["end"] == end_page:
            return True
    return False


def add_batch_to_checkpoint(
    checkpoint_data: dict, start_page: int, end_page: int, questions: list
):
    """Add completed batch to checkpoint."""
    from datetime import datetime

    batch_info = {
        "start": start_page,
        "end": end_page,
        "count": len(questions),
        "timestamp": datetime.now().isoformat(),
    }
    checkpoint_data["completed_batches"].append(batch_info)
    checkpoint_data["questions"].extend(questions)


def estimate_page_number(question_id: int) -> int:
    """Estimate page number based on question ID."""
    # Roughly 2.5-3 questions per page
    return max(1, (question_id - 1) // 3 + 1)


def estimate_state_page_number(state_question_num: int, state_ranges: list) -> int:
    """Estimate page number for state-specific questions."""
    state_index = (state_question_num - 1) // 10
    if state_index < len(state_ranges):
        return state_ranges[state_index][1] + ((state_question_num - 1) % 10) // 2
    return 112


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
