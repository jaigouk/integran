#!/usr/bin/env python3
"""
PDF Image Extraction Script for German Integration Exam

This script extracts images from the PDF and saves them with the proper naming convention.
It handles both single and multiple image questions and excludes header logos.
"""

import argparse
import io
import json
import logging
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFImageExtractor:
    """Extract images from PDF pages with logo filtering and quality optimization."""

    def __init__(self, pdf_path: Path, output_dir: Path):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Open PDF document
        try:
            self.doc = fitz.open(str(pdf_path))
            logger.info(f"Opened PDF: {pdf_path} ({self.doc.page_count} pages)")
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            raise

        # Image filtering criteria
        self.min_width = 50  # Minimum image width
        self.min_height = 50  # Minimum image height
        self.logo_exclusion_height = 100  # Exclude images in top 100px (logo area)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "doc"):
            self.doc.close()

    def get_page_images(self, page_number: int) -> list[dict]:
        """Extract all images from a specific page with metadata and filtering."""
        if page_number < 1 or page_number > self.doc.page_count:
            logger.warning(f"Page {page_number} out of range (1-{self.doc.page_count})")
            return []

        page = self.doc[page_number - 1]  # fitz uses 0-based indexing
        image_list = page.get_images(full=True)

        if not image_list:
            logger.debug(f"No images found on page {page_number}")
            return []

        extracted_images = []
        page_rect = page.rect

        for img_index, img in enumerate(image_list):
            try:
                # Get image reference and metadata
                xref = img[0]

                # Get image position on page
                image_rects = page.get_image_rects(img)
                if not image_rects:
                    logger.debug(
                        f"No position info for image {img_index} on page {page_number}"
                    )
                    continue

                # Use the first rectangle (main image position)
                img_rect = image_rects[0]

                # Filter out header logos (top area of page)
                if img_rect.y0 < self.logo_exclusion_height:
                    logger.debug(f"Skipping logo image at top of page {page_number}")
                    continue

                # Extract image data
                pix = fitz.Pixmap(self.doc, xref)

                # Filter by size
                if pix.width < self.min_width or pix.height < self.min_height:
                    logger.debug(
                        f"Skipping small image {pix.width}x{pix.height} on page {page_number}"
                    )
                    pix = None
                    continue

                # Convert to RGB if needed
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    image_data = pix.tobytes("png")
                else:  # CMYK
                    logger.debug(f"Converting CMYK image to RGB on page {page_number}")
                    pix_rgb = fitz.Pixmap(fitz.csRGB, pix)
                    image_data = pix_rgb.tobytes("png")
                    pix_rgb = None

                extracted_images.append(
                    {
                        "data": image_data,
                        "width": pix.width,
                        "height": pix.height,
                        "index": img_index + 1,
                        "xref": xref,
                        "position": {
                            "x0": img_rect.x0,
                            "y0": img_rect.y0,
                            "x1": img_rect.x1,
                            "y1": img_rect.y1,
                        },
                    }
                )

                pix = None  # Cleanup

            except Exception as e:
                logger.warning(
                    f"Failed to extract image {img_index} from page {page_number}: {e}"
                )
                continue

        logger.info(
            f"Page {page_number}: Found {len(extracted_images)} valid images (excluded logos)"
        )
        return extracted_images

    def optimize_image(self, image_data: bytes) -> bytes:
        """Optimize image quality and size for exam content."""
        try:
            # Load image
            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if "A" in img.mode:
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background

            # Resize if too large (maintain aspect ratio)
            max_size = (800, 600)
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.debug(f"Resized image to {img.size}")

            # Enhance contrast slightly for better readability
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)

            # Save optimized
            output = io.BytesIO()
            img.save(output, format="PNG", quality=95, optimize=True)
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Image optimization failed, using original: {e}")
            return image_data

    def extract_images_for_question(
        self, question_id: int, page_number: int, expected_count: int | None = None
    ) -> list[str]:
        """Extract images for a specific question with proper naming."""
        images = self.get_page_images(page_number)

        if not images:
            logger.warning(
                f"No images found for question {question_id} on page {page_number}"
            )
            return []

        # If expected count is specified, validate
        if expected_count and len(images) != expected_count:
            logger.warning(
                f"Expected {expected_count} images for Q{question_id}, found {len(images)}"
            )

        # Sort images by position (top to bottom, left to right)
        images.sort(key=lambda x: (x["position"]["y0"], x["position"]["x0"]))

        saved_paths = []
        for i, img in enumerate(images):
            # Generate filename with question-specific naming
            filename = f"q{question_id}_{i + 1}.png"
            file_path = self.output_dir / filename

            # Optimize and save image
            optimized_data = self.optimize_image(img["data"])
            with open(file_path, "wb") as f:
                f.write(optimized_data)

            # Use relative path from project root or absolute path as fallback
            try:
                rel_path = file_path.relative_to(Path.cwd())
                saved_paths.append(str(rel_path))
            except ValueError:
                saved_paths.append(str(file_path))
            logger.info(f"Saved: {filename} ({img['width']}x{img['height']})")

        return saved_paths


class ImageQuestionHandler:
    """Handle image question identification and extraction coordination."""

    # Known image questions from direct_pdf_processor.py analysis
    TEIL_1_IMAGE_QUESTIONS = {21, 55, 70, 130, 176, 181, 187, 209, 216, 226, 235}
    TEIL_2_IMAGE_QUESTIONS = {1, 8}  # For each state

    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self.dataset = self._load_dataset()

    def _load_dataset(self) -> dict:
        """Load the direct extraction dataset."""
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

    def get_image_questions(self) -> list[tuple[int, int, bool]]:
        """Get list of (question_id, page_number, is_multiple_images) for all image questions."""
        image_questions = []

        for q_id_str, question in self.dataset.get("questions", {}).items():
            q_id = int(q_id_str)

            if question.get("is_image_question", False):
                page_num = question.get("page_number", 0)

                # Determine if this is a multiple image question (4 images) or single image
                is_multiple = self._is_multiple_image_question(q_id, question)

                image_questions.append((q_id, page_num, is_multiple))

        logger.info(f"Found {len(image_questions)} image questions in dataset")
        return image_questions

    def _is_multiple_image_question(
        self, question_id: int, question_data: dict
    ) -> bool:
        """Determine if question has multiple images (4) or single image (1)."""
        # Check if options reference "Bild 1", "Bild 2", etc.
        options = question_data.get("options", [])
        has_bild_references = any("Bild" in str(opt) for opt in options)

        # Check existing images array length
        existing_images = question_data.get("images", [])
        has_multiple_images = len(existing_images) > 1

        return has_bild_references or has_multiple_images

    def get_question_by_id(self, question_id: int) -> dict | None:
        """Get question data by ID."""
        return self.dataset.get("questions", {}).get(str(question_id))


def main():
    """Main extraction function."""
    parser = argparse.ArgumentParser(
        description="Extract images from German Integration Exam PDF"
    )
    parser.add_argument(
        "--question-id", type=int, help="Extract images for specific question ID only"
    )
    parser.add_argument(
        "--pdf-path",
        type=Path,
        default=Path("data/gesamtfragenkatalog-lebenindeutschland.pdf"),
        help="Path to PDF file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/images"),
        help="Output directory for extracted images",
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=Path("data/direct_extraction.json"),
        help="Path to extraction dataset JSON",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.pdf_path.exists():
        logger.error(f"PDF file not found: {args.pdf_path}")
        return 1

    if not args.dataset_path.exists():
        logger.error(f"Dataset file not found: {args.dataset_path}")
        return 1

    # Initialize handlers
    question_handler = ImageQuestionHandler(args.dataset_path)

    # Extract images
    with PDFImageExtractor(args.pdf_path, args.output_dir) as extractor:
        if args.question_id:
            # Extract for specific question
            question_data = question_handler.get_question_by_id(args.question_id)
            if not question_data:
                logger.error(f"Question {args.question_id} not found in dataset")
                return 1

            if not question_data.get("is_image_question", False):
                logger.warning(
                    f"Question {args.question_id} is not marked as image question"
                )

            page_num = question_data.get("page_number", 0)
            logger.info(
                f"Extracting images for question {args.question_id} from page {page_num}"
            )

            # Determine expected image count
            is_multiple = question_handler._is_multiple_image_question(
                args.question_id, question_data
            )
            expected_count = 4 if is_multiple else None

            paths = extractor.extract_images_for_question(
                args.question_id, page_num, expected_count
            )

            if paths:
                logger.info(
                    f"Successfully extracted {len(paths)} images for question {args.question_id}"
                )
                for path in paths:
                    logger.info(f"  - {path}")
            else:
                logger.warning(f"No images extracted for question {args.question_id}")

        else:
            # Extract for all image questions
            image_questions = question_handler.get_image_questions()
            total_extracted = 0

            for q_id, page_num, is_multiple in image_questions:
                logger.info(f"Processing question {q_id} on page {page_num}")

                expected_count = 4 if is_multiple else None
                paths = extractor.extract_images_for_question(
                    q_id, page_num, expected_count
                )

                if paths:
                    total_extracted += len(paths)
                    logger.info(f"  ✓ Extracted {len(paths)} images")
                else:
                    logger.warning("  ❌ No images extracted")

            logger.info(
                f"Extraction complete: {total_extracted} total images extracted"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
