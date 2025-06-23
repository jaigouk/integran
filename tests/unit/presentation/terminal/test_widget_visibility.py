"""Test widget visibility fixes for settings and stats pages."""


def test_settings_widgets_have_proper_css():
    """Test that settings widgets have CSS that ensures visibility."""
    from src.presentation.terminal.settings_view import SettingsScreen

    css = SettingsScreen.CSS

    # Check that form items have proper height constraints (using new common CSS)
    assert "min-height: 4" in css
    assert ".form-item" in css

    # Check that Select widgets have explicit height and width
    assert ".form-item Select" in css
    assert "height: 3" in css
    assert "width: 100%" in css

    # Check that Switch widgets have proper height
    assert ".form-item Switch" in css


def test_stats_widgets_have_proper_css():
    """Test that stats widgets have CSS that ensures visibility."""
    from src.presentation.terminal.progress_view import ProgressScreen

    css = ProgressScreen.CSS

    # Check that stats widget has proper height constraints
    assert "#stats-widget" in css
    assert "min-height: 15" in css

    # Check that category container has proper height
    assert ".category-container" in css
    assert "min-height: 10" in css

    # Check that section headers have proper height (using new common CSS)
    assert ".text-section-header" in css
    assert "height: auto" in css


def test_stats_widgets_composition_code_has_loading_text():
    """Test that stats widget source code contains initial text."""
    import inspect

    from src.presentation.terminal.progress_view import StatsWidget

    # Get the source code of the __init__ method
    source = inspect.getsource(StatsWidget.__init__)

    # Check that initial text is in the source
    assert "Learning Statistics" in source


def test_category_widget_composition_code_has_loading_text():
    """Test that category widget source code contains loading text."""
    import inspect

    from src.presentation.terminal.progress_view import CategoryProgressWidget

    # Get the source code of the compose method
    source = inspect.getsource(CategoryProgressWidget.compose)

    # Check that loading text is in the source
    assert "Loading category data..." in source
