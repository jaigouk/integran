"""Simple tests for question_loader utility."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.utils.question_loader import ensure_questions_available


class TestQuestionLoader:
    """Test question loader utility."""

    @patch("src.utils.question_loader.get_settings")
    @patch("src.utils.question_loader.Path")
    def test_ensure_questions_available_json_exists(
        self, mock_path_class, mock_get_settings
    ):
        """Test when JSON file exists."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.questions_json_path = "data/questions.json"
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior
        mock_json_path = MagicMock()
        mock_json_path.exists.return_value = True
        mock_checkpoint_path = MagicMock()

        def path_side_effect(path_str):
            if "questions.json" in str(path_str):
                return mock_json_path
            elif "checkpoint" in str(path_str):
                return mock_checkpoint_path
            return MagicMock()

        mock_path_class.side_effect = path_side_effect

        result = ensure_questions_available()
        assert result == mock_json_path

    @patch("src.utils.question_loader.get_settings")
    @patch("src.utils.question_loader.Path")
    def test_ensure_questions_available_checkpoint_exists(
        self, mock_path_class, mock_get_settings
    ):
        """Test when checkpoint file exists but JSON doesn't."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.questions_json_path = "data/questions.json"
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior
        mock_json_path = MagicMock()
        mock_json_path.exists.return_value = False
        mock_checkpoint_path = MagicMock()
        mock_checkpoint_path.exists.return_value = True

        def path_side_effect(path_str):
            if "questions.json" in str(path_str):
                return mock_json_path
            elif "checkpoint" in str(path_str):
                return mock_checkpoint_path
            return MagicMock()

        mock_path_class.side_effect = path_side_effect

        with pytest.raises(FileNotFoundError) as exc_info:
            ensure_questions_available()

        assert "extraction checkpoint exists" in str(exc_info.value)
        assert "integran-build-dataset" in str(exc_info.value)

    @patch("src.utils.question_loader.get_settings")
    @patch("src.utils.question_loader.Path")
    def test_ensure_questions_available_no_files(
        self, mock_path_class, mock_get_settings
    ):
        """Test when no files exist."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.questions_json_path = "data/questions.json"
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior
        mock_json_path = MagicMock()
        mock_json_path.exists.return_value = False
        mock_checkpoint_path = MagicMock()
        mock_checkpoint_path.exists.return_value = False

        def path_side_effect(path_str):
            if "questions.json" in str(path_str):
                return mock_json_path
            elif "checkpoint" in str(path_str):
                return mock_checkpoint_path
            return MagicMock()

        mock_path_class.side_effect = path_side_effect

        with pytest.raises(FileNotFoundError) as exc_info:
            ensure_questions_available()

        assert "Questions file not found" in str(exc_info.value)
        assert "integran-direct-extract" in str(exc_info.value)
        assert "integran-build-dataset" in str(exc_info.value)
