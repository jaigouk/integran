#!/usr/bin/env python3
"""Test single question extraction."""

import json
from pathlib import Path
from src.direct_pdf_processor import DirectPDFProcessor

def test_single_question():
    processor = DirectPDFProcessor()
    pdf_path = Path("data/gesamtfragenkatalog-lebenindeutschland.pdf")
    
    # Load PDF
    pdf_base64 = processor.load_pdf_as_base64(pdf_path)
    
    # Extract question 1
    print("Extracting question 1...")
    questions = processor.process_pdf_with_structured_output(pdf_base64, 1, 1)
    
    if questions:
        print(f"\nExtracted {len(questions)} question(s):")
        print(json.dumps(questions[0], indent=2, ensure_ascii=False))
    else:
        print("No questions extracted")
    
    # Try question 130 (ballot paper with images)
    print("\n\nExtracting question 130...")
    questions_130 = processor.process_pdf_with_structured_output(pdf_base64, 130, 130)
    
    if questions_130:
        print(f"\nExtracted question 130:")
        print(json.dumps(questions_130[0], indent=2, ensure_ascii=False))
    else:
        print("No question 130 extracted")

if __name__ == "__main__":
    test_single_question()