"""Tests for settings screen constructor fixes."""

from unittest.mock import Mock, patch

import pytest

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
    def mock_app(self, mock_event_bus, mock_user_repository):
        """Create a mock app with event bus and user repository."""
        app = Mock()
        app.event_bus = mock_event_bus
        app.user_repository = mock_user_repository
        app.push_screen = Mock()
        return app

    def test_settings_screen_constructor_accepts_required_parameters(
        self, mock_event_bus, mock_user_repository
    ):
        """Test that SettingsScreen constructor accepts required parameters."""
        # Arrange & Act
        screen = SettingsScreen(
            event_bus=mock_event_bus,
            user_repository=mock_user_repository,
        )

        # Assert
        assert screen.event_bus is mock_event_bus
        assert screen.user_repository is mock_user_repository

    def test_settings_screen_constructor_fails_without_event_bus(
        self, mock_user_repository
    ):
        """Test that SettingsScreen constructor fails without event_bus."""
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="missing.*required.*event_bus"):
            SettingsScreen(user_repository=mock_user_repository)

    def test_settings_screen_constructor_fails_without_user_repository(
        self, mock_event_bus
    ):
        """Test that SettingsScreen constructor fails without user_repository."""
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="missing.*required.*user_repository"):
            SettingsScreen(event_bus=mock_event_bus)

    def test_main_menu_action_show_settings_creates_screen_correctly(self, mock_app):
        """Test that action_show_settings creates SettingsScreen with correct parameters."""
        # Arrange
        main_screen = MainMenuScreen()

        with patch.object(main_screen, "app", mock_app):
            # Act
            main_screen.action_show_settings()

            # Assert
            mock_app.push_screen.assert_called_once()
            pushed_screen = mock_app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, SettingsScreen)
            assert pushed_screen.event_bus is mock_app.event_bus
            assert pushed_screen.user_repository is mock_app.user_repository

    def test_main_menu_on_settings_button_calls_action_show_settings(self, mock_app):
        """Test that on_settings_button calls action_show_settings."""
        # Arrange
        main_screen = MainMenuScreen()

        with patch.object(main_screen, "app", mock_app), Mock() as mock_action:
            main_screen.action_show_settings = mock_action

            # Act
            main_screen.on_settings_button()

            # Assert
            mock_action.assert_called_once()

    def test_settings_screen_composes_settings_widget(
        self, mock_event_bus, mock_user_repository
    ):
        """Test that SettingsScreen composes SettingsWidget with correct parameters."""
        # Arrange
        screen = SettingsScreen(
            event_bus=mock_event_bus,
            user_repository=mock_user_repository,
        )

        # Act
        composed_widgets = list(screen.compose())

        # Assert
        assert len(composed_widgets) == 1
        settings_widget = composed_widgets[0]
        # Verify it's a SettingsWidget with correct parameters
        assert hasattr(settings_widget, "event_bus")
        assert hasattr(settings_widget, "user_repository")


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
            "action_review_practice",
            "action_show_stats",
            "action_show_settings",
            "action_confirm_quit",
        ]

        for action in required_actions:
            assert hasattr(main_screen, action), f"Missing action method: {action}"
            assert callable(getattr(main_screen, action)), (
                f"Action method not callable: {action}"
            )

    def test_practice_actions_create_practice_screens(self, mock_app):
        """Test that practice actions create practice screens correctly."""
        # Arrange
        main_screen = MainMenuScreen()

        practice_actions = [
            ("action_random_practice", "random"),
            ("action_sequential_practice", "sequential"),
            ("action_category_practice", "category"),
            ("action_review_practice", "review"),
        ]

        for action_name, expected_mode in practice_actions:
            # Reset mock
            mock_app.push_screen.reset_mock()

            with patch.object(main_screen, "app", mock_app):
                # Act
                action = getattr(main_screen, action_name)
                action()

                # Assert
                mock_app.push_screen.assert_called_once()
                pushed_screen = mock_app.push_screen.call_args[0][0]
                assert hasattr(pushed_screen, "practice_mode")
                assert pushed_screen.practice_mode == expected_mode
