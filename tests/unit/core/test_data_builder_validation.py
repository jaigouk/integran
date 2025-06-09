"""Comprehensive validation tests for the DataBuilder pipeline.

This module focuses on validating the complete data building workflow
and ensuring data integrity throughout the process.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.answer_engine import MultilingualAnswer
from src.core.data_builder import DataBuilder
from src.core.image_processor import ImageDescription


class TestDataBuilderValidation:
    """Validation tests for DataBuilder ensuring data integrity."""

    def create_mock_extraction_checkpoint(self, questions: list[dict]) -> Path:
        """Create a mock extraction checkpoint."""
        checkpoint_data = {"state": "completed", "questions": questions}

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(checkpoint_data, temp_file)
        temp_file.close()

        return Path(temp_file.name)

    def create_mock_multilingual_answer(self, question_id: int) -> MultilingualAnswer:
        """Create a mock multilingual answer for testing."""
        return MultilingualAnswer(
            question_id=question_id,
            correct_answer="A",
            explanations={
                "en": f"English explanation for question {question_id}",
                "de": f"Deutsche Erklärung für Frage {question_id}",
                "tr": f"Türkçe açıklama soru {question_id}",
                "uk": f"Українське пояснення питання {question_id}",
                "ar": f"شرح باللغة العربية للسؤال {question_id}",
            },
            why_others_wrong={
                "en": {
                    "B": "Wrong because...",
                    "C": "Also wrong...",
                    "D": "Incorrect...",
                },
                "de": {
                    "B": "Falsch weil...",
                    "C": "Auch falsch...",
                    "D": "Nicht richtig...",
                },
                "tr": {
                    "B": "Yanlış çünkü...",
                    "C": "Bu da yanlış...",
                    "D": "Doğru değil...",
                },
                "uk": {
                    "B": "Неправильно тому що...",
                    "C": "Також неправильно...",
                    "D": "Некоректно...",
                },
                "ar": {"B": "خاطئ لأن...", "C": "خاطئ أيضا...", "D": "غير صحيح..."},
            },
            key_concept={
                "en": f"Key concept {question_id}",
                "de": f"Schlüsselkonzept {question_id}",
                "tr": f"Ana kavram {question_id}",
                "uk": f"Ключова концепція {question_id}",
                "ar": f"المفهوم الأساسي {question_id}",
            },
            mnemonic={
                "en": f"Memory aid {question_id}",
                "de": f"Gedächtnisstütze {question_id}",
                "tr": f"Hafıza yardımcısı {question_id}",
                "uk": f"Мнемонічний прийом {question_id}",
                "ar": f"مساعد الذاكرة {question_id}",
            },
            image_context=f"Image context for question {question_id}"
            if question_id % 2 == 0
            else None,
            rag_sources=[f"source1_{question_id}.de", f"source2_{question_id}.de"],
        )

    @patch("src.core.data_builder.ImageProcessor")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.has_gemini_config")
    def test_complete_workflow_validation(
        self, mock_has_config, mock_answer_engine, mock_image_processor
    ):
        """Test complete workflow with realistic data validates correctly."""
        mock_has_config.return_value = True

        # Create realistic test questions
        test_questions = [
            {
                "id": 21,
                "question": "Welches ist das Wappen der BRD?",
                "page_number": 9,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
                "correct_answer": "A",
                "category": "Symbols",
                "difficulty": "medium",
            },
            {
                "id": 150,
                "question": "Wann wurde die BRD gegründet?",
                "page_number": 120,
                "option_a": "1945",
                "option_b": "1949",
                "option_c": "1950",
                "option_d": "1951",
                "correct_answer": "B",
                "category": "History",
                "difficulty": "easy",
            },
            {
                "id": 275,
                "question": "Welches Wappen gehört zu Bayern?",
                "page_number": 78,
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
                "correct_answer": "C",
                "category": "Federal States",
                "difficulty": "medium",
            },
        ]

        # Mock ImageProcessor
        mock_processor = Mock()
        mock_image_processor.return_value = mock_processor

        # Mock image processing results
        question_image_mapping = {
            21: ["data/images/page_9_img_1.png"],
            275: ["data/images/page_78_img_1.png"],
        }
        image_descriptions = {
            "data/images/page_9_img_1.png": ImageDescription(
                path="data/images/page_9_img_1.png",
                description="German federal eagle",
                visual_elements=["eagle", "yellow", "black"],
                context="Official German coat of arms",
                question_relevance="State symbols identification",
            ),
            "data/images/page_78_img_1.png": ImageDescription(
                path="data/images/page_78_img_1.png",
                description="Bavarian coat of arms",
                visual_elements=["blue", "white", "lion"],
                context="Bavarian state symbol",
                question_relevance="Federal state identification",
            ),
        }

        mock_processor.process_all_images.return_value = (
            question_image_mapping,
            image_descriptions,
        )

        # Mock AnswerEngine
        mock_engine = Mock()
        mock_answer_engine.return_value = mock_engine

        # Mock multilingual answers
        mock_answers = [
            self.create_mock_multilingual_answer(21),
            self.create_mock_multilingual_answer(150),
            self.create_mock_multilingual_answer(275),
        ]
        mock_engine.generate_batch_answers.return_value = mock_answers

        # Create test environment
        temp_dir = tempfile.mkdtemp()
        extraction_checkpoint = self.create_mock_extraction_checkpoint(test_questions)

        with (
            patch("src.core.data_builder.Path") as mock_path_class,
            patch("builtins.open", create=True) as mock_open,
            patch("json.load") as mock_json_load,
            patch("json.dump") as mock_json_dump,
        ):
            # Mock file operations
            mock_path_class.return_value.exists.return_value = True
            mock_json_load.return_value = {
                "state": "completed",
                "questions": test_questions,
            }

            # Initialize builder
            builder = DataBuilder()
            builder.checkpoint_file = Path(temp_dir) / "dataset_checkpoint.json"

            # Mock the extraction checkpoint loading
            with patch.object(
                builder, "_load_questions_from_extraction", return_value=test_questions
            ):
                result = builder.build_complete_dataset(
                    force_rebuild=True, use_rag=True, multilingual=True
                )

            # Verify successful completion
            assert result is True

            # Verify image processing was called
            mock_processor.process_all_images.assert_called_once()

            # Verify answer generation was called with correct parameters
            mock_engine.generate_batch_answers.assert_called()
            call_args = mock_engine.generate_batch_answers.call_args

            # Validate the questions passed to answer generation
            questions_arg = call_args[1]["questions"]
            assert len(questions_arg) == 3
            assert any(q["id"] == 21 for q in questions_arg)
            assert any(q["id"] == 150 for q in questions_arg)
            assert any(q["id"] == 275 for q in questions_arg)

            # Validate image mapping passed correctly
            mapping_arg = call_args[1]["question_image_mapping"]
            assert 21 in mapping_arg
            assert 275 in mapping_arg
            assert 150 not in mapping_arg  # Not an image question

            # Verify final dataset saving was called
            mock_json_dump.assert_called()

    @patch("src.core.data_builder.ImageProcessor")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.has_gemini_config")
    def test_final_dataset_structure_validation(
        self, mock_has_config, mock_answer_engine, mock_image_processor
    ):
        """Test that the final dataset structure is correct and complete."""
        mock_has_config.return_value = True

        # Setup mocks
        mock_processor = Mock()
        mock_image_processor.return_value = mock_processor
        mock_processor.process_all_images.return_value = ({}, {})

        mock_engine = Mock()
        mock_answer_engine.return_value = mock_engine
        mock_engine.generate_batch_answers.return_value = []

        builder = DataBuilder()

        # Test data
        test_questions = [
            {
                "id": 21,
                "question": "Test question",
                "option_a": "Bild 1",
                "option_b": "Bild 2",
                "option_c": "Bild 3",
                "option_d": "Bild 4",
                "correct_answer": "A",
                "category": "Test",
                "difficulty": "medium",
            }
        ]

        test_answers = [self.create_mock_multilingual_answer(21)]

        test_mapping = {21: ["data/images/page_9_img_1.png"]}

        test_descriptions = {
            "data/images/page_9_img_1.png": ImageDescription(
                path="data/images/page_9_img_1.png",
                description="Test image",
                visual_elements=["test"],
                context="Test context",
                question_relevance="Test relevance",
            )
        }

        # Capture the final dataset when it's saved
        saved_dataset = None

        def capture_json_dump(data, file, **kwargs):
            nonlocal saved_dataset
            saved_dataset = data

        with (
            patch("builtins.open", create=True),
            patch("json.dump", side_effect=capture_json_dump),
        ):
            builder._save_final_dataset(
                test_questions, test_answers, test_mapping, test_descriptions
            )

        # Validate final dataset structure
        assert saved_dataset is not None
        assert len(saved_dataset) == 1

        question = saved_dataset[0]

        # Validate basic structure
        assert question["id"] == 21
        assert question["question"] == "Test question"
        assert len(question["options"]) == 4
        assert question["correct"] == "A"
        assert question["category"] == "Test"
        assert question["difficulty"] == "medium"

        # Validate images section
        assert "images" in question
        assert len(question["images"]) == 1
        image = question["images"][0]
        assert image["path"] == "images/page_9_img_1.png"  # Should be relative
        assert image["description"] == "Test image"
        assert image["context"] == "Test context"

        # Validate multilingual answers
        assert "answers" in question
        answers = question["answers"]

        # Check all 5 languages are present
        required_languages = ["en", "de", "tr", "uk", "ar"]
        for lang in required_languages:
            assert lang in answers
            assert "explanation" in answers[lang]
            assert "why_others_wrong" in answers[lang]
            assert "key_concept" in answers[lang]
            assert "mnemonic" in answers[lang]

        # Validate RAG sources
        assert "rag_sources" in question
        assert len(question["rag_sources"]) == 2

    @patch("src.core.data_builder.ImageProcessor")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.has_gemini_config")
    def test_checkpoint_recovery_validation(
        self, mock_has_config, mock_answer_engine, mock_image_processor
    ):
        """Test that checkpoint recovery works correctly and maintains data integrity."""
        mock_has_config.return_value = True

        # Setup mocks
        mock_processor = Mock()
        mock_image_processor.return_value = mock_processor
        mock_processor.process_all_images.return_value = (
            {21: ["img1.png"]},
            {"img1.png": Mock()},
        )

        mock_engine = Mock()
        mock_answer_engine.return_value = mock_engine

        # Create a partial checkpoint (simulating interrupted build)
        existing_checkpoint = {
            "state": "in_progress",
            "started_at": "2025-01-09T12:00:00",
            "images_processed": True,
            "total_questions": 3,
            "question_image_mapping": {"21": ["img1.png"]},
            "image_descriptions": {
                "img1.png": {"path": "img1.png", "description": "test"}
            },
            "completed_answers": {
                "21": {
                    "question_id": 21,
                    "correct_answer": "A",
                    "explanations": {"en": "Test explanation"},
                    "why_others_wrong": {"en": {}},
                    "key_concept": {"en": "Test"},
                    "mnemonic": None,
                    "image_context": None,
                    "rag_sources": [],
                }
            },
        }

        test_questions = [
            {"id": 21, "question": "Completed question", "correct_answer": "A"},
            {"id": 22, "question": "Pending question", "correct_answer": "B"},
            {"id": 23, "question": "Another pending", "correct_answer": "C"},
        ]

        # Mock only generating answers for pending questions
        mock_engine.generate_batch_answers.return_value = [
            self.create_mock_multilingual_answer(22),
            self.create_mock_multilingual_answer(23),
        ]

        with (
            patch("builtins.open", create=True),
            patch("json.load", return_value=existing_checkpoint),
            patch("json.dump") as mock_save,
            patch.object(
                DataBuilder,
                "_load_questions_from_extraction",
                return_value=test_questions,
            ),
        ):
            builder = DataBuilder()
            builder.checkpoint_file = Path("test_checkpoint.json")

            # Mock checkpoint file existence
            with patch.object(builder.checkpoint_file, "exists", return_value=True):
                result = builder.build_complete_dataset(force_rebuild=False)

            assert result is True

            # Verify that only pending questions were processed
            mock_engine.generate_batch_answers.assert_called()
            call_args = mock_engine.generate_batch_answers.call_args
            questions_processed = call_args[1]["questions"]

            # Should only process questions 22 and 23 (21 was already completed)
            processed_ids = {q["id"] for q in questions_processed}
            assert processed_ids == {22, 23}
            assert 21 not in processed_ids

    def test_data_integrity_validation(self):
        """Test validation methods for data integrity."""
        builder = DataBuilder()

        # Test serialization/deserialization integrity
        original_answer = self.create_mock_multilingual_answer(42)

        # Serialize and deserialize
        serialized = builder._serialize_answer(original_answer)
        deserialized = builder._deserialize_answer(serialized)

        # Verify all fields are preserved
        assert deserialized.question_id == original_answer.question_id
        assert deserialized.correct_answer == original_answer.correct_answer
        assert deserialized.explanations == original_answer.explanations
        assert deserialized.why_others_wrong == original_answer.why_others_wrong
        assert deserialized.key_concept == original_answer.key_concept
        assert deserialized.mnemonic == original_answer.mnemonic
        assert deserialized.image_context == original_answer.image_context
        assert deserialized.rag_sources == original_answer.rag_sources

    @patch("src.core.data_builder.ImageProcessor")
    @patch("src.core.data_builder.AnswerEngine")
    @patch("src.core.data_builder.has_gemini_config")
    def test_build_status_accuracy(
        self, mock_has_config, mock_answer_engine, mock_image_processor
    ):
        """Test that build status reporting is accurate."""
        mock_has_config.return_value = True

        builder = DataBuilder()

        # Test 1: No checkpoint file exists
        with patch.object(builder.checkpoint_file, "exists", return_value=False):
            status = builder.get_build_status()
            assert status["state"] == "not_started"

        # Test 2: Checkpoint exists with partial progress
        checkpoint_data = {
            "state": "in_progress",
            "started_at": "2025-01-09T12:00:00",
            "images_processed": True,
            "total_questions": 100,
            "completed_answers": {str(i): {} for i in range(30)},  # 30 completed
        }

        with (
            patch.object(builder.checkpoint_file, "exists", return_value=True),
            patch("builtins.open", create=True),
            patch("json.load", return_value=checkpoint_data),
        ):
            status = builder.get_build_status()

            assert status["state"] == "in_progress"
            assert status["total_questions"] == 100
            assert status["completed_answers"] == 30
            assert status["progress_percent"] == 30.0
            assert status["images_processed"] is True
            assert status["started_at"] == "2025-01-09T12:00:00"

    def test_error_handling_validation(self):
        """Test that error handling preserves data integrity."""
        with (
            patch(
                "src.core.data_builder.ImageProcessor",
                side_effect=Exception("Image processing failed"),
            ),
            patch("src.core.data_builder.AnswerEngine"),
            patch("src.core.data_builder.has_gemini_config", return_value=True),
        ):
            builder = DataBuilder()

            # Should handle errors gracefully and return False
            result = builder.build_complete_dataset()
            assert result is False


class TestDataBuilderIntegration:
    """Integration tests for DataBuilder with realistic scenarios."""

    @pytest.mark.slow
    def test_placeholder_for_realistic_integration_tests(self):
        """Placeholder for realistic integration tests.

        These would test:
        - Complete workflow with realistic question counts (460 questions)
        - Memory usage and performance under realistic load
        - Recovery from various failure scenarios
        - Validation against known good datasets
        """
        assert True, "Structure ready for realistic integration tests"
