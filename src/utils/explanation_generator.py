"""Generate explanations for exam questions using Gemini AI with checkpoint support."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.settings import get_settings, has_gemini_config

try:
    from src.knowledge_base.rag_engine import RAGEngine

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGEngine = None

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)


class QuestionExplanation(BaseModel):
    """Model for a question with explanation."""

    question_id: int = Field(description="The question ID")
    question_text: str = Field(description="The question text")
    correct_answer: str = Field(description="The correct answer text")
    explanation: str = Field(
        description="Clear, easy-to-understand explanation in German that covers all options"
    )
    why_others_wrong: dict[str, str] = Field(
        description="Brief explanation for why each other option is incorrect"
    )
    key_concept: str = Field(description="The main concept or rule to remember")
    mnemonic: str | None = Field(
        None, description="Optional memory aid or trick to remember the answer"
    )


class ExplanationBatch(BaseModel):
    """Model for a batch of explanations."""

    explanations: list[QuestionExplanation] = Field(
        description="List of question explanations"
    )


class ExplanationGenerator:
    """Generate explanations for questions using Gemini AI."""

    def __init__(self) -> None:
        """Initialize the explanation generator."""
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is required for explanation generation. "
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

        # Load contextual knowledge
        self.knowledge_base = self._load_knowledge_base()

        # Initialize RAG engine if available
        self.rag_engine = None
        if RAG_AVAILABLE:
            try:
                self.rag_engine = RAGEngine()
                logger.info("RAG engine initialized for enhanced explanations")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG engine: {e}")
                self.rag_engine = None

    def _load_knowledge_base(self) -> dict[str, str]:
        """Load contextual knowledge for better explanations."""
        return {
            "grundgesetz": """
Das Grundgesetz (GG) ist die Verfassung der Bundesrepublik Deutschland:
- Artikel 1: Menschenwürde ist unantastbar
- Artikel 2: Recht auf freie Entfaltung der Persönlichkeit
- Artikel 3: Gleichberechtigung, Diskriminierungsverbot
- Artikel 4: Glaubens-, Gewissens- und Bekenntnisfreiheit
- Artikel 5: Meinungsfreiheit, Pressefreiheit
- Artikel 8: Versammlungsfreiheit
- Artikel 12: Berufsfreiheit
- Artikel 14: Eigentumsgarantie
- Artikel 16: Asylrecht
- Artikel 20: Demokratie, Rechtsstaat, Sozialstaat, Bundesstaat
            """,
            "political_system": """
Deutsches politisches System:
- Gewaltenteilung: Legislative (Bundestag/Bundesrat), Exekutive (Regierung), Judikative (Gerichte)
- Föderalismus: 16 Bundesländer mit eigenen Kompetenzen
- Bundesorgane: Bundestag, Bundesrat, Bundespräsident, Bundesregierung, Bundesverfassungsgericht
- Wahlsystem: Verhältniswahlrecht mit 5%-Hürde
- Kanzlerdemokratie: Bundeskanzler führt die Regierung
            """,
            "history": """
Wichtige Daten der deutschen Geschichte:
- 1933-1945: NS-Zeit und Zweiter Weltkrieg
- 1949: Gründung BRD und DDR, Verkündung Grundgesetz (23. Mai)
- 1961-1989: Berliner Mauer (Bau: 13. August 1961, Fall: 9. November 1989)
- 1990: Deutsche Wiedervereinigung (3. Oktober - Tag der Deutschen Einheit)
- 1957: Römische Verträge (EWG-Gründung)
- 1989: Friedliche Revolution in der DDR
            """,
            "federal_states": """
16 Bundesländer Deutschlands:
- Stadtstaaten: Berlin, Bremen, Hamburg
- Flächenstaaten: Baden-Württemberg (Stuttgart), Bayern (München), Brandenburg (Potsdam),
  Hessen (Wiesbaden), Mecklenburg-Vorpommern (Schwerin), Niedersachsen (Hannover),
  Nordrhein-Westfalen (Düsseldorf), Rheinland-Pfalz (Mainz), Saarland (Saarbrücken),
  Sachsen (Dresden), Sachsen-Anhalt (Magdeburg), Schleswig-Holstein (Kiel), Thüringen (Erfurt)
            """,
            "symbols": """
Deutsche Staatssymbole:
- Bundesflagge: Schwarz-Rot-Gold (waagerechte Streifen)
- Bundeswappen: Schwarzer Adler auf gelbem Grund
- Nationalhymne: "Einigkeit und Recht und Freiheit" (3. Strophe des Deutschlandlieds)
- Bundeshauptstadt: Berlin
- Nationalfeiertag: 3. Oktober (Tag der Deutschen Einheit)
            """,
        }

    def _get_relevant_context(self, question: dict[str, Any]) -> str:
        """Get relevant contextual knowledge for a question."""
        question_text = question.get("question", "").lower()
        category = question.get("category", "").lower()

        context_parts = []

        # Add relevant knowledge based on content
        if any(
            term in question_text
            for term in ["grundgesetz", "verfassung", "artikel", "grundrecht"]
        ):
            context_parts.append(self.knowledge_base["grundgesetz"])

        if any(
            term in question_text
            for term in ["bundestag", "bundesrat", "regierung", "kanzler", "präsident"]
        ):
            context_parts.append(self.knowledge_base["political_system"])

        if any(
            term in question_text
            for term in [
                "1933",
                "1945",
                "1949",
                "1961",
                "1989",
                "1990",
                "krieg",
                "mauer",
            ]
        ):
            context_parts.append(self.knowledge_base["history"])

        if any(
            term in question_text
            for term in ["bundesland", "land", "stadt", "hauptstadt"]
        ) or question.get("state"):
            context_parts.append(self.knowledge_base["federal_states"])

        if any(
            term in question_text
            for term in ["flagge", "wappen", "hymne", "farben", "symbol"]
        ):
            context_parts.append(self.knowledge_base["symbols"])

        # Add based on category
        if "politik" in category or "demokratie" in category:
            context_parts.append(self.knowledge_base["political_system"])
        elif "geschichte" in category:
            context_parts.append(self.knowledge_base["history"])
        elif "grundrecht" in category:
            context_parts.append(self.knowledge_base["grundgesetz"])

        return "\n\n".join(context_parts) if context_parts else ""

    def _get_batch_context(self, questions_batch: list[dict[str, Any]]) -> str:
        """Get combined contextual knowledge for a batch of questions."""
        all_context_parts = set()

        for question in questions_batch:
            context = self._get_relevant_context(question)
            if context:
                # Split context sections and add to set (avoid duplicates)
                sections = context.split("\n\n")
                all_context_parts.update(sections)

        return "\n\n".join(sorted(all_context_parts)) if all_context_parts else ""

    def load_questions(self) -> list[dict[str, Any]]:
        """Load questions from extraction checkpoint or JSON file."""
        # Try extraction checkpoint first (it has all 460 questions)
        checkpoint_path = Path("data/extraction_checkpoint.json")
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                data = json.load(f)
                if data.get("state") == "completed":
                    logger.info(
                        f"Loaded {len(data['questions'])} questions from checkpoint"
                    )
                    return data["questions"]

        # Fall back to questions.json if it exists
        json_path = Path("data/questions.json")
        if json_path.exists():
            with open(json_path) as f:
                questions = json.load(f)
                logger.info(f"Loaded {len(questions)} questions from JSON")
                return questions

        raise FileNotFoundError(
            "No questions data found. Please ensure either "
            "data/extraction_checkpoint.json or data/questions.json exists."
        )

    def load_explanation_checkpoint(self, checkpoint_file: Path) -> dict:
        """Load existing checkpoint or create new one."""
        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                return json.load(f)

        return {
            "completed_batches": [],
            "explanations": {},
            "state": "in_progress",
            "started_at": datetime.now(UTC).isoformat(),
            "total_questions": 0,
        }

    def save_explanation_checkpoint(self, checkpoint_file: Path, checkpoint_data: dict):
        """Save checkpoint to disk."""
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    def should_skip_question(self, checkpoint_data: dict, question_id: int) -> bool:
        """Check if question already has an explanation."""
        return str(question_id) in checkpoint_data.get("explanations", {})

    def add_explanations_to_checkpoint(
        self, checkpoint_data: dict, explanations: list[dict[str, Any]]
    ):
        """Add generated explanations to checkpoint."""
        for exp in explanations:
            question_id = exp["question_id"]
            checkpoint_data["explanations"][str(question_id)] = exp

        # Update batch info
        batch_info = {
            "timestamp": datetime.now(UTC).isoformat(),
            "count": len(explanations),
            "question_ids": [exp["question_id"] for exp in explanations],
        }
        checkpoint_data["completed_batches"].append(batch_info)

    def create_explanation_prompt(self, questions_batch: list[dict[str, Any]]) -> str:
        """Create prompt for generating explanations."""
        # Separate image questions from text questions
        image_questions = [
            q for q in questions_batch if q.get("is_image_question", False)
        ]
        text_questions = [
            q for q in questions_batch if not q.get("is_image_question", False)
        ]

        prompt = """Du bist ein erfahrener Lehrer für den deutschen Einbürgerungstest.
Deine Aufgabe ist es, klare und leicht verständliche Erklärungen für die richtigen Antworten zu erstellen.

WICHTIGE ANFORDERUNGEN:
1. Erkläre auf Deutsch in einfacher, klarer Sprache
2. Erkläre WARUM die richtige Antwort richtig ist
3. Erkläre KURZ warum die anderen Optionen falsch sind
4. Berücksichtige, dass in der echten Prüfung die Antwortoptionen vertauscht sein könnten
5. Gib einen Merksatz oder eine Eselsbrücke, falls hilfreich
6. Fokussiere auf das Verständnis des Konzepts, nicht nur auf Auswendiglernen

SPEZIELLE HINWEISE FÜR BILDFRAGEN:
- Bei Fragen mit Bildern (z.B. "Welches Wappen gehört zu..."), erkläre die visuellen Merkmale
- Beschreibe charakteristische Elemente (Farben, Symbole, Formen)
- Gib Tipps zum Erkennen und Unterscheiden der Bilder
- Vermeide zu abstrakte Erklärungen bei visuellen Fragen

KONTEXTWISSEN EINBEZIEHEN:
- Nutze historisches Wissen (wichtige Daten, Ereignisse)
- Verweise auf relevante Gesetze (Grundgesetz-Artikel)
- Erkläre politische Strukturen und Prozesse
- Verbinde mit alltäglichen Beispielen

"""

        # Add contextual knowledge for the batch
        batch_context = self._get_batch_context(questions_batch)
        if batch_context:
            prompt += f"\nRELEVANTES KONTEXTWISSEN FÜR DIESE FRAGEN:\n{batch_context}\n"

        if image_questions:
            prompt += f"\nBILDFRAGEN (besondere Aufmerksamkeit erforderlich):\n{json.dumps(image_questions, ensure_ascii=False, indent=2)}\n"

        if text_questions:
            prompt += f"\nTEXTFRAGEN:\n{json.dumps(text_questions, ensure_ascii=False, indent=2)}\n"

        prompt += (
            "\nErstelle für jede Frage eine Erklärung im JSON-Format gemäß dem Schema."
        )

        return prompt

    def prepare_questions_batch(
        self, questions: list[dict[str, Any]], start_idx: int, batch_size: int
    ) -> list[dict[str, Any]]:
        """Prepare a batch of questions for explanation generation."""
        batch = []
        end_idx = min(start_idx + batch_size, len(questions))

        for i in range(start_idx, end_idx):
            q = questions[i]

            # Handle different formats (checkpoint vs JSON)
            if "option_a" in q:
                # Checkpoint format
                options = {
                    "A": q["option_a"],
                    "B": q["option_b"],
                    "C": q["option_c"],
                    "D": q["option_d"],
                }
                correct_letter = q["correct_answer"]
                correct_text = options[correct_letter]
            else:
                # JSON format
                options = {
                    "A": q["options"][0],
                    "B": q["options"][1],
                    "C": q["options"][2],
                    "D": q["options"][3],
                }
                correct_text = q["correct"]
                # Find correct letter
                correct_letter = "A"
                for letter, text in options.items():
                    if text == correct_text:
                        correct_letter = letter
                        break

            batch.append(
                {
                    "question_id": q["id"],
                    "question_text": q["question"],
                    "options": options,
                    "correct_answer": correct_text,
                    "correct_letter": correct_letter,
                    "category": q.get("category", "Allgemein"),
                }
            )

        return batch

    def generate_explanations_batch_with_rag(
        self, questions_batch: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate explanations using RAG if available, fallback to basic method."""
        if not self.rag_engine:
            logger.info("RAG not available, using basic explanation generation")
            return self.generate_explanations_batch(questions_batch)

        explanations = []
        for question in questions_batch:
            try:
                # Use RAG to generate enhanced explanation
                rag_result = self.rag_engine.generate_explanation_with_rag(
                    question=question["question_text"],
                    correct_answer=question["correct_answer"],
                    options=question["options"],
                    category=question.get("category", ""),
                )

                # Format for checkpoint compatibility
                explanation = {
                    "question_id": question["question_id"],
                    "question_text": question["question_text"],
                    "correct_answer": question["correct_answer"],
                    "explanation": rag_result["explanation"],
                    "why_others_wrong": {},  # RAG explanation includes this context
                    "key_concept": ", ".join(rag_result.get("key_concepts", [])),
                    "mnemonic": None,
                    "context_sources": rag_result.get("context_sources", []),
                    "enhanced_with_rag": rag_result.get("context_used", False),
                }
                explanations.append(explanation)

            except Exception as e:
                logger.error(
                    f"RAG explanation failed for question {question['question_id']}: {e}"
                )
                # Fallback to basic method for this question
                basic_explanations = self.generate_explanations_batch([question])
                if basic_explanations:
                    basic_explanations[0]["enhanced_with_rag"] = False
                    explanations.extend(basic_explanations)

        return explanations

    def generate_explanations_batch(
        self, questions_batch: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate explanations for a batch of questions."""
        prompt = self.create_explanation_prompt(questions_batch)

        # Prepare the request
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[text_part])]

        # Configure generation
        generate_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExplanationBatch.model_json_schema(),
            temperature=0.3,  # Slightly higher for more creative explanations
            max_output_tokens=8192,
        )

        # Make API call with retry logic
        max_retries = 3
        retry_delay = 30

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Generating explanations for {len(questions_batch)} questions "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                if attempt > 0:
                    time.sleep(2)  # Wait between retries

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=generate_config,
                )
                break
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

        # Parse response
        response_text = response.text.strip()

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
            explanations = result.get("explanations", [])

            # Convert to dict format for checkpoint
            return [
                {
                    "question_id": exp["question_id"],
                    "question_text": exp["question_text"],
                    "correct_answer": exp["correct_answer"],
                    "explanation": exp["explanation"],
                    "why_others_wrong": exp["why_others_wrong"],
                    "key_concept": exp["key_concept"],
                    "mnemonic": exp.get("mnemonic"),
                }
                for exp in explanations
            ]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise

    def generate_all_explanations(
        self, batch_size: int = 10, resume: bool = True, use_rag: bool = False
    ) -> tuple[bool, int]:
        """Generate explanations for all questions with checkpoint support."""
        checkpoint_file = Path("data/explanations_checkpoint.json")

        # Load questions
        questions = self.load_questions()
        total_questions = len(questions)
        logger.info(f"Loaded {total_questions} questions")

        # Load or create checkpoint
        if resume and checkpoint_file.exists():
            checkpoint_data = self.load_explanation_checkpoint(checkpoint_file)
            logger.info(
                f"Resuming from checkpoint with {len(checkpoint_data['explanations'])} explanations"
            )
        else:
            checkpoint_data = self.load_explanation_checkpoint(Path("nonexistent"))
            checkpoint_data["total_questions"] = total_questions

        # Process in batches
        generated_count = 0

        for start_idx in range(0, total_questions, batch_size):
            # Check if all questions in batch already have explanations
            batch_questions = self.prepare_questions_batch(
                questions, start_idx, batch_size
            )

            # Filter out questions that already have explanations
            new_questions = [
                q
                for q in batch_questions
                if not self.should_skip_question(checkpoint_data, q["question_id"])
            ]

            if not new_questions:
                logger.info(
                    f"Skipping batch {start_idx}-{start_idx + batch_size} "
                    "(all questions already have explanations)"
                )
                continue

            try:
                # Generate explanations for new questions only
                if use_rag:
                    explanations = self.generate_explanations_batch_with_rag(
                        new_questions
                    )
                else:
                    explanations = self.generate_explanations_batch(new_questions)

                # Add to checkpoint
                self.add_explanations_to_checkpoint(checkpoint_data, explanations)
                self.save_explanation_checkpoint(checkpoint_file, checkpoint_data)

                generated_count += len(explanations)
                total_done = len(checkpoint_data["explanations"])

                logger.info(
                    f"Generated {len(explanations)} explanations. "
                    f"Total: {total_done}/{total_questions}"
                )

                # Throttle API calls
                if start_idx + batch_size < total_questions:
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Failed to generate batch {start_idx}: {e}")
                # Save checkpoint even on error
                self.save_explanation_checkpoint(checkpoint_file, checkpoint_data)
                continue

        # Mark as completed if all questions have explanations
        if len(checkpoint_data["explanations"]) == total_questions:
            checkpoint_data["state"] = "completed"
            checkpoint_data["completed_at"] = datetime.now(UTC).isoformat()
            self.save_explanation_checkpoint(checkpoint_file, checkpoint_data)

            # Save final explanations.json
            self.save_final_explanations(checkpoint_data["explanations"])

            logger.info(f"Successfully generated all {total_questions} explanations")
            return True, generated_count
        else:
            logger.warning(
                f"Incomplete: {len(checkpoint_data['explanations'])}/{total_questions} explanations"
            )
            return False, generated_count

    def save_final_explanations(self, explanations: dict[str, dict]):
        """Save final explanations to JSON file."""
        output_file = Path("data/explanations.json")

        # Convert dict to list sorted by question ID
        explanations_list = []
        for question_id in sorted(explanations.keys(), key=int):
            explanations_list.append(explanations[question_id])

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(explanations_list, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(explanations_list)} explanations to {output_file}")


def generate_explanations_cli(
    batch_size: int = 10,
    resume: bool = True,
    use_rag: bool = False,
) -> bool:
    """CLI entry point for generating explanations."""
    try:
        # Check if Gemini is configured
        if not GENAI_AVAILABLE:
            logger.error("google-genai package not available")
            return False

        if not has_gemini_config():
            logger.error("Gemini API not configured. Please set up authentication.")
            return False

        generator = ExplanationGenerator()
        success, count = generator.generate_all_explanations(
            batch_size=batch_size, resume=resume, use_rag=use_rag
        )

        if success:
            logger.info(f"✓ Successfully generated {count} explanations")
        else:
            logger.warning(f"⚠ Partially complete: generated {count} explanations")

        return success

    except Exception as e:
        logger.error(f"Failed to generate explanations: {e}")
        return False
