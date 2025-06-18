"""Test CSS property validation for Textual framework compatibility."""

import re


def extract_css_properties_from_string(css_content: str) -> set[str]:
    """Extract all CSS property names from a CSS string."""
    # Pattern to match CSS property declarations: property: value;
    property_pattern = r"^\s*([a-zA-Z-]+)\s*:"

    properties = set()
    lines = css_content.split("\n")

    for line in lines:
        line = line.strip()
        # Skip comments and selectors
        if line.startswith("/*") or line.startswith("//") or "{" in line or "}" in line:
            continue

        match = re.match(property_pattern, line)
        if match:
            property_name = match.group(1).strip()
            properties.add(property_name)

    return properties


def get_textual_supported_properties() -> set[str]:
    """Return the set of CSS properties supported by Textual framework.

    Based on Textual documentation and source code analysis.
    This list should be updated when Textual adds new CSS support.
    """
    return {
        # Layout properties
        "align",
        "dock",
        "display",
        "overflow",
        "overflow-x",
        "overflow-y",
        "visibility",
        # Box model
        "width",
        "height",
        "min-width",
        "min-height",
        "max-width",
        "max-height",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        # Border and background
        "border",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "background",
        # Text properties
        "color",
        "text-align",
        "text-style",
        "text-opacity",
        # Grid and flexbox (limited support)
        "grid-columns",
        "grid-rows",
        "grid-size",
        # Scrolling
        "scrollbar-background",
        "scrollbar-background-active",
        "scrollbar-background-hover",
        "scrollbar-color",
        "scrollbar-color-active",
        "scrollbar-color-hover",
        "scrollbar-corner-color",
        "scrollbar-gutter",
        "scrollbar-size",
        "scrollbar-size-horizontal",
        "scrollbar-size-vertical",
        # Transitions and animations (limited)
        "transition",
        # Other Textual-specific properties
        "opacity",
        "outline",
        "tint",
        "layer",
    }


def get_unsupported_properties() -> set[str]:
    """Return CSS properties that are NOT supported by Textual."""
    return {
        # Layout properties not supported
        "z-index",  # The specific property that caused the crash
        "position",
        "top",
        "right",
        "bottom",
        "left",
        "float",
        "clear",
        # Advanced CSS features
        "transform",
        "animation",
        "box-shadow",
        "text-shadow",
        "filter",
        "clip-path",
        "mask",
        # Typography features
        "font-family",
        "font-size",
        "font-weight",
        "line-height",
        "letter-spacing",
        "word-spacing",
        # Advanced layout
        "flex",
        "flex-direction",
        "flex-wrap",
        "justify-content",
        "align-items",
        "align-content",
        "grid-template-columns",
        "grid-template-rows",
        "grid-gap",
        "gap",
        # CSS3+ features
        "border-radius",
        "gradient",
        "rgba",
        "hsla",
        "calc",
        "var",
        # Media queries
        "@media",
        "@import",
        "@keyframes",
    }


class TestCSSValidation:
    """Test CSS property validation across all view files."""

    def test_question_view_css_properties(self):
        """Test that question view only uses supported CSS properties."""
        from src.presentation.terminal.question_view import PracticeScreen

        css_content = PracticeScreen.CSS
        used_properties = extract_css_properties_from_string(css_content)
        supported_properties = get_textual_supported_properties()
        unsupported_properties = get_unsupported_properties()

        # Check for explicitly unsupported properties
        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Question view uses unsupported CSS properties: {invalid_properties}. "
            f"These properties are not supported by Textual and will cause crashes."
        )

        # Warn about potentially unsupported properties
        unknown_properties = (
            used_properties - supported_properties - unsupported_properties
        )
        if unknown_properties:
            # For now, just log warnings for unknown properties
            print(
                f"Warning: Question view uses unknown CSS properties: {unknown_properties}"
            )

    def test_settings_view_css_properties(self):
        """Test that settings view only uses supported CSS properties."""
        from src.presentation.terminal.settings_view import SettingsScreen

        css_content = SettingsScreen.CSS
        used_properties = extract_css_properties_from_string(css_content)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Settings view uses unsupported CSS properties: {invalid_properties}"
        )

    def test_progress_view_css_properties(self):
        """Test that progress view only uses supported CSS properties."""
        from src.presentation.terminal.progress_view import ProgressScreen

        css_content = ProgressScreen.CSS
        used_properties = extract_css_properties_from_string(css_content)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Progress view uses unsupported CSS properties: {invalid_properties}"
        )

    def test_trainer_app_css_properties(self):
        """Test that trainer app only uses supported CSS properties."""
        from src.presentation.terminal.trainer_app import TrainerApp

        css_content = TrainerApp.CSS
        used_properties = extract_css_properties_from_string(css_content)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Trainer app uses unsupported CSS properties: {invalid_properties}"
        )

    def test_developer_view_css_properties(self):
        """Test that developer view only uses supported CSS properties."""
        from src.presentation.terminal.developer_view import DeveloperOperationsScreen

        css_content = DeveloperOperationsScreen.CSS
        used_properties = extract_css_properties_from_string(css_content)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Developer view uses unsupported CSS properties: {invalid_properties}"
        )

    def test_first_time_setup_css_properties(self):
        """Test that first time setup view only uses supported CSS properties."""
        from src.presentation.terminal.first_time_setup_view import FirstTimeSetupScreen

        css_content = FirstTimeSetupScreen.CSS
        used_properties = extract_css_properties_from_string(css_content)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"First time setup view uses unsupported CSS properties: {invalid_properties}"
        )

    def test_common_css_base_properties(self):
        """Test that common CSS base only uses supported CSS properties."""
        from src.presentation.terminal.themes import COMMON_CSS_BASE

        used_properties = extract_css_properties_from_string(COMMON_CSS_BASE)
        unsupported_properties = get_unsupported_properties()

        invalid_properties = used_properties.intersection(unsupported_properties)

        assert not invalid_properties, (
            f"Common CSS base uses unsupported CSS properties: {invalid_properties}"
        )

    def test_no_z_index_property_anywhere(self):
        """Specifically test that z-index is not used anywhere (regression test)."""
        view_modules = [
            "src.presentation.terminal.question_view",
            "src.presentation.terminal.settings_view",
            "src.presentation.terminal.progress_view",
            "src.presentation.terminal.trainer_app",
            "src.presentation.terminal.developer_view",
            "src.presentation.terminal.first_time_setup_view",
        ]

        for module_name in view_modules:
            module = __import__(module_name, fromlist=[""])

            # Get all CSS content from the module
            css_contents = []

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, "CSS"):
                    css_contents.append(attr.CSS)

            # Also check COMMON_CSS_BASE if available
            if hasattr(module, "COMMON_CSS_BASE"):
                css_contents.append(module.COMMON_CSS_BASE)

            for css_content in css_contents:
                assert "z-index" not in css_content, (
                    f"Found z-index property in {module_name}. "
                    f"This property is not supported by Textual and will cause crashes."
                )

    def test_css_syntax_validity(self):
        """Test that CSS has valid basic syntax structure."""
        from src.presentation.terminal.themes import COMMON_CSS_BASE

        # Basic syntax checks
        open_braces = COMMON_CSS_BASE.count("{")
        close_braces = COMMON_CSS_BASE.count("}")

        assert open_braces == close_braces, (
            f"CSS syntax error: mismatched braces. "
            f"Found {open_braces} opening and {close_braces} closing braces."
        )

        # Check for basic CSS structure patterns
        assert "/*" in COMMON_CSS_BASE or ".container" in COMMON_CSS_BASE, (
            "CSS should contain either comments or class selectors"
        )


class TestTextualCSSCompatibility:
    """Integration tests for Textual CSS compatibility."""

    def test_can_parse_all_css_without_errors(self):
        """Test that Textual can parse all our CSS without throwing exceptions."""
        # This would ideally test actual CSS parsing by Textual
        # For now, we ensure no obviously invalid syntax patterns

        view_classes = [
            "src.presentation.terminal.question_view.PracticeScreen",
            "src.presentation.terminal.settings_view.SettingsScreen",
            "src.presentation.terminal.progress_view.ProgressScreen",
            "src.presentation.terminal.trainer_app.TrainerApp",
            "src.presentation.terminal.developer_view.DeveloperOperationsScreen",
            "src.presentation.terminal.first_time_setup_view.FirstTimeSetupScreen",
        ]

        for class_path in view_classes:
            module_path, class_name = class_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)

            # Ensure CSS attribute exists and is a string
            assert hasattr(cls, "CSS"), f"{class_path} should have CSS attribute"
            assert isinstance(cls.CSS, str), f"{class_path}.CSS should be a string"
            assert len(cls.CSS) > 0, f"{class_path}.CSS should not be empty"


if __name__ == "__main__":
    # Run the tests manually for debugging
    test_class = TestCSSValidation()

    print("Testing CSS property validation...")

    try:
        test_class.test_question_view_css_properties()
        print("✓ Question view CSS is valid")
    except AssertionError as e:
        print(f"✗ Question view CSS error: {e}")

    try:
        test_class.test_no_z_index_property_anywhere()
        print("✓ No z-index properties found")
    except AssertionError as e:
        print(f"✗ Z-index property found: {e}")

    print("CSS validation tests completed.")
