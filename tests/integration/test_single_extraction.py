#!/usr/bin/env python3
"""Test single question extraction."""

from pathlib import Path

import pytest

from src.core.settings import has_gemini_config
from src.direct_pdf_processor import DirectPDFProcessor


@pytest.mark.slow
@pytest.mark.skipif(
    not has_gemini_config(), reason="Gemini API credentials not configured"
)
def test_single_question():
    """Test extracting a single question from PDF.

    This test requires Gemini API credentials and takes ~2 minutes to run.
    It's marked as 'slow' and skipped if credentials aren't available.
    """
    # Check if PDF exists
    pdf_path = Path("data/gesamtfragenkatalog-lebenindeutschland.pdf")
    if not pdf_path.exists():
        pytest.skip("PDF file not found")

    try:
        processor = DirectPDFProcessor()

        # Load PDF
        pdf_base64 = processor.load_pdf_as_base64(pdf_path)

        # Extract question 1 (simple test)
        print("Extracting question 1...")
        questions = processor.process_pdf_with_structured_output(pdf_base64, 1, 1)

        # Basic validation
        assert questions is not None, "Questions should not be None"
        if questions:
            assert len(questions) > 0, "Should extract at least one question"
            assert "id" in questions[0], "Question should have an ID"
            assert "question" in questions[0], "Question should have question text"
            print(f"\n✓ Successfully extracted question: {questions[0].get('id')}")
        else:
            pytest.fail("No questions extracted")

    except Exception as e:
        pytest.fail(f"Single question extraction failed: {e}")


if __name__ == "__main__":
    test_single_question()
