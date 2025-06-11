#!/usr/bin/env python3
"""
Update Dataset with Extracted Images

This script updates the direct_extraction.json dataset with the actual extracted image paths
and creates step1_images_extracted.json with proper image mappings.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def scan_extracted_images(images_dir: Path) -> Dict[int, List[str]]:
    """Scan the images directory and map question IDs to their image paths."""
    if not images_dir.exists():
        logger.error(f"Images directory not found: {images_dir}")
        return {}
    
    image_mapping = {}
    
    # Find all image files with pattern q{id}_{num}.png
    for image_file in images_dir.glob("q*.png"):
        try:
            # Parse filename: q21_1.png -> question_id=21, image_num=1
            stem = image_file.stem  # "q21_1"
            if not stem.startswith('q'):
                continue
                
            parts = stem[1:].split('_')  # ["21", "1"]
            if len(parts) != 2:
                continue
                
            question_id = int(parts[0])
            image_num = int(parts[1])
            
            if question_id not in image_mapping:
                image_mapping[question_id] = []
            
            # Store relative path from project root
            relative_path = f"data/images/{image_file.name}"
            image_mapping[question_id].append((image_num, relative_path))
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse image filename {image_file.name}: {e}")
            continue
    
    # Sort images by number for each question
    for question_id in image_mapping:
        image_mapping[question_id].sort(key=lambda x: x[0])  # Sort by image_num
        image_mapping[question_id] = [path for _, path in image_mapping[question_id]]
    
    logger.info(f"Found images for {len(image_mapping)} questions")
    return image_mapping


def update_question_images(question_data: Dict, extracted_images: Dict[int, List[str]]) -> Dict:
    """Update a single question's image data with extracted image paths."""
    question_id = question_data.get('id')
    if not question_id or not question_data.get('is_image_question', False):
        return question_data
    
    if question_id not in extracted_images:
        logger.warning(f"No extracted images found for question {question_id}")
        return question_data
    
    # Get extracted image paths
    image_paths = extracted_images[question_id]
    
    # Update images array with actual paths and existing descriptions
    updated_images = []
    existing_images = question_data.get('images', [])
    
    for i, image_path in enumerate(image_paths):
        # Try to preserve existing description and context if available
        if i < len(existing_images):
            existing_image = existing_images[i]
            updated_image = {
                "path": image_path,
                "description": existing_image.get('description', f"Image {i+1} for question {question_id}"),
                "context": existing_image.get('context', f"Image option {i+1}")
            }
        else:
            # Create new image entry if no existing data
            updated_image = {
                "path": image_path,
                "description": f"Image {i+1} for question {question_id}",
                "context": f"Image option {i+1}"
            }
        
        updated_images.append(updated_image)
    
    # Update the question data
    question_data['images'] = updated_images
    
    logger.debug(f"Updated question {question_id} with {len(updated_images)} images")
    return question_data


def create_step1_dataset(input_dataset: Dict, extracted_images: Dict[int, List[str]]) -> Dict:
    """Create the step1 dataset with updated image paths."""
    output_dataset = {
        "questions": {},
        "metadata": input_dataset.get("metadata", {}).copy()
    }
    
    # Update metadata
    output_dataset["metadata"]["step"] = "step1_images_extracted"
    output_dataset["metadata"]["description"] = "Dataset with extracted image paths added"
    output_dataset["metadata"]["extracted_images_count"] = sum(len(paths) for paths in extracted_images.values())
    output_dataset["metadata"]["image_questions_count"] = len(extracted_images)
    
    # Process all questions
    questions_updated = 0
    for question_id_str, question_data in input_dataset.get("questions", {}).items():
        # Update question with extracted images
        updated_question = update_question_images(question_data.copy(), extracted_images)
        output_dataset["questions"][question_id_str] = updated_question
        
        if updated_question.get('is_image_question', False) and updated_question.get('images'):
            questions_updated += 1
    
    logger.info(f"Updated {questions_updated} image questions with extracted image paths")
    return output_dataset


def main():
    """Main function to update dataset with extracted images."""
    # File paths
    input_dataset_path = Path("data/direct_extraction.json")
    output_dataset_path = Path("data/step1_images_extracted.json")
    images_dir = Path("data/images")
    
    # Validate inputs
    if not input_dataset_path.exists():
        logger.error(f"Input dataset not found: {input_dataset_path}")
        return 1
    
    if not images_dir.exists():
        logger.error(f"Images directory not found: {images_dir}")
        return 1
    
    # Load original dataset
    logger.info(f"Loading dataset from {input_dataset_path}")
    with open(input_dataset_path, 'r', encoding='utf-8') as f:
        input_dataset = json.load(f)
    
    logger.info(f"Loaded dataset with {len(input_dataset.get('questions', {}))} questions")
    
    # Scan extracted images
    logger.info(f"Scanning extracted images in {images_dir}")
    extracted_images = scan_extracted_images(images_dir)
    
    if not extracted_images:
        logger.error("No extracted images found")
        return 1
    
    # Create updated dataset
    logger.info("Creating step1 dataset with image paths")
    step1_dataset = create_step1_dataset(input_dataset, extracted_images)
    
    # Save step1 dataset
    logger.info(f"Saving step1 dataset to {output_dataset_path}")
    with open(output_dataset_path, 'w', encoding='utf-8') as f:
        json.dump(step1_dataset, f, ensure_ascii=False, indent=2)
    
    # Print summary
    total_questions = len(step1_dataset["questions"])
    image_questions = len([q for q in step1_dataset["questions"].values() if q.get('is_image_question', False)])
    total_images = sum(len(q.get('images', [])) for q in step1_dataset["questions"].values())
    
    logger.info("=" * 50)
    logger.info("STEP 1 EXTRACTION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total questions: {total_questions}")
    logger.info(f"Image questions: {image_questions}")
    logger.info(f"Total images extracted: {total_images}")
    logger.info(f"Output file: {output_dataset_path}")
    logger.info("=" * 50)
    
    # Show some examples
    logger.info("Example image questions:")
    count = 0
    for q_id, q_data in step1_dataset["questions"].items():
        if q_data.get('is_image_question', False) and q_data.get('images'):
            logger.info(f"  Q{q_id}: {len(q_data['images'])} images")
            count += 1
            if count >= 5:
                break
    
    return 0


if __name__ == "__main__":
    sys.exit(main())