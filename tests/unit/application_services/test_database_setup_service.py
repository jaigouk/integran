"""Tests for database setup service."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.application.setup.database_setup_service import (
    _create_config_file,
    _create_sample_questions,
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

    @patch("src.application.setup.database_setup_service.console")
    def test_create_config_file_new(self, mock_console, temp_dir: Path) -> None:
        """Test creating new config file."""
        with patch("src.application.setup.database_setup_service.Path") as mock_path:
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

    @patch("src.application.setup.database_setup_service.console")
    def test_create_config_file_existing(self, mock_console, temp_dir: Path) -> None:
        """Test that existing config file is not overwritten."""
        with patch("src.application.setup.database_setup_service.Path") as mock_path:
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

    @pytest.mark.asyncio
    async def test_initialize_user_configuration_success(self) -> None:
        """Test successful user configuration initialization."""
        # Create a mock database manager
        mock_db_manager = Mock()

        # Import the function to test
        from src.application.setup.database_setup_service import (
            _initialize_user_configuration,
        )

        # Mock the imports inside the function
        with (
            patch("src.domain.user.models.user_models.Language") as mock_language_class,
            patch("src.domain.user.models.user_models.UserSettings"),
            patch("src.domain.user.services.load_user_settings.LoadUserSettings") as mock_load_class,
            patch("src.domain.user.services.save_user_settings.SaveUserSettings") as mock_save_class,
            patch("src.infrastructure.messaging.event_bus.EventBus") as mock_event_bus_class,
            patch("src.infrastructure.repositories.user_repository.UserSettingsRepository") as mock_repo_class,
        ):
            # Setup mocks
            mock_language_class.return_value = Mock()
            mock_event_bus = Mock()
            mock_event_bus_class.return_value = mock_event_bus

            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            mock_load_service = Mock()
            mock_load_result = Mock()
            mock_load_result.success = True
            mock_load_result.user_settings = Mock()
            mock_load_result.user_settings.update_language = Mock(return_value=Mock())
            mock_load_service.call.return_value = mock_load_result
            mock_load_class.return_value = mock_load_service

            mock_save_service = Mock()
            mock_save_class.return_value = mock_save_service

            # Call the function - should complete successfully
            await _initialize_user_configuration(mock_db_manager, "de")

            # Verify load service was called
            assert mock_load_service.call.called

    @pytest.mark.asyncio
    async def test_initialize_user_configuration_error_handling(self) -> None:
        """Test error handling in user configuration initialization."""
        # Create a mock database manager
        mock_db_manager = Mock()

        # Import the function to test
        from src.application.setup.database_setup_service import (
            _initialize_user_configuration,
        )

        # Mock one of the imports to raise an exception
        with patch("src.domain.user.models.user_models.Language", side_effect=ImportError("Test error")):
            # Call the function - should not raise exception (error is caught internally)
            await _initialize_user_configuration(mock_db_manager, "de")

            # Function should complete without raising

    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.ensure_questions_available")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch(
        "src.application.setup.database_setup_service._initialize_user_configuration"
    )
    @patch("src.application.setup.database_setup_service.Path")
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
        assert "✅ User configuration initialized with language: de" in result.output
        assert "🎉 Setup completed successfully!" in result.output

        # Verify mocks were called
        mock_db.load_questions.assert_called_once_with(questions_file)
        mock_create_config.assert_called_once()
        mock_init_settings.assert_called_once_with(mock_db, "de")




    @pytest.mark.skip("Complex mocking - test main integration instead")
    def test_main_database_exists_cancel(self) -> None:
        """Test setup cancellation when database exists."""
        # This test is complex to mock properly due to Path operations
        # Integration tests cover this scenario better
        pass

    @patch("src.application.setup.database_setup_service._initialize_user_configuration")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch("src.application.setup.database_setup_service.DatabaseManager")
    def test_main_force_flag(self, mock_db_class, mock_init_user_config, runner: CliRunner, temp_dir: Path) -> None:
        """Test setup with force flag bypasses existing database check."""
        questions_file = temp_dir / "questions.json"
        with open(questions_file, "w") as f:
            json.dump([{"id": 1, "question": "Test"}], f)

        mock_db = Mock()
        mock_db.load_questions.return_value = 1
        mock_db_class.return_value = mock_db
        mock_init_user_config.return_value = None

        # Run with force flag and custom questions file
        result = runner.invoke(
            main, ["--force", "--questions-file", str(questions_file)]
        )

        # Should succeed without prompting about existing database
        assert result.exit_code == 0
        assert "🎉 Setup completed successfully!" in result.output

        # Verify custom questions file was used
        mock_db.load_questions.assert_called_once_with(questions_file)

    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.Path")
    def test_main_keyboard_interrupt(self, mock_path_class, mock_db_class, runner: CliRunner) -> None:
        """Test keyboard interrupt handling."""
        # Mock final dataset exists to get past initial checks
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = True

        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Make DatabaseManager raise KeyboardInterrupt
        mock_db_class.side_effect = KeyboardInterrupt()

        result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Setup interrupted." in result.output

    @patch("src.application.setup.database_setup_service.DatabaseManager")
    def test_main_general_exception(self, mock_db_class, runner: CliRunner) -> None:
        """Test general exception handling."""
        mock_db_class.side_effect = Exception("Test error")

        result = runner.invoke(main)

        assert result.exit_code == 1
        assert "Setup failed: Test error" in result.output

    @patch("src.application.setup.database_setup_service._initialize_user_configuration")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.Path")
    def test_main_with_final_dataset(
        self,
        mock_path_class,
        mock_db_class,
        mock_create_config,
        mock_init_user_config,
        runner: CliRunner,
    ) -> None:
        """Test successful setup with final_dataset.json."""
        # Setup mock final dataset file
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = True
        mock_final_dataset.__str__ = Mock(return_value="data/final_dataset.json")

        # Mock Path constructor to return final dataset when called with the right path
        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Setup database mock
        mock_db = Mock()
        mock_db.load_questions.return_value = 460  # Realistic count
        mock_db_class.return_value = mock_db

        # Make init_user_config async
        mock_init_user_config.return_value = None

        # Run with force to skip database existence check
        result = runner.invoke(main, ["--force", "--language", "de"])

        # Verify success
        assert result.exit_code == 0
        assert "Using final dataset" in result.output
        assert "Successfully loaded 460 questions" in result.output
        assert "User configuration initialized with language: de" in result.output
        assert "Setup completed successfully" in result.output

        # Verify mocks were called correctly
        mock_db.load_questions.assert_called_once_with(mock_final_dataset)
        mock_create_config.assert_called_once()
        mock_init_user_config.assert_called_once_with(mock_db, "de")

    @patch("src.application.setup.database_setup_service._initialize_user_configuration")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch("src.application.setup.database_setup_service.ensure_questions_available")
    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.Path")
    def test_main_fallback_to_ensure_questions(
        self,
        mock_path_class,
        mock_db_class,
        mock_ensure_questions,
        mock_init_user_config,
        runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test fallback to ensure_questions_available when final_dataset.json doesn't exist."""
        # Mock final dataset doesn't exist
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = False

        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Mock ensure_questions_available returns fallback file
        fallback_file = temp_dir / "questions.json"
        mock_ensure_questions.return_value = fallback_file

        # Setup database mock
        mock_db = Mock()
        mock_db.load_questions.return_value = 300
        mock_db_class.return_value = mock_db

        mock_init_user_config.return_value = None

        # Run with force flag
        result = runner.invoke(main, ["--force"])

        # Verify success
        assert result.exit_code == 0
        assert "Questions available at" in result.output
        assert "Successfully loaded 300 questions" in result.output

        # Verify fallback was used
        mock_ensure_questions.assert_called_once()
        mock_db.load_questions.assert_called_once_with(fallback_file)

    @patch("src.application.setup.database_setup_service._initialize_user_configuration")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch("src.application.setup.database_setup_service.ensure_questions_available")
    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.Path")
    @patch("src.application.setup.database_setup_service.click.confirm")
    def test_main_create_sample_questions(
        self,
        mock_confirm,
        mock_path_class,
        mock_db_class,
        mock_ensure_questions,
        mock_init_user_config,
        runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test creating sample questions when no questions found."""
        # Mock final dataset doesn't exist
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = False

        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            elif "questions.json" in str(path_str):
                return temp_dir / "questions.json"
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Mock ensure_questions_available raises FileNotFoundError
        mock_ensure_questions.side_effect = FileNotFoundError("No questions found")

        # User confirms sample creation
        mock_confirm.return_value = True

        # Setup database mock
        mock_db = Mock()
        mock_db.load_questions.return_value = 3  # Sample has 3 questions
        mock_db_class.return_value = mock_db

        mock_init_user_config.return_value = None

        # Run with force flag
        result = runner.invoke(main, ["--force"])

        # Verify success
        assert result.exit_code == 0
        assert "No questions data found" in result.output
        assert "Sample questions created" in result.output
        assert "Successfully loaded 3 questions" in result.output

        # Verify confirm was called
        mock_confirm.assert_called_once()

    @patch("src.application.setup.database_setup_service.ensure_questions_available")
    @patch("src.application.setup.database_setup_service.Path")
    @patch("src.application.setup.database_setup_service.click.confirm")
    def test_main_decline_sample_questions(
        self,
        mock_confirm,
        mock_path_class,
        mock_ensure_questions,
        runner: CliRunner,
    ) -> None:
        """Test declining sample questions creation."""
        # Mock final dataset doesn't exist
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = False

        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Mock ensure_questions_available raises FileNotFoundError
        mock_ensure_questions.side_effect = FileNotFoundError("No questions found")

        # User declines sample creation
        mock_confirm.return_value = False

        # Run command
        result = runner.invoke(main)

        # Verify early return
        assert result.exit_code == 0
        assert "No questions data found" in result.output
        assert "Setup completed without questions" in result.output

    @patch("src.application.setup.database_setup_service._initialize_user_configuration")
    @patch("src.application.setup.database_setup_service._create_config_file")
    @patch("src.application.setup.database_setup_service.DatabaseManager")
    @patch("src.application.setup.database_setup_service.Path")
    def test_main_questions_loading_error(
        self,
        mock_path_class,
        mock_db_class,
        mock_init_user_config,
        runner: CliRunner,
    ) -> None:
        """Test error handling when questions loading fails."""
        # Mock final dataset exists
        mock_final_dataset = Mock()
        mock_final_dataset.exists.return_value = True
        mock_final_dataset.__str__ = Mock(return_value="data/final_dataset.json")

        def path_side_effect(path_str):
            if "final_dataset.json" in str(path_str):
                return mock_final_dataset
            return Mock(exists=Mock(return_value=False))

        mock_path_class.side_effect = path_side_effect

        # Mock database load_questions to raise error
        mock_db = Mock()
        mock_db.load_questions.side_effect = Exception("Database error")
        mock_db_class.return_value = mock_db

        # Run with force flag
        result = runner.invoke(main, ["--force"])

        # Verify error handling
        assert result.exit_code == 1
        assert "Error loading questions: Database error" in result.output

        # User config should not be called if questions loading fails
        mock_init_user_config.assert_not_called()
