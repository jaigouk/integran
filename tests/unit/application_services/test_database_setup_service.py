"""Tests for database setup service."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.application_services.setup.database_setup_service import (
    _create_config_file,
    _create_sample_questions,
    _initialize_user_settings,
    main,
)


class TestDatabaseSetupService:
    """Test database setup service functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_create_sample_questions(self, temp_dir: Path) -> None:
        """Test creating sample questions file."""
        questions_file = temp_dir / "questions.json"

        _create_sample_questions(questions_file)

        # Verify file was created
        assert questions_file.exists()

        # Verify content
        with open(questions_file, encoding="utf-8") as f:
            questions = json.load(f)

        assert len(questions) == 3
        assert questions[0]["id"] == 1
        assert "Regierung sagen" in questions[0]["question"]
        assert "hier Meinungsfreiheit gilt." in questions[0]["options"]
        assert questions[0]["category"] == "Grundrechte"
        assert questions[1]["difficulty"] == "easy"
        assert questions[2]["difficulty"] == "hard"

    def test_create_sample_questions_creates_parent_dir(self, temp_dir: Path) -> None:
        """Test that sample questions creation creates parent directories."""
        questions_file = temp_dir / "nested" / "dir" / "questions.json"

        _create_sample_questions(questions_file)

        assert questions_file.exists()
        assert questions_file.parent.exists()

    @patch("src.application_services.setup.database_setup_service.console")
    def test_create_config_file_new(self, mock_console, temp_dir: Path) -> None:
        """Test creating new config file."""
        with patch(
            "src.application_services.setup.database_setup_service.Path"
        ) as mock_path:
            config_file = temp_dir / "config.json"
            mock_path.return_value = config_file

            _create_config_file()

            # Verify file was created
            assert config_file.exists()

            # Verify content
            with open(config_file, encoding="utf-8") as f:
                config = json.load(f)

            assert config["repetition_interval"] == 3
            assert config["max_daily_questions"] == 50
            assert config["show_explanations"] is True
            assert config["spaced_repetition"] is True

            # Verify console print was called
            mock_console.print.assert_called_once()

    @patch("src.application_services.setup.database_setup_service.console")
    def test_create_config_file_existing(self, mock_console, temp_dir: Path) -> None:
        """Test that existing config file is not overwritten."""
        with patch(
            "src.application_services.setup.database_setup_service.Path"
        ) as mock_path:
            config_file = temp_dir / "config.json"
            mock_path.return_value = config_file

            # Create existing config
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as f:
                json.dump({"existing": "config"}, f)

            _create_config_file()

            # Verify file was not modified
            with open(config_file) as f:
                config = json.load(f)

            assert config == {"existing": "config"}

            # Verify no console output (file already exists)
            mock_console.print.assert_not_called()

    def test_initialize_user_settings(self) -> None:
        """Test initializing user settings in database."""
        mock_db = Mock()

        # Mock existing settings (some exist, some don't)
        def mock_get_setting(key: str) -> str | None:
            if key == "preferred_language":
                return "de"  # Already exists
            return None  # Doesn't exist

        mock_db.get_user_setting.side_effect = mock_get_setting

        _initialize_user_settings(mock_db)

        # Should only set settings that don't exist
        expected_calls = [
            (("show_explanations", True),),
            (("multilingual_mode", True),),
            (("image_descriptions", True),),
        ]

        # Verify get_user_setting was called for all defaults
        assert mock_db.get_user_setting.call_count == 4

        # Verify set_user_setting was called only for missing settings
        assert mock_db.set_user_setting.call_count == 3
        for call in expected_calls:
            mock_db.set_user_setting.assert_any_call(*call[0])

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    @patch(
        "src.application_services.setup.database_setup_service.ensure_questions_available"
    )
    @patch("src.application_services.setup.database_setup_service._create_config_file")
    @patch(
        "src.application_services.setup.database_setup_service._initialize_user_settings"
    )
    @patch("src.application_services.setup.database_setup_service.Path")
    def test_main_success_with_questions(
        self,
        mock_path_class,
        mock_init_settings,
        mock_create_config,
        mock_ensure_questions,
        mock_db_class,
        runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test successful setup with questions file."""
        # Setup mocks
        questions_file = temp_dir / "questions.json"
        mock_ensure_questions.return_value = questions_file

        # Mock Path to simulate no existing database
        mock_data_dir = Mock()
        mock_data_dir.exists.return_value = False  # No existing database
        mock_path_class.return_value = mock_data_dir

        mock_db = Mock()
        mock_db.load_questions.return_value = 100  # Loaded 100 questions
        mock_db_class.return_value = mock_db

        # Run command
        result = runner.invoke(main, ["--language", "de"])

        # Verify success
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exit code: {result.exit_code}")
        assert result.exit_code == 0
        assert "🚀 Integran Setup" in result.output
        assert "✅ Successfully loaded 100 questions!" in result.output
        assert "✅ Preferred language set to: de" in result.output
        assert "🎉 Setup completed successfully!" in result.output

        # Verify mocks were called
        mock_db.load_questions.assert_called_once_with(questions_file)
        mock_db.set_user_setting.assert_called_with("preferred_language", "de")
        mock_create_config.assert_called_once()
        mock_init_settings.assert_called_once_with(mock_db)

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    @patch(
        "src.application_services.setup.database_setup_service.ensure_questions_available"
    )
    @patch("src.application_services.setup.database_setup_service.click.confirm")
    @patch(
        "src.application_services.setup.database_setup_service._create_sample_questions"
    )
    def test_main_no_questions_create_sample(
        self,
        mock_create_sample,
        mock_confirm,
        mock_ensure_questions,
        mock_db_class,
        runner: CliRunner,
    ) -> None:
        """Test setup when no questions found but user wants sample."""
        # Setup mocks
        mock_ensure_questions.side_effect = FileNotFoundError("No questions found")
        mock_confirm.return_value = True  # User wants to create sample

        mock_db = Mock()
        mock_db.load_questions.return_value = 3  # Sample questions
        mock_db_class.return_value = mock_db

        # Run command
        result = runner.invoke(main)

        # Verify behavior
        assert result.exit_code == 0
        assert "⚠️  No questions data found." in result.output
        assert "✅ Sample questions created" in result.output

        # Verify sample was created
        mock_create_sample.assert_called_once()
        mock_db.load_questions.assert_called_once()

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    @patch(
        "src.application_services.setup.database_setup_service.ensure_questions_available"
    )
    @patch("src.application_services.setup.database_setup_service.click.confirm")
    def test_main_no_questions_decline_sample(
        self,
        mock_confirm,
        mock_ensure_questions,
        mock_db_class,
        runner: CliRunner,
    ) -> None:
        """Test setup when no questions found and user declines sample."""
        # Setup mocks
        mock_ensure_questions.side_effect = FileNotFoundError("No questions found")
        mock_confirm.return_value = False  # User doesn't want sample

        # Run command
        result = runner.invoke(main)

        # Verify early return
        assert result.exit_code == 0
        assert "Setup completed without questions" in result.output

        # Database operations should not be called
        mock_db_class.assert_called_once()  # Still creates instance
        mock_db = mock_db_class.return_value
        mock_db.load_questions.assert_not_called()

    def test_main_with_custom_questions_file(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test setup with custom questions file."""
        # Create a test questions file
        questions_file = temp_dir / "custom_questions.json"
        questions = [{"id": 1, "question": "Test?", "correct": "A"}]
        with open(questions_file, "w") as f:
            json.dump(questions, f)

        with (
            patch(
                "src.application_services.setup.database_setup_service.DatabaseManager"
            ) as mock_db_class,
            patch(
                "src.application_services.setup.database_setup_service._create_config_file"
            ),
            patch(
                "src.application_services.setup.database_setup_service._initialize_user_settings"
            ),
        ):
            mock_db = Mock()
            mock_db.load_questions.return_value = 1
            mock_db_class.return_value = mock_db

            # Run with custom file and force flag to avoid database existence check
            result = runner.invoke(
                main, ["--force", "--questions-file", str(questions_file)]
            )

            # Debug output if test fails
            if result.exit_code != 0:
                print(f"Command output: {result.output}")
                print(f"Exit code: {result.exit_code}")

            # Verify custom file was used
            assert result.exit_code == 0
            mock_db.load_questions.assert_called_once_with(questions_file)

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    @patch("src.application_services.setup.database_setup_service.Path")
    @patch("src.application_services.setup.database_setup_service.click.confirm")
    @patch(
        "src.application_services.setup.database_setup_service.ensure_questions_available"
    )
    def test_main_database_exists_cancel(
        self,
        mock_ensure_questions,
        mock_confirm,
        mock_path_class,
        _mock_db_class,
        runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test setup cancellation when database exists."""
        # Setup questions file
        questions_file = temp_dir / "questions.json"
        mock_ensure_questions.return_value = questions_file

        # Setup mocks
        mock_confirm.return_value = False  # User cancels

        # Mock Path behavior - properly mock the division operation
        mock_data_dir = Mock()
        mock_data_dir.exists.return_value = True
        mock_db_file = Mock()
        mock_db_file.exists.return_value = True

        # Mock the division operator (__truediv__)
        def mock_truediv(_self, other):
            if other == "trainer.db":
                return mock_db_file
            return Mock()

        mock_data_dir.__truediv__ = mock_truediv
        mock_path_class.return_value = mock_data_dir

        # Run command
        result = runner.invoke(main)

        # Debug output if test fails
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exit code: {result.exit_code}")

        # Verify cancellation
        assert result.exit_code == 0
        assert "Setup cancelled." in result.output

    def test_main_force_flag(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test setup with force flag bypasses existing database check."""
        questions_file = temp_dir / "questions.json"
        with open(questions_file, "w") as f:
            json.dump([{"id": 1, "question": "Test"}], f)

        with patch(
            "src.application_services.setup.database_setup_service.DatabaseManager"
        ) as mock_db_class:
            mock_db = Mock()
            mock_db.load_questions.return_value = 1
            mock_db_class.return_value = mock_db

            # Run with force flag
            result = runner.invoke(
                main, ["--force", "--questions-file", str(questions_file)]
            )

            # Should succeed without prompting about existing database
            assert result.exit_code == 0
            assert "🎉 Setup completed successfully!" in result.output

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    def test_main_keyboard_interrupt(self, mock_db_class, runner: CliRunner) -> None:
        """Test keyboard interrupt handling."""
        mock_db_class.side_effect = KeyboardInterrupt()

        result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Setup interrupted." in result.output

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    def test_main_general_exception(self, mock_db_class, runner: CliRunner) -> None:
        """Test general exception handling."""
        mock_db_class.side_effect = Exception("Test error")

        result = runner.invoke(main)

        assert result.exit_code == 1
        assert "Setup failed: Test error" in result.output

    @patch("src.application_services.setup.database_setup_service.DatabaseManager")
    @patch(
        "src.application_services.setup.database_setup_service.ensure_questions_available"
    )
    @patch("src.application_services.setup.database_setup_service._create_config_file")
    @patch(
        "src.application_services.setup.database_setup_service._initialize_user_settings"
    )
    def test_main_questions_load_error(
        self,
        _mock_init_settings,
        _mock_create_config,
        mock_ensure_questions,
        mock_db_class,
        runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test error handling during questions loading."""
        questions_file = temp_dir / "questions.json"
        mock_ensure_questions.return_value = questions_file

        mock_db = Mock()
        mock_db.load_questions.side_effect = Exception("Failed to load questions")
        mock_db_class.return_value = mock_db

        # Use force flag to bypass database existence check
        result = runner.invoke(main, ["--force"])

        assert result.exit_code == 1
        assert "❌ Error loading questions: Failed to load questions" in result.output
