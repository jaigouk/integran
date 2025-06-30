"""Tests to prevent CSS-related crashes that affect app usability."""

from unittest.mock import Mock

import pytest

from src.infrastructure.containers.main_container import MainContainer
from src.presentation.terminal.question_view import PracticeScreen
from src.presentation.terminal.settings_view import SettingsScreen
from src.presentation.terminal.themes import COMMON_CSS_BASE
from src.presentation.terminal.trainer_app import MainMenuScreen, TrainerApp


class TestCSSCrashPrevention:
    """Tests to prevent CSS-related crashes that directly affect app usage."""

    def test_common_css_base_contains_critical_classes(self):
        """Test that COMMON_CSS_BASE contains all critical CSS classes."""
        critical_classes = [
            "container-centered",
            "text-title",
            "text-subtitle",
            "buttons-vertical",
            "buttons-horizontal",
            "hidden",
            "text-help",
            "form-item",
            "warning-box",
            "content-section",
        ]

        for css_class in critical_classes:
            assert css_class in COMMON_CSS_BASE, (
                f"Critical CSS class '{css_class}' missing from COMMON_CSS_BASE. "
                f"This could cause UI crashes when components use this class."
            )

    def test_trainer_app_has_valid_css(self):
        """Test that TrainerApp has valid CSS that won't cause crashes."""
        # Create minimal container for testing
        container = Mock()
        mock_event_bus = Mock()
        mock_session_workflow = Mock()
        mock_query_service = Mock()
        mock_user_repository = Mock()

        app = TrainerApp(
            event_bus=mock_event_bus,
            session_workflow=mock_session_workflow,
            query_service=mock_query_service,
            user_repository=mock_user_repository,
            container=container,
        )

        # Verify CSS is properly defined
        assert app.CSS is not None
        assert len(app.CSS) > 0
        assert isinstance(app.CSS, str)

        # Verify critical CSS classes are included
        critical_classes = ["container-centered", "text-title", "buttons-vertical"]
        for css_class in critical_classes:
            assert css_class in app.CSS, (
                f"CSS class '{css_class}' missing from TrainerApp.CSS"
            )

    def test_main_menu_screen_has_compose_method(self):
        """Test that MainMenuScreen has compose method to prevent startup crashes."""
        main_screen = MainMenuScreen()

        assert hasattr(main_screen, "compose"), "MainMenuScreen missing compose method"
        assert callable(main_screen.compose), "MainMenuScreen.compose is not callable"

        # Verify compose method returns valid widgets
        composed_widgets = list(main_screen.compose())
        assert len(composed_widgets) > 0, "MainMenuScreen.compose returns no widgets"

    def test_practice_screen_has_valid_css(self):
        """Test that PracticeScreen has valid CSS to prevent rendering crashes."""
        practice_screen = PracticeScreen(
            practice_mode="sequential",
            user_repository=Mock(),
            submit_answer_command_handler=Mock(),
            start_practice_command_handler=Mock(),
        )

        assert hasattr(practice_screen, "CSS"), "PracticeScreen missing CSS attribute"
        assert practice_screen.CSS is not None
        assert len(practice_screen.CSS) > 0
        assert isinstance(practice_screen.CSS, str)

        # Verify critical practice-specific CSS classes
        practice_classes = [
            "question-tabs",
            "question-container",
            "answer-options",
            "answer-option",
            "answer-result",
        ]
        for css_class in practice_classes:
            assert css_class in practice_screen.CSS, (
                f"Practice CSS class '{css_class}' missing from PracticeScreen.CSS"
            )

    def test_settings_screen_has_valid_css(self):
        """Test that SettingsScreen has valid CSS to prevent rendering crashes."""
        event_bus = Mock()
        load_user_settings_handler = Mock()
        save_user_settings_handler = Mock()
        toggle_developer_mode_handler = Mock()

        settings_screen = SettingsScreen(
            event_bus=event_bus,
            load_user_settings_query_handler=load_user_settings_handler,
            save_user_settings_command_handler=save_user_settings_handler,
            toggle_developer_mode_command_handler=toggle_developer_mode_handler,
        )

        assert hasattr(settings_screen, "CSS"), "SettingsScreen missing CSS attribute"
        assert settings_screen.CSS is not None
        assert len(settings_screen.CSS) > 0
        assert isinstance(settings_screen.CSS, str)

    def test_all_screens_have_required_attributes(self):
        """Test that all screen classes have required attributes to prevent crashes."""
        screen_classes = [
            (MainMenuScreen, {}),
            (
                PracticeScreen,
                {
                    "practice_mode": "sequential",
                    "user_repository": Mock(),
                    "submit_answer_command_handler": Mock(),
                    "start_practice_command_handler": Mock(),
                },
            ),
        ]

        for screen_class, kwargs in screen_classes:
            screen = screen_class(**kwargs)

            # All screens should have these basic attributes
            assert hasattr(screen, "compose"), (
                f"{screen_class.__name__} missing compose method"
            )
            assert callable(screen.compose), (
                f"{screen_class.__name__}.compose not callable"
            )

            # Verify compose doesn't crash
            try:
                composed_widgets = list(screen.compose())
                assert isinstance(composed_widgets, list)
            except Exception as e:
                pytest.fail(f"{screen_class.__name__}.compose() crashed: {e}")

    def test_trainer_app_screens_registration(self):
        """Test that TrainerApp has all required screens registered."""
        container = Mock()
        mock_event_bus = Mock()
        mock_session_workflow = Mock()
        mock_query_service = Mock()
        mock_user_repository = Mock()

        app = TrainerApp(
            event_bus=mock_event_bus,
            session_workflow=mock_session_workflow,
            query_service=mock_query_service,
            user_repository=mock_user_repository,
            container=container,
        )

        required_screens = ["main", "practice", "stats", "settings"]

        for screen_name in required_screens:
            assert screen_name in app.SCREENS, (
                f"Required screen '{screen_name}' not registered in TrainerApp.SCREENS"
            )

    def test_main_menu_bindings_prevent_crashes(self):
        """Test that MainMenuScreen bindings are properly configured."""
        main_screen = MainMenuScreen()

        assert hasattr(main_screen, "BINDINGS"), "MainMenuScreen missing BINDINGS"
        assert isinstance(main_screen.BINDINGS, list), (
            "MainMenuScreen.BINDINGS not a list"
        )

        # Verify each binding has correct format (key, action, description)
        for binding in main_screen.BINDINGS:
            assert len(binding) == 3, f"Invalid binding format: {binding}"
            key, action, description = binding
            assert isinstance(key, str), f"Binding key not string: {key}"
            assert isinstance(action, str), f"Binding action not string: {action}"
            assert isinstance(description, str), (
                f"Binding description not string: {description}"
            )

            # Verify action method exists
            # Skip built-in actions and special cases
            if action not in ["quit", "confirm_quit"]:  # Built-in/special actions
                action_method = (
                    f"action_{action}" if not action.startswith("action_") else action
                )
                assert hasattr(main_screen, action_method), (
                    f"Action method '{action_method}' missing for binding '{key}'"
                )

    def test_css_syntax_validation(self):
        """Test that CSS syntax is valid to prevent rendering crashes."""
        # Test COMMON_CSS_BASE syntax
        css_content = COMMON_CSS_BASE

        # Basic syntax checks
        assert css_content.count("{") == css_content.count("}"), (
            "Mismatched braces in COMMON_CSS_BASE CSS"
        )

        # Should not have obvious syntax errors
        syntax_errors = [
            ";;",  # Double semicolons
            "{}",  # Empty rules
            "{{",  # Double opening braces
            "}}",  # Double closing braces
        ]

        for error in syntax_errors:
            assert error not in css_content, (
                f"CSS syntax error '{error}' found in COMMON_CSS_BASE"
            )

    def test_main_container_integration_prevents_crashes(self):
        """Test that MainContainer integrates properly to prevent dependency crashes."""
        try:
            container = MainContainer()

            # Verify essential services are available
            assert container.get_event_bus() is not None
            assert container.get_session_workflow() is not None
            assert container.get_query_service() is not None
            assert container.get_analytics_service() is not None
            assert container.get_user_container() is not None

        except Exception as e:
            pytest.fail(f"MainContainer initialization crashed: {e}")

    def test_practice_screen_initialization_prevents_crashes(self):
        """Test that PracticeScreen can be initialized without crashing."""
        modes = ["random", "sequential", "category", "review"]

        for mode in modes:
            try:
                screen = PracticeScreen(
                    practice_mode=mode,
                    user_repository=Mock(),
                    submit_answer_command_handler=Mock(),
                    start_practice_command_handler=Mock(),
                )
                assert screen.practice_mode == mode
                assert screen.session_id is None  # Should be None initially
                assert hasattr(screen, "_create_practice_session")

            except Exception as e:
                pytest.fail(
                    f"PracticeScreen initialization crashed for mode '{mode}': {e}"
                )


class TestCSSRegressionPrevention:
    """Tests to prevent regression of CSS-related issues."""

    def test_settings_screen_constructor_compatibility(self):
        """Test that SettingsScreen constructor is compatible with caller expectations."""
        event_bus = Mock()
        load_user_settings_handler = Mock()
        save_user_settings_handler = Mock()
        toggle_developer_mode_handler = Mock()

        # This should not raise any errors
        screen = SettingsScreen(
            event_bus=event_bus,
            load_user_settings_query_handler=load_user_settings_handler,
            save_user_settings_command_handler=save_user_settings_handler,
            toggle_developer_mode_command_handler=toggle_developer_mode_handler,
        )

        # Verify the screen can be composed without errors
        try:
            widgets = list(screen.compose())
            assert len(widgets) > 0
        except Exception as e:
            pytest.fail(f"SettingsScreen composition failed: {e}")

    def test_question_widget_session_id_compatibility(self):
        """Test that QuestionWidget accepts session_id parameter without breaking."""
        import json

        from src.domain.content.models.question_models import Question
        from src.presentation.terminal.question_view import QuestionWidget

        question = Question(
            id=1,
            question="Test?",
            options=json.dumps(["A", "B"]),
            correct="A",
            category="Test",
        )

        event_bus = Mock()

        # Create mock handlers
        enhanced_question_handler = Mock()
        load_user_settings_handler = Mock()
        submit_answer_handler = Mock()

        # Test with session_id
        widget1 = QuestionWidget(
            question=question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_answer_handler,
            session_id=123,
        )
        assert widget1.session_id == 123

        # Test without session_id (should default to None)
        widget2 = QuestionWidget(
            question=question,
            event_bus=event_bus,
            enhanced_question_query_handler=enhanced_question_handler,
            load_user_settings_query_handler=load_user_settings_handler,
            submit_answer_command_handler=submit_answer_handler,
        )
        assert widget2.session_id is None
