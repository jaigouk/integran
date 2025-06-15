"""Domain service for processing and describing images."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from src.domain.content.events.content_events import (
    ContentGenerationFailedEvent,
    ImageProcessedEvent,
)
from src.domain.content.models.answer_models import (
    ImageDescription,
    ImageProcessingRequest,
    ImageProcessingResult,
)
from src.domain.shared.services import DomainService
from src.infrastructure.config.settings import get_settings, has_gemini_config
from src.infrastructure.messaging.event_bus import EventBus

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ProcessImage(DomainService[ImageProcessingRequest, ImageProcessingResult]):
    """Domain service for processing images and generating descriptions."""

    def __init__(self, event_bus: EventBus):
        """Initialize the image processing service."""
        super().__init__(event_bus)

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

    async def call(self, request: ImageProcessingRequest) -> ImageProcessingResult:
        """Process and describe an image using AI vision."""
        if not has_gemini_config():
            return ImageProcessingResult(
                success=False,
                description=None,
                error_message="Gemini API not configured. Please set up authentication.",
            )

        start_time = time.time()
        logger.info(f"Processing image: {request.image_path}")

        image_path = Path(request.image_path)
        if not image_path.exists():
            error_msg = f"Image not found: {request.image_path}"
            logger.error(error_msg)

            await self.event_bus.publish(
                ContentGenerationFailedEvent(
                    operation_type="image_processing",
                    entity_id=request.image_path,
                    error_message=error_msg,
                    retry_count=0,
                )
            )

            return ImageProcessingResult(
                success=False,
                description=None,
                error_message=error_msg,
            )

        try:
            # Read image file
            with open(image_path, "rb") as f:
                image_data = f.read()

            # Create prompt for image description
            prompt = self._create_image_analysis_prompt(request)

            # Describe the image
            response = await self._analyze_image_async(image_data, prompt)

            # Parse the response
            description = self._parse_image_description(response, request)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Publish success event
            await self.event_bus.publish(
                ImageProcessedEvent(
                    image_path=request.image_path,
                    page_number=request.page_number,
                    has_description=True,
                    processing_time_ms=processing_time_ms,
                )
            )

            logger.info(f"Successfully processed image: {request.image_path}")
            return ImageProcessingResult(success=True, description=description)

        except Exception as e:
            logger.error(f"Failed to process image {request.image_path}: {e}")

            # Publish failure event
            await self.event_bus.publish(
                ContentGenerationFailedEvent(
                    operation_type="image_processing",
                    entity_id=request.image_path,
                    error_message=str(e),
                    retry_count=0,
                )
            )

            return ImageProcessingResult(
                success=False,
                description=None,
                error_message=str(e),
            )

    def _create_image_analysis_prompt(self, request: ImageProcessingRequest) -> str:
        """Create prompt for image analysis."""
        prompt = """Analyze this image from a German Integration Exam (Leben in Deutschland Test).

Please provide:
1. DESCRIPTION: What exactly is shown in the image (symbols, colors, text, objects)
2. VISUAL_ELEMENTS: List specific visual elements (colors, symbols, shapes, text)
3. CONTEXT: Historical, political, or cultural context relevant to German integration
4. QUESTION_RELEVANCE: How this image relates to German citizenship/integration knowledge

Focus on details that would help someone answer exam questions about German symbols, history, politics, or culture."""

        if request.question_context:
            prompt += f"\n\nAdditional context: {request.question_context}"

        prompt += "\n\nRespond in JSON format with these exact keys: description, visual_elements, context, question_relevance"

        return prompt

    async def _analyze_image_async(self, image_data: bytes, prompt: str) -> str:
        """Analyze image using AI vision (simulated async)."""
        # Note: Current Gemini SDK doesn't support true async, so we simulate it
        return await self._simulate_async_vision_call(image_data, prompt)

    async def _simulate_async_vision_call(self, image_data: bytes, prompt: str) -> str:
        """Simulate async vision API call."""
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

        return response_text.strip()

    def _parse_image_description(
        self, response_text: str, request: ImageProcessingRequest
    ) -> ImageDescription:
        """Parse AI response into ImageDescription."""
        try:
            result = json.loads(response_text)
            return ImageDescription(
                path=request.image_path,
                description=result.get("description", ""),
                visual_elements=result.get("visual_elements", []),
                context=result.get("context", ""),
                question_relevance=result.get("question_relevance", ""),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response for {request.image_path}: {e}")
            # Fallback description
            page_info = (
                f"page {request.page_number}" if request.page_number else "unknown page"
            )
            return ImageDescription(
                path=request.image_path,
                description=f"Image from {page_info}",
                visual_elements=[],
                context="Unable to analyze image",
                question_relevance="Unknown",
            )
