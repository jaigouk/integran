"""Image processing and mapping for German Integration Exam questions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.settings import get_settings, has_gemini_config

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class ImageDescription:
    """Metadata for an extracted image."""

    path: str
    description: str  # What the image shows
    visual_elements: list[str]  # Colors, symbols, text
    context: str  # Historical/political context
    question_relevance: str  # How this relates to integration exam


@dataclass
class PageInfo:
    """Information about a PDF page with images."""

    page_number: int
    has_images: bool
    image_paths: list[str]
    question_pattern: str  # "Aufgabe X" pattern found
    question_ids: list[int]  # Questions extracted from this page


class ImageProcessor:
    """Process images and create question-to-image mappings."""

    def __init__(self) -> None:
        """Initialize the image processor."""
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for image processing. "
                "Install with: pip install google-genai"
            )

        settings = get_settings()
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region
        self.model_id = settings.gemini_model
        self.use_vertex_ai = settings.use_vertex_ai

        # Initialize Gemini client
        if self.use_vertex_ai:
            if not self.project_id:
                raise ValueError("GCP_PROJECT_ID is required for Vertex AI")

            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location="global",
            )
        else:
            self.api_key = settings.gemini_api_key
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is required")

            self.client = genai.Client(api_key=self.api_key)

    def analyze_pdf_structure(
        self, extraction_checkpoint_path: Path
    ) -> dict[int, PageInfo]:
        """Parse extraction checkpoint to find page structure and image mappings."""
        if not extraction_checkpoint_path.exists():
            raise FileNotFoundError(
                f"Extraction checkpoint not found: {extraction_checkpoint_path}"
            )

        with open(extraction_checkpoint_path) as f:
            checkpoint_data = json.load(f)

        if checkpoint_data.get("state") != "completed":
            raise ValueError("Extraction checkpoint is not completed")

        questions = checkpoint_data.get("questions", [])
        page_info: dict[int, PageInfo] = {}

        # Analyze each question to build page mapping
        for question in questions:
            page_num = question.get("page_number")
            if not page_num:
                continue

            question_id = question.get("id")
            if not question_id:
                continue

            # Initialize page info if not exists
            if page_num not in page_info:
                page_info[page_num] = PageInfo(
                    page_number=page_num,
                    has_images=False,
                    image_paths=[],
                    question_pattern="",
                    question_ids=[],
                )

            page_info[page_num].question_ids.append(question_id)

            # Check if this question has images or image-related options
            if self._is_image_question(question):
                page_info[page_num].has_images = True
                # Look for existing images for this page
                images_dir = Path("data/images")
                page_images = list(
                    images_dir.glob(f"page_{page_num}_img_*.png")
                ) + list(images_dir.glob(f"page_{page_num}_img_*.jpeg"))
                page_info[page_num].image_paths = [str(img) for img in page_images]

        logger.info(f"Analyzed {len(page_info)} pages from extraction checkpoint")
        return page_info

    def _is_image_question(self, question: dict[str, Any]) -> bool:
        """Check if a question involves images."""
        # Check for "Bild X" patterns in options
        options = [
            question.get("option_a", ""),
            question.get("option_b", ""),
            question.get("option_c", ""),
            question.get("option_d", ""),
        ]

        bild_pattern_count = sum(
            1
            for option in options
            if "bild" in option.lower() and any(char.isdigit() for char in option)
        )

        # Check for image-related keywords in question text
        question_text = question.get("question", "").lower()
        image_keywords = ["wappen", "flagge", "symbol", "bild", "abbildung", "zeigt"]

        has_image_keywords = any(keyword in question_text for keyword in image_keywords)

        return bild_pattern_count >= 2 or has_image_keywords

    def describe_images_with_ai(
        self, image_paths: list[Path]
    ) -> dict[str, ImageDescription]:
        """Use Gemini Vision to describe each image."""
        descriptions: dict[str, ImageDescription] = {}

        for image_path in image_paths:
            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}")
                continue

            try:
                description = self._describe_single_image(image_path)
                descriptions[str(image_path)] = description
                logger.info(f"Described image: {image_path.name}")
            except Exception as e:
                logger.error(f"Failed to describe image {image_path}: {e}")
                continue

        return descriptions

    def _describe_single_image(self, image_path: Path) -> ImageDescription:
        """Describe a single image using Gemini Vision."""
        # Read image file
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Create prompt for image description
        prompt = """Analyze this image from a German Integration Exam (Leben in Deutschland Test).

Please provide:
1. DESCRIPTION: What exactly is shown in the image (symbols, colors, text, objects)
2. VISUAL_ELEMENTS: List specific visual elements (colors, symbols, shapes, text)
3. CONTEXT: Historical, political, or cultural context relevant to German integration
4. QUESTION_RELEVANCE: How this image relates to German citizenship/integration knowledge

Focus on details that would help someone answer exam questions about German symbols, history, politics, or culture.

Respond in JSON format with these exact keys: description, visual_elements, context, question_relevance"""

        # Prepare the request
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/png")
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[text_part, image_part])]

        # Configure generation
        generate_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for factual descriptions
            max_output_tokens=1000,
        )

        # Make API call
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,  # type: ignore[arg-type]
            config=generate_config,
        )

        # Parse response
        response_text = response.text.strip() if response.text else ""

        # Remove markdown if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)
            return ImageDescription(
                path=str(image_path),
                description=result.get("description", ""),
                visual_elements=result.get("visual_elements", []),
                context=result.get("context", ""),
                question_relevance=result.get("question_relevance", ""),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response for {image_path}: {e}")
            # Fallback description
            return ImageDescription(
                path=str(image_path),
                description=f"Image from page {self._extract_page_number(image_path)}",
                visual_elements=[],
                context="Unable to analyze image",
                question_relevance="Unknown",
            )

    def _extract_page_number(self, image_path: Path) -> int:
        """Extract page number from image filename."""
        name = image_path.name
        # Extract number from pattern like "page_123_img_2.png"
        try:
            parts = name.split("_")
            if len(parts) >= 2 and parts[0] == "page":
                return int(parts[1])
        except (ValueError, IndexError):
            pass
        return 0

    def create_question_image_mapping(
        self,
        page_info: dict[int, PageInfo],
        _image_descriptions: dict[str, ImageDescription],
    ) -> dict[int, list[str]]:
        """Create final mapping: question_id -> [image_paths]."""
        question_image_mapping: dict[int, list[str]] = {}

        for _page_num, info in page_info.items():
            if not info.has_images or not info.image_paths:
                continue

            # All questions on this page get access to all images on the page
            for question_id in info.question_ids:
                question_image_mapping[question_id] = info.image_paths.copy()

        logger.info(
            f"Created image mappings for {len(question_image_mapping)} questions"
        )
        return question_image_mapping

    def process_all_images(
        self,
    ) -> tuple[dict[int, list[str]], dict[str, ImageDescription]]:
        """Complete image processing pipeline."""
        if not has_gemini_config():
            raise ValueError("Gemini API not configured. Please set up authentication.")

        # Step 1: Analyze PDF structure from checkpoint
        checkpoint_path = Path("data/extraction_checkpoint.json")
        page_info = self.analyze_pdf_structure(checkpoint_path)

        # Step 2: Find all image pages
        image_pages = [info for info in page_info.values() if info.has_images]
        logger.info(f"Found {len(image_pages)} pages with images")

        # Step 3: Collect all unique image paths
        all_image_paths = set()
        for info in image_pages:
            all_image_paths.update(info.image_paths)

        image_path_objects = [Path(path) for path in all_image_paths]
        logger.info(f"Processing {len(image_path_objects)} unique images")

        # Step 4: Describe images with AI
        image_descriptions = self.describe_images_with_ai(image_path_objects)

        # Step 5: Create question-to-image mapping
        question_image_mapping = self.create_question_image_mapping(
            page_info, image_descriptions
        )

        return question_image_mapping, image_descriptions
