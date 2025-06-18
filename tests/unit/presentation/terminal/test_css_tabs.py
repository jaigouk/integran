"""Test CSS changes for tab-based navigation."""


def test_css_contains_tab_styles():
    """Test that CSS contains tab-specific styles."""
    from src.presentation.terminal.question_view import PracticeScreen

    css = PracticeScreen.CSS

    # Should contain tab-related classes
    assert ".question-tabs" in css
    assert ".question-pane" in css
    assert ".learn-pane" in css
    assert ".question-container" in css
    assert ".learn-container" in css

    # Should contain docked rating styles
    assert "dock: bottom" in css
    assert ".fsrs-rating" in css


def test_tab_css_responsive_layout():
    """Test that tab CSS uses responsive layout."""
    from src.presentation.terminal.question_view import PracticeScreen

    css = PracticeScreen.CSS

    # Should use responsive units
    assert "max-height: 70vh" in css  # Tabs container
    assert "max-height: 65vh" in css  # Individual containers
    assert "overflow-y: auto" in css
    assert "scrollbar-gutter: stable" in css


def test_improved_text_contrast():
    """Test that CSS improves text contrast for readability."""
    from src.presentation.terminal.question_view import PracticeScreen

    css = PracticeScreen.CSS

    # Wrong explanation should have better contrast
    assert ".wrong-explanation" in css
    assert "color: $text" in css  # Not $text-muted
    assert "background: $surface" in css  # Added background for contrast


def test_fixed_rating_positioning():
    """Test that FSRS rating buttons are docked at bottom."""
    from src.presentation.terminal.question_view import PracticeScreen

    css = PracticeScreen.CSS

    # Rating should be docked at bottom
    assert "dock: bottom" in css
    rating_section = css[css.find(".fsrs-rating") : css.find(".rating-prompt")]
    assert "dock: bottom" in rating_section
    assert "width: 100%" in rating_section
    assert "min-height: 8" in rating_section


def test_eliminated_nested_scrolling():
    """Test that nested scrolling is eliminated."""
    from src.presentation.terminal.question_view import PracticeScreen

    css = PracticeScreen.CSS

    # Enhanced content should not have max-height causing overflow
    enhanced_section = css[css.find(".enhanced-content") : css.find(".content-section")]
    assert (
        "overflow: auto" in enhanced_section
    )  # Changed from 'visible' to fix Textual compatibility
    assert (
        "max-height: 40vh" not in enhanced_section
    )  # Old nested container style removed
