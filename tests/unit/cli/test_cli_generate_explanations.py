"""Tests for generate explanations CLI command."""

import sys
from unittest.mock import Mock, patch

import pytest

from src.cli.generate_explanations import main


class TestGenerateExplanationsCLI:
    """Test the generate explanations CLI command."""

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    @patch("src.utils.explanation_generator.ExplanationGenerator")
    def test_cli_basic_generation(self, mock_generator_class, mock_has_gemini, capsys):
        """Test basic explanation generation without RAG."""
        mock_has_gemini.return_value = True

        # Mock the generator instance
        mock_generator = Mock()
        mock_generator.generate_all_explanations.return_value = (True, 10)
        mock_generator_class.return_value = mock_generator

        with (
            patch.object(sys, "argv", ["generate-explanations"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Explanation generation completed successfully!" in captured.out

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    @patch("src.utils.explanation_generator.ExplanationGenerator")
    def test_cli_verbose_mode(self, mock_generator_class, mock_has_gemini, capsys):
        """Test CLI with verbose output."""
        mock_has_gemini.return_value = True

        # Mock the generator instance
        mock_generator = Mock()
        mock_generator.generate_all_explanations.return_value = (True, 10)
        mock_generator_class.return_value = mock_generator

        with (
            patch.object(sys, "argv", ["generate-explanations", "--verbose"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Integran Explanation Generator" in captured.out

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", False)
    def test_cli_no_genai_available(self, capsys):
        """Test CLI when genai is not available."""
        with (
            patch.object(sys, "argv", ["generate-explanations"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "partially complete" in captured.out or "Error" in captured.out

    @patch("src.utils.explanation_generator.GENAI_AVAILABLE", True)
    @patch("src.utils.explanation_generator.has_gemini_config")
    def test_cli_no_gemini_config(self, mock_has_gemini, capsys):
        """Test CLI when Gemini config is missing."""
        mock_has_gemini.return_value = False

        with (
            patch.object(sys, "argv", ["generate-explanations"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "partially complete" in captured.out or "Error" in captured.out
