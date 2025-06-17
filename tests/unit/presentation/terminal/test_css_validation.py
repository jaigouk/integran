"""Test CSS validation for terminal UI components.

This module ensures that Textual CSS doesn't contain unsupported features
like @media queries which cause runtime errors.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


def get_terminal_ui_files() -> list[Path]:
    """Get all Python files in the terminal presentation layer."""
    terminal_dir = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "presentation"
        / "terminal"
    )
    return list(terminal_dir.glob("*.py"))


def extract_css_from_file(file_path: Path) -> list[str]:
    """Extract CSS strings from Python file."""
    css_blocks = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse the AST to find CSS assignments
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "CSS"
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        css_blocks.append(node.value.value)

    except Exception:
        # If AST parsing fails, fall back to regex
        css_pattern = r'CSS\s*=\s*"""(.*?)"""'
        matches = re.findall(css_pattern, content, re.DOTALL)
        css_blocks.extend(matches)

    return css_blocks


@pytest.mark.parametrize("file_path", get_terminal_ui_files())
def test_no_media_queries_in_css(file_path: Path) -> None:
    """Test that CSS doesn't contain @media queries."""
    css_blocks = extract_css_from_file(file_path)

    for css_block in css_blocks:
        # Check for @media queries
        media_matches = re.findall(r"@media\s*\([^)]*\)", css_block, re.IGNORECASE)
        assert not media_matches, (
            f"Found unsupported @media query in {file_path}: {media_matches}. "
            "Textual CSS doesn't support @media queries."
        )


@pytest.mark.parametrize("file_path", get_terminal_ui_files())
def test_no_unsupported_at_rules_in_css(file_path: Path) -> None:
    """Test that CSS doesn't contain other unsupported @-rules."""
    css_blocks = extract_css_from_file(file_path)

    # List of CSS @-rules that Textual doesn't support
    unsupported_at_rules = [
        "@media",
        "@keyframes",
        "@import",
        "@font-face",
        "@supports",
        "@namespace",
        "@page",
        "@charset",
    ]

    for css_block in css_blocks:
        for at_rule in unsupported_at_rules:
            pattern = rf"{re.escape(at_rule)}\s*[\(\{{]"
            matches = re.findall(pattern, css_block, re.IGNORECASE)
            assert not matches, (
                f"Found unsupported {at_rule} in {file_path}. "
                f"Textual CSS doesn't support this @-rule."
            )


@pytest.mark.parametrize("file_path", get_terminal_ui_files())
def test_no_decimal_values_in_css(file_path: Path) -> None:
    """Test that CSS doesn't contain decimal values (Textual only supports integers)."""
    css_blocks = extract_css_from_file(file_path)

    for css_block in css_blocks:
        # Look for decimal values in CSS properties
        decimal_pattern = r":\s*\d+\.\d+"
        matches = re.findall(decimal_pattern, css_block)
        assert not matches, (
            f"Found decimal values in {file_path}: {matches}. "
            "Textual CSS only supports integer values for spacing, sizes, etc."
        )


@pytest.mark.parametrize("file_path", get_terminal_ui_files())
def test_no_unsupported_properties_in_css(file_path: Path) -> None:
    """Test that CSS doesn't contain properties unsupported by Textual."""
    css_blocks = extract_css_from_file(file_path)

    # Properties that Textual doesn't support
    unsupported_properties = [
        "word-wrap",
        "line-height",
        "font-size",  # Should use text-size instead
        "font-family",
        "letter-spacing",
        "word-spacing",
    ]

    for css_block in css_blocks:
        for prop in unsupported_properties:
            pattern = rf"{re.escape(prop)}\s*:"
            matches = re.findall(pattern, css_block, re.IGNORECASE)
            alternative = ""
            if prop == "font-size":
                alternative = " Use 'text-size' instead."
            elif prop in ["word-wrap", "line-height"]:
                alternative = " This is handled automatically by Textual."

            assert not matches, (
                f"Found unsupported property '{prop}' in {file_path}.{alternative}"
            )


def test_css_syntax_validity() -> None:
    """Test basic CSS syntax validity in terminal UI files."""
    files = get_terminal_ui_files()

    for file_path in files:
        css_blocks = extract_css_from_file(file_path)

        for css_block in css_blocks:
            # Check for basic syntax issues

            # Count braces
            open_braces = css_block.count("{")
            close_braces = css_block.count("}")
            assert open_braces == close_braces, (
                f"Mismatched braces in CSS from {file_path}. "
                f"Open: {open_braces}, Close: {close_braces}"
            )

            # Check for common syntax errors
            lines = css_block.split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("/*") or line.endswith("*/"):
                    continue

                # Skip if it's a CSS selector or comment
                if line.endswith("{") or line.startswith("}") or "/*" in line:
                    continue

                # Check property declarations end with semicolon or closing brace
                if (
                    ":" in line
                    and not line.endswith((";", "}", "{"))
                    and not any(c in line for c in ["(", ")", ","])
                    and line != lines[-1].strip()
                ):
                    pytest.fail(
                        f"Missing semicolon in CSS from {file_path} at line {i}: '{line}'"
                    )
