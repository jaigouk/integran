#!/usr/bin/env python3
"""Analyze image pages and create comprehensive mapping strategy."""

import json
from pathlib import Path
from typing import List, Set

def main():
    """Analyze current state and create strategy."""
    
    # Complete list of pages with images (from user)
    expected_pages = {
        21, 27, 48, 64, 67, 70, 78, 81, 85, 88, 115, 117, 120, 122, 125, 127, 
        130, 132, 135, 137, 140, 142, 145, 147, 150, 152, 155, 157, 160, 162, 
        165, 167, 170, 172, 175, 177, 180, 182, 185, 187, 190, 223
    }
    
    # Check which pages we currently have images for
    images_dir = Path("data/images")
    current_pages = set()
    
    if images_dir.exists():
        for img_file in images_dir.glob("page_*_img_*"):
            try:
                page_num = int(img_file.stem.split('_')[1])
                current_pages.add(page_num)
            except (ValueError, IndexError):
                continue
    
    missing_pages = expected_pages - current_pages
    extra_pages = current_pages - expected_pages
    
    print("=== IMAGE PAGE ANALYSIS ===")
    print(f"Expected pages with images: {len(expected_pages)}")
    print(f"Currently extracted pages: {len(current_pages)}")
    print(f"Missing pages: {len(missing_pages)}")
    print(f"Extra pages: {len(extra_pages)}")
    print()
    
    if missing_pages:
        print("Missing pages:", sorted(missing_pages))
    if extra_pages:
        print("Extra pages:", sorted(extra_pages))
    
    # Load extraction checkpoint to see which questions are on missing pages
    checkpoint_path = Path("data/extraction_checkpoint.json")
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions_on_missing_pages = []
        for q in data.get("questions", []):
            if q.get("page_number") in missing_pages:
                questions_on_missing_pages.append({
                    "id": q.get("id"),
                    "page": q.get("page_number"),
                    "question": q.get("question", "")[:100] + "..."
                })
        
        print(f"\nQuestions on missing pages: {len(questions_on_missing_pages)}")
        for q in questions_on_missing_pages[:10]:  # Show first 10
            print(f"  Q{q['id']} (page {q['page']}): {q['question']}")
        if len(questions_on_missing_pages) > 10:
            print(f"  ... and {len(questions_on_missing_pages) - 10} more")
    
    # Strategy recommendations
    print("\n=== RECOMMENDED STRATEGY ===")
    print("1. Extract missing images from PDF pages")
    print("2. Use basic placeholder descriptions for missing images")
    print("3. Process images in smaller batches to avoid timeouts")
    print("4. Create dataset with current available images first")
    print("5. Incrementally add missing images")

if __name__ == "__main__":
    main()