"""Tests for the build dataset CLI command."""

from __future__ import annotations

import sys
from unittest.mock import Mock, patch

import pytest

from src.cli.build_dataset import build_dataset_cli
from src.core.data_builder import BuildCheckpoint, BuildStatus


class TestBuildDatasetCLI:
    """Tests for build_dataset_cli function."""

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_status_command(self, mock_has_config, mock_data_builder, capsys):
        """Test --status command."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder

        # Mock status response
        mock_status = BuildCheckpoint(
            status=BuildStatus.IN_PROGRESS,
            total_questions=460,
            processed_questions=150,
            processed_images=25,
            current_step="generating_answers",
        )
        mock_builder.get_build_status.return_value = mock_status

        with patch.object(sys, "argv", ["build-dataset", "--status"]):
            build_dataset_cli()

        captured = capsys.readouterr()

        # Verify status output
        assert "Build Status: IN_PROGRESS" in captured.out
        assert "150/460" in captured.out
        assert "generating_answers" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_status_not_started(self, mock_has_config, mock_data_builder, capsys):
        """Test --status when build not started."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder

        # Mock status response
        mock_status = BuildCheckpoint(
            status=BuildStatus.NOT_STARTED,
            total_questions=0,
            processed_questions=0,
            processed_images=0,
            current_step="",
        )
        mock_builder.get_build_status.return_value = mock_status

        with patch.object(sys, "argv", ["build-dataset", "--status"]):
            build_dataset_cli()

        captured = capsys.readouterr()

        # Verify status output
        assert "Build Status: NOT_STARTED" in captured.out
        assert "Images not yet processed" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_build_command_success(self, mock_has_config, mock_data_builder, capsys):
        """Test successful dataset building."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset"]):
            build_dataset_cli()

        captured = capsys.readouterr()

        # Verify build was called
        mock_builder.build_complete_dataset.assert_called_once()
        assert "Building multilingual dataset" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_build_command_failure(self, mock_has_config, mock_data_builder, capsys):
        """Test failed dataset building."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = False

        with patch.object(sys, "argv", ["build-dataset"]):
            with pytest.raises(SystemExit) as exc_info:
                build_dataset_cli()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Dataset building failed" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_force_rebuild_flag(self, mock_has_config, mock_data_builder):
        """Test --force-rebuild flag."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset", "--force-rebuild"]):
            build_dataset_cli()

        # Verify force_rebuild was passed
        mock_builder.build_complete_dataset.assert_called_once_with(
            force_rebuild=True,
            use_rag=True,
            multilingual=True,
            batch_size=10,
        )

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_no_rag_flag(self, mock_has_config, mock_data_builder):
        """Test --no-rag flag."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset", "--no-rag"]):
            build_dataset_cli()

        # Verify use_rag was set to False
        mock_builder.build_complete_dataset.assert_called_once_with(
            force_rebuild=False,
            use_rag=False,
            multilingual=True,
            batch_size=10,
        )

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_no_multilingual_flag(self, mock_has_config, mock_data_builder):
        """Test --no-multilingual flag."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset", "--no-multilingual"]):
            build_dataset_cli()

        # Verify multilingual was set to False
        mock_builder.build_complete_dataset.assert_called_once_with(
            force_rebuild=False,
            use_rag=True,
            multilingual=False,
            batch_size=10,
        )

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_batch_size_option(self, mock_has_config, mock_data_builder):
        """Test --batch-size option."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset", "--batch-size", "20"]):
            build_dataset_cli()

        # Verify batch_size was passed
        mock_builder.build_complete_dataset.assert_called_once_with(
            force_rebuild=False,
            use_rag=True,
            multilingual=True,
            batch_size=20,
        )

    @patch("src.cli.build_dataset.has_gemini_config")
    def test_missing_gemini_config(self, mock_has_config, capsys):
        """Test behavior when Gemini config is missing."""
        mock_has_config.return_value = False

        with patch.object(sys, "argv", ["build-dataset"]):
            with pytest.raises(SystemExit) as exc_info:
                build_dataset_cli()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()

        # Verify error message
        assert "Gemini API not configured" in captured.out
        assert "GCP_PROJECT_ID" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_verbose_flag(self, mock_has_config, mock_data_builder, capsys):
        """Test --verbose flag."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(sys, "argv", ["build-dataset", "--verbose"]):
            build_dataset_cli()

        captured = capsys.readouterr()

        # Verify verbose output
        assert "Building with options:" in captured.out
        assert "Force rebuild: False" in captured.out
        assert "Use RAG: True" in captured.out
        assert "Multilingual: True" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_help_command(self, mock_has_config, mock_data_builder):
        """Test --help command."""
        mock_has_config.return_value = True

        with (
            patch.object(sys, "argv", ["build-dataset", "--help"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            build_dataset_cli()

        assert exc_info.value.code == 0

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_version_command(self, mock_has_config, mock_data_builder):
        """Test --version command."""
        mock_has_config.return_value = True

        with (
            patch.object(sys, "argv", ["build-dataset", "--version"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            build_dataset_cli()

        assert exc_info.value.code == 0

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_keyboard_interrupt(self, mock_has_config, mock_data_builder, capsys):
        """Test handling of keyboard interrupt."""
        mock_has_config.return_value = True

        # Mock DataBuilder to raise KeyboardInterrupt
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.side_effect = KeyboardInterrupt()

        with patch.object(sys, "argv", ["build-dataset"]):
            with pytest.raises(SystemExit) as exc_info:
                build_dataset_cli()

        assert exc_info.value.code == 130
        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_general_exception(self, mock_has_config, mock_data_builder, capsys):
        """Test handling of general exceptions."""
        mock_has_config.return_value = True

        # Mock DataBuilder to raise general exception
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.side_effect = Exception("Unexpected error")

        with patch.object(sys, "argv", ["build-dataset"]):
            with pytest.raises(SystemExit) as exc_info:
                build_dataset_cli()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unexpected error during dataset building" in captured.out
        assert "Unexpected error" in captured.out

    @patch("src.cli.build_dataset.DataBuilder")
    @patch("src.cli.build_dataset.has_gemini_config")
    def test_all_flags_combined(self, mock_has_config, mock_data_builder):
        """Test combining multiple flags."""
        mock_has_config.return_value = True

        # Mock DataBuilder
        mock_builder = Mock()
        mock_data_builder.return_value = mock_builder
        mock_builder.build_complete_dataset.return_value = True

        with patch.object(
            sys,
            "argv",
            [
                "build-dataset",
                "--force-rebuild",
                "--no-rag",
                "--no-multilingual",
                "--batch-size",
                "5",
                "--verbose",
            ],
        ):
            build_dataset_cli()

        # Verify all options were passed correctly
        mock_builder.build_complete_dataset.assert_called_once_with(
            force_rebuild=True,
            use_rag=False,
            multilingual=False,
            batch_size=5,
        )


class TestBuildDatasetCLIIntegration:
    """Integration tests for build dataset CLI."""

    @pytest.mark.slow
    def test_placeholder_for_integration_tests(self):
        """Placeholder for future integration tests.

        Future tests might include:
        - End-to-end CLI testing with real components
        - Testing CLI with various terminal configurations
        - Testing error handling with real failure scenarios
        """
        assert True, "Structure ready for integration tests"
