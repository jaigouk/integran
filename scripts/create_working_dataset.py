#!/usr/bin/env python3
"""Create a working dataset with available images and placeholders for missing ones.

This creates a functional questions.json that can be improved incrementally.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_image_questions(questions: List[Dict[str, Any]]) -> Dict[int, str]:
    """Detect image questions and categorize them."""
    image_questions = {}
    
    for q in questions:
        question_id = q.get("id", 0)
        options = [
            q.get("option_a", ""),
            q.get("option_b", ""),
            q.get("option_c", ""),
            q.get("option_d", "")
        ]
        
        # Count options that contain "Bild"
        bild_count = sum(1 for opt in options if "Bild" in str(opt))
        
        if bild_count >= 2:
            page_num = q.get("page_number", 0)
            image_questions[question_id] = f"page_{page_num}"
            logger.info(f"Detected image question: Q{question_id} on page {page_num}")
    
    return image_questions


def get_available_images() -> Dict[int, List[str]]:
    """Map available image files to page numbers."""
    images_dir = Path("data/images")
    page_images = {}
    
    if not images_dir.exists():
        return page_images
    
    for img_file in images_dir.glob("page_*_img_*"):
        try:
            page_num = int(img_file.stem.split('_')[1])
            if page_num not in page_images:
                page_images[page_num] = []
            page_images[page_num].append(f"images/{img_file.name}")
        except (ValueError, IndexError):
            continue
    
    return page_images


def create_image_mapping(image_questions: Dict[int, str], available_images: Dict[int, List[str]]) -> Dict[int, List[Dict[str, str]]]:
    """Create comprehensive image mapping."""
    mapping = {}
    
    for question_id, page_info in image_questions.items():
        page_num = int(page_info.split('_')[1])
        
        if page_num in available_images:
            # Use real images
            mapping[question_id] = [
                {
                    "path": img_path,
                    "description": f"Image for question {question_id} from page {page_num}",
                    "context": "Extracted from official exam PDF"
                }
                for img_path in available_images[page_num]
            ]
            logger.info(f"✓ Q{question_id}: Mapped {len(available_images[page_num])} real images")
        else:
            # Create placeholder for missing images
            mapping[question_id] = [
                {
                    "path": f"images/page_{page_num}_img_placeholder.png",
                    "description": f"Placeholder image for question {question_id} on page {page_num}",
                    "context": "⚠️ Missing: Image not extracted from PDF yet"
                }
            ]
            logger.warning(f"⚠️ Q{question_id}: Created placeholder for missing page {page_num}")
    
    return mapping


def create_working_dataset():
    """Create working dataset with available images and placeholders."""
    logger.info("Creating working dataset from extraction checkpoint...")
    
    # Load extraction checkpoint
    checkpoint_path = Path("data/extraction_checkpoint.json")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Extraction checkpoint not found: {checkpoint_path}")
    
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        extraction_data = json.load(f)
    
    questions = extraction_data.get("questions", [])
    logger.info(f"Loaded {len(questions)} questions from extraction checkpoint")
    
    # Detect image questions
    image_questions = detect_image_questions(questions)
    logger.info(f"Detected {len(image_questions)} image questions")
    
    # Get available images
    available_images = get_available_images()
    available_pages = len(available_images)
    total_image_files = sum(len(imgs) for imgs in available_images.values())
    logger.info(f"Found {total_image_files} image files across {available_pages} pages")
    
    # Create image mapping (real + placeholders)
    image_mapping = create_image_mapping(image_questions, available_images)
    
    # Convert to new format
    output_questions = []
    real_image_count = 0
    placeholder_count = 0
    
    for q in questions:
        question_id = q.get("id", 0)
        
        # Create options array
        options = [
            q.get("option_a", ""),
            q.get("option_b", ""),
            q.get("option_c", ""),
            q.get("option_d", "")
        ]
        
        # Convert letter answer to actual text
        correct_letter = q.get("correct_answer", "A")
        correct_mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
        correct_index = correct_mapping.get(correct_letter, 0)
        correct_text = options[correct_index] if correct_index < len(options) else options[0]
        
        # Standard question fields
        output_q = {
            "id": question_id,
            "question": q.get("question", ""),
            "options": options,
            "correct": correct_text,
            "category": q.get("category", "General"),
            "difficulty": q.get("difficulty", "medium"),
            "question_type": q.get("question_type", "general"),
            "state": q.get("state"),
            "page_number": q.get("page_number")
        }
        
        # Add images if this is an image question
        if question_id in image_mapping:
            output_q["images"] = image_mapping[question_id]
            
            # Count real vs placeholder images
            if any("placeholder" in img["path"] for img in image_mapping[question_id]):
                placeholder_count += 1
            else:
                real_image_count += 1
        
        # Add basic English-only answers for now
        output_q["answers"] = {
            "en": {
                "explanation": f"Explanation for question {question_id} - to be enhanced with AI",
                "why_others_wrong": {
                    "A": "Analysis pending",
                    "B": "Analysis pending", 
                    "C": "Analysis pending",
                    "D": "Analysis pending"
                },
                "key_concept": "German integration test concept",
                "mnemonic": "Memory aid to be added"
            }
        }
        
        output_questions.append(output_q)
    
    # Save to questions.json
    output_path = Path("data/questions.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_questions, f, ensure_ascii=False, indent=2)
    
    # Report results
    logger.info("=" * 60)
    logger.info("WORKING DATASET CREATED")
    logger.info("=" * 60)
    logger.info(f"✓ Total questions: {len(output_questions)}")
    logger.info(f"✓ Image questions: {len(image_questions)}")
    logger.info(f"✓ With real images: {real_image_count}")
    logger.info(f"⚠️ With placeholders: {placeholder_count}")
    logger.info(f"✓ Available image files: {total_image_files}")
    logger.info(f"✓ Saved to: {output_path}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Extract missing images from PDF pages")
    logger.info("2. Generate AI descriptions for real images")
    logger.info("3. Add multilingual answers")
    logger.info("4. Replace placeholders with real images")
    
    return True


if __name__ == "__main__":
    create_working_dataset()