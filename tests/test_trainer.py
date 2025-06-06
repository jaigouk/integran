"""Tests for src/trainer.py module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.trainer import (
    _display_stats,
    _display_welcome,
    _export_stats,
    _handle_reset,
    _start_category_mode,
    _start_interactive_menu,
    _start_review_mode,
    _start_trainer,
    main,
)


class TestMainCommand:
    """Test the main CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_option(self):
        """Test --version option."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "integran, version 0.1.0" in result.output

    def test_help_option(self):
        """Test --help option."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert (
            "Integran - Interactive trainer for German Integration Exam"
            in result.output
        )
        assert "--mode" in result.output
        assert "--category" in result.output
        assert "--review" in result.output

    @patch("src.trainer.DatabaseManager")
    @patch("src.trainer.Path")
    def test_missing_questions_file(self, mock_path, mock_db):
        """Test behavior when questions file is missing."""
        # Mock questions file not existing
        mock_questions_file = Mock()
        mock_questions_file.exists.return_value = False
        mock_path.return_value = mock_questions_file

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Questions file not found" in result.output
        assert "integran-setup" in result.output

    @patch("src.trainer.DatabaseManager")
    @patch("src.trainer.Path")
    @patch("src.trainer._start_trainer")
    def test_normal_startup(self, mock_start_trainer, mock_path, mock_db):
        """Test normal startup flow."""
        # Mock questions file existing
        mock_questions_file = Mock()
        mock_questions_file.exists.return_value = True
        mock_path.return_value = mock_questions_file

        result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        mock_start_trainer.assert_called_once()

    @patch("src.trainer.DatabaseManager")
    @patch("src.trainer._handle_reset")
    def test_reset_flag(self, mock_handle_reset, mock_db):
        """Test --reset flag."""
        result = self.runner.invoke(main, ["--reset"])

        assert result.exit_code == 0
        mock_handle_reset.assert_called_once()

    @patch("src.trainer.DatabaseManager")
    @patch("src.trainer._display_stats")
    def test_stats_flag(self, mock_display_stats, mock_db):
        """Test --stats flag."""
        result = self.runner.invoke(main, ["--stats"])

        assert result.exit_code == 0
        mock_display_stats.assert_called_once()

    @patch("src.trainer.DatabaseManager")
    @patch("src.trainer._export_stats")
    def test_export_stats_flag(self, mock_export_stats, mock_db):
        """Test --export-stats flag."""
        result = self.runner.invoke(main, ["--export-stats"])

        assert result.exit_code == 0
        mock_export_stats.assert_called_once()

    @patch("src.trainer.DatabaseManager")
    def test_keyboard_interrupt(self, mock_db):
        """Test keyboard interrupt handling."""
        mock_db.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Training session interrupted" in result.output

    @patch("src.trainer.DatabaseManager")
    def test_general_exception(self, mock_db):
        """Test general exception handling."""
        mock_db.side_effect = Exception("Test error")

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Error: Test error" in result.output


class TestResetHandler:
    """Test the reset handler function."""

    @patch("src.trainer.click.confirm")
    @patch("src.trainer.console.print")
    def test_reset_confirmed(self, mock_print, mock_confirm):
        """Test reset when user confirms."""
        mock_confirm.return_value = True
        mock_db = Mock()

        _handle_reset(mock_db)

        mock_confirm.assert_called_once_with("Are you sure you want to continue?")
        mock_db.reset_progress.assert_called_once()
        mock_print.assert_called_with("[green]✅ Progress reset successfully![/green]")

    @patch("src.trainer.click.confirm")
    @patch("src.trainer.console.print")
    def test_reset_cancelled(self, mock_print, mock_confirm):
        """Test reset when user cancels."""
        mock_confirm.return_value = False
        mock_db = Mock()

        _handle_reset(mock_db)

        mock_confirm.assert_called_once_with("Are you sure you want to continue?")
        mock_db.reset_progress.assert_not_called()
        mock_print.assert_called_with("[blue]Reset cancelled.[/blue]")


class TestDisplayStats:
    """Test the display stats function."""

    @patch("src.trainer.console.print")
    def test_display_stats(self, mock_print):
        """Test displaying learning statistics."""
        mock_db = Mock()
        mock_stats = Mock()
        mock_stats.total_mastered = 50
        mock_stats.total_learning = 30
        mock_stats.total_new = 20
        mock_stats.overdue_count = 5
        mock_stats.next_review_count = 10
        mock_stats.average_easiness = 2.75
        mock_stats.study_streak = 7
        mock_db.get_learning_stats.return_value = mock_stats

        _display_stats(mock_db)

        mock_db.get_learning_stats.assert_called_once()
        assert mock_print.call_count >= 8  # Multiple print calls for stats


class TestExportStats:
    """Test the export stats function."""

    @patch("src.trainer.console.print")
    def test_export_stats(self, mock_print):
        """Test exporting statistics to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup mocks
            mock_db = Mock()
            mock_stats = Mock()
            mock_stats.total_mastered = 50
            mock_stats.total_learning = 30
            mock_stats.total_new = 20
            mock_stats.overdue_count = 5
            mock_stats.next_review_count = 10
            mock_stats.average_easiness = 2.75
            mock_stats.study_streak = 7
            mock_db.get_learning_stats.return_value = mock_stats

            # Mock Path to use temp directory
            with patch("src.trainer.Path") as mock_path_class:
                export_path = Path(temp_dir) / "stats_export.txt"
                mock_path_instance = Mock()
                mock_path_instance.parent.mkdir = Mock()
                mock_path_class.return_value = export_path

                # Create the actual file for testing
                export_path.parent.mkdir(parents=True, exist_ok=True)

                _export_stats(mock_db)

                # Verify file was created and contains expected content
                assert export_path.exists()
                content = export_path.read_text()
                assert "Integran Learning Statistics" in content
                assert "Mastered Questions: 50" in content
                assert "Study Streak: 7 days" in content


class TestDisplayWelcome:
    """Test the welcome display function."""

    @patch("src.trainer.console.print")
    def test_display_welcome(self, mock_print):
        """Test displaying welcome message."""
        _display_welcome()

        # Should have multiple print calls for the welcome box
        assert mock_print.call_count >= 4


class TestStartTrainer:
    """Test the start trainer function."""

    @patch("src.trainer._display_welcome")
    @patch("src.trainer._start_review_mode")
    def test_start_trainer_review_mode(self, mock_review, mock_welcome):
        """Test starting trainer in review mode."""
        mock_db = Mock()

        _start_trainer(mock_db, "random", None, True)

        mock_welcome.assert_called_once()
        mock_review.assert_called_once_with(mock_db)

    @patch("src.trainer._display_welcome")
    @patch("src.trainer._start_category_mode")
    def test_start_trainer_category_mode(self, mock_category, mock_welcome):
        """Test starting trainer in category mode."""
        mock_db = Mock()

        _start_trainer(mock_db, "category", "test_category", False)

        mock_welcome.assert_called_once()
        mock_category.assert_called_once_with(mock_db, "test_category")

    @patch("src.trainer._display_welcome")
    @patch("src.trainer._start_interactive_menu")
    def test_start_trainer_interactive_mode(self, mock_interactive, mock_welcome):
        """Test starting trainer in interactive mode."""
        mock_db = Mock()

        _start_trainer(mock_db, "random", None, False)

        mock_welcome.assert_called_once()
        mock_interactive.assert_called_once_with(mock_db)


class TestReviewMode:
    """Test the review mode function."""

    @patch("src.trainer.console.print")
    def test_start_review_mode_no_questions(self, mock_print):
        """Test review mode when no questions are due."""
        mock_db = Mock()
        mock_db.get_questions_for_review.return_value = []

        _start_review_mode(mock_db)

        mock_db.get_questions_for_review.assert_called_once()
        mock_print.assert_called_with(
            "[green]🎉 No questions due for review! Well done![/green]"
        )

    @patch("src.trainer.console.print")
    def test_start_review_mode_with_questions(self, mock_print):
        """Test review mode when questions are due."""
        mock_db = Mock()
        mock_questions = [Mock(), Mock(), Mock()]
        mock_db.get_questions_for_review.return_value = mock_questions

        _start_review_mode(mock_db)

        mock_db.get_questions_for_review.assert_called_once()
        # Should print about starting session with question count
        print_calls = [call[0][0] if call[0] else str(call) for call in mock_print.call_args_list]
        assert any("3 questions" in call for call in print_calls)


class TestCategoryMode:
    """Test the category mode function."""

    @patch("src.trainer.console.print")
    def test_start_category_mode_no_questions(self, mock_print):
        """Test category mode when no questions found."""
        mock_db = Mock()
        mock_db.get_questions_by_category.return_value = []

        _start_category_mode(mock_db, "test_category")

        mock_db.get_questions_by_category.assert_called_once_with("test_category")
        mock_print.assert_called_with(
            "[red]No questions found for category: test_category[/red]"
        )

    @patch("src.trainer.console.print")
    def test_start_category_mode_with_questions(self, mock_print):
        """Test category mode when questions are found."""
        mock_db = Mock()
        mock_questions = [Mock(), Mock()]
        mock_db.get_questions_by_category.return_value = mock_questions

        _start_category_mode(mock_db, "test_category")

        mock_db.get_questions_by_category.assert_called_once_with("test_category")
        # Should print about starting practice with question count
        print_calls = [call[0][0] if call[0] else str(call) for call in mock_print.call_args_list]
        assert any("2 questions from test_category" in call for call in print_calls)


class TestInteractiveMenu:
    """Test the interactive menu function."""

    @patch("src.trainer.console.print")
    def test_start_interactive_menu(self, mock_print):
        """Test starting interactive menu."""
        mock_db = Mock()

        _start_interactive_menu(mock_db)

        # Should have multiple print calls for menu options
        assert mock_print.call_count >= 8
        print_calls = [call[0][0] if call[0] else str(call) for call in mock_print.call_args_list]

        # Verify menu items are displayed
        menu_text = " ".join(print_calls)
        assert "Random Practice" in menu_text
        assert "Sequential Practice" in menu_text
        assert "Practice by Category" in menu_text
        assert "Review Questions" in menu_text
        assert "View Statistics" in menu_text
