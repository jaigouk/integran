"""External image viewer for opening question images in system image viewer."""
# mypy: ignore-errors

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not available - external viewer will not work")


class ExternalImageViewer:
    """Open original PNG images in system image viewer."""

    @staticmethod
    async def view_question_images(
        question_id: int, images: list[dict[str, str]], question_text: str | None = None
    ) -> bool:
        """Create composite of 4 original PNG images and open externally.

        Args:
            question_id: Question ID for display
            images: List of image dictionaries with 'path' key
            question_text: Optional question text for title

        Returns:
            True if successfully opened, False otherwise
        """
        if not HAS_PIL:
            logger.error("PIL not available - cannot create image composite")
            return False

        if not images:
            logger.error("No images provided")
            return False

        try:
            # Load all 4 original PNG images
            pil_images = []
            for i, img_data in enumerate(images[:4]):
                img_path = Path(img_data["path"])
                if img_path.exists():
                    # Load original PNG
                    img = PILImage.open(img_path)

                    # Add option letter overlay
                    draw = ImageDraw.Draw(img)
                    option_letter = chr(65 + i)  # A, B, C, D

                    # Try to use a nice font, fallback to default
                    font = ExternalImageViewer._get_font(60)

                    # Draw letter with outline for visibility
                    ExternalImageViewer._draw_text_with_outline(
                        draw, (20, 20), option_letter, font, "white", "black", 3
                    )

                    pil_images.append(img)  # type: ignore[arg-type]
                else:
                    # Create placeholder if original image missing
                    placeholder = ExternalImageViewer._create_placeholder(
                        chr(65 + i), str(img_path)
                    )
                    pil_images.append(placeholder)  # type: ignore[arg-type]

            # Create 2x2 grid composite
            if pil_images:
                composite = ExternalImageViewer._create_composite(
                    pil_images,
                    question_id,
                    question_text,  # type: ignore[arg-type]
                )

                # Save and open
                success = await ExternalImageViewer._save_and_open(
                    composite, question_id
                )
                return success

        except Exception as e:
            logger.error(f"Failed to open images externally: {e}")
            return False

        return False

    @staticmethod
    def _get_font(size: int) -> object | None:
        """Get the best available font."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            except Exception:  # noqa: S112
                # Font loading failed, try next font
                continue

        # Fallback to default
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    @staticmethod
    def _draw_text_with_outline(
        draw: object,
        position: tuple[int, int],
        text: str,
        font: object,
        fill_color: str,
        outline_color: str,
        outline_width: int,
    ) -> None:
        """Draw text with outline for better visibility."""
        x, y = position

        # Draw outline
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text(
                        (x + adj_x, y + adj_y), text, fill=outline_color, font=font
                    )

        # Draw main text
        draw.text(position, text, fill=fill_color, font=font)

    @staticmethod
    def _create_placeholder(option_letter: str, img_path: str) -> PILImage.Image:
        """Create placeholder image for missing files."""
        placeholder = PILImage.new("RGB", (400, 400), color="lightgray")
        draw = ImageDraw.Draw(placeholder)

        font = ExternalImageViewer._get_font(24)

        text = f"Image {option_letter}\\nNot Found\\n{Path(img_path).name}"
        draw.text((200, 180), text, fill="black", anchor="mm", font=font)

        return placeholder

    @staticmethod
    def _create_composite(
        pil_images: list[PILImage.Image | object],
        question_id: int,
        question_text: str | None,
    ) -> PILImage.Image:
        """Create 2x2 grid composite of images."""
        # Get max dimensions from actual images
        max_width = max(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)

        # Create composite with padding
        padding = 30
        title_height = 80
        composite_width = max_width * 2 + padding * 3
        composite_height = max_height * 2 + padding * 3 + title_height

        composite = PILImage.new("RGB", (composite_width, composite_height), "white")

        # Add title
        draw = ImageDraw.Draw(composite)
        title_font = ExternalImageViewer._get_font(24)

        title = f"Question {question_id}"
        if question_text:
            # Truncate long question text
            if len(question_text) > 80:
                question_text = question_text[:77] + "..."
            title += f" - {question_text}"

        # Center the title
        draw.text(
            (composite_width // 2, 25),
            title,
            fill="black",
            font=title_font,
            anchor="mm",
        )

        # Add instruction
        instruction = "Select the correct image"
        draw.text(
            (composite_width // 2, 50),
            instruction,
            fill="gray",
            font=ExternalImageViewer._get_font(16),
            anchor="mm",
        )

        # Position images in 2x2 grid
        positions = [
            (padding, title_height + padding),  # A - top left
            (max_width + padding * 2, title_height + padding),  # B - top right
            (padding, title_height + max_height + padding * 2),  # C - bottom left
            (
                max_width + padding * 2,
                title_height + max_height + padding * 2,
            ),  # D - bottom right
        ]

        for img, pos in zip(pil_images, positions, strict=False):
            composite.paste(img, pos)

        return composite

    @staticmethod
    async def _save_and_open(image: PILImage.Image, question_id: int) -> bool:
        """Save composite image and open in system viewer."""
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(
                suffix=f"_q{question_id}.png", delete=False
            ) as tmp:
                image.save(tmp.name, "PNG")
                temp_path = tmp.name

                logger.info(f"Saved composite image to: {temp_path}")

                # Open with system viewer
                success = await ExternalImageViewer._open_with_system_viewer(temp_path)

                if success:
                    logger.info(
                        f"Opened images for question {question_id} in external viewer"
                    )
                else:
                    logger.error(f"Failed to open images for question {question_id}")

                return success

        except Exception as e:
            logger.error(f"Failed to save and open image: {e}")
            return False

    @staticmethod
    async def _open_with_system_viewer(file_path: str) -> bool:
        """Open file with system default image viewer."""
        try:
            if sys.platform == "darwin":  # macOS
                await asyncio.create_subprocess_exec(
                    "open",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            elif sys.platform == "win32":  # Windows
                # Windows 'start' command requires shell=True  # noqa: S602
                await asyncio.create_subprocess_exec(  # noqa: S604
                    "start",
                    "",
                    file_path,
                    shell=True,  # noqa: S602
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:  # Linux/Unix
                await asyncio.create_subprocess_exec(
                    "xdg-open",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            # Don't wait for the external viewer to close - let it run independently
            # This allows the user to continue using the app while viewing images
            # Process started successfully if we reach here
            return True

        except Exception as e:
            logger.error(f"Failed to open with system viewer: {e}")
            return False
