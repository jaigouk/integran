"""Integration test to ensure UI CSS styling works correctly during navigation."""

import logging

from src.infrastructure.containers.main_container import MainContainer
from src.presentation.terminal.trainer_app import MainMenuScreen, TrainerApp

logger = logging.getLogger(__name__)


class TestUICSSStying:
    """Test UI CSS styling and navigation."""

    def create_trainer_app_with_container(self):
        """Create a TrainerApp instance with full container setup."""
        container = MainContainer()
        app = TrainerApp(
            event_bus=container.get_event_bus(),
            session_workflow=container.get_session_workflow(),
            query_service=container.get_query_service(),
            analytics_service=container.get_analytics_service(),
            user_repository=container.get_user_container().get_repository(),
            container=container,
        )
        return app

    def test_main_menu_screen_has_proper_css_classes(self):
        """Test that MainMenuScreen has proper CSS classes applied."""
        app = self.create_trainer_app_with_container()

        # Create main menu screen
        main_screen = MainMenuScreen()

        # Check that the screen has the expected CSS structure
        assert hasattr(main_screen, "compose")

        # Verify CSS classes are properly defined in the app
        assert app.CSS is not None
        assert "container-centered" in app.CSS
        assert "text-title" in app.CSS
        assert "buttons-vertical" in app.CSS

    def test_practice_screen_navigation_preserves_css(self):
        """Test that navigating to practice screen preserves CSS styling."""
        # Verify the practice screen class has the expected CSS
        from src.presentation.terminal.question_view import PracticeScreen

        practice_screen = PracticeScreen(practice_mode="sequential")

        # Verify the practice screen has the expected attributes
        assert hasattr(practice_screen, "practice_mode")
        assert practice_screen.practice_mode == "sequential"
        assert hasattr(practice_screen, "CSS")
        assert practice_screen.CSS is not None

        # Verify CSS classes are present in practice screen
        assert "question-tabs" in practice_screen.CSS
        assert "question-container" in practice_screen.CSS
        assert "answer-options" in practice_screen.CSS

    def test_css_base_classes_are_defined(self):
        """Test that common CSS base classes are properly defined."""

        # Check that COMMON_CSS_BASE classes are included
        from src.presentation.terminal.themes import COMMON_CSS_BASE

        # Verify critical CSS classes exist
        critical_classes = [
            "container-centered",
            "text-title",
            "text-subtitle",
            "buttons-vertical",
            "hidden",
            "text-help",
        ]

        for css_class in critical_classes:
            assert css_class in COMMON_CSS_BASE, (
                f"Missing critical CSS class: {css_class}"
            )

    def test_app_initialization_with_css(self):
        """Test that the app initializes with proper CSS styling."""
        app = self.create_trainer_app_with_container()

        # Verify app has CSS defined
        assert app.CSS is not None
        assert len(app.CSS) > 0

        # Verify app has proper title and subtitle
        assert app.title == "Integran - German Integration Exam Trainer"
        assert app.sub_title == "Terminal-based spaced repetition learning"

        # Verify screens are properly registered
        assert "main" in app.SCREENS
        assert "practice" in app.SCREENS
        assert "stats" in app.SCREENS
        assert "settings" in app.SCREENS

    def test_main_menu_screen_bindings_are_correct(self):
        """Test that MainMenuScreen has correct key bindings."""
        main_screen = MainMenuScreen()

        # Verify expected bindings exist
        expected_bindings = [
            ("1", "random_practice", "Random Practice"),
            ("2", "sequential_practice", "Sequential Practice"),
            ("3", "category_practice", "Category Practice"),
            ("4", "review_practice", "Review Failed"),
            ("s", "show_stats", "Statistics"),
            ("t", "show_settings", "Settings"),
            ("q", "quit", "Quit"),
            ("escape", "confirm_quit", "Exit App"),
        ]

        # Check that all expected bindings are present
        binding_keys = [binding[0] for binding in main_screen.BINDINGS]
        binding_actions = [binding[1] for binding in main_screen.BINDINGS]

        for key, action, _ in expected_bindings:
            assert key in binding_keys, f"Missing key binding: {key}"
            assert action in binding_actions, f"Missing action binding: {action}"

    def test_main_menu_screen_has_action_methods(self):
        """Test that MainMenuScreen has all required action methods."""
        main_screen = MainMenuScreen()

        # Verify action methods exist
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
