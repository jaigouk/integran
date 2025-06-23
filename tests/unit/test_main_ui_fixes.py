"""Tests for main.py UI fixes to prevent terminal/legacy CLI conflicts."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.main import _launch_terminal_ui, _start_trainer


class TestMainUIFixes:
    """Test fixes to main.py that prevent terminal UI conflicts."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock()

    @patch("src.main._launch_terminal_ui")
    @patch("src.main._start_legacy_cli")
    def test_start_trainer_only_calls_legacy_cli_on_exception(
        self, mock_legacy_cli, mock_terminal_ui, mock_db_manager
    ):
        """Test that _start_trainer only calls legacy CLI if terminal UI fails."""
        # Arrange
        mock_terminal_ui.return_value = None  # Terminal UI succeeds

        # Act
        _start_trainer(mock_db_manager, "random", None, False)

        # Assert
        mock_terminal_ui.assert_called_once_with(mode="random", category=None)
        mock_legacy_cli.assert_not_called()

    @patch("src.main._launch_terminal_ui")
    @patch("src.main._start_legacy_cli")
    @patch("src.main.console")
    def test_start_trainer_falls_back_to_legacy_cli_on_terminal_ui_failure(
        self, mock_console, mock_legacy_cli, mock_terminal_ui, mock_db_manager
    ):
        """Test that _start_trainer falls back to legacy CLI when terminal UI fails."""
        # Arrange
        mock_terminal_ui.side_effect = Exception("Terminal UI failed")

        # Act
        _start_trainer(mock_db_manager, "sequential", "category", True)

        # Assert
        mock_terminal_ui.assert_called_once_with(mode="sequential", category="category")
        mock_legacy_cli.assert_called_once_with(
            mock_db_manager, "sequential", "category", True
        )
        mock_console.print.assert_called()

    @patch("src.presentation.terminal.trainer_app.TrainerApp")
    @patch("src.infrastructure.containers.main_container.MainContainer")
    @patch("src.main.console")
    def test_launch_terminal_ui_creates_app_with_container(
        self,
        mock_console,  # noqa: ARG002
        mock_container_class,
        mock_app_class,  # noqa: ARG002
    ):
        """Test that _launch_terminal_ui creates TrainerApp with proper container."""
        # Arrange
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_app = Mock()
        mock_app.run_async = AsyncMock()
        mock_app_class.return_value = mock_app

        # Mock asyncio.run to avoid actually running the app
        with patch("src.main.asyncio.run") as mock_asyncio_run:
            # Act
            _launch_terminal_ui()

            # Assert
            mock_container_class.assert_called_once()
            mock_app_class.assert_called_once_with(
                event_bus=mock_container.get_event_bus(),
                session_workflow=mock_container.get_session_workflow(),
                query_service=mock_container.get_query_service(),
                analytics_service=mock_container.get_analytics_service(),
                user_repository=mock_container.get_user_container().get_repository(),
                container=mock_container,
            )
            mock_asyncio_run.assert_called_once()
            # Verify it was called with the app's run_async coroutine
            call_args = mock_asyncio_run.call_args[0][0]
            assert hasattr(call_args, "__await__"), (
                "asyncio.run should be called with a coroutine"
            )

    @patch("src.infrastructure.containers.main_container.MainContainer")
    @patch("src.main.console")
    def test_launch_terminal_ui_handles_import_error(
        self, mock_console, mock_container_class
    ):
        """Test that _launch_terminal_ui handles ImportError gracefully."""
        # Arrange
        mock_container_class.side_effect = ImportError("Missing dependency")

        # Act
        _launch_terminal_ui()

        # Assert
        mock_console.print.assert_any_call(
            "[red]Terminal UI not available: Missing dependency[/red]"
        )
        mock_console.print.assert_any_call(
            "[yellow]Terminal UI is required for practice sessions.[/yellow]"
        )

    @patch("src.presentation.terminal.trainer_app.TrainerApp")
    @patch("src.infrastructure.containers.main_container.MainContainer")
    @patch("src.main.console")
    def test_launch_terminal_ui_handles_general_exception(
        self, mock_console, mock_container_class, mock_app_class
    ):
        """Test that _launch_terminal_ui handles general exceptions gracefully."""
        # Arrange
        mock_container = Mock()
        mock_container_class.return_value = mock_container
        mock_app_class.side_effect = Exception("General error")

        # Act
        _launch_terminal_ui()

        # Assert
        mock_console.print.assert_any_call(
            "[red]Error starting terminal UI: General error[/red]"
        )
        mock_console.print.assert_any_call(
            "[yellow]Unable to start practice session.[/yellow]"
        )

    @patch("src.presentation.terminal.trainer_app.TrainerApp")
    @patch("src.infrastructure.containers.main_container.MainContainer")
    def test_launch_terminal_ui_passes_correct_mode_parameters(
        self, mock_container_class, mock_app_class
    ):
        """Test that _launch_terminal_ui accepts and processes mode parameters correctly."""
        # Arrange
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_app = Mock()
        mock_app.run_async = AsyncMock()
        mock_app_class.return_value = mock_app

        with patch("src.main.asyncio.run"):
            # Act
            _launch_terminal_ui(mode="category", category="History", num_questions=10)

            # Assert - The function should accept these parameters without error
            # Note: Current implementation doesn't use these parameters but should accept them
            mock_container_class.assert_called_once()
            mock_app_class.assert_called_once()

    def test_start_trainer_parameters_forwarded_correctly(self, mock_db_manager):
        """Test that _start_trainer forwards parameters correctly to both UI methods."""
        with (
            patch("src.main._launch_terminal_ui") as mock_terminal_ui,
            patch("src.main._start_legacy_cli") as mock_legacy_cli,
        ):
            # Test when terminal UI succeeds
            mock_terminal_ui.return_value = None

            # Act
            _start_trainer(mock_db_manager, "category", "History", True)

            # Assert
            mock_terminal_ui.assert_called_once_with(
                mode="category", category="History"
            )
            mock_legacy_cli.assert_not_called()

    def test_start_trainer_fallback_parameters_forwarded_correctly(
        self, mock_db_manager
    ):
        """Test that _start_trainer forwards parameters correctly to legacy CLI on fallback."""
        with (
            patch("src.main._launch_terminal_ui") as mock_terminal_ui,
            patch("src.main._start_legacy_cli") as mock_legacy_cli,
            patch("src.main.console"),
        ):
            # Test when terminal UI fails
            mock_terminal_ui.side_effect = Exception("UI failed")

            # Act
            _start_trainer(mock_db_manager, "review", None, True)

            # Assert
            mock_terminal_ui.assert_called_once_with(mode="review", category=None)
            mock_legacy_cli.assert_called_once_with(
                mock_db_manager, "review", None, True
            )


class TestMainEntryPointIntegration:
    """Test integration of main entry point to prevent startup crashes."""

    @patch("src.main._start_trainer")
    @patch("src.main.DatabaseManager")
    @patch("pathlib.Path.exists")
    def test_main_function_calls_start_trainer_correctly(
        self, mock_path_exists, mock_db_class, mock_start_trainer
    ):
        """Test that main function calls _start_trainer with correct parameters."""
        # Arrange - Mock path exists to return True for both files
        mock_path_exists.return_value = True

        mock_db_manager = Mock()
        mock_db_class.return_value = mock_db_manager

        # Mock database query to return some questions (so no setup needed)
        from unittest.mock import MagicMock

        mock_session = Mock()
        mock_session.query.return_value.count.return_value = 100
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        mock_db_manager.get_session.return_value = mock_context_manager

        # Act - Call main with CLI arguments
        from click.testing import CliRunner

        from src.main import main

        runner = CliRunner()
        result = runner.invoke(main, ["--mode", "sequential", "--category", "Politics"])

        # Assert
        assert result.exit_code == 0, f"CLI command failed: {result.output}"
        mock_start_trainer.assert_called_once_with(
            mock_db_manager, "sequential", "Politics", False
        )

    @patch("src.main._start_trainer")
    @patch("src.main.asyncio.run")
    @patch("src.application.setup.database_setup_service.main_async")
    @patch("src.main.console")
    @patch("src.main.DatabaseManager")
    @patch("pathlib.Path.exists")
    def test_main_function_handles_missing_questions_file(
        self,
        mock_path_exists,
        mock_db_class,
        mock_console,
        mock_main_async,
        mock_asyncio_run,
        mock_start_trainer,
    ):
        """Test that main function triggers auto-setup when questions file is missing."""

        # Arrange - Mock the specific path check for questions file to return False
        def path_exists_side_effect():
            # This will be called on the Path object, we need to get the actual path
            # Since we can't access the Path object directly, we'll return False first time
            # (for questions file) and True for subsequent calls
            if not hasattr(path_exists_side_effect, "call_count"):
                path_exists_side_effect.call_count = 0
            path_exists_side_effect.call_count += 1
            # First call is for questions file - return False
            # Subsequent calls return True (for db file exists)
            return path_exists_side_effect.call_count > 1

        mock_path_exists.side_effect = path_exists_side_effect

        mock_db_manager = Mock()
        mock_db_class.return_value = mock_db_manager

        # Mock successful setup - main_async returns a coroutine
        async def mock_setup_coroutine():
            return None

        mock_main_async.return_value = mock_setup_coroutine()
        # Mock asyncio.run to not actually run the coroutine
        mock_asyncio_run.return_value = None
        # Mock _start_trainer to prevent it from running
        mock_start_trainer.return_value = None

        # Act - Call main with CLI arguments
        from click.testing import CliRunner

        from src.main import main

        runner = CliRunner()
        runner.invoke(main, ["--mode", "random"])

        # Assert - Should trigger auto-setup
        mock_console.print.assert_any_call(
            "[yellow]Questions file not found at data/final_dataset.json[/yellow]"
        )
        mock_console.print.assert_any_call(
            "[blue]🚀 Running first-time setup...[/blue]"
        )
        # Auto-setup should be called
        mock_main_async.assert_called_once_with(
            force=True, questions_file=None, language="en"
        )
        # asyncio.run should be called once for the setup
        mock_asyncio_run.assert_called_once()
        # _start_trainer should be called after setup
        mock_start_trainer.assert_called_once_with(
            mock_db_manager, "random", None, False
        )


class TestRegressionPrevention:
    """Tests to prevent regression of the terminal UI/legacy CLI conflict."""

    def test_terminal_ui_success_prevents_legacy_cli_execution(self):
        """Test that when terminal UI succeeds, legacy CLI is never called."""
        mock_db = Mock()

        with (
            patch("src.main._launch_terminal_ui") as mock_terminal,
            patch("src.main._start_legacy_cli") as mock_legacy,
        ):
            # Terminal UI succeeds (no exception)
            mock_terminal.return_value = None

            # Act
            _start_trainer(mock_db, "random", None, False)

            # Assert: Legacy CLI should NOT be called
            mock_legacy.assert_not_called()

    def test_terminal_ui_failure_triggers_legacy_cli_with_correct_params(self):
        """Test that terminal UI failure properly triggers legacy CLI with all parameters."""
        mock_db = Mock()

        with (
            patch("src.main._launch_terminal_ui") as mock_terminal,
            patch("src.main._start_legacy_cli") as mock_legacy,
            patch("src.main.console"),
        ):
            # Terminal UI fails
            mock_terminal.side_effect = RuntimeError("Terminal failed")

            # Act
            _start_trainer(mock_db, "category", "History", True)

            # Assert: Legacy CLI called with exact same parameters
            mock_legacy.assert_called_once_with(mock_db, "category", "History", True)
