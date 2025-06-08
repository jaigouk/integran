#!/usr/bin/env python3
"""Test script to verify explanation generation with a small batch."""

import json
from pathlib import Path

from src.core.settings import has_gemini_config
from src.utils.explanation_generator import ExplanationGenerator


def test_small_batch():
    """Test explanation generation with a small batch of questions."""

    # Check if Gemini is configured
    if not has_gemini_config():
        print("❌ Gemini API not configured.")
        print("Please set GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        return False

    try:
        # Initialize generator
        print("✓ Initializing explanation generator...")
        generator = ExplanationGenerator()

        # Load questions
        print("✓ Loading questions...")
        questions = generator.load_questions()
        print(f"  Found {len(questions)} questions")

        # Test with just first 3 questions
        test_batch_size = 3
        print(f"\n✓ Testing with first {test_batch_size} questions...")

        # Prepare batch
        batch = generator.prepare_questions_batch(questions, 0, test_batch_size)

        # Display questions to be processed
        print("\nQuestions to process:")
        for q in batch:
            print(f"  {q['question_id']}: {q['question_text'][:60]}...")

        # Generate explanations
        print("\n✓ Generating explanations...")
        explanations = generator.generate_explanations_batch(batch)

        # Display results
        print(f"\n✓ Generated {len(explanations)} explanations:")
        for exp in explanations:
            print(f"\n  Question {exp['question_id']}:")
            print(f"    Q: {exp['question_text'][:60]}...")
            print(f"    A: {exp['correct_answer']}")
            print(f"    Explanation: {exp['explanation'][:100]}...")
            print(f"    Key concept: {exp['key_concept']}")
            if exp.get('mnemonic'):
                print(f"    Mnemonic: {exp['mnemonic']}")

        # Save test results
        test_output = Path("data/test_explanations.json")
        with open(test_output, "w", encoding="utf-8") as f:
            json.dump(explanations, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Test results saved to: {test_output}")
        print("\n✅ Test completed successfully!")

        # Test checkpoint functionality
        print("\n✓ Testing checkpoint functionality...")
        checkpoint_file = Path("data/test_checkpoint.json")
        checkpoint_data = generator.load_explanation_checkpoint(checkpoint_file)
        generator.add_explanations_to_checkpoint(checkpoint_data, explanations)
        generator.save_explanation_checkpoint(checkpoint_file, checkpoint_data)
        print(f"  Checkpoint saved to: {checkpoint_file}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_small_batch()
    exit(0 if success else 1)
