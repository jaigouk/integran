#!/usr/bin/env python3
"""Pre-flight check for dataset generation.

Verifies all prerequisites are met before starting the expensive dataset generation.
"""

import json
import sys
from pathlib import Path
from typing import Tuple, List


def check_extraction_checkpoint() -> Tuple[bool, str]:
    """Check if extraction checkpoint exists and is complete."""
    checkpoint_path = Path("data/extraction_checkpoint.json")
    
    if not checkpoint_path.exists():
        return False, f"❌ Extraction checkpoint not found: {checkpoint_path}"
        
    try:
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        state = data.get("state", "unknown")
        questions = data.get("questions", [])
        
        if state != "completed":
            return False, f"❌ Extraction not completed. State: {state}"
            
        if len(questions) != 460:
            return False, f"❌ Expected 460 questions, found {len(questions)}"
            
        # Count image questions
        image_questions = 0
        for q in questions:
            options = [q.get(f"option_{x}", "") for x in ['a', 'b', 'c', 'd']]
            if any("Bild" in opt for opt in options):
                image_questions += 1
                
        return True, f"✅ Extraction checkpoint valid: 460 questions ({image_questions} with images)"
        
    except Exception as e:
        return False, f"❌ Failed to load extraction checkpoint: {e}"


def check_images() -> Tuple[bool, str]:
    """Check if images are extracted."""
    images_dir = Path("data/images")
    
    if not images_dir.exists():
        return False, f"❌ Images directory not found: {images_dir}"
        
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpeg"))
    
    if len(image_files) == 0:
        return False, "❌ No images found in data/images/"
        
    # Check for specific pages we know have images
    critical_pages = [9, 78, 85, 112, 117, 122, 127, 132, 137, 142, 147, 152, 157, 162, 167, 172, 177, 182, 187]
    found_pages = set()
    
    for img in image_files:
        # Extract page number from filename (e.g., page_9_img_1.png)
        if img.stem.startswith("page_"):
            try:
                page_num = int(img.stem.split('_')[1])
                found_pages.add(page_num)
            except:
                pass
                
    missing_pages = set(critical_pages) - found_pages
    
    if missing_pages:
        return False, f"❌ Missing images from critical pages: {sorted(missing_pages)}"
        
    return True, f"✅ Found {len(image_files)} images covering {len(found_pages)} pages"


def check_api_configuration() -> Tuple[bool, str]:
    """Check if Gemini API is configured."""
    try:
        from src.core.answer_engine import has_gemini_config
        
        if not has_gemini_config():
            return False, "❌ Gemini API not configured (check environment variables)"
            
        from src.core.settings import get_settings
        settings = get_settings()
        
        return True, f"✅ Gemini API configured (Project: {settings.gcp_project_id})"
        
    except Exception as e:
        return False, f"❌ Failed to check API configuration: {e}"


def check_rag_system() -> Tuple[bool, str]:
    """Check if RAG system is available."""
    try:
        vector_store_path = Path("data/vector_store")
        
        if not vector_store_path.exists():
            return False, "⚠️  RAG vector store not found (optional)"
            
        # Check if ChromaDB has data
        sqlite_path = vector_store_path / "chroma.sqlite3"
        if sqlite_path.exists():
            return True, "✅ RAG system available with vector store"
        else:
            return False, "⚠️  RAG vector store empty (optional)"
            
    except Exception as e:
        return False, f"⚠️  Failed to check RAG system: {e}"


def estimate_cost() -> str:
    """Estimate the cost of dataset generation."""
    # Rough estimates based on Gemini pricing
    image_descriptions = 57  # Number of images
    multilingual_answers = 460 * 5  # 460 questions * 5 languages
    
    # Assume ~500 tokens per request, ~1000 tokens per response
    total_requests = image_descriptions + (multilingual_answers // 10)  # Batch of 10
    
    # Rough cost estimate (varies by model and region)
    cost_per_1k_tokens = 0.00025  # Example rate
    estimated_tokens = total_requests * 1500  # Input + output
    estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens
    
    return f"💰 Estimated cost: ${estimated_cost:.2f} - ${estimated_cost * 3:.2f} (varies by usage)"


def main():
    """Run all pre-flight checks."""
    print("🚀 INTEGRAN DATASET GENERATION - PRE-FLIGHT CHECK")
    print("=" * 60)
    
    checks: List[Tuple[str, Tuple[bool, str]]] = [
        ("Extraction Checkpoint", check_extraction_checkpoint()),
        ("Image Files", check_images()),
        ("API Configuration", check_api_configuration()),
        ("RAG System", check_rag_system()),
    ]
    
    all_required_pass = True
    
    for name, (success, message) in checks:
        print(f"\n{name}:")
        print(f"  {message}")
        
        # Only API and extraction are required
        if not success and name in ["Extraction Checkpoint", "Image Files", "API Configuration"]:
            all_required_pass = False
    
    print(f"\n{estimate_cost()}")
    
    print("\n" + "=" * 60)
    if all_required_pass:
        print("✅ ALL REQUIRED CHECKS PASSED - Ready to generate dataset!")
        print("\nNext command:")
        print("  integran-build-dataset --verbose --use-rag --multilingual")
        return 0
    else:
        print("❌ PRE-FLIGHT CHECK FAILED - Please fix issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())