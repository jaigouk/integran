#!/usr/bin/env python3
"""Test single question extraction with mocked API."""

import json
from unittest.mock import MagicMock, patch


def test_single_question():
    """Test single question extraction workflow with mocked Gemini API.

    This test verifies the integration between components without making
    actual API calls, making it fast and reliable.
    """
    # Mock response data that simulates what Gemini would return
    mock_response_data = {
        "questions": {
            "1": {
                "id": 1,
                "question": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
                "options": [
                    "hier Religionsfreiheit gilt.",
                    "die Menschen Steuern zahlen.",
                    "die Menschen das Wahlrecht haben.",
                    "hier Meinungsfreiheit gilt.",
                ],
                "correct": "hier Meinungsfreiheit gilt.",
                "category": "Politik in der Demokratie",
                "difficulty": "easy",
                "question_type": "general",
                "state": None,
                "page_number": 1,
                "is_image_question": False,
                "images": [],
                "correct_answer_letter": "D",
            }
        }
    }

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_response_data)

    # Mock the Gemini client initialization and API call
    with patch("src.direct_pdf_processor.genai.Client") as MockClient:
        # Set up the mock client
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        MockClient.return_value = mock_client_instance

        # Also mock the PDF loading to avoid file I/O
        with patch(
            "src.direct_pdf_processor.DirectPDFProcessor.load_pdf_as_base64"
        ) as mock_load_pdf:
            # Return a valid base64 string (empty PDF)
            mock_load_pdf.return_value = (
                "JVBERi0xLjQKJeLjz9MKCg=="  # Minimal valid PDF base64
            )

            # Import and create processor
            from src.direct_pdf_processor import DirectPDFProcessor

            processor = DirectPDFProcessor()

            # Call the method we're testing
            questions = processor.process_pdf_with_structured_output(
                "JVBERi0xLjQKJeLjz9MKCg==", 1, 1
            )

            # Verify the API was called
            assert mock_client_instance.models.generate_content.called

            # Validate the extracted questions
            assert questions is not None, "Questions should not be None"
            assert len(questions) == 1, "Should extract exactly one question"

            question = questions[0]
            assert question["id"] == 1, "Question ID should be 1"
            assert "gegen die Regierung" in question["question"], (
                "Question text should contain expected content"
            )
            assert question["correct"] == "hier Meinungsfreiheit gilt.", (
                "Correct answer should match"
            )
            assert len(question["options"]) == 4, "Should have 4 options"
            assert question["category"] == "Politik in der Demokratie", (
                "Category should match"
            )
            assert question["difficulty"] == "easy", "Difficulty should be easy"
            assert not question["is_image_question"], "Should not be an image question"


def test_batch_processing_integration():
    """Test the batch processing integration with mocked API."""
    # Mock multiple questions for batch processing
    mock_response_data = {
        "questions": {
            "1": {
                "id": 1,
                "question": "Question 1",
                "options": ["A", "B", "C", "D"],
                "correct": "A",
                "category": "Test",
                "difficulty": "easy",
                "question_type": "general",
                "state": None,
                "page_number": 1,
                "is_image_question": False,
                "images": [],
            },
            "2": {
                "id": 2,
                "question": "Question 2",
                "options": ["A", "B", "C", "D"],
                "correct": "B",
                "category": "Test",
                "difficulty": "medium",
                "question_type": "general",
                "state": None,
                "page_number": 1,
                "is_image_question": False,
                "images": [],
            },
        }
    }

    # Create mock response
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_response_data)

    with patch("src.direct_pdf_processor.genai.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        MockClient.return_value = mock_client_instance

        with patch("src.direct_pdf_processor.DirectPDFProcessor.load_pdf_as_base64"):
            from src.direct_pdf_processor import DirectPDFProcessor

            processor = DirectPDFProcessor()

            # Test batch processing with valid base64
            questions = processor.process_pdf_with_structured_output(
                "JVBERi0xLjQKJeLjz9MKCg==", 1, 2
            )

            assert len(questions) == 2
            assert questions[0]["id"] == 1
            assert questions[1]["id"] == 2


if __name__ == "__main__":
    test_single_question()
    test_batch_processing_integration()
