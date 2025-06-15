"""Direct Gemini client wrapper without LangChain dependencies."""

import json
import logging
import time
from typing import Any

from src.infrastructure.config.settings import Settings, get_settings

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)


class GeminiClient:
    """Direct wrapper for Google Gemini AI client."""

    def __init__(self, settings: Settings | None = None):
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for Gemini AI. "
                "Install with: pip install google-genai"
            )

        if settings is None:
            settings = get_settings()

        self.settings = settings
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region
        self.model_id = settings.gemini_model
        self.use_vertex_ai = settings.use_vertex_ai

        # Initialize client
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

        logger.info(f"Initialized Gemini client with model: {self.model_id}")

    def generate_text(
        self,
        prompt: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.3,
        max_retries: int = 3,
        retry_delay: int = 30,
    ) -> str:
        """Generate text response from prompt."""

        # Prepare content
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[text_part])]

        # Configure generation
        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        # Generate with retry logic
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating text (attempt {attempt + 1}/{max_retries})")

                if attempt > 0:
                    time.sleep(2)  # Wait between retries

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=generate_config,
                )

                response_text = response.text.strip()
                logger.debug(f"Generated response length: {len(response_text)}")
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
                    logger.error(f"Error generating text: {e}")
                    raise

        raise RuntimeError("Failed to generate text after all retries")

    def generate_json_response(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_output_tokens: int = 8192,
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Generate structured JSON response."""

        # Prepare content
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[text_part])]

        # Configure generation for JSON
        config_kwargs = {
            "response_mime_type": "application/json",
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        if schema:
            config_kwargs["response_schema"] = schema

        generate_config = types.GenerateContentConfig(**config_kwargs)

        # Generate with retry logic
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating JSON (attempt {attempt + 1}/{max_retries})")

                if attempt > 0:
                    time.sleep(2)

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=generate_config,
                )

                response_text = response.text.strip()
                logger.debug(f"JSON response length: {len(response_text)}")

                # Check for truncated JSON response
                if response_text and not response_text.endswith("}"):
                    logger.warning(
                        f"JSON response appears truncated (length: {len(response_text)})"
                    )
                    if attempt < max_retries - 1:
                        logger.info("Retrying due to truncated JSON response...")
                        time.sleep(2)
                        continue

                # Clean up response if needed
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                # Parse JSON
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response text: {response_text[:500]}")
                    if attempt == max_retries - 1:
                        raise
                    continue

            except Exception as e:
                if "overloaded" in str(e).lower() or "unavailable" in str(e).lower():
                    if attempt < max_retries - 1:
                        logger.warning("API overloaded, retrying...")
                        time.sleep(30 * (attempt + 1))
                        continue
                    else:
                        logger.error("API still overloaded after all retries")
                        raise
                else:
                    logger.error(f"Error generating JSON: {e}")
                    if attempt == max_retries - 1:
                        raise
                    continue

        raise RuntimeError("Failed to generate JSON after all retries")

    def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: str | None = None,
        max_output_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Generate response with context (for RAG)."""

        # Build the prompt with context
        prompt = f"{system_prompt}\n\n" if system_prompt else ""

        prompt += f"""Kontext:
{context}

Frage: {query}

Bitte beantworte die Frage basierend auf dem gegebenen Kontext. Gib eine klare, präzise Antwort auf Deutsch."""

        return self.generate_text(
            prompt=prompt, max_output_tokens=max_output_tokens, temperature=temperature
        )

    def summarize_text(
        self, text: str, max_length: int = 500, language: str = "German"
    ) -> str:
        """Summarize a piece of text."""

        prompt = f"""Fasse den folgenden Text in {language} zusammen. Die Zusammenfassung sollte maximal {max_length} Zeichen lang sein und die wichtigsten Punkte enthalten.

Text:
{text}

Zusammenfassung:"""

        return self.generate_text(
            prompt=prompt,
            max_output_tokens=max_length // 2,  # Rough estimate
            temperature=0.2,
        )

    def extract_key_concepts(self, text: str, max_concepts: int = 10) -> list[str]:
        """Extract key concepts from text."""

        prompt = f"""Extrahiere bis zu {max_concepts} wichtige Konzepte oder Schlüsselbegriffe aus dem folgenden Text. Gib sie als Liste zurück, einen Begriff pro Zeile.

Text:
{text}

Wichtige Konzepte:"""

        response = self.generate_text(
            prompt=prompt, max_output_tokens=1024, temperature=0.2
        )

        # Parse the response into a list
        concepts = []
        for line in response.split("\n"):
            line = line.strip()
            # Remove bullets, numbers, etc.
            line = line.lstrip("•-*1234567890. ")
            if line:
                concepts.append(line)

        return concepts[:max_concepts]

    def check_relevance(
        self, query: str, document: str, threshold: float = 0.5
    ) -> bool:
        """Check if a document is relevant to a query."""

        prompt = f"""Bewerte auf einer Skala von 0.0 bis 1.0, wie relevant das folgende Dokument für die gegebene Frage ist.

Frage: {query}

Dokument:
{document}

Gib nur eine Zahl zwischen 0.0 und 1.0 zurück, wobei 1.0 sehr relevant und 0.0 nicht relevant bedeutet.

Relevanz-Score:"""

        try:
            response = self.generate_text(
                prompt=prompt, max_output_tokens=100, temperature=0.1
            )

            # Extract numeric score
            import re

            score_match = re.search(r"(\d+\.\d+|\d+)", response)
            if score_match:
                score = float(score_match.group(1))
                # Normalize if needed
                if score > 1.0:
                    score = score / 10.0  # Handle cases like "8.5" meaning 0.85
                return score >= threshold
            else:
                logger.warning(f"Could not parse relevance score: {response}")
                return False

        except Exception as e:
            logger.error(f"Error checking relevance: {e}")
            return False
