"""Comprehensive validation tests for the AnswerEngine multilingual generation.

This module focuses on validating the quality and consistency of
multilingual answer generation across all supported languages.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.core.answer_engine import AnswerEngine, MultilingualAnswer
from src.core.image_processor import ImageDescription


class TestAnswerEngineValidation:
    """Validation tests for AnswerEngine ensuring multilingual quality."""

    @patch("src.core.answer_engine.GENAI_AVAILABLE", True)
    @patch("src.core.answer_engine.RAG_AVAILABLE", True)
    @patch("src.core.answer_engine.genai.Client")
    @patch("src.core.answer_engine.RAGEngine")
    @patch("src.core.answer_engine.get_settings")
    @patch("src.core.answer_engine.has_gemini_config")
    def test_multilingual_answer_completeness(
        self, mock_has_config, mock_settings, mock_rag_engine, mock_client
    ):
        """Test that all 5 languages are properly generated and complete."""
        mock_has_config.return_value = True
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        # Mock RAG engine
        mock_rag = Mock()
        mock_rag_engine.return_value = mock_rag
        mock_rag.generate_explanation_with_firecrawl.return_value = {
            "explanation": "RAG context explanation",
            "context_sources": ["bundestag.de", "bundesregierung.de"],
        }

        # Mock Gemini API response with complete multilingual data
        mock_api_response = {
            "explanations": {
                "en": "The German federal eagle is the official coat of arms of Germany since 1950.",
                "de": "Der Bundesadler ist das offizielle Wappen Deutschlands seit 1950.",
                "tr": "Alman federal kartalı, 1950'den beri Almanya'nın resmi armasıdır.",
                "uk": "Німецький федеральний орел є офіційним гербом Німеччини з 1950 року.",
                "ar": "النسر الفيدرالي الألماني هو الشعار الرسمي لألمانيا منذ عام 1950.",
            },
            "why_others_wrong": {
                "en": {
                    "B": "This is not the official German symbol",
                    "C": "Incorrect historical symbol",
                    "D": "Wrong national emblem",
                },
                "de": {
                    "B": "Das ist nicht das offizielle deutsche Symbol",
                    "C": "Falsches historisches Symbol",
                    "D": "Falsches Nationalemblem",
                },
                "tr": {
                    "B": "Bu resmi Alman sembolü değil",
                    "C": "Yanlış tarihi sembol",
                    "D": "Yanlış ulusal amblem",
                },
                "uk": {
                    "B": "Це не офіційний німецький символ",
                    "C": "Неправильний історичний символ",
                    "D": "Неправильна національна емблема",
                },
                "ar": {
                    "B": "هذا ليس الرمز الألماني الرسمي",
                    "C": "رمز تاريخي خاطئ",
                    "D": "شعار وطني خاطئ",
                },
            },
            "key_concept": {
                "en": "German national symbols and federal eagle",
                "de": "Deutsche nationale Symbole und Bundesadler",
                "tr": "Alman ulusal sembolleri ve federal kartal",
                "uk": "Німецькі національні символи та федеральний орел",
                "ar": "الرموز الوطنية الألمانية والنسر الفيدرالي",
            },
            "mnemonic": {
                "en": "Eagle = Germany (like USA has eagle too)",
                "de": "Adler = Deutschland (wie USA auch Adler hat)",
                "tr": "Kartal = Almanya (ABD'nin de kartalı var)",
                "uk": "Орел = Німеччина (як у США теж є орел)",
                "ar": "النسر = ألمانيا (مثل الولايات المتحدة لديها نسر أيضاً)",
            },
        }

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(
            text=f"```json\n{str(mock_api_response).replace("'", '"')}\n```"
        )

        engine = AnswerEngine()

        # Test question (typical image question)
        test_question = {
            "id": 21,
            "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
            "option_a": "Bild 1",
            "option_b": "Bild 2",
            "option_c": "Bild 3",
            "option_d": "Bild 4",
            "correct_answer": "A",
            "category": "Symbols",
        }

        # Test with image context
        test_images = [
            ImageDescription(
                path="page_9_img_1.png",
                description="German federal eagle on yellow background with red claws",
                visual_elements=["eagle", "yellow", "red", "black"],
                context="Official coat of arms of Germany established in 1950",
                question_relevance="Identifies the correct German national symbol",
            )
        ]

        result = engine.generate_answer_with_explanation(
            question=test_question, images=test_images, use_rag=True
        )

        # Validate result completeness
        assert isinstance(result, MultilingualAnswer)
        assert result.question_id == 21
        assert result.correct_answer == "A"

        # Validate all 5 languages are present
        required_languages = ["en", "de", "tr", "uk", "ar"]
        for lang in required_languages:
            assert lang in result.explanations, (
                f"Missing explanation for language: {lang}"
            )
            assert lang in result.why_others_wrong, (
                f"Missing wrong options for language: {lang}"
            )
            assert lang in result.key_concept, (
                f"Missing key concept for language: {lang}"
            )

            # Validate content quality
            assert len(result.explanations[lang]) > 20, (
                f"Explanation too short for {lang}"
            )
            assert result.key_concept[lang].strip(), f"Empty key concept for {lang}"

            # Validate wrong options explanations
            wrong_options = result.why_others_wrong[lang]
            assert "B" in wrong_options, f"Missing explanation for option B in {lang}"
            assert "C" in wrong_options, f"Missing explanation for option C in {lang}"
            assert "D" in wrong_options, f"Missing explanation for option D in {lang}"

        # Validate image context integration
        assert result.image_context is not None
        assert "German federal eagle" in result.image_context

        # Validate RAG sources
        assert len(result.rag_sources) > 0
        assert "bundestag.de" in result.rag_sources

    @patch("src.core.answer_engine.GENAI_AVAILABLE", True)
    @patch("src.core.answer_engine.genai.Client")
    @patch("src.core.answer_engine.get_settings")
    @patch("src.core.answer_engine.has_gemini_config")
    def test_answer_consistency_across_languages(
        self, mock_has_config, mock_settings, mock_client
    ):
        """Test that answers are consistent in meaning across all languages."""
        mock_has_config.return_value = True
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        # Mock consistent multilingual response
        consistent_response = {
            "explanations": {
                "en": "Germany has 16 federal states (Bundesländer).",
                "de": "Deutschland hat 16 Bundesländer.",
                "tr": "Almanya'nın 16 federal eyaleti vardır.",
                "uk": "Німеччина має 16 федеральних земель.",
                "ar": "ألمانيا لديها 16 ولاية فيدرالية.",
            },
            "why_others_wrong": {
                "en": {
                    "A": "14 is incorrect",
                    "B": "15 is too few",
                    "D": "17 is too many",
                },
                "de": {
                    "A": "14 ist falsch",
                    "B": "15 ist zu wenig",
                    "D": "17 ist zu viel",
                },
                "tr": {"A": "14 yanlış", "B": "15 çok az", "D": "17 çok fazla"},
                "uk": {"A": "14 неправильно", "B": "15 замало", "D": "17 забагато"},
                "ar": {"A": "14 خاطئ", "B": "15 قليل جداً", "D": "17 كثير جداً"},
            },
            "key_concept": {
                "en": "German federal structure",
                "de": "Deutsche Bundesstruktur",
                "tr": "Alman federal yapısı",
                "uk": "Німецька федеральна структура",
                "ar": "البنية الفيدرالية الألمانية",
            },
            "mnemonic": {
                "en": "16 states like 16 puzzle pieces",
                "de": "16 Länder wie 16 Puzzleteile",
                "tr": "16 eyalet 16 puzzle parçası gibi",
                "uk": "16 земель як 16 частин головоломки",
                "ar": "16 ولاية مثل 16 قطعة أحجية",
            },
        }

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(
            text=f"{str(consistent_response).replace("'", '"')}"
        )

        engine = AnswerEngine()

        test_question = {
            "id": 1,
            "question": "Wie viele Bundesländer hat Deutschland?",
            "option_a": "14",
            "option_b": "15",
            "option_c": "16",
            "option_d": "17",
            "correct_answer": "C",
            "category": "Government",
        }

        result = engine.generate_answer_with_explanation(
            question=test_question, use_rag=False
        )

        # Validate numerical consistency
        # All languages should convey that Germany has 16 federal states
        assert "16" in result.explanations["en"]
        assert "16" in result.explanations["de"]
        assert "16" in result.explanations["tr"]
        assert "16" in result.explanations["uk"]
        assert "16" in result.explanations["ar"]

        # Validate that wrong option explanations are consistent
        for lang in ["en", "de", "tr", "uk", "ar"]:
            wrong_explanations = result.why_others_wrong[lang]
            # Should explain why 14, 15, and 17 are wrong
            assert "A" in wrong_explanations  # 14
            assert "B" in wrong_explanations  # 15
            assert "D" in wrong_explanations  # 17

    @patch("src.core.answer_engine.GENAI_AVAILABLE", True)
    @patch("src.core.answer_engine.genai.Client")
    @patch("src.core.answer_engine.get_settings")
    @patch("src.core.answer_engine.has_gemini_config")
    def test_batch_processing_consistency(
        self, mock_has_config, mock_settings, mock_client
    ):
        """Test that batch processing maintains quality and consistency."""
        mock_has_config.return_value = True
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        # Mock responses for different questions
        def mock_generate_response(*args, **kwargs):
            # Extract question content from the prompt to provide relevant responses
            prompt = args[1][0].parts[0].text if len(args) > 1 else ""

            if "Wappen" in prompt or "coat of arms" in prompt:
                return Mock(
                    text='{"explanations": {"en": "German coat of arms", "de": "Deutsches Wappen", "tr": "Alman arması", "uk": "Німецький герб", "ar": "الشعار الألماني"}, "why_others_wrong": {"en": {}, "de": {}, "tr": {}, "uk": {}, "ar": {}}, "key_concept": {"en": "Symbols", "de": "Symbole", "tr": "Semboller", "uk": "Символи", "ar": "الرموز"}, "mnemonic": {"en": "Eagle=Germany", "de": "Adler=Deutschland", "tr": "Kartal=Almanya", "uk": "Орел=Німеччина", "ar": "النسر=ألمانيا"}}'
                )
            else:
                return Mock(
                    text='{"explanations": {"en": "Standard explanation", "de": "Standard Erklärung", "tr": "Standart açıklama", "uk": "Стандартне пояснення", "ar": "شرح قياسي"}, "why_others_wrong": {"en": {}, "de": {}, "tr": {}, "uk": {}, "ar": {}}, "key_concept": {"en": "Concept", "de": "Konzept", "tr": "Kavram", "uk": "Концепція", "ar": "مفهوم"}, "mnemonic": {"en": "Memory aid", "de": "Gedächtnisstütze", "tr": "Hafıza yardımcısı", "uk": "Мнемоніка", "ar": "مساعد الذاكرة"}}'
                )

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.side_effect = (
            mock_generate_response
        )

        engine = AnswerEngine()

        # Test batch of questions
        test_questions = [
            {
                "id": 21,
                "question": "Welches ist das Wappen der BRD?",
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
                "correct_answer": "A",
                "category": "Symbols",
            },
            {
                "id": 22,
                "question": "Wie viele Bundesländer hat Deutschland?",
                "option_a": "14",
                "option_b": "15",
                "option_c": "16",
                "option_d": "17",
                "correct_answer": "C",
                "category": "Government",
            },
            {
                "id": 23,
                "question": "Wann wurde die BRD gegründet?",
                "option_a": "1945",
                "option_b": "1949",
                "option_c": "1950",
                "option_d": "1951",
                "correct_answer": "B",
                "category": "History",
            },
        ]

        # Mock image data
        question_image_mapping = {21: ["page_9_img_1.png"]}
        image_descriptions = {
            "page_9_img_1.png": ImageDescription(
                path="page_9_img_1.png",
                description="German federal eagle",
                visual_elements=["eagle"],
                context="German symbol",
                question_relevance="National symbol",
            )
        }

        with patch("time.sleep"):  # Skip delays in testing
            results = engine.generate_batch_answers(
                questions=test_questions,
                question_image_mapping=question_image_mapping,
                image_descriptions=image_descriptions,
                use_rag=False,
            )

        # Validate batch results
        assert len(results) == 3

        # Each result should be complete
        for i, result in enumerate(results):
            assert isinstance(result, MultilingualAnswer)
            assert result.question_id == test_questions[i]["id"]

            # All languages should be present
            for lang in ["en", "de", "tr", "uk", "ar"]:
                assert lang in result.explanations
                assert lang in result.key_concept
                assert result.explanations[lang].strip()
                assert result.key_concept[lang].strip()

        # Question 21 should have image context (it's an image question)
        wappen_result = next(r for r in results if r.question_id == 21)
        assert wappen_result.image_context is not None

        # Questions 22 and 23 should not have image context
        for qid in [22, 23]:
            result = next(r for r in results if r.question_id == qid)
            assert result.image_context is None

    @patch("src.core.answer_engine.GENAI_AVAILABLE", True)
    @patch("src.core.answer_engine.genai.Client")
    @patch("src.core.answer_engine.get_settings")
    @patch("src.core.answer_engine.has_gemini_config")
    def test_error_recovery_and_fallbacks(
        self, mock_has_config, mock_settings, mock_client
    ):
        """Test that error recovery produces valid fallback responses."""
        mock_has_config.return_value = True
        mock_settings.return_value = Mock(
            use_vertex_ai=True,
            gcp_project_id="test",
            gcp_region="us-central1",
            gemini_model="test",
            gemini_api_key=None,
        )

        # Mock API failure
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(
            text="Invalid JSON response that cannot be parsed"
        )

        engine = AnswerEngine()

        test_question = {
            "id": 1,
            "question": "Test question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_answer": "A",
            "category": "Test",
        }

        result = engine.generate_answer_with_explanation(question=test_question)

        # Should get fallback response
        assert isinstance(result, MultilingualAnswer)
        assert result.question_id == 1
        assert result.correct_answer == "A"

        # Should have fallback explanations in all languages
        required_languages = ["en", "de", "tr", "uk", "ar"]
        for lang in required_languages:
            assert lang in result.explanations
            assert result.explanations[lang].strip()  # Should not be empty

            # Check for fallback text patterns
            explanation = result.explanations[lang].lower()
            fallback_indicators = [
                "unable",
                "konnte nicht",
                "oluşturulamadı",
                "не вдалося",
                "تعذر",
            ]
            assert any(indicator in explanation for indicator in fallback_indicators)

    def test_multilingual_answer_dataclass_validation(self):
        """Test MultilingualAnswer dataclass validation and completeness."""
        # Test complete answer
        complete_answer = MultilingualAnswer(
            question_id=42,
            correct_answer="B",
            explanations={
                "en": "English explanation",
                "de": "Deutsche Erklärung",
                "tr": "Türkçe açıklama",
                "uk": "Українське пояснення",
                "ar": "شرح عربي",
            },
            why_others_wrong={
                "en": {"A": "Wrong A", "C": "Wrong C", "D": "Wrong D"},
                "de": {"A": "Falsch A", "C": "Falsch C", "D": "Falsch D"},
                "tr": {"A": "Yanlış A", "C": "Yanlış C", "D": "Yanlış D"},
                "uk": {
                    "A": "Неправильно A",
                    "C": "Неправильно C",
                    "D": "Неправильно D",
                },
                "ar": {"A": "خاطئ A", "C": "خاطئ C", "D": "خاطئ D"},
            },
            key_concept={
                "en": "Key concept",
                "de": "Schlüsselkonzept",
                "tr": "Ana kavram",
                "uk": "Ключова концепція",
                "ar": "المفهوم الأساسي",
            },
            mnemonic={
                "en": "Memory trick",
                "de": "Gedächtnisstütze",
                "tr": "Hafıza hilesi",
                "uk": "Мнемоніка",
                "ar": "حيلة الذاكرة",
            },
            image_context="Image shows German symbol",
            rag_sources=["source1.de", "source2.de"],
        )

        # Validate all required fields
        assert complete_answer.question_id == 42
        assert complete_answer.correct_answer == "B"
        assert len(complete_answer.explanations) == 5
        assert len(complete_answer.key_concept) == 5
        assert complete_answer.image_context is not None
        assert len(complete_answer.rag_sources) == 2

        # Test minimal answer (optional fields can be None)
        minimal_answer = MultilingualAnswer(
            question_id=1,
            correct_answer="A",
            explanations={"en": "Test"},
            why_others_wrong={"en": {}},
            key_concept={"en": "Test"},
            mnemonic=None,
            image_context=None,
            rag_sources=[],
        )

        assert minimal_answer.mnemonic is None
        assert minimal_answer.image_context is None
        assert minimal_answer.rag_sources == []


class TestAnswerEngineIntegration:
    """Integration tests for AnswerEngine with realistic scenarios."""

    @pytest.mark.slow
    def test_placeholder_for_realistic_multilingual_tests(self):
        """Placeholder for realistic multilingual integration tests.

        These would test:
        - Full multilingual generation with real AI models
        - Quality assessment of generated explanations
        - Cultural appropriateness of translations
        - Performance with large batches of questions
        """
        assert True, "Structure ready for multilingual integration tests"
