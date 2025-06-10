"""Direct PDF processor - Upload PDF to Gemini File API and process with structured output."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.core.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionSchema(BaseModel):
    """Schema for individual questions with proper image handling."""
    id: int = Field(description="Sequential question number (1-460)")
    question: str = Field(description="Full German question text")
    options: List[str] = Field(description="Four answer options as list")
    correct_answer: str = Field(description="Letter A, B, C, or D")
    correct_text: str = Field(description="Full text of the correct answer")
    category: str = Field(description="Question category (Grundrechte, Geschichte, etc.)")
    difficulty: str = Field(description="easy, medium, or hard")
    question_type: str = Field(description="general or state_specific")
    state: str | None = Field(description="State name for state-specific questions", default=None)
    page_number: int = Field(description="PDF page number where question appears")
    has_images: bool = Field(description="Whether question includes images")
    image_type: str | None = Field(description="single, option_images, or null", default=None)
    image_description: str | None = Field(description="Description of what images show", default=None)


class DatasetSchema(BaseModel):
    """Schema for the complete dataset."""
    questions: List[QuestionSchema] = Field(description="All 460 questions")
    metadata: Dict[str, Any] = Field(description="Extraction metadata")


class DirectPDFProcessor:
    """Upload PDF to Gemini File API and process with structured output."""
    
    def __init__(self):
        """Initialize with Gemini client."""
        settings = get_settings()
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location="global"
        )
        self.model_id = settings.gemini_model
        
    def upload_pdf_to_file_api(self, pdf_path: Path) -> str:
        """Upload PDF to Gemini File API and return file URI."""
        
        logger.info(f"Uploading PDF to Gemini File API: {pdf_path}")
        
        try:
            # Upload file using File API
            upload_response = self.client.files.upload(
                path=str(pdf_path),
                mime_type="application/pdf"
            )
            
            file_uri = upload_response.uri
            logger.info(f"File uploaded successfully: {file_uri}")
            
            # Wait for file to be processed
            logger.info("Waiting for file processing...")
            time.sleep(10)  # Give time for processing
            
            return file_uri
            
        except Exception as e:
            logger.error(f"Failed to upload PDF: {e}")
            raise
    
    def process_pdf_with_structured_output(self, file_uri: str, batch_start: int = 1, batch_end: int = 460) -> List[Dict[str, Any]]:
        """Process PDF with structured JSON output and proper error handling."""
        
        logger.info(f"Processing questions {batch_start}-{batch_end} with structured output")
        
        # Create the optimized prompt
        prompt = f"""Extract questions {batch_start}-{batch_end} from the German Integration Exam PDF (Leben in Deutschland Test).

CRITICAL REQUIREMENTS:

1. Extract questions {batch_start} to {batch_end} with these exact fields:
   - id: Question number ({batch_start}-{batch_end})
   - question: Full German text
   - options: Array of 4 options OR ["Bild 1", "Bild 2", "Bild 3", "Bild 4"] for image questions
   - correct_answer: Letter (A, B, C, or D)
   - correct_text: Actual text/content of correct answer
   - category: One of [Grundrechte, Demokratie und Wahlen, Geschichte, Geografie, Kultur und Gesellschaft, Rechtssystem, Föderalismus, Allgemein]
   - difficulty: easy/medium/hard
   - question_type: "general" (1-300) or "state_specific" (301-460)
   - state: For questions 301-460, state name (Bayern, Berlin, etc.)
   - page_number: Actual PDF page number
   - has_images: true if question involves images
   - image_type: "option_images" if options are images, "single" if one image in question, null otherwise
   - image_description: For image questions, describe what images show

2. SPECIAL ATTENTION for image questions:
   - Questions like "Welches ist das Wappen..." → has_images=true, image_type="option_images"
   - Question 130 (ballot papers) → has_images=true, image_type="option_images"
   - Options should be ["Bild 1", "Bild 2", "Bild 3", "Bild 4"]
   - Describe each image briefly

3. STATE QUESTIONS (301-460):
   - Pages 112-191 contain 160 state-specific questions
   - 10 questions per state, 16 states total
   - Include state name for each

4. VALIDATION POINTS:
   - Question 130 must have has_images=true
   - All questions 1-300 have question_type="general"
   - All questions 301-460 have question_type="state_specific" with state name
   - Each question has exactly 4 options
   - correct_answer matches one of A/B/C/D

Return JSON with questions array and metadata about extraction."""

        try:
            # Create file part from uploaded file
            file_part = types.Part.from_uri(
                file_uri=file_uri,
                mime_type="application/pdf"
            )
            
            # Create text part with prompt
            text_part = types.Part.from_text(prompt)
            
            # Create content
            contents = [types.Content(
                role="user",
                parts=[text_part, file_part]
            )]
            
            # Configure generation with structured output
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DatasetSchema.model_json_schema(),
                temperature=0.1,
                max_output_tokens=65535
            )
            
            logger.info("Generating structured output from PDF...")
            
            # Make the request with retry logic
            max_retries = 3
            retry_delay = 30
            
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=contents,
                        config=config
                    )
                    
                    # Parse JSON response
                    result = json.loads(response.text)
                    questions = result.get("questions", [])
                    
                    logger.info(f"Successfully extracted {len(questions)} questions")
                    
                    # Validate critical questions
                    self._validate_batch(questions, batch_start, batch_end)
                    
                    return questions
                    
                except Exception as e:
                    if "timeout" in str(e).lower() or "overloaded" in str(e).lower():
                        if attempt < max_retries - 1:
                            logger.warning(f"API timeout/overload, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error("API still unavailable after all retries")
                            raise
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"Failed to process batch {batch_start}-{batch_end}: {e}")
            raise
    
    def process_full_pdf_in_batches(self, pdf_path: Path, batch_size: int = 50) -> List[Dict[str, Any]]:
        """Process the full PDF in manageable batches to avoid timeouts."""
        
        # Upload PDF once to File API
        file_uri = self.upload_pdf_to_file_api(pdf_path)
        
        all_questions = []
        
        # Process in batches to avoid timeouts
        for start in range(1, 461, batch_size):
            end = min(start + batch_size - 1, 460)
            
            logger.info(f"Processing batch {start}-{end}")
            
            try:
                batch_questions = self.process_pdf_with_structured_output(file_uri, start, end)
                all_questions.extend(batch_questions)
                
                # Save incremental progress
                self._save_checkpoint(all_questions, start, end)
                
                # Throttle between batches
                if end < 460:
                    logger.info("Sleeping 10 seconds between batches...")
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"Batch {start}-{end} failed: {e}")
                # Continue with next batch instead of failing completely
                continue
        
        return all_questions
    
    def _validate_batch(self, questions: List[Dict[str, Any]], batch_start: int, batch_end: int):
        """Validate that critical questions are correctly extracted."""
        
        # Check if Question 130 is in this batch
        if 130 >= batch_start and 130 <= batch_end:
            q130 = next((q for q in questions if q.get("id") == 130), None)
            
            if q130:
                if not q130.get("has_images"):
                    logger.error("Question 130 not marked as image question!")
                else:
                    logger.info("✓ Question 130 correctly marked as image question")
                    
                if q130.get("image_type") != "option_images":
                    logger.error(f"Question 130 has wrong image_type: {q130.get('image_type')}")
                else:
                    logger.info("✓ Question 130 has correct image_type")
            else:
                logger.error("Question 130 not found in batch!")
        
        # Validate batch completeness
        expected_count = batch_end - batch_start + 1
        if len(questions) != expected_count:
            logger.warning(f"Expected {expected_count} questions, got {len(questions)}")
        
        # Check image questions in batch
        image_questions = [q for q in questions if q.get("has_images")]
        logger.info(f"Found {len(image_questions)} image questions in batch {batch_start}-{batch_end}")
    
    def _save_checkpoint(self, questions: List[Dict[str, Any]], batch_start: int, batch_end: int):
        """Save incremental progress."""
        checkpoint = {
            "processed_batches": f"1-{batch_end}",
            "total_questions": len(questions),
            "last_batch": f"{batch_start}-{batch_end}",
            "questions": questions
        }
        
        checkpoint_path = Path("data/direct_extraction_checkpoint.json")
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Checkpoint saved: {len(questions)} questions processed")


def main():
    """Run direct PDF extraction with batching."""
    processor = DirectPDFProcessor()
    
    pdf_path = Path("data/gesamtfragenkatalog-lebenindeutschland.pdf")
    output_path = Path("data/direct_extraction.json")
    
    # Process PDF in batches
    questions = processor.process_full_pdf_in_batches(pdf_path, batch_size=50)
    
    # Save final results
    final_dataset = {
        "questions": questions,
        "metadata": {
            "total_questions": len(questions),
            "extraction_method": "direct_pdf_file_api",
            "has_images_count": len([q for q in questions if q.get("has_images")]),
            "state_questions_count": len([q for q in questions if q.get("question_type") == "state_specific"])
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)
        
    logger.info(f"✓ Saved {len(questions)} questions to {output_path}")
    logger.info(f"✓ Image questions: {final_dataset['metadata']['has_images_count']}")
    logger.info(f"✓ State questions: {final_dataset['metadata']['state_questions_count']}")
    

if __name__ == "__main__":
    main()