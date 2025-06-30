"""Regression tests for image practice mode issues."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.application.commands.start_practice_session_command import (
    StartPracticeSessionCommand,
)
from src.infrastructure.containers.main_container import MainContainer
from src.presentation.terminal.question_view import PracticeScreen


class TestImagePracticeModeRegression:
    """Test image practice mode to prevent regressions."""

    def test_main_container_has_correct_method_names(self):
        """Test that MainContainer has the correct command handler method names."""
        container = MainContainer()

        # The method should be called get_start_practice_session_command_handler
        # NOT get_start_session_command_handler
        assert hasattr(container, "get_start_practice_session_command_handler")

        # Verify the method returns something callable
        handler = container.get_start_practice_session_command_handler()
        assert handler is not None
        assert hasattr(handler, "handle")

    def test_main_container_has_required_dependencies(self):
        """Test that MainContainer provides all required dependencies for StartPracticeSessionCommand."""
        container = MainContainer()

        # These methods must exist for StartPracticeSessionCommand to work
        assert hasattr(container, "get_question_repository")
        assert hasattr(container, "get_user_repository")
        assert hasattr(container, "get_event_bus")

        # Verify they return non-None values
        assert container.get_question_repository() is not None
        assert container.get_user_repository() is not None
        assert container.get_event_bus() is not None

    def test_start_practice_session_command_requires_dependencies(self):
        """Test that StartPracticeSessionCommand requires all necessary dependencies."""
        container = MainContainer()

        # This should work without errors - command should accept these dependencies
        try:
            command = StartPracticeSessionCommand(
                practice_mode="images",
                user_repository=container.get_user_repository(),
                session_repository=container.get_session_repository(),
                event_bus=container.get_event_bus(),
                user_id=1,
                limit=1,
            )
            # If we get here, the command was created successfully
            assert command.practice_mode == "images"
            assert command.user_id == 1
            assert command.limit == 1
        except TypeError as e:
            # If we get a TypeError, it means missing required arguments
            pytest.fail(f"StartPracticeSessionCommand missing required arguments: {e}")

    def test_start_practice_session_command_fails_without_dependencies(self):
        """Test that StartPracticeSessionCommand fails when missing required dependencies."""
        # This should fail with TypeError for missing required positional arguments
        with pytest.raises(TypeError, match="missing.*required positional arguments"):
            StartPracticeSessionCommand(
                practice_mode="images",
                user_id=1,
                limit=1,
                # Missing: question_repository, user_repository, event_bus
            )

    @pytest.mark.asyncio
    async def test_practice_screen_load_question_method_exists(self):
        """Test that PracticeScreen has the load_next_question method that caused the original error."""
        # Create a minimal practice screen
        mock_user_repo = Mock()
        practice_screen = PracticeScreen(
            practice_mode="images",
            user_repository=mock_user_repo,
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )

        # The method that was failing should exist
        assert hasattr(practice_screen, "load_next_question")

        # We don't actually call it since it requires complex mocking,
        # but we verify the method exists to prevent regression


class TestImagePracticeModeIntegration:
    """Integration tests for image practice mode workflow."""

    def test_image_practice_mode_command_creation_pattern(self):
        """Test the exact pattern used in question_view.py for creating commands."""
        # This test replicates the exact pattern from the fixed code
        container = MainContainer()
        command_handler = container.get_start_practice_session_command_handler()

        # Verify the handler exists
        assert command_handler is not None

        # This is the exact pattern that was failing before the fix
        command = StartPracticeSessionCommand(
            practice_mode="images",
            user_repository=container.get_user_repository(),  # ✅ This was missing
            session_repository=container.get_session_repository(),  # ✅ Required for session tracking
            event_bus=container.get_event_bus(),  # ✅ This was missing
            user_id=1,
            limit=1,
            category_index=0,
            question_indices={},
            last_question_id=0,
        )

        # Verify command was created successfully
        assert command.practice_mode == "images"
        assert command.user_repository is not None
        assert command.event_bus is not None

    def test_method_name_regression_prevention(self):
        """Specific test to prevent the method name regression."""
        container = MainContainer()

        # The original error was calling get_start_session_command_handler
        # but the correct method is get_start_practice_session_command_handler

        # This should work (correct method name)
        assert hasattr(container, "get_start_practice_session_command_handler")

        # This should NOT exist (the wrong method name that caused the error)
        assert not hasattr(container, "get_start_session_command_handler")

        # For reference, there IS a different command for start_session_command
        # but it's for session creation, not practice session creation
        from src.application.commands.start_session_command import StartSessionCommand

        # These are different commands for different purposes
        assert StartPracticeSessionCommand != StartSessionCommand


class TestImagePracticeModeErrorScenarios:
    """Test error scenarios that should be handled gracefully."""

    def test_missing_container_scenario(self):
        """Test behavior when container is missing."""
        mock_user_repo = Mock()
        practice_screen = PracticeScreen(
            practice_mode="images",
            user_repository=mock_user_repo,
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )

        # The _create_practice_session method should handle this gracefully
        # We can't easily test this without complex async mocking, but we verify the method exists
        assert hasattr(practice_screen, "_create_practice_session")

        # Verify the method exists to prevent regression
        assert callable(practice_screen._create_practice_session)

    def test_container_method_compatibility(self):
        """Test that container methods are compatible with expected signatures."""
        container = MainContainer()

        # Get the handler
        handler = container.get_start_practice_session_command_handler()

        # It should have a handle method (for the old CQRS pattern)
        assert hasattr(handler, "handle")

        # The handler should be callable
        assert callable(handler.handle)
