"""Multilingual answer generation engine for German Integration Exam questions."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from src.core.image_processor import ImageDescription
from src.core.settings import get_settings, has_gemini_config

# RAG functionality removed as it was not used in final dataset generation

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
class MultilingualAnswer:
    """Multilingual answer with explanations in multiple languages."""

    question_id: int
    correct_answer: str
    explanations: dict[
        str, str
    ]  # {"en": "...", "de": "...", "tr": "...", "uk": "...", "ar": "..."}
    why_others_wrong: dict[str, dict[str, str]]  # Per language
    key_concept: dict[str, str]  # Per language
    mnemonic: dict[str, str] | None  # Per language
    image_context: str | None  # If question has images
    rag_sources: list[str]  # Sources used from RAG


class AnswerEngine:
    """Generate multilingual answers with explanations."""

    def __init__(self) -> None:
        """Initialize the answer engine."""
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for answer generation. "
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

        # RAG engine removed as it was not used in final dataset generation

    def generate_answer_with_explanation(
        self,
        question: dict[str, Any],
        images: list[ImageDescription] | None = None,
    ) -> MultilingualAnswer:
        """Generate a complete multilingual answer with explanations."""
        if not has_gemini_config():
            raise ValueError("Gemini API not configured. Please set up authentication.")

        # Create comprehensive prompt (RAG removed as not used in final dataset)
        prompt = self._create_multilingual_prompt(question, images)

        # Generate multilingual response
        response = self._call_gemini_api(prompt)

        # Parse and structure the response
        return self._parse_multilingual_response(response, question, images)

    def _create_multilingual_prompt(
        self,
        question: dict[str, Any],
        images: list[ImageDescription] | None,
    ) -> str:
        """Create a comprehensive prompt for multilingual answer generation."""
        question_text = question.get("question", "")
        options = {
            "A": question.get("option_a", ""),
            "B": question.get("option_b", ""),
            "C": question.get("option_c", ""),
            "D": question.get("option_d", ""),
        }
        correct_answer = question.get("correct_answer", "")
        category = question.get("category", "")

        prompt = f"""You are an expert teacher for the German Integration Exam (Leben in Deutschland Test).
Your task is to create comprehensive, multilingual explanations for exam questions.

QUESTION DETAILS:
Question: {question_text}
Options: {json.dumps(options, ensure_ascii=False)}
Correct Answer: {correct_answer}
Category: {category}

"""

        # Add image context if available
        if images:
            prompt += "IMAGE CONTEXT:\n"
            for i, img in enumerate(images, 1):
                prompt += f"Image {i}: {img.description}\n"
                prompt += f"Visual Elements: {', '.join(img.visual_elements)}\n"
                prompt += f"Context: {img.context}\n"
                prompt += f"Relevance: {img.question_relevance}\n\n"

        # RAG context removed as it was not used in final dataset generation

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

    def _call_gemini_api(self, prompt: str) -> str:
        """Make API call to Gemini with retry logic."""
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

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,  # type: ignore[arg-type]
                    config=generate_config,
                )

                response_text = response.text.strip() if response.text else ""

                # Check for truncated response (common issue)
                if response_text and not response_text.endswith("}"):
                    logger.warning(
                        f"Response appears truncated (length: {len(response_text)})"
                    )
                    logger.warning(f"Response ends with: ...{response_text[-50:]}")
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
        question: dict[str, Any],
        images: list[ImageDescription] | None,
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
            if images:
                image_summaries = [img.description for img in images]
                image_context = " | ".join(image_summaries)

            return MultilingualAnswer(
                question_id=question.get("id", 0),
                correct_answer=question.get("correct_answer", ""),
                explanations=result.get("explanations", {}),
                why_others_wrong=result.get("why_others_wrong", {}),
                key_concept=result.get("key_concept", {}),
                mnemonic=result.get("mnemonic"),
                image_context=image_context,
                rag_sources=[],  # Empty since RAG was removed
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse multilingual response: {e}")
            logger.error(f"Response length: {len(response_text)}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}")
            logger.error(f"Response text (last 100 chars): ...{response_text[-100:]}")

            # Check if this looks like a truncated JSON
            if (
                response_text
                and "{" in response_text
                and response_text.count("{") > response_text.count("}")
            ):
                logger.error("Response appears to be truncated JSON (unmatched braces)")

            # Create fallback response
            return MultilingualAnswer(
                question_id=question.get("id", 0),
                correct_answer=question.get("correct_answer", ""),
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
                rag_sources=[],  # Empty since RAG was removed
            )

    def generate_batch_answers(
        self,
        questions: list[dict[str, Any]],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
    ) -> list[MultilingualAnswer]:
        """Generate answers for a batch of questions."""
        answers = []

        for question in questions:
            question_id = question.get("id", 0)

            # Get images for this question
            images = None
            if question_id in question_image_mapping:
                image_paths = question_image_mapping[question_id]
                images = [
                    image_descriptions[path]
                    for path in image_paths
                    if path in image_descriptions
                ]

            try:
                answer = self.generate_answer_with_explanation(
                    question=question, images=images
                )
                answers.append(answer)
                logger.info(f"Generated multilingual answer for question {question_id}")

                # Throttle API calls
                time.sleep(1)

            except Exception as e:
                logger.error(
                    f"Failed to generate answer for question {question_id}: {e}"
                )
                continue

        return answers
