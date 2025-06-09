"""Tests for the answer generation engine."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.core.answer_engine import (
    AnswerEngine,
    MultilingualAnswer,
)


class TestMultilingualAnswer:
    """Tests for MultilingualAnswer dataclass."""

    def test_multilingual_answer_creation(self):
        """Test creating a MultilingualAnswer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={
                "en": "English explanation",
                "de": "German explanation",
            },
            why_others_wrong={
                "en": {"B": "Wrong because...", "C": "Wrong because..."},
                "de": {"B": "Falsch weil...", "C": "Falsch weil..."},
            },
            key_concept={
                "en": "Key concept",
                "de": "Schlüsselkonzept",
            },
            mnemonic={
                "en": "Memory aid",
                "de": "Gedächtnisstütze",
            },
            image_context="Image shows...",
            rag_sources=["source1.de", "source2.de"],
        )

        assert answer.question_id == 1
        assert answer.correct_answer == "A"
        assert len(answer.explanations) == 2
        assert "en" in answer.explanations
        assert "de" in answer.explanations
        assert answer.image_context == "Image shows..."
        assert len(answer.rag_sources) == 2

    def test_multilingual_answer_minimal(self):
        """Test creating a minimal MultilingualAnswer."""
        answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={"en": "English explanation"},
            why_others_wrong={"en": {"B": "Wrong"}},
            key_concept={"en": "Concept"},
        )

        assert answer.question_id == 1
        assert answer.mnemonic is None
        assert answer.image_context is None
        assert answer.rag_sources == []


class TestAnswerEngine:
    """Tests for AnswerEngine class."""

    def setup_method(self):
        """Setup for each test method."""
        with patch("src.core.answer_engine.RAGEngine"):
            self.engine = AnswerEngine()

    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_initialization(self, mock_rag_engine, mock_gemini_client):
        """Test AnswerEngine initialization."""
        engine = AnswerEngine()

        # Verify components are initialized
        mock_rag_engine.assert_called_once()
        mock_gemini_client.assert_called_once()

    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_generate_answer_with_explanation_basic(
        self, mock_rag_engine, mock_gemini_client
    ):
        """Test basic answer generation without images or RAG."""
        # Mock Gemini client response
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        mock_client.generate_multilingual_answer.return_value = {
            "en": {
                "explanation": "English explanation",
                "why_others_wrong": {"B": "Wrong because...", "C": "Wrong because..."},
                "key_concept": "Key concept",
                "mnemonic": "Memory aid",
            },
            "de": {
                "explanation": "German explanation",
                "why_others_wrong": {"B": "Falsch weil...", "C": "Falsch weil..."},
                "key_concept": "Schlüsselkonzept",
                "mnemonic": "Gedächtnisstütze",
            },
        }

        engine = AnswerEngine()
        question = {
            "id": 1,
            "question": "Test question",
            "options": {"A": "Correct", "B": "Wrong 1", "C": "Wrong 2"},
            "correct": "A",
        }

        result = engine.generate_answer_with_explanation(question, use_rag=False)

        # Verify result structure
        assert isinstance(result, MultilingualAnswer)
        assert result.question_id == 1
        assert result.correct_answer == "A"
        assert "en" in result.explanations
        assert "de" in result.explanations
        assert result.image_context is None
        assert result.rag_sources == []

    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_generate_answer_with_rag(self, mock_rag_engine, mock_gemini_client):
        """Test answer generation with RAG enhancement."""
        # Mock RAG engine
        mock_rag = Mock()
        mock_rag_engine.return_value = mock_rag
        mock_rag.search_knowledge_base.return_value = [
            {
                "content": "RAG content",
                "metadata": {"source": "test_source.de"},
            }
        ]

        # Mock Gemini client
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        mock_client.generate_multilingual_answer_with_context.return_value = {
            "en": {
                "explanation": "Enhanced explanation with RAG",
                "why_others_wrong": {"B": "Wrong because...", "C": "Wrong because..."},
                "key_concept": "Enhanced concept",
                "mnemonic": "Enhanced memory aid",
            }
        }

        engine = AnswerEngine()
        question = {
            "id": 1,
            "question": "Test question",
            "options": {"A": "Correct", "B": "Wrong 1", "C": "Wrong 2"},
            "correct": "A",
            "category": "History",
        }

        result = engine.generate_answer_with_explanation(question, use_rag=True)

        # Verify RAG was used
        mock_rag.search_knowledge_base.assert_called_once()
        assert len(result.rag_sources) > 0
        assert "test_source.de" in result.rag_sources

    @patch("src.core.answer_engine.ImageDescription")
    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_generate_answer_with_images(
        self, mock_rag_engine, mock_gemini_client, mock_image_description
    ):
        """Test answer generation with image descriptions."""
        # Mock image descriptions
        mock_images = [
            Mock(
                path="image1.png",
                description="Image description",
                context="Image context",
                question_relevance="Relevant to question",
            )
        ]

        # Mock Gemini client
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        mock_client.generate_multilingual_answer_with_images.return_value = {
            "en": {
                "explanation": "Explanation with image context",
                "why_others_wrong": {"B": "Wrong because...", "C": "Wrong because..."},
                "key_concept": "Visual concept",
                "mnemonic": "Visual memory aid",
            }
        }

        engine = AnswerEngine()
        question = {
            "id": 21,  # Image question
            "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
            "options": {"A": "Bild 1", "B": "Bild 2", "C": "Bild 3"},
            "correct": "A",
        }

        result = engine.generate_answer_with_explanation(question, images=mock_images)

        # Verify image context was included
        assert result.image_context is not None
        assert "image context" in result.image_context.lower()

    def test_supported_languages(self):
        """Test that all supported languages are handled."""
        with patch("src.core.answer_engine.RAGEngine"):
            engine = AnswerEngine()

        expected_languages = ["en", "de", "tr", "uk", "ar"]
        assert engine.supported_languages == expected_languages

    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_error_handling(self, mock_rag_engine, mock_gemini_client):
        """Test error handling in answer generation."""
        # Mock Gemini client to raise an exception
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        mock_client.generate_multilingual_answer.side_effect = Exception("API Error")

        engine = AnswerEngine()
        question = {
            "id": 1,
            "question": "Test question",
            "options": {"A": "Correct", "B": "Wrong"},
            "correct": "A",
        }

        # Should handle error gracefully and return a fallback answer
        result = engine.generate_answer_with_explanation(question)

        assert isinstance(result, MultilingualAnswer)
        assert result.question_id == 1
        # Should have at least English explanation as fallback
        assert "en" in result.explanations

    @patch("src.core.answer_engine.logger")
    @patch("src.core.answer_engine.GeminiClient")
    @patch("src.core.answer_engine.RAGEngine")
    def test_logging(self, mock_rag_engine, mock_gemini_client, mock_logger):
        """Test that errors are properly logged."""
        # Mock Gemini client to raise an exception
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        mock_client.generate_multilingual_answer.side_effect = Exception("API Error")

        engine = AnswerEngine()
        question = {
            "id": 1,
            "question": "Test question",
            "options": {"A": "Correct", "B": "Wrong"},
            "correct": "A",
        }

        engine.generate_answer_with_explanation(question)

        # Should log the error
        mock_logger.error.assert_called()

    def test_multilingual_coverage(self):
        """Test that all required languages are covered in generation."""
        with patch("src.core.answer_engine.RAGEngine"):
            engine = AnswerEngine()

        # Mock successful multilingual generation
        with patch.object(
            engine, "_generate_multilingual_explanations"
        ) as mock_generate:
            mock_generate.return_value = {
                "en": {
                    "explanation": "English",
                    "why_others_wrong": {},
                    "key_concept": "Concept",
                },
                "de": {
                    "explanation": "Deutsch",
                    "why_others_wrong": {},
                    "key_concept": "Konzept",
                },
                "tr": {
                    "explanation": "Türkçe",
                    "why_others_wrong": {},
                    "key_concept": "Kavram",
                },
                "uk": {
                    "explanation": "Українська",
                    "why_others_wrong": {},
                    "key_concept": "Концепція",
                },
                "ar": {
                    "explanation": "العربية",
                    "why_others_wrong": {},
                    "key_concept": "مفهوم",
                },
            }

            question = {
                "id": 1,
                "question": "Test question",
                "options": {"A": "Correct", "B": "Wrong"},
                "correct": "A",
            }

            result = engine.generate_answer_with_explanation(question)

            # Should have all 5 languages
            assert len(result.explanations) == 5
            assert all(
                lang in result.explanations for lang in engine.supported_languages
            )


class TestAnswerEngineIntegration:
    """Integration tests for AnswerEngine."""

    @pytest.mark.slow
    def test_placeholder_for_integration_tests(self):
        """Placeholder for future integration tests.

        Future tests might include:
        - End-to-end answer generation with real AI models
        - Performance testing with large question sets
        - Quality testing of generated explanations
        """
        assert True, "Structure ready for integration tests"
