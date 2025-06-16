"""Terminal UI themes and styling configuration for Integran."""

from __future__ import annotations

from rich.theme import Theme
from textual.design import ColorSystem

# Rich theme for consistent color styling
INTEGRAN_THEME = Theme(
    {
        # Primary brand colors
        "primary": "#2563eb",  # Blue
        "primary.light": "#60a5fa",  # Light blue
        "primary.dark": "#1d4ed8",  # Dark blue
        # Semantic colors
        "success": "#16a34a",  # Green
        "warning": "#d97706",  # Orange
        "error": "#dc2626",  # Red
        "info": "#0ea5e9",  # Cyan
        # UI colors
        "accent": "#8b5cf6",  # Purple
        "muted": "#6b7280",  # Gray
        "background": "#f8fafc",  # Light gray
        "surface": "#ffffff",  # White
        # Learning-specific colors
        "correct": "#16a34a",  # Green for correct answers
        "incorrect": "#dc2626",  # Red for incorrect answers
        "leech": "#f59e0b",  # Amber for leech cards
        "review": "#8b5cf6",  # Purple for review cards
        # FSRS difficulty colors
        "easy": "#22c55e",  # Green
        "good": "#3b82f6",  # Blue
        "hard": "#f59e0b",  # Amber
        "again": "#ef4444",  # Red
    }
)

# Textual color system for consistent styling
INTEGRAN_COLOR_SYSTEM = ColorSystem(
    primary="#2563eb",
    secondary="#8b5cf6",
    accent="#0ea5e9",
    warning="#d97706",
    error="#dc2626",
    success="#16a34a",
    surface="#ffffff",
    background="#f8fafc",
)


# Common styling constants
class UIConstants:
    """UI styling constants."""

    # Box drawing characters
    BOX_HORIZONTAL = "─"
    BOX_VERTICAL = "│"
    BOX_TOP_LEFT = "┌"
    BOX_TOP_RIGHT = "┐"
    BOX_BOTTOM_LEFT = "└"
    BOX_BOTTOM_RIGHT = "┘"
    BOX_CROSS = "┼"

    # Progress indicators
    PROGRESS_COMPLETE = "█"
    PROGRESS_PARTIAL = "▓"
    PROGRESS_EMPTY = "░"

    # Status indicators
    CHECK_MARK = "✓"
    CROSS_MARK = "✗"
    WARNING_MARK = "⚠"
    INFO_MARK = "ℹ"

    # Learning indicators
    LEECH_MARK = "🔥"
    REVIEW_MARK = "📖"
    NEW_MARK = "✨"

    # Padding and spacing
    CONTENT_PADDING = 2
    SECTION_SPACING = 1

    # Common widths
    SIDEBAR_WIDTH = 30
    MAIN_CONTENT_MIN_WIDTH = 60
    MODAL_WIDTH = 80

    # Common heights
    HEADER_HEIGHT = 3
    FOOTER_HEIGHT = 3
    STATUS_BAR_HEIGHT = 1


# Style mappings for different UI components
COMPONENT_STYLES = {
    "header": {
        "background": "primary",
        "color": "white",
        "padding": (1, 2),
        "text_align": "center",
    },
    "sidebar": {
        "background": "surface",
        "border": ("solid", "muted"),
        "padding": (1, 2),
    },
    "main_content": {
        "background": "background",
        "padding": (2, 4),
    },
    "question_box": {
        "background": "surface",
        "border": ("solid", "primary"),
        "padding": (2, 3),
        "margin": (1, 0),
    },
    "answer_option": {
        "background": "surface",
        "border": ("solid", "muted"),
        "padding": (1, 2),
        "margin": (0, 1),
    },
    "answer_selected": {
        "background": "primary.light",
        "border": ("solid", "primary"),
        "padding": (1, 2),
        "margin": (0, 1),
    },
    "progress_bar": {
        "background": "muted",
        "color": "success",
        "height": 1,
    },
    "status_bar": {
        "background": "primary.dark",
        "color": "white",
        "padding": (0, 2),
    },
    "modal": {
        "background": "surface",
        "border": ("solid", "primary"),
        "padding": (2, 4),
    },
    "button_primary": {
        "background": "primary",
        "color": "white",
        "padding": (1, 3),
        "border": ("solid", "primary.dark"),
    },
    "button_secondary": {
        "background": "surface",
        "color": "primary",
        "padding": (1, 3),
        "border": ("solid", "primary"),
    },
}


def get_difficulty_color(rating: int) -> str:
    """Get color for FSRS rating/difficulty."""
    rating_colors = {
        1: "again",  # Again - Red
        2: "hard",  # Hard - Amber
        3: "good",  # Good - Blue
        4: "easy",  # Easy - Green
    }
    return rating_colors.get(rating, "muted")


def get_progress_color(percentage: float) -> str:
    """Get color for progress percentage."""
    if percentage >= 90:
        return "success"
    elif percentage >= 70:
        return "good"
    elif percentage >= 50:
        return "warning"
    else:
        return "error"


def format_percentage(value: float, total: float) -> str:
    """Format percentage with color."""
    percentage = (value / total * 100) if total > 0 else 0
    color = get_progress_color(percentage)
    return f"[{color}]{percentage:.1f}%[/{color}]"
