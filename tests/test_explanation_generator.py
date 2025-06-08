"""Tests for explanation generator module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.utils.explanation_generator import (
    ExplanationBatch,
    ExplanationGenerator,
    QuestionExplanation,
    generate_explanations_cli,
)


class TestQuestionExplanation:
    """Test QuestionExplanation model."""

    def test_question_explanation_creation(self):
        """Test creating a question explanation."""
        explanation = QuestionExplanation(
            question_id=1,
            question_text="Was ist die Hauptstadt von Deutschland?",
            correct_answer="Berlin",
            explanation="Berlin ist seit 1990 die Hauptstadt der Bundesrepublik Deutschland.",
            why_others_wrong={
                "München": "München ist die Hauptstadt von Bayern",
                "Hamburg": "Hamburg ist eine Hansestadt",
            },
            key_concept="Deutsche Hauptstadt",
            mnemonic="Berlin = Bär + Lin",
        )

        assert explanation.question_id == 1
        assert explanation.question_text == "Was ist die Hauptstadt von Deutschland?"
        assert explanation.correct_answer == "Berlin"
        assert "Berlin ist seit 1990" in explanation.explanation
        assert "München" in explanation.why_others_wrong
        assert explanation.key_concept == "Deutsche Hauptstadt"
        assert explanation.mnemonic == "Berlin = Bär + Lin"

    def test_question_explanation_without_mnemonic(self):
        """Test creating explanation without mnemonic."""
        explanation = QuestionExplanation(
            question_id=2,
            question_text="Wann wurde das Grundgesetz verkündet?",
            correct_answer="23. Mai 1949",
            explanation="Das Grundgesetz wurde am 23. Mai 1949 verkündet.",
            why_others_wrong={
                "1945": "Das war Kriegsende",
                "1990": "Das war Wiedervereinigung",
            },
            key_concept="Grundgesetz-Datum",
        )

        assert explanation.mnemonic is None


class TestExplanationBatch:
    """Test ExplanationBatch model."""

    def test_explanation_batch_creation(self):
        """Test creating a batch of explanations."""
        explanation1 = QuestionExplanation(
            question_id=1,
            question_text="Question 1",
            correct_answer="Answer 1",
            explanation="Explanation 1",
            why_others_wrong={},
            key_concept="Concept 1",
        )

        explanation2 = QuestionExplanation(
            question_id=2,
            question_text="Question 2",
            correct_answer="Answer 2",
            explanation="Explanation 2",
            why_others_wrong={},
            key_concept="Concept 2",
        )

        batch = ExplanationBatch(explanations=[explanation1, explanation2])

        assert len(batch.explanations) == 2
        assert batch.explanations[0].question_id == 1
        assert batch.explanations[1].question_id == 2


class TestExplanationGenerator:
    """Test ExplanationGenerator class."""

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", False)
    def test_init_without_genai(self):
        """Test initialization without genai available."""
        with pytest.raises(ImportError, match="google-genai package is required"):
            ExplanationGenerator()

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.genai")
    @patch("src.utils.explanation_generator.get_settings")
    def test_init_with_vertex_ai(self, mock_get_settings, mock_genai):
        """Test initialization with Vertex AI."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "us-central1"
        mock_settings.gemini_model = "gemini-2.5-pro"
        mock_settings.use_vertex_ai = True
        mock_get_settings.return_value = mock_settings

        # Mock genai client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        # Mock RAG availability
        with patch("src.utils.explanation_generator.RAG_AVAILABLE", False):
            generator = ExplanationGenerator()

        assert generator.project_id == "test-project"
        assert generator.region == "us-central1"
        assert generator.model_id == "gemini-2.5-pro"
        assert generator.use_vertex_ai is True
        assert generator.client == mock_client
        assert generator.rag_engine is None

        mock_genai.Client.assert_called_once_with(
            vertexai=True, project="test-project", location="global"
        )

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.genai")
    @patch("src.utils.explanation_generator.get_settings")
    def test_init_with_api_key(self, mock_get_settings, mock_genai):
        """Test initialization with API key."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gemini_api_key = "test-api-key"
        mock_settings.use_vertex_ai = False
        mock_get_settings.return_value = mock_settings

        # Mock genai client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        # Mock RAG availability
        with patch("src.utils.explanation_generator.RAG_AVAILABLE", False):
            generator = ExplanationGenerator()

        assert generator.api_key == "test-api-key"
        assert generator.use_vertex_ai is False
        assert generator.client == mock_client

        mock_genai.Client.assert_called_once_with(api_key="test-api-key")

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.get_settings")
    def test_init_missing_project_id(self, mock_get_settings):
        """Test initialization with missing project ID for Vertex AI."""
        mock_settings = Mock()
        mock_settings.gcp_project_id = ""
        mock_settings.use_vertex_ai = True
        mock_get_settings.return_value = mock_settings

        with pytest.raises(
            ValueError, match="GCP_PROJECT_ID is required for Vertex AI"
        ):
            ExplanationGenerator()

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.get_settings")
    def test_init_missing_api_key(self, mock_get_settings):
        """Test initialization with missing API key."""
        mock_settings = Mock()
        mock_settings.use_vertex_ai = False
        mock_settings.gemini_api_key = ""
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            ExplanationGenerator()

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.genai")
    @patch("src.utils.explanation_generator.get_settings")
    @patch("src.utils.explanation_generator.RAG_AVAILABLE", True)
    @patch("src.utils.explanation_generator.RAGEngine")
    def test_init_with_rag_success(
        self, mock_rag_engine_class, mock_get_settings, _mock_genai
    ):
        """Test initialization with RAG engine successfully."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.gcp_project_id = "test-project"
        mock_settings.use_vertex_ai = True
        mock_get_settings.return_value = mock_settings

        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine_class.return_value = mock_rag_engine

        generator = ExplanationGenerator()

        assert generator.rag_engine == mock_rag_engine
        mock_rag_engine_class.assert_called_once()

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.genai")
    @patch("src.utils.explanation_generator.get_settings")
    @patch("src.utils.explanation_generator.RAG_AVAILABLE", True)
    @patch("src.utils.explanation_generator.RAGEngine")
    def test_init_with_rag_failure(
        self, mock_rag_engine_class, mock_get_settings, _mock_genai
    ):
        """Test initialization with RAG engine failure."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.gcp_project_id = "test-project"
        mock_settings.use_vertex_ai = True
        mock_get_settings.return_value = mock_settings

        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("RAG init failed")

        generator = ExplanationGenerator()

        assert generator.rag_engine is None
        mock_rag_engine_class.assert_called_once()

    def test_get_relevant_context(self):
        """Test getting relevant context for questions."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Test Grundgesetz question
            question = {
                "question": "Was steht in Artikel 1 des Grundgesetzes?",
                "category": "",
            }
            context = generator._get_relevant_context(question)
            assert "Grundgesetz" in context
            assert "Menschenwürde" in context

            # Test political question
            question = {"question": "Wer wählt den Bundeskanzler?", "category": ""}
            context = generator._get_relevant_context(question)
            assert "Bundestag" in context

            # Test history question
            question = {"question": "Wann fiel die Berliner Mauer?", "category": ""}
            context = generator._get_relevant_context(question)
            assert "1989" in context
            assert "Mauer" in context

            # Test states question
            question = {
                "question": "Was ist die Hauptstadt von Bayern?",
                "category": "",
            }
            context = generator._get_relevant_context(question)
            assert "Bayern" in context
            assert "München" in context

            # Test symbols question
            question = {
                "question": "Welche Farben hat die deutsche Flagge?",
                "category": "",
            }
            context = generator._get_relevant_context(question)
            assert "Schwarz-Rot-Gold" in context

    def test_get_batch_context(self):
        """Test getting combined context for a batch of questions."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            questions = [
                {
                    "question": "Was steht in Artikel 1 des Grundgesetzes?",
                    "category": "",
                },
                {"question": "Wer wählt den Bundeskanzler?", "category": ""},
                {"question": "Was ist die Hauptstadt von Bayern?", "category": ""},
            ]

            context = generator._get_batch_context(questions)

            # Should contain context from multiple knowledge areas
            assert "Grundgesetz" in context
            assert "Bundestag" in context
            assert "Bayern" in context

    def test_load_questions_from_checkpoint(self):
        """Test loading questions from extraction checkpoint."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Mock checkpoint file
            checkpoint_data = {
                "state": "completed",
                "questions": [
                    {"id": 1, "question": "Test question 1"},
                    {"id": 2, "question": "Test question 2"},
                ],
            }

            with (
                patch(
                    "builtins.open", mock_open(read_data=json.dumps(checkpoint_data))
                ),
                patch("pathlib.Path.exists", return_value=True),
            ):
                questions = generator.load_questions()

                assert len(questions) == 2
                assert questions[0]["id"] == 1
                assert questions[1]["id"] == 2

    def test_load_questions_from_json_fallback(self):
        """Test loading questions from JSON file as fallback."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Mock JSON file
            questions_data = [
                {"id": 1, "question": "Test question 1"},
                {"id": 2, "question": "Test question 2"},
            ]

            def mock_exists(self):
                # Checkpoint doesn't exist, JSON does
                return "checkpoint" not in str(self)

            with (
                patch("builtins.open", mock_open(read_data=json.dumps(questions_data))),
                patch.object(Path, "exists", mock_exists),
            ):
                questions = generator.load_questions()

                assert len(questions) == 2
                assert questions[0]["id"] == 1

    def test_load_questions_file_not_found(self):
        """Test error when no questions file found."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            with (
                patch("pathlib.Path.exists", return_value=False),
                pytest.raises(FileNotFoundError, match="No questions data found"),
            ):
                generator.load_questions()

    def test_load_explanation_checkpoint_existing(self):
        """Test loading existing explanation checkpoint."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Mock existing checkpoint
            checkpoint_data = {
                "completed_batches": [{"count": 5}],
                "explanations": {"1": {}, "2": {}},
                "state": "in_progress",
            }

            with tempfile.NamedTemporaryFile() as tmp:
                checkpoint_file = Path(tmp.name)

                with (
                    patch(
                        "builtins.open",
                        mock_open(read_data=json.dumps(checkpoint_data)),
                    ),
                    patch("pathlib.Path.exists", return_value=True),
                ):
                    result = generator.load_explanation_checkpoint(checkpoint_file)

                    assert result["state"] == "in_progress"
                    assert len(result["explanations"]) == 2
                    assert len(result["completed_batches"]) == 1

    def test_load_explanation_checkpoint_new(self):
        """Test creating new explanation checkpoint."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            with tempfile.NamedTemporaryFile() as tmp:
                checkpoint_file = Path(tmp.name)

                with patch("pathlib.Path.exists", return_value=False):
                    result = generator.load_explanation_checkpoint(checkpoint_file)

                    assert result["state"] == "in_progress"
                    assert result["explanations"] == {}
                    assert result["completed_batches"] == []
                    assert result["total_questions"] == 0
                    assert "started_at" in result

    def test_should_skip_question(self):
        """Test checking if question should be skipped."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            checkpoint_data = {"explanations": {"1": {}, "3": {}}}

            assert generator.should_skip_question(checkpoint_data, 1) is True
            assert generator.should_skip_question(checkpoint_data, 2) is False
            assert generator.should_skip_question(checkpoint_data, 3) is True

    def test_add_explanations_to_checkpoint(self):
        """Test adding explanations to checkpoint."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            checkpoint_data = {"explanations": {}, "completed_batches": []}

            explanations = [
                {"question_id": 1, "explanation": "Test 1"},
                {"question_id": 2, "explanation": "Test 2"},
            ]

            generator.add_explanations_to_checkpoint(checkpoint_data, explanations)

            assert "1" in checkpoint_data["explanations"]
            assert "2" in checkpoint_data["explanations"]
            assert len(checkpoint_data["completed_batches"]) == 1
            assert checkpoint_data["completed_batches"][0]["count"] == 2
            assert checkpoint_data["completed_batches"][0]["question_ids"] == [1, 2]

    def test_prepare_questions_batch_checkpoint_format(self):
        """Test preparing questions batch from checkpoint format."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            questions = [
                {
                    "id": 1,
                    "question": "Test question 1",
                    "option_a": "Option A",
                    "option_b": "Option B",
                    "option_c": "Option C",
                    "option_d": "Option D",
                    "correct_answer": "B",
                    "category": "Test Category",
                }
            ]

            batch = generator.prepare_questions_batch(questions, 0, 1)

            assert len(batch) == 1
            assert batch[0]["question_id"] == 1
            assert batch[0]["question_text"] == "Test question 1"
            assert batch[0]["correct_answer"] == "Option B"
            assert batch[0]["correct_letter"] == "B"
            assert batch[0]["category"] == "Test Category"
            assert batch[0]["options"]["A"] == "Option A"

    def test_prepare_questions_batch_json_format(self):
        """Test preparing questions batch from JSON format."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            questions = [
                {
                    "id": 1,
                    "question": "Test question 1",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct": "Option B",
                    "category": "Test Category",
                }
            ]

            batch = generator.prepare_questions_batch(questions, 0, 1)

            assert len(batch) == 1
            assert batch[0]["question_id"] == 1
            assert batch[0]["question_text"] == "Test question 1"
            assert batch[0]["correct_answer"] == "Option B"
            assert batch[0]["correct_letter"] == "B"
            assert batch[0]["options"]["B"] == "Option B"

    def test_create_explanation_prompt(self):
        """Test creating explanation prompt."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            questions_batch = [
                {
                    "question_id": 1,
                    "question_text": "Was ist die Hauptstadt?",
                    "options": {"A": "Berlin", "B": "München"},
                    "correct_answer": "Berlin",
                    "is_image_question": False,
                },
                {
                    "question_id": 2,
                    "question_text": "Welches Wappen?",
                    "options": {"A": "Wappen 1", "B": "Wappen 2"},
                    "correct_answer": "Wappen 1",
                    "is_image_question": True,
                },
            ]

            prompt = generator.create_explanation_prompt(questions_batch)

            assert "Du bist ein erfahrener Lehrer" in prompt
            assert "BILDFRAGEN" in prompt
            assert "TEXTFRAGEN" in prompt
            assert "Was ist die Hauptstadt?" in prompt
            assert "Welches Wappen?" in prompt


class TestGenerateExplanationsCLI:
    """Test generate_explanations_cli function."""

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", False)
    def test_cli_genai_not_available(self):
        """Test CLI when genai is not available."""
        result = generate_explanations_cli()
        assert result is False

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    def test_cli_no_gemini_config(self, mock_has_gemini):
        """Test CLI when Gemini config is missing."""
        mock_has_gemini.return_value = False

        result = generate_explanations_cli()
        assert result is False

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    @patch("src.utils.explanation_generator.ExplanationGenerator")
    def test_cli_success(self, mock_generator_class, mock_has_gemini):
        """Test successful CLI execution."""
        mock_has_gemini.return_value = True

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_all_explanations.return_value = (True, 10)
        mock_generator_class.return_value = mock_generator

        result = generate_explanations_cli(batch_size=5, resume=False, use_rag=True)

        assert result is True
        mock_generator.generate_all_explanations.assert_called_once_with(
            batch_size=5, resume=False, use_rag=True
        )

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    @patch("src.utils.explanation_generator.ExplanationGenerator")
    def test_cli_partial_success(self, mock_generator_class, mock_has_gemini):
        """Test partial success CLI execution."""
        mock_has_gemini.return_value = True

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_all_explanations.return_value = (False, 5)
        mock_generator_class.return_value = mock_generator

        result = generate_explanations_cli()

        assert result is False

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    @patch("src.utils.explanation_generator.ExplanationGenerator")
    def test_cli_exception(self, mock_generator_class, mock_has_gemini):
        """Test CLI with exception."""
        mock_has_gemini.return_value = True

        # Mock generator to raise exception
        mock_generator_class.side_effect = Exception("Test error")

        result = generate_explanations_cli()

        assert result is False

    def test_save_explanation_checkpoint(self):
        """Test saving explanation checkpoint."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            checkpoint_data = {
                "completed_batches": [],
                "explanations": {"1": {"question_id": 1}},
                "state": "in_progress",
            }

            with tempfile.NamedTemporaryFile() as tmp:
                checkpoint_file = Path(tmp.name)

                with patch("builtins.open", mock_open()) as mock_file:
                    generator.save_explanation_checkpoint(
                        checkpoint_file, checkpoint_data
                    )

                    # Verify file was opened for writing
                    mock_file.assert_called_once_with(checkpoint_file, "w")

    def test_save_final_explanations(self):
        """Test saving final explanations to JSON."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            explanations = {
                "2": {"question_id": 2, "explanation": "Test 2"},
                "1": {"question_id": 1, "explanation": "Test 1"},
                "3": {"question_id": 3, "explanation": "Test 3"},
            }

            with patch("builtins.open", mock_open()) as mock_file:
                generator.save_final_explanations(explanations)

                # Verify file was opened for writing
                mock_file.assert_called()

    def test_generate_explanations_batch_with_rag_fallback(self):
        """Test RAG batch generation with fallback to basic method."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()
            generator.rag_engine = None  # No RAG engine available

            questions_batch = [
                {
                    "question_id": 1,
                    "question_text": "Test question",
                    "options": {"A": "Option A", "B": "Option B"},
                    "correct_answer": "Option A",
                    "category": "Test",
                }
            ]

            # Mock the basic generation method
            with patch.object(generator, "generate_explanations_batch") as mock_basic:
                mock_basic.return_value = [
                    {"question_id": 1, "explanation": "Test explanation"}
                ]

                result = generator.generate_explanations_batch_with_rag(questions_batch)

                assert len(result) == 1
                assert result[0]["question_id"] == 1
                mock_basic.assert_called_once_with(questions_batch)

    def test_generate_all_explanations_already_completed(self):
        """Test generate_all_explanations when checkpoint shows completion."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Mock questions loading
            questions = [
                {
                    "id": 1,
                    "question": "Q1",
                    "options": ["A1", "B1", "C1", "D1"],
                    "correct": "A1",
                },
                {
                    "id": 2,
                    "question": "Q2",
                    "options": ["A2", "B2", "C2", "D2"],
                    "correct": "A2",
                },
            ]

            with (
                patch.object(generator, "load_questions", return_value=questions),
                patch.object(
                    generator, "load_explanation_checkpoint"
                ) as mock_load_checkpoint,
                patch.object(
                    generator, "save_explanation_checkpoint"
                ) as mock_save_checkpoint,
                patch.object(generator, "save_final_explanations") as mock_save_final,
            ):
                # Mock checkpoint data showing all questions already explained
                checkpoint_data = {
                    "explanations": {
                        "1": {"question_id": 1, "explanation": "Explanation 1"},
                        "2": {"question_id": 2, "explanation": "Explanation 2"},
                    },
                    "total_questions": 2,
                    "state": "in_progress",
                }
                mock_load_checkpoint.return_value = checkpoint_data

                success, count = generator.generate_all_explanations(
                    batch_size=2, resume=True
                )

                assert success is True
                assert count == 0  # No new explanations generated

                # Verify checkpoint was marked as completed
                mock_save_checkpoint.assert_called()
                mock_save_final.assert_called_once()

    def test_generate_all_explanations_partial_completion(self):
        """Test generate_all_explanations with partial completion."""
        with (
            patch("src.utils.explanation_generator.GENAI_AVAILABLE", True),
            patch("src.utils.explanation_generator.genai"),
            patch("src.utils.explanation_generator.get_settings") as mock_settings,
            patch("src.utils.explanation_generator.RAG_AVAILABLE", False),
        ):
            mock_settings.return_value.gcp_project_id = "test"
            mock_settings.return_value.use_vertex_ai = True

            generator = ExplanationGenerator()

            # Mock questions loading
            questions = [
                {
                    "id": 1,
                    "question": "Q1",
                    "options": ["A1", "B1", "C1", "D1"],
                    "correct": "A1",
                },
                {
                    "id": 2,
                    "question": "Q2",
                    "options": ["A2", "B2", "C2", "D2"],
                    "correct": "A2",
                },
                {
                    "id": 3,
                    "question": "Q3",
                    "options": ["A3", "B3", "C3", "D3"],
                    "correct": "A3",
                },
            ]

            with (
                patch.object(generator, "load_questions", return_value=questions),
                patch.object(
                    generator, "load_explanation_checkpoint"
                ) as mock_load_checkpoint,
                patch.object(generator, "save_explanation_checkpoint"),
                patch.object(
                    generator, "generate_explanations_batch"
                ) as mock_generate_batch,
            ):
                # Mock checkpoint data showing partial completion
                checkpoint_data = {
                    "explanations": {"1": {"question_id": 1}},
                    "total_questions": 3,
                    "state": "in_progress",
                    "completed_batches": [],
                }
                mock_load_checkpoint.return_value = checkpoint_data

                # Mock successful generation for remaining questions
                mock_generate_batch.return_value = [
                    {"question_id": 2, "explanation": "Explanation 2"},
                    {"question_id": 3, "explanation": "Explanation 3"},
                ]

                success, count = generator.generate_all_explanations(
                    batch_size=2, resume=True
                )

                # After generating the remaining questions, it should be complete
                assert success is True  # Now complete
                assert count == 2  # Two new explanations generated
