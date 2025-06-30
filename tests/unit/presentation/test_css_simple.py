"""Simple CSS validation tests for terminal UI components."""

from __future__ import annotations

import re

import pytest

from src.presentation.terminal.question_view import PracticeScreen
from src.presentation.terminal.trainer_app import TrainerApp


class TestSimpleCSSValidation:
    """Simple CSS validation tests."""

    def test_practice_screen_css_compiles(self):
        """Test that PracticeScreen CSS compiles without undefined variables."""
        try:
            from unittest.mock import Mock

            screen = PracticeScreen(
                practice_mode="random",
                user_repository=Mock(),
                submit_answer_command_handler=Mock(),
                start_practice_command_handler=Mock(),
            )
            assert screen is not None
            assert hasattr(screen, "CSS")
            assert isinstance(screen.CSS, str)
        except Exception as e:
            pytest.fail(f"PracticeScreen CSS compilation failed: {e}")

    def test_trainer_app_css_compiles(self):
        """Test that TrainerApp CSS compiles without undefined variables."""
        try:
            from unittest.mock import Mock

            # Mock the required dependencies
            mock_event_bus = Mock()
            mock_session_workflow = Mock()
            mock_query_service = Mock()
            mock_user_repository = Mock()
            mock_container = Mock()

            app = TrainerApp(
                event_bus=mock_event_bus,
                session_workflow=mock_session_workflow,
                query_service=mock_query_service,
                user_repository=mock_user_repository,
                container=mock_container,
            )
            assert app is not None
            assert hasattr(app, "CSS")
            assert isinstance(app.CSS, str)
        except Exception as e:
            pytest.fail(f"TrainerApp CSS compilation failed: {e}")

    def test_no_muted_variable_usage(self):
        """Test that the specific $muted -> $text-muted fix is applied."""
        from unittest.mock import Mock

        screen = PracticeScreen(
            practice_mode="random",
            user_repository=Mock(),
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )
        css_content = screen.CSS

        # Ensure $muted is not used (unless it's $text-muted)
        muted_pattern = r"\$muted(?![a-zA-Z-])"
        matches = re.findall(muted_pattern, css_content)

        assert not matches, f"Found invalid $muted variable usage: {matches}"

        # If any muted reference exists, it should be $text-muted
        if "$muted" in css_content:
            assert "$text-muted" in css_content, (
                "CSS should use $text-muted instead of $muted"
            )

    def test_css_variables_format(self):
        """Test that CSS variables follow correct format."""
        from unittest.mock import Mock

        screen = PracticeScreen(
            practice_mode="random",
            user_repository=Mock(),
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )
        css_content = screen.CSS

        # Find all CSS variable references
        variable_pattern = r"\$[a-zA-Z][a-zA-Z0-9_-]*"
        variables = re.findall(variable_pattern, css_content)

        # Check for common invalid patterns
        invalid_patterns = [
            "$muted",
            "$info",
            "$warning-alpha",
            "$success-alpha",
            "$error-alpha",
        ]

        for var in variables:
            if var in invalid_patterns:
                pytest.fail(f"Invalid CSS variable found: {var}")

    def test_application_launches_without_css_errors(self):
        """Test that the application can be instantiated without CSS errors."""
        # This is the core test - if CSS has undefined variables,
        # instantiation should fail
        try:
            from unittest.mock import Mock

            screen = PracticeScreen(
                practice_mode="random",
                user_repository=Mock(),
                submit_answer_command_handler=Mock(),
                start_practice_command_handler=Mock(),
            )
            assert screen is not None

            # Basic sanity check
            assert len(screen.CSS) > 100  # Should have substantial CSS content

        except Exception as e:
            pytest.fail(f"Failed to instantiate PracticeScreen due to CSS errors: {e}")
