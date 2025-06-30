"""Domain service for processing and describing images."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from src.domain.content.events.content_events import (
    ContentGenerationFailedEvent,
    ImageProcessedEvent,
)
from src.domain.content.models.answer_models import (
    ImageDescription,
    ImageProcessingRequest,
    ImageProcessingResult,
)
from src.domain.shared.configuration import APIConfigurationInterface
from src.domain.shared.services import DomainService, EventBusInterface

try:
    from google import genai
    from google.genai import types

    from src.domain.shared.repositories import UserRepository
    from src.domain.user.models.user_models import LoadUserSettingsRequest

    # User domain imports for developer mode validation
    from src.domain.user.services.load_user_settings import LoadUserSettings

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)


class ProcessImage(DomainService[ImageProcessingRequest, ImageProcessingResult]):
    """Domain service for processing images and generating descriptions."""

    def __init__(
        self,
        event_bus: EventBusInterface,
        api_config: APIConfigurationInterface,
        user_repository: UserRepository | None = None,
    ):
        """Initialize the image processing service."""
        super().__init__(event_bus)
        self.api_config = api_config
        self.client: Any | None = None  # Initialize lazily when needed

        # User settings repository for developer mode validation
        self.user_repository = user_repository
        self._load_user_settings: LoadUserSettings | None = None

        logger.debug(
            "ProcessImage service initialized (credentials will be checked when used)"
        )

    def _ensure_client_initialized(self) -> None:
        """Initialize the Gemini client if not already done."""
        if self.client is not None:
            return

        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for image processing. "
                "Install with: pip install google-genai"
            )

        # Get configuration from domain interface
        gemini_config = self.api_config.get_gemini_config()
        if not gemini_config:
            raise ValueError("Gemini configuration not available")

        # Initialize Gemini client based on configuration
        if gemini_config.get("use_vertex_ai", True):
            project_id = gemini_config.get("project_id")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID is required for Vertex AI")

            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location="global",
            )
        else:
            api_key = gemini_config.get("api_key")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required")

            self.client = genai.Client(api_key=api_key)

    async def call(self, request: ImageProcessingRequest) -> ImageProcessingResult:
        """Process and describe an image using AI vision."""
        if not self.api_config.is_gemini_available():
            return ImageProcessingResult(
                success=False,
                description=None,
                error_message="Gemini API not configured. Please set up authentication.",
            )

        # Check developer mode before using Gemini API
        developer_mode_result = await self._check_developer_mode()
        if not developer_mode_result.success:
            return ImageProcessingResult(
                success=False,
                description=None,
                error_message=developer_mode_result.error_message,
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

    async def _check_developer_mode(self) -> ImageProcessingResult:
        """Check if developer mode is enabled for API usage.

        Returns:
            ImageProcessingResult with success=True if developer mode enabled,
            otherwise error result with user-friendly message.
        """
        try:
            # Initialize LoadUserSettings service if needed
            if self._load_user_settings is None:
                if self.user_repository is None:
                    return ImageProcessingResult(
                        success=False,
                        description=None,
                        error_message="User settings not available. Cannot verify developer mode permissions.",
                    )
                self._load_user_settings = LoadUserSettings(
                    self.event_bus, self.user_repository
                )

            # Load user settings to check developer mode
            load_request = LoadUserSettingsRequest(user_id=1)  # Default user ID
            load_result = await self._load_user_settings.call(load_request)

            if not load_result.success or not load_result.user_settings:
                return ImageProcessingResult(
                    success=False,
                    description=None,
                    error_message="Unable to load user settings. Cannot verify developer mode permissions.",
                )

            # Check if developer mode is enabled
            if not load_result.user_settings.developer_mode.enabled:
                return ImageProcessingResult(
                    success=False,
                    description=None,
                    error_message=(
                        "Developer mode is required for AI-powered image processing. "
                        "Please enable developer mode in settings to use this feature. "
                        "Note: This feature uses external APIs and may incur costs."
                    ),
                )

            # Developer mode is enabled
            return ImageProcessingResult(success=True, description=None)

        except Exception as e:
            logger.error(f"Error checking developer mode: {e}")
            return ImageProcessingResult(
                success=False,
                description=None,
                error_message=f"Error verifying developer mode permissions: {e}",
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
        self._ensure_client_initialized()

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
        assert (
            self.client is not None
        )  # Type guard: _ensure_client_initialized guarantees this

        # Get model name from configuration
        gemini_config = self.api_config.get_gemini_config()
        model_id = gemini_config.get("model_name", "gemini-1.5-pro")

        response = self.client.models.generate_content(
            model=model_id,
            contents=contents,
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
