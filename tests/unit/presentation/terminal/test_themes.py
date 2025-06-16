"""Simplified tests for terminal UI themes and styling."""

from __future__ import annotations

from rich.theme import Theme
from textual.design import ColorSystem

from src.presentation.terminal.themes import (
    COMPONENT_STYLES,
    INTEGRAN_COLOR_SYSTEM,
    INTEGRAN_THEME,
    UIConstants,
    format_percentage,
    get_difficulty_color,
    get_progress_color,
)


class TestIntegranTheme:
    """Basic tests for the Integran Rich theme."""

    def test_theme_is_rich_theme(self) -> None:
        """Test that INTEGRAN_THEME is a valid Rich Theme object."""
        assert isinstance(INTEGRAN_THEME, Theme)

    def test_has_styles_dict(self) -> None:
        """Test that theme has styles dictionary."""
        assert hasattr(INTEGRAN_THEME, "styles")
        assert isinstance(INTEGRAN_THEME.styles, dict)

    def test_custom_colors_added(self) -> None:
        """Test that our custom colors were added to the theme."""
        custom_colors = [
            "primary",
            "success",
            "warning",
            "error",
            "easy",
            "good",
            "hard",
            "again",
        ]

        for color in custom_colors:
            assert color in INTEGRAN_THEME.styles
            assert INTEGRAN_THEME.styles[color] is not None


class TestIntegranColorSystem:
    """Basic tests for the Integran Textual color system."""

    def test_color_system_is_textual_type(self) -> None:
        """Test that INTEGRAN_COLOR_SYSTEM is a valid Textual ColorSystem."""
        assert isinstance(INTEGRAN_COLOR_SYSTEM, ColorSystem)

    def test_has_required_color_properties(self) -> None:
        """Test that color system has basic required properties."""
        required_properties = [
            "primary",
            "secondary",
            "accent",
            "warning",
            "error",
            "success",
        ]

        for prop in required_properties:
            assert hasattr(INTEGRAN_COLOR_SYSTEM, prop)
            color_value = getattr(INTEGRAN_COLOR_SYSTEM, prop)
            assert color_value is not None


class TestUIConstants:
    """Tests for UI constants."""

    def test_has_drawing_characters(self) -> None:
        """Test that UI constants has drawing characters."""
        assert hasattr(UIConstants, "BOX_HORIZONTAL")
        assert hasattr(UIConstants, "BOX_VERTICAL")
        assert isinstance(UIConstants.BOX_HORIZONTAL, str)

    def test_has_numeric_constants(self) -> None:
        """Test that UI constants has numeric layout values."""
        assert hasattr(UIConstants, "SIDEBAR_WIDTH")
        assert hasattr(UIConstants, "HEADER_HEIGHT")
        assert isinstance(UIConstants.SIDEBAR_WIDTH, int)
        assert UIConstants.SIDEBAR_WIDTH > 0


class TestComponentStyles:
    """Tests for component style definitions."""

    def test_is_dictionary(self) -> None:
        """Test that component styles is a dictionary."""
        assert isinstance(COMPONENT_STYLES, dict)
        assert len(COMPONENT_STYLES) > 0

    def test_has_basic_components(self) -> None:
        """Test that basic UI components have styles."""
        basic_components = ["header", "sidebar", "main_content", "button_primary"]

        for component in basic_components:
            assert component in COMPONENT_STYLES
            assert isinstance(COMPONENT_STYLES[component], dict)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_difficulty_color_valid_ratings(self) -> None:
        """Test difficulty color for valid FSRS ratings."""
        # Test valid ratings return color names
        assert get_difficulty_color(1) == "again"
        assert get_difficulty_color(2) == "hard"
        assert get_difficulty_color(3) == "good"
        assert get_difficulty_color(4) == "easy"

    def test_get_difficulty_color_invalid_rating(self) -> None:
        """Test difficulty color for invalid ratings."""
        assert get_difficulty_color(0) == "muted"
        assert get_difficulty_color(5) == "muted"

    def test_get_progress_color_ranges(self) -> None:
        """Test progress color for different percentage ranges."""
        assert get_progress_color(95.0) == "success"  # 90%+
        assert get_progress_color(80.0) == "good"  # 70-89%
        assert get_progress_color(60.0) == "warning"  # 50-69%
        assert get_progress_color(30.0) == "error"  # <50%

    def test_format_percentage_basic(self) -> None:
        """Test basic percentage formatting."""
        result = format_percentage(80.0, 100.0)
        assert "80.0%" in result
        assert "[good]" in result
        assert "[/good]" in result

    def test_format_percentage_zero_total(self) -> None:
        """Test percentage formatting with zero total."""
        result = format_percentage(50.0, 0.0)
        assert "0.0%" in result
        assert "[error]" in result
