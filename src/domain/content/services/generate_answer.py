"""Domain service for generating multilingual answers."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from src.domain.content.events.content_events import (
    AnswerGeneratedEvent,
    ContentGenerationFailedEvent,
)
from src.domain.content.models.answer_models import (
    AnswerGenerationRequest,
    AnswerGenerationResult,
    MultilingualAnswer,
)
from src.domain.shared.configuration import APIConfigurationInterface
from src.domain.shared.services import DomainService, EventBusInterface

try:
    from google import genai
    from google.genai import types

    from src.domain.shared.repositories import UserRepository
    from src.domain.user.models.user_models import LoadUserSettingsRequest
    from src.domain.user.services.load_user_settings import LoadUserSettings

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)


class GenerateAnswer(DomainService[AnswerGenerationRequest, AnswerGenerationResult]):
    """Domain service for generating multilingual answers with explanations."""

    def __init__(
        self,
        event_bus: EventBusInterface,
        api_config: APIConfigurationInterface,
        user_repository: UserRepository | None = None,
    ):
        """Initialize the answer generation service."""
        super().__init__(event_bus)
        self.api_config = api_config
        self.client: Any | None = None  # Initialize lazily when needed

        # User settings repository for developer mode validation
        self.user_repository = user_repository
        self._load_user_settings: LoadUserSettings | None = None

        logger.debug(
            "GenerateAnswer service initialized (credentials will be checked when used)"
        )

    def _ensure_client_initialized(self) -> None:
        """Initialize the Gemini client if not already done."""
        if self.client is not None:
            return

        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for answer generation. "
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

    async def call(self, request: AnswerGenerationRequest) -> AnswerGenerationResult:
        """Generate multilingual answer with explanations."""
        if not self.api_config.is_gemini_available():
            return AnswerGenerationResult(
                success=False,
                answer=None,
                error_message="Gemini API not configured. Please set up authentication.",
            )

        # Check developer mode before using Gemini API
        developer_mode_result = await self._check_developer_mode()
        if not developer_mode_result.success:
            return AnswerGenerationResult(
                success=False,
                answer=None,
                error_message=developer_mode_result.error_message,
            )

        start_time = time.time()
        logger.info(
            f"Generating multilingual answer for question {request.question_id}"
        )

        try:
            # Create comprehensive prompt
            prompt = self._create_multilingual_prompt(request)

            # Generate multilingual response
            response = await self._call_gemini_api_async(prompt)

            # Parse and structure the response
            answer = self._parse_multilingual_response(response, request)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Publish success event
            await self.event_bus.publish(
                AnswerGeneratedEvent(
                    question_id=request.question_id,
                    language_count=len(answer.explanations),
                    has_images=request.images is not None,
                    has_mnemonic=answer.mnemonic is not None,
                    generation_time_ms=processing_time_ms,
                )
            )

            logger.info(
                f"Successfully generated multilingual answer for question {request.question_id}"
            )
            return AnswerGenerationResult(success=True, answer=answer)

        except Exception as e:
            logger.error(
                f"Failed to generate answer for question {request.question_id}: {e}"
            )

            # Publish failure event
            await self.event_bus.publish(
                ContentGenerationFailedEvent(
                    operation_type="answer_generation",
                    entity_id=str(request.question_id),
                    error_message=str(e),
                    retry_count=0,
                )
            )

            return AnswerGenerationResult(
                success=False,
                answer=None,
                error_message=str(e),
            )

    async def _check_developer_mode(self) -> AnswerGenerationResult:
        """Check if developer mode is enabled for API usage.

        Returns:
            AnswerGenerationResult with success=True if developer mode enabled,
            otherwise error result with user-friendly message.
        """
        try:
            # Initialize LoadUserSettings service if needed
            if self._load_user_settings is None:
                if self.user_repository is None:
                    return AnswerGenerationResult(
                        success=False,
                        answer=None,
                        error_message="User settings not available. Cannot verify developer mode permissions.",
                    )
                self._load_user_settings = LoadUserSettings(
                    self.event_bus, self.user_repository
                )

            # Load user settings to check developer mode
            load_request = LoadUserSettingsRequest(user_id=1)  # Default user ID
            load_result = await self._load_user_settings.call(load_request)

            if not load_result.success or not load_result.user_settings:
                return AnswerGenerationResult(
                    success=False,
                    answer=None,
                    error_message="Unable to load user settings. Cannot verify developer mode permissions.",
                )

            # Check if developer mode is enabled
            if not load_result.user_settings.developer_mode.enabled:
                return AnswerGenerationResult(
                    success=False,
                    answer=None,
                    error_message=(
                        "Developer mode is required for AI-powered answer generation. "
                        "Please enable developer mode in settings to use this feature. "
                        "Note: This feature uses external APIs and may incur costs."
                    ),
                )

            # Developer mode is enabled
            return AnswerGenerationResult(success=True, answer=None)

        except Exception as e:
            logger.error(f"Error checking developer mode: {e}")
            return AnswerGenerationResult(
                success=False,
                answer=None,
                error_message=f"Error verifying developer mode permissions: {e}",
            )

    def _create_multilingual_prompt(self, request: AnswerGenerationRequest) -> str:
        """Create a comprehensive prompt for multilingual answer generation."""
        prompt = f"""You are an expert teacher for the German Integration Exam (Leben in Deutschland Test).
Your task is to create comprehensive, multilingual explanations for exam questions.

QUESTION DETAILS:
Question: {request.question_text}
Options: {json.dumps(request.options, ensure_ascii=False)}
Correct Answer: {request.correct_answer}
Category: {request.category}

"""

        # Add image context if available
        if request.images:
            prompt += "IMAGE CONTEXT:\n"
            for i, img in enumerate(request.images, 1):
                prompt += f"Image {i}: {img.description}\n"
                prompt += f"Visual Elements: {', '.join(img.visual_elements)}\n"
                prompt += f"Context: {img.context}\n"
                prompt += f"Relevance: {img.question_relevance}\n\n"

        prompt += """REQUIREMENTS:
1. Generate explanations in 5 languages: English (primary), German, Turkish, Ukrainian, Arabic
2. Explain WHY the correct answer is right with specific facts and legal basis
3. For each WRONG option, explain WHY IT'S WRONG by referencing the specific content of that option
4. Be SPECIFIC about what makes each option incorrect (not generic statements)
5. Provide key concepts and legal/historical context
6. Create helpful mnemonics where appropriate
7. Use simple, clear language appropriate for exam preparation
8. Reference specific German laws, articles, dates, or facts when relevant

CRITICAL: For "why_others_wrong", you MUST analyze the actual text of each wrong option and explain what specifically makes it incorrect. Do NOT use generic phrases like "does not align with German law". Instead, explain the specific factual or legal error in each option.

IMPORTANT: Keep explanations concise but specific. Focus on quality over quantity to avoid response truncation.

RESPONSE FORMAT (JSON):
{
  "explanations": {
    "en": "Clear explanation in English why this answer is correct, with specific facts...",
    "de": "Klare Erklärung auf Deutsch warum diese Antwort richtig ist, mit spezifischen Fakten...",
    "tr": "Bu cevabın neden doğru olduğuna dair Türkçe açıklama, spesifik gerçeklerle...",
    "uk": "Чітке пояснення українською, чому ця відповідь правильна, зі специфічними фактами...",
    "ar": "شرح واضح باللغة العربية لماذا هذه الإجابة صحيحة، مع حقائق محددة..."
  },
  "why_others_wrong": {
    "en": {"B": "Option B '[actual option text]' is incorrect because [specific reason]", "C": "Option C '[actual text]' is wrong because [specific factual error]", "D": "..."},
    "de": {"B": "Option B '[aktueller Optionstext]' ist falsch, weil [spezifischer Grund]", "C": "...", "D": "..."},
    "tr": {"B": "B seçeneği '[gerçek seçenek metni]' yanlış çünkü [spesifik neden]", "C": "...", "D": "..."},
    "uk": {"B": "Варіант B '[фактичний текст варіанту]' неправильний, тому що [конкретна причина]", "C": "...", "D": "..."},
    "ar": {"B": "الخيار B '[النص الفعلي للخيار]' خاطئ لأن [السبب المحدد]", "C": "...", "D": "..."}
  },
  "key_concept": {
    "en": "Main concept to remember",
    "de": "Hauptkonzept zum Merken",
    "tr": "Hatırlanması gereken ana kavram",
    "uk": "Основна концепція для запам'ятовування",
    "ar": "المفهوم الرئيسي للتذكر"
  },
  "mnemonic": {
    "en": "Memory aid or trick",
    "de": "Merkhilfe oder Trick",
    "tr": "Hafıza yardımcısı veya ipucu",
    "uk": "Мнемонічний прийом або підказка",
    "ar": "مساعد الذاكرة أو الحيلة"
  }
}

Generate the multilingual explanation now:"""

        return prompt

    async def _call_gemini_api_async(self, prompt: str) -> str:
        """Make async API call to Gemini with retry logic."""
        # Note: Current Gemini SDK doesn't support true async, so we simulate it
        # In a real async implementation, you would use an async client
        return await self._simulate_async_api_call(prompt)

    async def _simulate_async_api_call(self, prompt: str) -> str:
        """Simulate async API call (wrapper around sync call)."""
        self._ensure_client_initialized()

        # Prepare the request
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[text_part])]

        # Configure generation with higher token limit
        generate_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,  # Balanced for accuracy and creativity
            max_output_tokens=8192,  # Increased for multilingual responses
        )

        # Make API call with retry logic
        max_retries = 3
        retry_delay = 30

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Generating multilingual answer (attempt {attempt + 1}/{max_retries})"
                )

                if attempt > 0:
                    time.sleep(2)  # Wait between retries

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

                response_text = response.text.strip() if response.text else ""

                # Check for truncated response (common issue)
                if response_text and not response_text.endswith("}"):
                    logger.warning(
                        f"Response appears truncated (length: {len(response_text)})"
                    )
                    if attempt < max_retries - 1:
                        logger.info("Retrying due to truncated response...")
                        continue

                return response_text

            except Exception as e:
                if "overloaded" in str(e).lower() or "unavailable" in str(e).lower():
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

        return ""

    def _parse_multilingual_response(
        self,
        response_text: str,
        request: AnswerGenerationRequest,
    ) -> MultilingualAnswer:
        """Parse the API response into a structured multilingual answer."""
        # Clean up response text
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)

            # Create image context summary
            image_context = None
            if request.images:
                image_summaries = [img.description for img in request.images]
                image_context = " | ".join(image_summaries)

            return MultilingualAnswer(
                question_id=request.question_id,
                correct_answer=request.correct_answer,
                explanations=result.get("explanations", {}),
                why_others_wrong=result.get("why_others_wrong", {}),
                key_concept=result.get("key_concept", {}),
                mnemonic=result.get("mnemonic"),
                image_context=image_context,
                rag_sources=[],  # Empty since RAG was removed
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse multilingual response: {e}")

            # Create fallback response
            return MultilingualAnswer(
                question_id=request.question_id,
                correct_answer=request.correct_answer,
                explanations={
                    "en": "Unable to generate explanation",
                    "de": "Erklärung konnte nicht generiert werden",
                    "tr": "Açıklama oluşturulamadı",
                    "uk": "Не вдалося створити пояснення",
                    "ar": "تعذر إنشاء الشرح",
                },
                why_others_wrong={},
                key_concept={},
                mnemonic=None,
                image_context=None,
                rag_sources=[],
            )
