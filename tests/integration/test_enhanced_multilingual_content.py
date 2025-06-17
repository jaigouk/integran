#!/usr/bin/env python3
"""Integration tests for enhanced multilingual content utilization from final_dataset.json.

This test suite validates the complete implementation of enhanced question display
with multilingual explanations, wrong answer analysis, key concepts, mnemonics,
image descriptions, and progressive disclosure based on user preferences.
"""

import asyncio
import sys
import time
from pathlib import Path

import pytest

from src.domain.content.services.enhanced_question_display import (
    EnhancedQuestionDisplay,
    EnhancedQuestionDisplayRequest,
)
from src.domain.user.models.user_models import Language
from src.infrastructure.messaging.enhanced_event_bus import EventBus

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.asyncio
async def test_multilingual_explanations():
    """Test multilingual explanation loading for different languages."""
    print("Testing multilingual explanations...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    # Test all supported languages
    languages = [
        Language.ENGLISH,
        Language.GERMAN,
        Language.TURKISH,
        Language.UKRAINIAN,
        Language.ARABIC,
    ]

    for lang in languages:
        request = EnhancedQuestionDisplayRequest(
            question_id=1,
            preferred_language=lang,
        )
        result = await service.call(request)

        assert result.success, f"Failed to load content for {lang.value}"
        assert result.question_data is not None, f"No question data for {lang.value}"

        explanation = result.question_data.multilingual_content.explanation
        assert len(explanation) > 50, (
            f"Explanation too short for {lang.value}: {len(explanation)} chars"
        )

        print(f"  ✓ {lang.value}: {len(explanation)} chars")

    print("  ✅ All languages supported")


@pytest.mark.asyncio
async def test_wrong_answer_analysis():
    """Test wrong answer analysis feature."""
    print("\nTesting wrong answer analysis...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    request = EnhancedQuestionDisplayRequest(
        question_id=1,
        preferred_language=Language.ENGLISH,
        include_wrong_analysis=True,
    )
    result = await service.call(request)

    assert result.success, "Failed to load wrong answer analysis"
    assert result.question_data is not None, "No question data"

    wrong_analysis = result.question_data.wrong_answer_analysis
    assert len(wrong_analysis) >= 3, (
        f"Expected at least 3 wrong answers, got {len(wrong_analysis)}"
    )

    # Verify each wrong answer has proper structure
    for analysis in wrong_analysis:
        assert analysis.option_letter in ["A", "B", "C", "D"], (
            f"Invalid option letter: {analysis.option_letter}"
        )
        assert len(analysis.option_text) > 0, "Empty option text"
        assert len(analysis.explanation) > 10, (
            f"Explanation too short: {len(analysis.explanation)} chars"
        )
        print(f"  ✓ Option {analysis.option_letter}: {analysis.explanation[:50]}...")

    print("  ✅ Wrong answer analysis working correctly")


@pytest.mark.asyncio
async def test_educational_enhancements():
    """Test key concepts and mnemonics."""
    print("\nTesting educational enhancements...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    request = EnhancedQuestionDisplayRequest(
        question_id=1,
        preferred_language=Language.ENGLISH,
        include_key_concepts=True,
        include_mnemonics=True,
    )
    result = await service.call(request)

    assert result.success, "Failed to load educational content"
    assert result.question_data is not None, "No question data"

    content = result.question_data.multilingual_content

    # Test key concept
    assert len(content.key_concept) > 20, (
        f"Key concept too short: {len(content.key_concept)} chars"
    )
    print(f"  ✓ Key concept: {content.key_concept[:50]}...")

    # Test mnemonic (may be None for some questions)
    if content.mnemonic:
        assert len(content.mnemonic) > 5, (
            f"Mnemonic too short: {len(content.mnemonic)} chars"
        )
        print(f"  ✓ Mnemonic: {content.mnemonic}")
    else:
        print("  ✓ Mnemonic: Not available for this question")

    print("  ✅ Educational enhancements working correctly")


@pytest.mark.asyncio
async def test_image_question_support():
    """Test image question descriptions and context."""
    print("\nTesting image question support...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    # Test with question 21 (known image question)
    request = EnhancedQuestionDisplayRequest(
        question_id=21,
        preferred_language=Language.ENGLISH,
        include_image_descriptions=True,
    )
    result = await service.call(request)

    assert result.success, "Failed to load image question"
    assert result.question_data is not None, "No question data"

    question_data = result.question_data
    assert question_data.is_image_question, (
        "Question should be marked as image question"
    )
    assert len(question_data.images) > 0, (
        "Image question should have image descriptions"
    )

    # Verify image descriptions
    for i, image in enumerate(question_data.images, 1):
        assert len(image.path) > 0, f"Image {i} missing path"
        assert len(image.description) > 10, (
            f"Image {i} description too short: {len(image.description)} chars"
        )
        assert len(image.context) > 0, f"Image {i} missing context"
        print(f"  ✓ Image {i}: {image.context} - {image.description[:40]}...")

    print(f"  ✅ Image support working correctly ({len(question_data.images)} images)")


@pytest.mark.asyncio
async def test_progressive_disclosure_preferences():
    """Test progressive disclosure with different preference combinations."""
    print("\nTesting progressive disclosure preferences...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    # Test different preference combinations
    test_cases = [
        ("Full disclosure", True, True, True, True),
        ("Minimal disclosure", False, False, False, False),
        ("Educational focus", True, True, False, False),
        ("Analysis focus", False, False, True, True),
    ]

    for case_name, _explanations, concepts, mnemonics, wrong_analysis in test_cases:
        request = EnhancedQuestionDisplayRequest(
            question_id=1,
            preferred_language=Language.ENGLISH,
            include_wrong_analysis=wrong_analysis,
            include_key_concepts=concepts,
            include_mnemonics=mnemonics,
        )
        result = await service.call(request)

        assert result.success, f"Failed to load content for {case_name}"
        assert result.question_data is not None, f"No question data for {case_name}"

        # Verify content matches preferences
        if wrong_analysis:
            assert len(result.question_data.wrong_answer_analysis) > 0, (
                f"{case_name}: Expected wrong analysis"
            )

        print(f"  ✓ {case_name}: Content loaded based on preferences")

    print("  ✅ Progressive disclosure working correctly")


@pytest.mark.asyncio
async def test_performance_with_large_dataset():
    """Test performance with multiple questions."""
    print("\nTesting performance with multiple questions...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    # Test loading multiple questions
    question_ids = [1, 21, 50, 100, 200]  # Mix of regular and image questions

    start_time = time.time()

    for question_id in question_ids:
        request = EnhancedQuestionDisplayRequest(
            question_id=question_id,
            preferred_language=Language.ENGLISH,
            include_wrong_analysis=True,
            include_key_concepts=True,
            include_mnemonics=True,
            include_image_descriptions=True,
        )
        result = await service.call(request)

        if result.success:
            print(f"  ✓ Question {question_id}: Loaded successfully")
        else:
            print(f"  ⚠ Question {question_id}: {result.error_message}")

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(question_ids)

    print(
        f"  ✅ Performance: {total_time:.2f}s total, {avg_time:.3f}s avg per question"
    )

    # Performance should be reasonable (< 1s per question)
    assert avg_time < 1.0, f"Performance too slow: {avg_time:.3f}s avg per question"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\nTesting error handling...")

    event_bus = EventBus()
    service = EnhancedQuestionDisplay(event_bus)

    # Test with non-existent question
    request = EnhancedQuestionDisplayRequest(
        question_id=99999,
        preferred_language=Language.ENGLISH,
    )
    result = await service.call(request)

    assert not result.success, "Should fail for non-existent question"
    assert "not found" in result.error_message.lower(), (
        f"Unexpected error message: {result.error_message}"
    )
    print("  ✓ Non-existent question handled correctly")

    print("  ✅ Error handling working correctly")


async def run_all_tests():
    """Run all integration tests for enhanced multilingual content."""
    print("🎯 Enhanced Multilingual Content Integration Tests")
    print("=" * 60)

    try:
        await test_multilingual_explanations()
        await test_wrong_answer_analysis()
        await test_educational_enhancements()
        await test_image_question_support()
        await test_progressive_disclosure_preferences()
        await test_performance_with_large_dataset()
        await test_error_handling()

        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Enhanced multilingual content utilization is working correctly")
        print("\nImplemented features:")
        print("   • Multilingual explanations (5 languages)")
        print("   • Wrong answer analysis")
        print("   • Key concepts for educational value")
        print("   • Memory techniques (mnemonics)")
        print("   • Image descriptions and context")
        print("   • User preference-based language selection")
        print("   • Progressive disclosure based on user settings")
        print("   • Performance optimization")
        print("   • Error handling")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
