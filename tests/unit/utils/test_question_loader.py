"""Tests for question_loader utility."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.question_loader import ensure_questions_available


class TestQuestionLoader:
    """Test the question loader utility."""

    @patch("src.utils.question_loader.get_settings")
    def test_ensure_questions_available_existing_file(self, mock_get_settings):
        """Test when questions file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock questions file
            questions_file = Path(temp_dir) / "questions.json"
            questions_file.write_text('{"test": "data"}')

            # Mock settings to point to our test file
            mock_settings = Mock()
            mock_settings.questions_json_path = str(questions_file)
            mock_get_settings.return_value = mock_settings

            # Should return the existing file path
            result = ensure_questions_available()
            assert result == questions_file

    @patch("src.utils.question_loader.get_settings")
    def test_ensure_questions_available_with_checkpoint(self, mock_get_settings):
        """Test when checkpoint file exists but not questions file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create checkpoint file
            checkpoint_file = Path(temp_dir) / "direct_extraction_checkpoint.json"
            checkpoint_file.write_text('{"checkpoint": "data"}')

            # Mock settings to point to non-existent questions file
            mock_settings = Mock()
            mock_settings.questions_json_path = str(Path(temp_dir) / "questions.json")
            mock_get_settings.return_value = mock_settings

            # Should raise FileNotFoundError with checkpoint message
            with patch("src.utils.question_loader.Path") as mock_path:
                # Mock the checkpoint path to exist
                mock_checkpoint = Mock()
                mock_checkpoint.exists.return_value = True
                mock_path.side_effect = lambda x: (
                    mock_checkpoint
                    if "checkpoint" in str(x)
                    else Mock(exists=Mock(return_value=False))
                )

                with pytest.raises(FileNotFoundError) as exc_info:
                    ensure_questions_available()

                assert "checkpoint exists" in str(exc_info.value)

    @patch("src.utils.question_loader.get_settings")
    def test_ensure_questions_available_no_files(self, mock_get_settings):
        """Test when no files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock settings to point to non-existent files
            mock_settings = Mock()
            mock_settings.questions_json_path = str(Path(temp_dir) / "questions.json")
            mock_get_settings.return_value = mock_settings

            # Should raise FileNotFoundError with general message
            with patch("src.utils.question_loader.Path") as mock_path:
                # Mock both paths to not exist
                mock_file = Mock()
                mock_file.exists.return_value = False
                mock_path.return_value = mock_file

                with pytest.raises(FileNotFoundError) as exc_info:
                    ensure_questions_available()

                assert "Questions file not found" in str(exc_info.value)
                assert "integran-direct-extract" in str(exc_info.value)
