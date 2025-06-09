"""Unified data pipeline builder for German Integration Exam dataset."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.answer_engine import AnswerEngine, MultilingualAnswer
from src.core.image_processor import ImageDescription, ImageProcessor
from src.core.settings import has_gemini_config

logger = logging.getLogger(__name__)


class DataBuilder:
    """Build complete dataset from extraction checkpoint."""

    def __init__(self) -> None:
        """Initialize the data builder."""
        self.image_processor = ImageProcessor()
        self.answer_engine = AnswerEngine()
        self.checkpoint_file = Path("data/dataset_checkpoint.json")

    def build_complete_dataset(
        self,
        force_rebuild: bool = False,
        use_rag: bool = True,
        multilingual: bool = True,
        batch_size: int = 10,
    ) -> bool:
        """Build the complete multilingual dataset with image mappings."""
        if not has_gemini_config():
            raise ValueError("Gemini API not configured. Please set up authentication.")

        try:
            # Load or create checkpoint
            checkpoint_data = self._load_checkpoint(force_rebuild)

            # Step 1: Load questions from extraction checkpoint
            questions = self._load_questions_from_extraction()
            checkpoint_data["total_questions"] = len(questions)
            logger.info(f"Loaded {len(questions)} questions from extraction checkpoint")

            # Step 2: Process images and create mappings
            if not checkpoint_data.get("images_processed", False):
                logger.info("Processing images and creating mappings...")
                question_image_mapping, image_descriptions = self._process_images(
                    checkpoint_data
                )
                checkpoint_data["images_processed"] = True
                self._save_checkpoint(checkpoint_data)
            else:
                logger.info("Loading existing image mappings...")
                question_image_mapping = checkpoint_data.get(
                    "question_image_mapping", {}
                )
                image_descriptions = self._load_image_descriptions(checkpoint_data)

            # Step 3: Generate multilingual answers with RAG
            if multilingual:
                answers = self._generate_multilingual_answers(
                    questions=questions,
                    question_image_mapping=question_image_mapping,
                    image_descriptions=image_descriptions,
                    checkpoint_data=checkpoint_data,
                    use_rag=use_rag,
                    batch_size=batch_size,
                )
            else:
                # Skip multilingual generation for testing
                answers = []

            # Step 4: Save to final questions.json format
            self._save_final_dataset(
                questions, answers, question_image_mapping, image_descriptions
            )

            # Mark as completed
            checkpoint_data["state"] = "completed"
            checkpoint_data["completed_at"] = datetime.now(UTC).isoformat()
            self._save_checkpoint(checkpoint_data)

            logger.info("✓ Successfully built complete multilingual dataset")
            return True

        except Exception as e:
            logger.error(f"Failed to build dataset: {e}")
            return False

    def _load_checkpoint(self, force_rebuild: bool) -> dict[str, Any]:
        """Load existing checkpoint or create new one."""
        if force_rebuild or not self.checkpoint_file.exists():
            return {
                "state": "in_progress",
                "started_at": datetime.now(UTC).isoformat(),
                "images_processed": False,
                "completed_answers": {},
                "total_questions": 0,
                "question_image_mapping": {},
                "image_descriptions": {},
            }

        with open(self.checkpoint_file) as f:
            return json.load(f)

    def _save_checkpoint(self, checkpoint_data: dict[str, Any]) -> None:
        """Save checkpoint to disk."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    def _load_questions_from_extraction(self) -> list[dict[str, Any]]:
        """Load questions from extraction checkpoint."""
        extraction_path = Path("data/extraction_checkpoint.json")
        if not extraction_path.exists():
            raise FileNotFoundError("Extraction checkpoint not found")

        with open(extraction_path) as f:
            data = json.load(f)

        if data.get("state") != "completed":
            raise ValueError("Extraction checkpoint is not completed")

        return data.get("questions", [])

    def _process_images(
        self, checkpoint_data: dict[str, Any]
    ) -> tuple[dict[int, list[str]], dict[str, ImageDescription]]:
        """Process all images and create mappings."""
        logger.info("Starting image processing...")

        # Use ImageProcessor to analyze and describe images
        question_image_mapping, image_descriptions = (
            self.image_processor.process_all_images()
        )

        # Save to checkpoint
        checkpoint_data["question_image_mapping"] = {
            str(k): v for k, v in question_image_mapping.items()
        }
        checkpoint_data["image_descriptions"] = {
            path: {
                "path": desc.path,
                "description": desc.description,
                "visual_elements": desc.visual_elements,
                "context": desc.context,
                "question_relevance": desc.question_relevance,
            }
            for path, desc in image_descriptions.items()
        }

        logger.info(f"Processed {len(image_descriptions)} images")
        logger.info(f"Created mappings for {len(question_image_mapping)} questions")

        return question_image_mapping, image_descriptions

    def _load_image_descriptions(
        self, checkpoint_data: dict[str, Any]
    ) -> dict[str, ImageDescription]:
        """Load image descriptions from checkpoint."""
        descriptions = {}
        for path, data in checkpoint_data.get("image_descriptions", {}).items():
            descriptions[path] = ImageDescription(
                path=data["path"],
                description=data["description"],
                visual_elements=data["visual_elements"],
                context=data["context"],
                question_relevance=data["question_relevance"],
            )
        return descriptions

    def _generate_multilingual_answers(
        self,
        questions: list[dict[str, Any]],
        _question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
        checkpoint_data: dict[str, Any],
        use_rag: bool,
        batch_size: int,
    ) -> list[MultilingualAnswer]:
        """Generate multilingual answers for all questions."""
        logger.info("Starting multilingual answer generation...")

        completed_answers = checkpoint_data.get("completed_answers", {})
        all_answers = []

        # Process questions in batches
        for i in range(0, len(questions), batch_size):
            batch = questions[i : i + batch_size]

            # Filter out already completed questions
            new_questions = [
                q for q in batch if str(q.get("id", 0)) not in completed_answers
            ]

            if not new_questions:
                logger.info(f"Skipping batch {i // batch_size + 1} (all completed)")
                # Load existing answers
                for q in batch:
                    qid = str(q.get("id", 0))
                    if qid in completed_answers:
                        all_answers.append(
                            self._deserialize_answer(completed_answers[qid])
                        )
                continue

            logger.info(
                f"Processing batch {i // batch_size + 1}: {len(new_questions)} new questions"
            )

            try:
                # Convert string keys back to int for mapping lookup
                int_mapping = {
                    int(k): v
                    for k, v in checkpoint_data["question_image_mapping"].items()
                }

                batch_answers = self.answer_engine.generate_batch_answers(
                    questions=new_questions,
                    question_image_mapping=int_mapping,
                    image_descriptions=image_descriptions,
                    use_rag=use_rag,
                )

                # Save answers to checkpoint
                for answer in batch_answers:
                    completed_answers[str(answer.question_id)] = self._serialize_answer(
                        answer
                    )
                    all_answers.append(answer)

                checkpoint_data["completed_answers"] = completed_answers
                self._save_checkpoint(checkpoint_data)

                logger.info(
                    f"Completed batch {i // batch_size + 1}: {len(batch_answers)} answers generated"
                )

            except Exception as e:
                logger.error(f"Failed to process batch {i // batch_size + 1}: {e}")
                continue

        logger.info(f"Generated {len(all_answers)} multilingual answers")
        return all_answers

    def _serialize_answer(self, answer: MultilingualAnswer) -> dict[str, Any]:
        """Serialize MultilingualAnswer for checkpoint storage."""
        return {
            "question_id": answer.question_id,
            "correct_answer": answer.correct_answer,
            "explanations": answer.explanations,
            "why_others_wrong": answer.why_others_wrong,
            "key_concept": answer.key_concept,
            "mnemonic": answer.mnemonic,
            "image_context": answer.image_context,
            "rag_sources": answer.rag_sources,
        }

    def _deserialize_answer(self, data: dict[str, Any]) -> MultilingualAnswer:
        """Deserialize checkpoint data back to MultilingualAnswer."""
        return MultilingualAnswer(
            question_id=data["question_id"],
            correct_answer=data["correct_answer"],
            explanations=data["explanations"],
            why_others_wrong=data["why_others_wrong"],
            key_concept=data["key_concept"],
            mnemonic=data["mnemonic"],
            image_context=data["image_context"],
            rag_sources=data["rag_sources"],
        )

    def _save_final_dataset(
        self,
        questions: list[dict[str, Any]],
        answers: list[MultilingualAnswer],
        question_image_mapping: dict[int, list[str]],
        image_descriptions: dict[str, ImageDescription],
    ) -> None:
        """Save the final questions.json dataset."""
        output_file = Path("data/questions.json")

        # Create answer lookup
        answer_lookup = {answer.question_id: answer for answer in answers}

        # Build final dataset
        final_questions = []

        for question in questions:
            question_id = question.get("id", 0)

            # Convert extraction format to final format
            final_question = {
                "id": question_id,
                "question": question.get("question", ""),
                "options": [
                    question.get("option_a", ""),
                    question.get("option_b", ""),
                    question.get("option_c", ""),
                    question.get("option_d", ""),
                ],
                "correct": question.get("correct_answer", ""),
                "category": question.get("category", ""),
                "difficulty": question.get("difficulty", "medium"),
            }

            # Add images if available
            if question_id in question_image_mapping:
                image_paths = question_image_mapping[question_id]
                final_question["images"] = []

                for path in image_paths:
                    if path in image_descriptions:
                        desc = image_descriptions[path]
                        final_question["images"].append(
                            {
                                "path": path.replace("data/", ""),  # Relative path
                                "description": desc.description,
                                "context": desc.context,
                            }
                        )

            # Add multilingual answers if available
            if question_id in answer_lookup:
                answer = answer_lookup[question_id]
                final_question["answers"] = {
                    "en": {
                        "explanation": answer.explanations.get("en", ""),
                        "why_others_wrong": answer.why_others_wrong.get("en", {}),
                        "key_concept": answer.key_concept.get("en", ""),
                        "mnemonic": answer.mnemonic.get("en", "")
                        if answer.mnemonic
                        else "",
                    },
                    "de": {
                        "explanation": answer.explanations.get("de", ""),
                        "why_others_wrong": answer.why_others_wrong.get("de", {}),
                        "key_concept": answer.key_concept.get("de", ""),
                        "mnemonic": answer.mnemonic.get("de", "")
                        if answer.mnemonic
                        else "",
                    },
                    "tr": {
                        "explanation": answer.explanations.get("tr", ""),
                        "why_others_wrong": answer.why_others_wrong.get("tr", {}),
                        "key_concept": answer.key_concept.get("tr", ""),
                        "mnemonic": answer.mnemonic.get("tr", "")
                        if answer.mnemonic
                        else "",
                    },
                    "uk": {
                        "explanation": answer.explanations.get("uk", ""),
                        "why_others_wrong": answer.why_others_wrong.get("uk", {}),
                        "key_concept": answer.key_concept.get("uk", ""),
                        "mnemonic": answer.mnemonic.get("uk", "")
                        if answer.mnemonic
                        else "",
                    },
                    "ar": {
                        "explanation": answer.explanations.get("ar", ""),
                        "why_others_wrong": answer.why_others_wrong.get("ar", {}),
                        "key_concept": answer.key_concept.get("ar", ""),
                        "mnemonic": answer.mnemonic.get("ar", "")
                        if answer.mnemonic
                        else "",
                    },
                }

                if answer.rag_sources:
                    final_question["rag_sources"] = answer.rag_sources

            final_questions.append(final_question)

        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_questions, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(final_questions)} questions to {output_file}")

    def get_build_status(self) -> dict[str, Any]:
        """Get current build status."""
        if not self.checkpoint_file.exists():
            return {"state": "not_started"}

        with open(self.checkpoint_file) as f:
            checkpoint = json.load(f)

        completed_count = len(checkpoint.get("completed_answers", {}))
        total_count = checkpoint.get("total_questions", 0)

        return {
            "state": checkpoint.get("state", "unknown"),
            "started_at": checkpoint.get("started_at"),
            "completed_at": checkpoint.get("completed_at"),
            "images_processed": checkpoint.get("images_processed", False),
            "completed_answers": completed_count,
            "total_questions": total_count,
            "progress_percent": (completed_count / total_count * 100)
            if total_count > 0
            else 0,
        }
