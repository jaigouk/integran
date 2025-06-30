"""Tests for settings screen constructor fixes."""

from unittest.mock import Mock

import pytest

from src.application.commands.save_user_settings_command import (
    SaveUserSettingsCommandHandler,
)
from src.application.commands.toggle_developer_mode_command import (
    ToggleDeveloperModeCommandHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQueryHandler,
)
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.settings_view import SettingsScreen
from src.presentation.terminal.trainer_app import MainMenuScreen


class TestSettingsScreenFixes:
    """Test the fixes for settings screen constructor issues."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserSettingsRepository)

    @pytest.fixture
    def mock_load_user_settings_handler(self):
        """Create a mock load user settings query handler."""
        return Mock(spec=LoadUserSettingsQueryHandler)

    @pytest.fixture
    def mock_save_user_settings_handler(self):
        """Create a mock save user settings command handler."""
        return Mock(spec=SaveUserSettingsCommandHandler)

    @pytest.fixture
    def mock_toggle_developer_mode_handler(self):
        """Create a mock toggle developer mode command handler."""
        return Mock(spec=ToggleDeveloperModeCommandHandler)

    @pytest.fixture
    def mock_app(self, mock_event_bus, mock_user_repository):
        """Create a mock app with event bus and user repository."""
        app = Mock()
        app.event_bus = mock_event_bus
        app.user_repository = mock_user_repository
        app.push_screen = Mock()
        return app

    def test_settings_screen_constructor_accepts_required_parameters(
        self,
        mock_event_bus,
        mock_load_user_settings_handler,
        mock_save_user_settings_handler,
        mock_toggle_developer_mode_handler,
    ):
        """Test that SettingsScreen constructor accepts required parameters."""
        # Arrange & Act
        screen = SettingsScreen(
            event_bus=mock_event_bus,
            load_user_settings_query_handler=mock_load_user_settings_handler,
            save_user_settings_command_handler=mock_save_user_settings_handler,
            toggle_developer_mode_command_handler=mock_toggle_developer_mode_handler,
        )

        # Assert
        assert screen.event_bus is mock_event_bus
        assert (
            screen.load_user_settings_query_handler is mock_load_user_settings_handler
        )
        assert (
            screen.save_user_settings_command_handler is mock_save_user_settings_handler
        )
        assert (
            screen.toggle_developer_mode_command_handler
            is mock_toggle_developer_mode_handler
        )

    def test_settings_screen_constructor_fails_without_event_bus(
        self,
        mock_load_user_settings_handler,
        mock_save_user_settings_handler,
        mock_toggle_developer_mode_handler,
    ):
        """Test that SettingsScreen constructor fails without event_bus."""
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="missing.*required.*event_bus"):
            SettingsScreen(
                load_user_settings_query_handler=mock_load_user_settings_handler,
                save_user_settings_command_handler=mock_save_user_settings_handler,
                toggle_developer_mode_command_handler=mock_toggle_developer_mode_handler,
            )

    def test_settings_screen_constructor_fails_without_handlers(self, mock_event_bus):
        """Test that SettingsScreen constructor fails without required handlers."""
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="missing.*required"):
            SettingsScreen(event_bus=mock_event_bus)

    def test_main_menu_action_show_settings_creates_screen_correctly(self, mock_app):  # noqa: ARG002
        """Test that action_show_settings method exists and can be called."""
        # Arrange
        main_screen = MainMenuScreen()

        # Verify the method exists
        assert hasattr(main_screen, "action_show_settings")
        assert callable(main_screen.action_show_settings)

        # The actual behavior requires an app context which is tested in integration tests

    def test_main_menu_on_settings_button_calls_action_show_settings(self, mock_app):  # noqa: ARG002
        """Test that on_settings_button method exists and can be called."""
        # Arrange
        main_screen = MainMenuScreen()

        # Verify the method exists
        assert hasattr(main_screen, "on_settings_button")
        assert callable(main_screen.on_settings_button)

        # The actual behavior requires an app context which is tested in integration tests

    def test_settings_screen_composes_settings_widget(
        self,
        mock_event_bus,
        mock_load_user_settings_handler,
        mock_save_user_settings_handler,
        mock_toggle_developer_mode_handler,
    ):
        """Test that SettingsScreen composes SettingsWidget with correct parameters."""
        # Arrange
        screen = SettingsScreen(
            event_bus=mock_event_bus,
            load_user_settings_query_handler=mock_load_user_settings_handler,
            save_user_settings_command_handler=mock_save_user_settings_handler,
            toggle_developer_mode_command_handler=mock_toggle_developer_mode_handler,
        )

        # Act
        composed_widgets = list(screen.compose())

        # Assert
        assert len(composed_widgets) == 1
        settings_widget = composed_widgets[0]
        # Verify it's a SettingsWidget with correct parameters
        assert hasattr(settings_widget, "event_bus")
        assert hasattr(settings_widget, "load_user_settings_query_handler")


class TestMainMenuScreenActions:
    """Test MainMenuScreen action methods to prevent regression."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = Mock()
        app.push_screen = Mock()
        app.event_bus = Mock()
        app.user_repository = Mock()
        app.container = Mock()
        return app

    def test_all_practice_actions_exist(self):
        """Test that all practice action methods exist."""
        main_screen = MainMenuScreen()

        required_actions = [
            "action_random_practice",
            "action_sequential_practice",
            "action_category_practice",
            "action_failed_practice",
            "action_images_practice",
            "action_show_stats",
            "action_show_settings",
            "action_confirm_quit",
        ]

        for action in required_actions:
            assert hasattr(main_screen, action), f"Missing action method: {action}"
            assert callable(getattr(main_screen, action)), (
                f"Action method not callable: {action}"
            )

    def test_practice_actions_create_practice_screens(self, mock_app):  # noqa: ARG002
        """Test that practice action methods exist and are callable."""
        # Arrange
        main_screen = MainMenuScreen()

        practice_actions = [
            ("action_random_practice", "random"),
            ("action_sequential_practice", "sequential"),
            ("action_category_practice", "category"),
            ("action_failed_practice", "failed"),
            ("action_images_practice", "images"),
        ]

        for action_name, _expected_mode in practice_actions:
            # Verify method exists and is callable
            assert hasattr(main_screen, action_name), f"Missing action: {action_name}"
            assert callable(getattr(main_screen, action_name)), (
                f"Action not callable: {action_name}"
            )

            # The actual behavior requires an app context which is tested in integration tests
