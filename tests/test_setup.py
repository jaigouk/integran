"""Tests for src/setup.py module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from src.setup import _create_config_file, _create_sample_questions, main


class TestMainCommand:
    """Test the main CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_option(self):
        """Test --version option."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "integran-setup, version 0.1.0" in result.output

    def test_help_option(self):
        """Test --help option."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Initialize Integran database and load questions" in result.output
        assert "--force" in result.output
        assert "--questions-file" in result.output

    @patch("src.setup.DatabaseManager")
    @patch("src.setup.console.print")
    @patch("src.setup._create_config_file")
    @patch("src.setup.ensure_questions_available")
    def test_basic_setup_success(
        self, mock_ensure_questions, mock_create_config, mock_print, mock_db_class
    ):
        """Test basic setup without questions file."""
        mock_db = Mock()
        mock_db.load_questions.return_value = 3
        mock_db_class.return_value = mock_db

        # Mock successful questions finding
        questions_path = Path("data/questions.json")
        mock_ensure_questions.return_value = questions_path

        result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        mock_db_class.assert_called_once()
        mock_create_config.assert_called_once()
        mock_ensure_questions.assert_called_once()
        mock_db.load_questions.assert_called_once_with(questions_path)

        # Verify success messages
        print_calls = [
            call[0][0] if call[0] else str(call) for call in mock_print.call_args_list
        ]
        setup_text = " ".join(print_calls)
        assert "Setup completed successfully" in setup_text

    @patch("src.setup.DatabaseManager")
    @patch("src.setup.console.print")
    @patch("src.setup._create_config_file")
    @patch("src.setup._create_sample_questions")
    @patch("src.setup.ensure_questions_available")
    def test_setup_with_sample_questions(
        self,
        mock_ensure_questions,
        mock_create_sample,
        _mock_create_config,
        mock_print,
        mock_db_class,
    ):
        """Test setup with sample questions creation."""
        mock_db = Mock()
        mock_db.load_questions.return_value = 3
        mock_db_class.return_value = mock_db

        # Mock ensure_questions_available to raise FileNotFoundError
        mock_ensure_questions.side_effect = FileNotFoundError("No questions data found")

        with tempfile.TemporaryDirectory(), patch("src.setup.Path") as mock_path_class:

            def path_side_effect(path_str):
                if path_str == "data":
                    # Mock data directory that doesn't exist yet
                    mock_data_dir = Mock()
                    mock_data_dir.exists.return_value = False
                    return mock_data_dir
                else:
                    # Mock questions file that doesn't exist
                    mock_questions_file = Mock()
                    mock_questions_file.exists.return_value = False
                    return mock_questions_file

            mock_path_class.side_effect = path_side_effect

            # Mock click.confirm to return True (create sample)
            with patch("src.setup.click.confirm", return_value=True):
                result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        mock_create_sample.assert_called_once()
        mock_db.load_questions.assert_called_once()

        # Verify sample creation messages
        print_calls = [
            call[0][0] if call[0] else str(call) for call in mock_print.call_args_list
        ]
        setup_text = " ".join(print_calls)
        assert "Sample questions created" in setup_text
        assert "Successfully loaded 3 questions" in setup_text

    def test_setup_with_existing_questions_file(self):
        """Test setup when questions file already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary questions file
            questions_file = Path(temp_dir) / "questions.json"
            sample_questions = [
                {
                    "id": 1,
                    "question": "Test question?",
                    "options": ["A", "B", "C", "D"],
                    "correct": "A",
                    "category": "Test",
                    "difficulty": "easy",
                }
            ]
            questions_file.write_text(json.dumps(sample_questions))

            with patch("src.setup.DatabaseManager") as mock_db_class:
                mock_db = Mock()
                mock_db.load_questions.return_value = 1
                mock_db_class.return_value = mock_db

                with patch("src.setup._create_config_file"):
                    result = self.runner.invoke(
                        main, ["--questions-file", str(questions_file)]
                    )

            assert result.exit_code == 0
            mock_db.load_questions.assert_called_once_with(questions_file)

    @patch("src.setup.DatabaseManager")
    @patch("src.setup.click.confirm")
    @patch("src.setup.ensure_questions_available")
    def test_setup_existing_database_cancel(
        self, mock_ensure_questions, mock_confirm, mock_db_class
    ):
        """Test setup when database exists and user cancels."""
        mock_confirm.return_value = False
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock successful questions finding
        questions_path = Path("data/questions.json")
        mock_ensure_questions.return_value = questions_path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake database file
            data_dir = Path(temp_dir) / "data"
            data_dir.mkdir()
            (data_dir / "trainer.db").touch()

            with patch("src.setup.Path") as mock_path_class:
                mock_path_class.side_effect = (
                    lambda x: Path(temp_dir) / x if x == "data" else Mock()
                )

                result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Setup cancelled" in result.output

    @patch("src.setup.DatabaseManager")
    @patch("src.setup.click.confirm")
    @patch("src.setup._create_config_file")
    @patch("src.setup.ensure_questions_available")
    def test_setup_existing_database_continue(
        self, mock_ensure_questions, mock_create_config, mock_confirm, mock_db_class
    ):
        """Test setup when database exists and user continues."""
        mock_confirm.return_value = True
        mock_db = Mock()
        mock_db.load_questions.return_value = 3
        mock_db_class.return_value = mock_db

        # Mock successful questions finding
        questions_path = Path("data/questions.json")
        mock_ensure_questions.return_value = questions_path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake database file
            data_dir = Path(temp_dir) / "data"
            data_dir.mkdir()
            (data_dir / "trainer.db").touch()

            with patch("src.setup.Path") as mock_path_class:
                mock_path_class.side_effect = (
                    lambda x: Path(temp_dir) / x if x == "data" else Mock()
                )

                result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        mock_create_config.assert_called_once()
        mock_db.load_questions.assert_called_once_with(questions_path)

    @patch("src.setup.DatabaseManager")
    @patch("src.setup.ensure_questions_available")
    def test_setup_force_flag(self, mock_ensure_questions, mock_db_class):
        """Test setup with --force flag."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock ensure_questions_available to return a questions file path
        mock_ensure_questions.return_value = Path("data/questions.json")

        with (
            patch("src.setup._create_config_file"),
            patch("src.setup.Path") as mock_path_class,
        ):
            mock_path_class.return_value = Mock(exists=Mock(return_value=False))

            with patch("src.setup.click.confirm", return_value=False):
                result = self.runner.invoke(main, ["--force"])

        assert result.exit_code == 0
        # With --force, should not prompt user about existing database

    @patch("src.setup.DatabaseManager")
    def test_setup_questions_load_error(self, mock_db_class):
        """Test setup when question loading fails."""
        mock_db = Mock()
        mock_db.load_questions.side_effect = Exception("Load error")
        mock_db_class.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            questions_file = Path(temp_dir) / "questions.json"
            questions_file.write_text("[]")

            result = self.runner.invoke(main, ["--questions-file", str(questions_file)])

        assert result.exit_code == 1
        assert "Error loading questions: Load error" in result.output

    @patch("src.setup.DatabaseManager")
    def test_keyboard_interrupt(self, mock_db_class):
        """Test keyboard interrupt handling."""
        mock_db_class.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Setup interrupted" in result.output

    @patch("src.setup.DatabaseManager")
    def test_general_exception(self, mock_db_class):
        """Test general exception handling."""
        mock_db_class.side_effect = Exception("Test error")

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Setup failed: Test error" in result.output


class TestCreateSampleQuestions:
    """Test the create sample questions function."""

    def test_create_sample_questions(self):
        """Test creating sample questions file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            questions_file = Path(temp_dir) / "questions.json"

            _create_sample_questions(questions_file)

            assert questions_file.exists()

            # Verify content
            with open(questions_file, encoding="utf-8") as f:
                questions = json.load(f)

            assert len(questions) == 3
            assert questions[0]["id"] == 1
            assert questions[0]["category"] == "Grundrechte"
            assert questions[1]["category"] == "Demokratie und Wahlen"
            assert questions[2]["category"] == "Geschichte"

            # Verify structure
            for question in questions:
                assert "id" in question
                assert "question" in question
                assert "options" in question
                assert "correct" in question
                assert "category" in question
                assert "difficulty" in question
                assert len(question["options"]) == 4
                assert question["correct"] in question["options"]

    def test_create_sample_questions_creates_directory(self):
        """Test that creating sample questions creates parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            questions_file = Path(temp_dir) / "subdir" / "questions.json"

            _create_sample_questions(questions_file)

            assert questions_file.exists()
            assert questions_file.parent.exists()


class TestCreateConfigFile:
    """Test the create config file function."""

    @patch("src.setup.console.print")
    def test_create_config_file_new(self, mock_print):
        """Test creating new config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            with patch("src.setup.Path", return_value=config_file):
                _create_config_file()

            assert config_file.exists()

            # Verify content
            with open(config_file) as f:
                config = json.load(f)

            expected_keys = [
                "repetition_interval",
                "max_daily_questions",
                "show_explanations",
                "color_mode",
                "terminal_width",
                "question_timeout",
                "auto_save",
                "spaced_repetition",
            ]

            for key in expected_keys:
                assert key in config

            # Verify some specific values
            assert config["repetition_interval"] == 3
            assert config["max_daily_questions"] == 50
            assert config["show_explanations"] is True
            assert config["spaced_repetition"] is True

            mock_print.assert_called_once()

    def test_create_config_file_existing(self):
        """Test that existing config file is not overwritten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            # Create existing config
            original_config = {"test": "value"}
            with open(config_file, "w") as f:
                json.dump(original_config, f)

            with (
                patch("src.setup.Path", return_value=config_file),
                patch("src.setup.console.print") as mock_print,
            ):
                _create_config_file()

            # Verify original content unchanged
            with open(config_file) as f:
                config = json.load(f)

            assert config == original_config
            mock_print.assert_not_called()

    @patch("src.setup.console.print")
    def test_create_config_file_creates_directory(self, mock_print):
        """Test that creating config file creates parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "subdir" / "config.json"

            with patch("src.setup.Path", return_value=config_file):
                _create_config_file()

            assert config_file.exists()
            assert config_file.parent.exists()
            mock_print.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios."""

    def test_complete_setup_flow(self):
        """Test complete setup flow from start to finish."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create questions file
            questions_file = Path(temp_dir) / "questions.json"
            sample_questions = [
                {
                    "id": 1,
                    "question": "Test question?",
                    "options": ["A", "B", "C", "D"],
                    "correct": "A",
                    "category": "Test",
                    "difficulty": "easy",
                }
            ]
            questions_file.write_text(json.dumps(sample_questions))

            with patch("src.setup.DatabaseManager") as mock_db_class:
                mock_db = Mock()
                mock_db.load_questions.return_value = 1
                mock_db_class.return_value = mock_db

                # Mock Path for data directory and config
                with patch("src.setup.Path") as mock_path_class:

                    def path_side_effect(path_str):
                        if path_str == "data":
                            return Path(temp_dir) / "data"
                        elif path_str.endswith("config.json"):
                            return Path(temp_dir) / "config.json"
                        else:
                            return questions_file

                    mock_path_class.side_effect = path_side_effect

                    result = runner.invoke(
                        main, ["--questions-file", str(questions_file)]
                    )

            assert result.exit_code == 0
            assert "Setup completed successfully" in result.output
            assert "Successfully loaded 1 questions" in result.output
