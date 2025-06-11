#!/usr/bin/env python3
"""
Generate Multilingual Explanations

This script generates comprehensive multilingual explanations (EN, DE, TR, UK, AR) 
for all questions in the German Integration Exam dataset, including:
- Detailed explanations for correct answers
- "Why others wrong" explanations for each incorrect option
- Key concepts and mnemonics for better learning
- Proper handling of different image question types
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import base64

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.settings import get_settings
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultilingualExplanationGenerator:
    """Generate comprehensive multilingual explanations for exam questions."""
    
    def __init__(self):
        """Initialize with Gemini client for content generation."""
        settings = get_settings()
        
        # Use Vertex AI client with service account credentials
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region
        )
        self.model_id = "gemini-1.5-pro"
        
    def load_image_as_base64(self, image_path: Path) -> str:
        """Load image file as base64 string."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            raise
    
    def generate_text_only_explanation(self, question_data: Dict) -> Optional[Dict]:
        """Generate explanation for text-only questions (no images)."""
        question_id = question_data.get('id')
        question_text = question_data.get('question', '')
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct', '')
        correct_letter = question_data.get('correct_answer_letter', '')
        category = question_data.get('category', '')
        
        logger.info(f"Generating explanations for text question {question_id}")
        
        try:
            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

Generate detailed explanations in 5 languages (English, German, Turkish, Ukrainian, Arabic) that help learners understand:
1. WHY the correct answer is right (with cultural/legal context)
2. WHY each incorrect option is wrong (specific reasons)
3. KEY CONCEPT that this question tests
4. MNEMONIC device to remember the answer

Respond in JSON format:
{{
    "explanations": {{
        "en": "Detailed explanation of why {correct_answer} is correct, including background context...",
        "de": "Detaillierte Erklärung auf Deutsch...",
        "tr": "Türkçe detaylı açıklama...",
        "uk": "Детальне пояснення українською...",
        "ar": "شرح مفصل باللغة العربية..."
    }},
    "why_others_wrong": {{
        "en": {{
            "A": "Explanation of why option A is wrong...",
            "B": "Explanation of why option B is wrong...",
            "C": "Explanation of why option C is wrong...",
            "D": "Explanation of why option D is wrong..."
        }},
        "de": {{
            "A": "Erklärung warum Option A falsch ist...",
            "B": "Erklärung warum Option B falsch ist...",
            "C": "Erklärung warum Option C falsch ist...",
            "D": "Erklärung warum Option D falsch ist..."
        }},
        "tr": {{
            "A": "A seçeneği neden yanlış...",
            "B": "B seçeneği neden yanlış...",
            "C": "C seçeneği neden yanlış...",
            "D": "D seçeneği neden yanlış..."
        }},
        "uk": {{
            "A": "Пояснення чому варіант A неправильний...",
            "B": "Пояснення чому варіант B неправильний...",
            "C": "Пояснення чому варіант C неправильний...",
            "D": "Пояснення чому варіант D неправильний..."
        }},
        "ar": {{
            "A": "توضيح لماذا الخيار A خاطئ...",
            "B": "توضيح لماذا الخيار B خاطئ...",
            "C": "توضيح لماذا الخيار C خاطئ...",
            "D": "توضيح لماذا الخيار D خاطئ..."
        }}
    }},
    "key_concept": {{
        "en": "Core concept this question tests (1-2 sentences)...",
        "de": "Kernkonzept dieser Frage...",
        "tr": "Bu sorunun test ettiği temel kavram...",
        "uk": "Основна концепція цього питання...",
        "ar": "المفهوم الأساسي لهذا السؤال..."
    }},
    "mnemonic": {{
        "en": "Memory device to remember this answer...",
        "de": "Gedächtnisstütze für diese Antwort...",
        "tr": "Bu cevabı hatırlamak için hafıza yardımcısı...",
        "uk": "Мнемонічний прийом для запам'ятовування...",
        "ar": "وسيلة تذكر للإجابة..."
    }}
}}

Note: Skip the correct answer letter from why_others_wrong explanations."""
            
            # Create text content
            contents = [types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )]
            
            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192
            )
            
            # Make request
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Remove the correct answer from why_others_wrong
            if 'why_others_wrong' in result:
                for lang in result['why_others_wrong']:
                    if correct_letter in result['why_others_wrong'][lang]:
                        del result['why_others_wrong'][lang][correct_letter]
            
            logger.info(f"Q{question_id}: Generated text-only explanations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate explanation for question {question_id}: {e}")
            return None
    
    def generate_single_image_explanation(self, question_data: Dict, images_dir: Path) -> Optional[Dict]:
        """Generate explanation for questions with 1 image (may contain marked options)."""
        question_id = question_data.get('id')
        question_text = question_data.get('question', '')
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct', '')
        correct_letter = question_data.get('correct_answer_letter', '')
        category = question_data.get('category', '')
        
        # Find the image file
        image_path = images_dir / f"q{question_id}_1.png"
        if not image_path.exists():
            logger.warning(f"Image not found for question {question_id}: {image_path}")
            return self.generate_text_only_explanation(question_data)
        
        logger.info(f"Generating explanations for single-image question {question_id}")
        
        try:
            # Load image
            image_base64 = self.load_image_as_base64(image_path)
            
            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

IMPORTANT: Analyze the provided image carefully. The image may:
- Show marked/highlighted options corresponding to A, B, C, D
- Contain visual elements that directly relate to the correct answer
- Provide context that explains why the correct answer is right

Generate detailed explanations in 5 languages that reference the visual content when relevant.

Respond in JSON format with the same structure as text-only questions, but include visual references in explanations where appropriate:
{{
    "explanations": {{
        "en": "Based on the image, {correct_answer} is correct because...",
        "de": "Basierend auf dem Bild ist {correct_answer} richtig, weil...",
        "tr": "Görsel temelinde {correct_answer} doğrudur çünkü...",
        "uk": "На основі зображення {correct_answer} правильна, тому що...",
        "ar": "بناءً على الصورة، {correct_answer} صحيح لأن..."
    }},
    "why_others_wrong": {{
        // Same multilingual structure, referencing image when relevant
    }},
    "key_concept": {{
        // Same multilingual structure
    }},
    "mnemonic": {{
        // Same multilingual structure
    }},
    "image_description": "Detailed description of what the image shows and how it relates to the question"
}}"""
            
            # Create image part
            image_part = types.Part.from_bytes(
                data=base64.b64decode(image_base64),
                mime_type="image/png"
            )
            
            # Create text part
            text_part = types.Part.from_text(text=prompt)
            
            # Create content
            contents = [types.Content(
                role="user",
                parts=[text_part, image_part]
            )]
            
            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192
            )
            
            # Make request
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Remove the correct answer from why_others_wrong
            if 'why_others_wrong' in result:
                for lang in result['why_others_wrong']:
                    if correct_letter in result['why_others_wrong'][lang]:
                        del result['why_others_wrong'][lang][correct_letter]
            
            logger.info(f"Q{question_id}: Generated single-image explanations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate explanation for question {question_id}: {e}")
            return None
    
    def generate_multiple_image_explanation(self, question_data: Dict, images_dir: Path) -> Optional[Dict]:
        """Generate explanation for questions with 4 images (one per option)."""
        question_id = question_data.get('id')
        question_text = question_data.get('question', '')
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct', '')
        correct_letter = question_data.get('correct_answer_letter', '')
        category = question_data.get('category', '')
        
        # Find all image files for this question
        image_paths = []
        for i in range(1, 5):
            image_path = images_dir / f"q{question_id}_{i}.png"
            if image_path.exists():
                image_paths.append(image_path)
        
        if len(image_paths) != 4:
            logger.warning(f"Expected 4 images for question {question_id}, found {len(image_paths)}")
            return self.generate_text_only_explanation(question_data)
        
        logger.info(f"Generating explanations for multiple-image question {question_id}")
        
        try:
            # Load all images
            image_parts = []
            for i, image_path in enumerate(image_paths):
                image_base64 = self.load_image_as_base64(image_path)
                image_part = types.Part.from_bytes(
                    data=base64.b64decode(image_base64),
                    mime_type="image/png"
                )
                image_parts.append(image_part)
            
            prompt = f"""Generate comprehensive multilingual explanations for German Integration Exam question {question_id}.

Question: {question_text}

Options:
A) {options[0]} (Image 1)
B) {options[1]} (Image 2)
C) {options[2]} (Image 3)
D) {options[3]} (Image 4)

Correct Answer: {correct_answer} (Letter: {correct_letter})
Category: {category}

IMPORTANT: Analyze all 4 provided images carefully. Each image corresponds to an option:
- Image 1 = Option A: {options[0]}
- Image 2 = Option B: {options[1]}
- Image 3 = Option C: {options[2]}
- Image 4 = Option D: {options[3]}

Generate detailed explanations that describe what each image shows and explain why the correct image/option is right while others are wrong.

Respond in JSON format:
{{
    "explanations": {{
        "en": "Image {correct_letter} correctly shows {correct_answer} because...",
        "de": "Bild {correct_letter} zeigt korrekt {correct_answer} weil...",
        "tr": "Resim {correct_letter} doğru bir şekilde {correct_answer} gösteriyor çünkü...",
        "uk": "Зображення {correct_letter} правильно показує {correct_answer} тому що...",
        "ar": "الصورة {correct_letter} تُظهر بشكل صحيح {correct_answer} لأن..."
    }},
    "why_others_wrong": {{
        "en": {{
            "A": "Image 1 shows... which is incorrect because...",
            "B": "Image 2 shows... which is incorrect because...",
            "C": "Image 3 shows... which is incorrect because...",
            "D": "Image 4 shows... which is incorrect because..."
        }},
        // Same for other languages
    }},
    "key_concept": {{
        // Same multilingual structure
    }},
    "mnemonic": {{
        // Same multilingual structure  
    }},
    "image_descriptions": [
        "Description of what Image 1 (Option A) shows",
        "Description of what Image 2 (Option B) shows", 
        "Description of what Image 3 (Option C) shows",
        "Description of what Image 4 (Option D) shows"
    ]
}}"""
            
            # Create text part
            text_part = types.Part.from_text(text=prompt)
            
            # Create content with all images
            all_parts = [text_part] + image_parts
            contents = [types.Content(
                role="user",
                parts=all_parts
            )]
            
            # Configure generation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192
            )
            
            # Make request
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Remove the correct answer from why_others_wrong
            if 'why_others_wrong' in result:
                for lang in result['why_others_wrong']:
                    if correct_letter in result['why_others_wrong'][lang]:
                        del result['why_others_wrong'][lang][correct_letter]
            
            logger.info(f"Q{question_id}: Generated multiple-image explanations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate explanation for question {question_id}: {e}")
            return None


class DatasetEnhancer:
    """Enhance dataset with comprehensive multilingual explanations."""
    
    def __init__(self, dataset_path: Path, images_dir: Path):
        self.dataset_path = dataset_path
        self.images_dir = images_dir
        self.generator = MultilingualExplanationGenerator()
        self.dataset = self._load_dataset()
        
    def _load_dataset(self) -> Dict:
        """Load the step2 dataset."""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded dataset with {len(data.get('questions', {}))} questions")
            return data
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def determine_question_type(self, question_data: Dict) -> str:
        """Determine the type of question based on images."""
        if not question_data.get('is_image_question', False):
            return "text_only"
        
        question_id = question_data.get('id')
        
        # Check for multiple images (4 images = one per option)
        multiple_images = all(
            (self.images_dir / f"q{question_id}_{i}.png").exists() 
            for i in range(1, 5)
        )
        
        if multiple_images:
            return "multiple_images"
        
        # Check for single image
        single_image = (self.images_dir / f"q{question_id}_1.png").exists()
        
        if single_image:
            return "single_image"
        
        logger.warning(f"No images found for question {question_id}, treating as text-only")
        return "text_only"
    
    def enhance_question(self, question_data: Dict) -> Dict:
        """Enhance a single question with multilingual explanations."""
        question_id = question_data.get('id')
        question_type = self.determine_question_type(question_data)
        
        logger.info(f"Processing question {question_id} (type: {question_type})")
        
        # Generate explanations based on question type
        if question_type == "multiple_images":
            explanations = self.generator.generate_multiple_image_explanation(question_data, self.images_dir)
        elif question_type == "single_image":
            explanations = self.generator.generate_single_image_explanation(question_data, self.images_dir)
        else:  # text_only
            explanations = self.generator.generate_text_only_explanation(question_data)
        
        if not explanations:
            logger.error(f"Failed to generate explanations for question {question_id}")
            return question_data
        
        # Create enhanced question
        enhanced_question = question_data.copy()
        
        # Add generated content
        enhanced_question.update({
            'explanations': explanations.get('explanations', {}),
            'why_others_wrong': explanations.get('why_others_wrong', {}),
            'key_concept': explanations.get('key_concept', {}),
            'mnemonic': explanations.get('mnemonic', {}),
        })
        
        # Add image descriptions if available
        if 'image_description' in explanations:
            enhanced_question['image_description'] = explanations['image_description']
        if 'image_descriptions' in explanations:
            enhanced_question['image_descriptions'] = explanations['image_descriptions']
        
        return enhanced_question
    
    def enhance_all_questions(self) -> Dict:
        """Enhance all questions with multilingual explanations."""
        enhanced_dataset = {
            "questions": {},
            "metadata": self.dataset.get('metadata', {}).copy()
        }
        
        # Update metadata
        enhanced_dataset["metadata"]["step"] = "step3_multilingual_explanations"
        enhanced_dataset["metadata"]["description"] = "Complete dataset with multilingual explanations, mnemonics, and key concepts"
        enhanced_dataset["metadata"]["languages"] = ["en", "de", "tr", "uk", "ar"]
        
        total_questions = len(self.dataset.get('questions', {}))
        processed = 0
        failed = 0
        
        for q_id_str, question_data in self.dataset.get('questions', {}).items():
            try:
                enhanced_question = self.enhance_question(question_data)
                enhanced_dataset["questions"][q_id_str] = enhanced_question
                processed += 1
                
                # Add delay to avoid rate limits
                time.sleep(2)
                
                if processed % 10 == 0:
                    logger.info(f"Progress: {processed}/{total_questions} questions processed")
                
            except Exception as e:
                logger.error(f"Failed to process question {q_id_str}: {e}")
                enhanced_dataset["questions"][q_id_str] = question_data  # Keep original
                failed += 1
                continue
        
        # Update metadata with results
        enhanced_dataset["metadata"]["processing_results"] = {
            "total_questions": total_questions,
            "successfully_processed": processed,
            "failed": failed,
            "success_rate": round((processed / total_questions) * 100, 1) if total_questions > 0 else 0
        }
        
        logger.info(f"Enhancement complete: {processed}/{total_questions} questions processed successfully")
        return enhanced_dataset


def main():
    """Main function to generate multilingual explanations."""
    # File paths
    input_dataset_path = Path("data/step2_answers_fixed.json")
    output_dataset_path = Path("data/final_dataset.json")
    images_dir = Path("data/images")
    
    # Validate inputs
    if not input_dataset_path.exists():
        logger.error(f"Input dataset not found: {input_dataset_path}")
        return 1
    
    # Initialize enhancer
    enhancer = DatasetEnhancer(input_dataset_path, images_dir)
    
    # Generate explanations for all questions
    logger.info("Starting multilingual explanation generation...")
    enhanced_dataset = enhancer.enhance_all_questions()
    
    # Save results
    logger.info(f"Saving enhanced dataset to {output_dataset_path}")
    with open(output_dataset_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_dataset, f, ensure_ascii=False, indent=2)
    
    # Print summary
    results = enhanced_dataset["metadata"]["processing_results"]
    logger.info("=" * 60)
    logger.info("STEP 3 MULTILINGUAL EXPLANATION GENERATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total questions: {results['total_questions']}")
    logger.info(f"Successfully processed: {results['successfully_processed']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Success rate: {results['success_rate']}%")
    logger.info(f"Languages: English, German, Turkish, Ukrainian, Arabic")
    logger.info(f"Output file: {output_dataset_path}")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())