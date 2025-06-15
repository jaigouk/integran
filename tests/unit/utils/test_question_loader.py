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

    @patch("src.utils.question_loader.logger")
    @patch("src.utils.question_loader.get_settings")
    def test_ensure_questions_available_logging(self, mock_get_settings, mock_logger):
        """Test that logging occurs when file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock questions file
            questions_file = Path(temp_dir) / "questions.json"
            questions_file.write_text('{"test": "data"}')

            # Mock settings to point to our test file
            mock_settings = Mock()
            mock_settings.questions_json_path = str(questions_file)
            mock_get_settings.return_value = mock_settings

            # Call the function
            ensure_questions_available()

            # Verify logging was called
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "Using existing questions file" in log_message

    @patch("src.utils.question_loader.get_settings")
    def test_path_construction(self, mock_get_settings):
        """Test that Path objects are constructed correctly."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.questions_json_path = "test/path/questions.json"
        mock_get_settings.return_value = mock_settings

        # This will fail because files don't exist, but we can verify Path construction
        with pytest.raises(FileNotFoundError):
            ensure_questions_available()

        # Verify get_settings was called
        mock_get_settings.assert_called_once()

    @patch("src.utils.question_loader.get_settings")
    def test_checkpoint_error_message_detail(self, mock_get_settings):
        """Test detailed checkpoint error message."""
        mock_settings = Mock()
        mock_settings.questions_json_path = "data/questions.json"
        mock_get_settings.return_value = mock_settings

        # Mock to simulate checkpoint exists but questions.json doesn't
        with patch("src.utils.question_loader.Path") as mock_path:

            def path_side_effect(path_str):
                mock_path_obj = Mock()
                if "checkpoint" in str(path_str):
                    mock_path_obj.exists.return_value = True
                else:
                    mock_path_obj.exists.return_value = False
                return mock_path_obj

            mock_path.side_effect = path_side_effect

            with pytest.raises(FileNotFoundError) as exc_info:
                ensure_questions_available()

            error_msg = str(exc_info.value)
            assert "However, extraction checkpoint exists" in error_msg
            assert "integran-build-dataset" in error_msg
            assert "Copy the checkpoint file" in error_msg

    @patch("src.utils.question_loader.get_settings")
    def test_no_files_error_message_detail(self, mock_get_settings):
        """Test detailed error message when no files exist."""
        mock_settings = Mock()
        mock_settings.questions_json_path = "data/questions.json"
        mock_get_settings.return_value = mock_settings

        # Mock all paths to not exist
        with patch("src.utils.question_loader.Path") as mock_path:
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = False
            mock_path.return_value = mock_path_obj

            with pytest.raises(FileNotFoundError) as exc_info:
                ensure_questions_available()

            error_msg = str(exc_info.value)
            assert "integran-direct-extract" in error_msg
            assert "integran-build-dataset" in error_msg
            assert "processed questions" in error_msg

    def test_import_and_module_structure(self):
        """Test that the module can be imported and has expected structure."""
        from src.utils import question_loader

        assert hasattr(question_loader, "ensure_questions_available")
        assert callable(question_loader.ensure_questions_available)
        assert hasattr(question_loader, "logger")

    @patch("src.utils.question_loader.get_settings")
    def test_return_type_is_path(self, mock_get_settings):
        """Test that function returns a Path object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock questions file
            questions_file = Path(temp_dir) / "questions.json"
            questions_file.write_text('{"test": "data"}')

            # Mock settings
            mock_settings = Mock()
            mock_settings.questions_json_path = str(questions_file)
            mock_get_settings.return_value = mock_settings

            # Call function and verify return type
            result = ensure_questions_available()
            assert isinstance(result, Path)
            assert result.exists()
            assert result.name == "questions.json"
