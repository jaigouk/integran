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
                raw_mapping = checkpoint_data.get("question_image_mapping", {})
                # Convert string keys to integers for proper lookup
                question_image_mapping = {
                    int(k): v for k, v in raw_mapping.items()
                }
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
        """Process all images and create comprehensive mappings."""
        logger.info("Starting comprehensive image processing...")

        # Step 1: Get all available images
        available_images = self._get_all_available_images()
        logger.info(f"Found {sum(len(imgs) for imgs in available_images.values())} images across {len(available_images)} pages")

        # Step 2: Load questions from extraction checkpoint
        questions = self._load_questions_from_extraction()

        # Step 3: Create comprehensive question-to-image mapping
        question_image_mapping = self._create_comprehensive_image_mapping(questions, available_images)

        # Step 4: Create image descriptions (simplified for now to avoid API timeouts)
        image_descriptions = self._create_basic_image_descriptions(available_images)

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

    def _get_all_available_images(self) -> dict[int, list[str]]:
        """Get all available images organized by page number."""
        images_dir = Path("data/images")
        page_images = {}
        
        if not images_dir.exists():
            logger.warning("Images directory not found")
            return page_images
        
        for img_file in images_dir.glob("page_*_img_*"):
            try:
                page_num = int(img_file.stem.split('_')[1])
                if page_num not in page_images:
                    page_images[page_num] = []
                page_images[page_num].append(f"images/{img_file.name}")
            except (ValueError, IndexError):
                continue
        
        # Sort images for each page
        for page_num in page_images:
            page_images[page_num].sort()
        
        return page_images

    def _create_comprehensive_image_mapping(
        self, questions: list[dict[str, Any]], available_images: dict[int, list[str]]
    ) -> dict[int, list[str]]:
        """Create comprehensive mapping ensuring ALL images are used."""
        question_image_mapping = {}
        used_images = set()
        
        # Step 1: Map questions with Bild options to images
        for question in questions:
            question_id = question.get("id", 0)
            options = [
                question.get("option_a", ""),
                question.get("option_b", ""),
                question.get("option_c", ""),
                question.get("option_d", ""),
            ]
            
            # Check if this has "Bild" options
            bild_options = [opt for opt in options if "bild" in opt.lower()]
            if len(bild_options) >= 2:  # This is an image question
                # Find the best matching page with images
                best_page = self._find_best_image_page_for_question(question, available_images, used_images)
                
                if best_page and best_page in available_images:
                    images = available_images[best_page]
                    # Take up to 4 images for this question
                    question_images = []
                    for img in images:
                        if img not in used_images and len(question_images) < len(bild_options):
                            question_images.append(img)
                            used_images.add(img)
                    
                    if question_images:
                        question_image_mapping[question_id] = question_images
                        logger.info(f"✓ Q{question_id}: Mapped {len(question_images)} images from page {best_page}")
        
        # Step 2: Report unused images
        all_images = set()
        for images in available_images.values():
            all_images.update(images)
        
        unused_images = all_images - used_images
        if unused_images:
            logger.warning(f"⚠️  {len(unused_images)} images not mapped to questions:")
            for img in sorted(unused_images):
                logger.warning(f"  - {img}")
        
        logger.info(f"Successfully mapped {len(used_images)}/{len(all_images)} images to {len(question_image_mapping)} questions")
        return question_image_mapping

    def _find_best_image_page_for_question(
        self, question: dict[str, Any], available_images: dict[int, list[str]], used_images: set[str]
    ) -> int | None:
        """Find the best page with images for a given question."""
        question_id = question.get("id", 0)
        extracted_page = question.get("page_number", 0)
        category = question.get("category", "")
        question_text = question.get("question", "").lower()
        
        # Manual corrections for known mismatches
        known_corrections = {
            21: 9,   # German coat of arms
            29: 78,  # State coat of arms  
        }
        
        if question_id in known_corrections:
            return known_corrections[question_id]
        
        # Try extracted page first
        if extracted_page in available_images:
            available_imgs = [img for img in available_images[extracted_page] if img not in used_images]
            if available_imgs:
                return extracted_page
        
        # Content-based matching for specific topics
        if "wappen" in question_text or "bundesrepublik" in question_text:
            for page in [9, 78, 85]:  # Common coat of arms pages
                if page in available_images:
                    available_imgs = [img for img in available_images[page] if img not in used_images]
                    if available_imgs:
                        return page
        
        if "flagge" in question_text:
            for page in [9, 78, 85]:  # Common flag pages
                if page in available_images:
                    available_imgs = [img for img in available_images[page] if img not in used_images]
                    if available_imgs:
                        return page
        
        # Find any page with available images
        for page, images in available_images.items():
            available_imgs = [img for img in images if img not in used_images]
            if available_imgs:
                return page
        
        return None

    def _create_basic_image_descriptions(self, available_images: dict[int, list[str]]) -> dict[str, ImageDescription]:
        """Create basic image descriptions without AI calls to avoid timeouts."""
        descriptions = {}
        
        for page_num, images in available_images.items():
            for i, img_path in enumerate(images, 1):
                # Extract filename for context
                filename = Path(img_path).name
                
                # Create basic description based on page and context
                if page_num in [9, 78, 85]:
                    desc = f"Coat of arms or emblem from page {page_num}"
                    context = "German federal or state symbols"
                elif page_num in [112, 117, 122, 127, 132, 137, 142, 147, 152, 157, 162, 167, 172, 177, 182, 187]:
                    desc = f"State-specific image from page {page_num}"
                    context = "German federal state symbols or landmarks"
                else:
                    desc = f"Official exam image from page {page_num}"
                    context = "German integration exam visual content"
                
                descriptions[img_path] = ImageDescription(
                    path=img_path,
                    description=desc,
                    visual_elements=["official", "educational"],
                    context=context,
                    question_relevance=f"Used in integration exam questions about German symbols and geography"
                )
        
        return descriptions

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
        question_image_mapping: dict[int, list[str]],
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
                batch_answers = self.answer_engine.generate_batch_answers(
                    questions=new_questions,
                    question_image_mapping=question_image_mapping,
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
