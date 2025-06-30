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


# Common CSS Base Classes for consistent UI styling
COMMON_CSS_BASE = """
/* ===== LAYOUT FOUNDATIONS ===== */
.container-centered {
    align: center middle;
    width: 95vw;
    max-width: 120;
    height: auto;
    max-height: 85vh;
    background: $surface;
    border: solid white;
    padding: 2;
    margin: 1;
}

.container-full {
    width: 100%;
    height: 100%;
    display: block;
}

.container-scrollable {
    width: 100%;
    height: auto;
    max-height: 70vh;
    overflow-y: auto;
    scrollbar-gutter: stable;
    padding: 1;
}

.container-main {
    width: 100%;
    height: 100%;
}

/* ===== TYPOGRAPHY SYSTEM ===== */
.text-title {
    text-align: center;
    text-style: bold;
    color: $primary;
    margin: 1 0;
    height: auto;
}

.text-subtitle {
    text-align: center;
    color: $text 50%;
    margin-bottom: 2;
    text-style: italic;
    height: auto;
}

.text-section-header {
    text-style: bold;
    color: $primary;
    margin-bottom: 1;
    border-bottom: solid white;
    padding-bottom: 1;
    height: auto;
}

.text-help {
    color: $text 50%;
    text-style: italic;
    margin-top: 1;
    height: auto;
}

.text-warning {
    color: $warning;
    text-style: bold;
    margin: 1 0;
}

.text-tip {
    color: $accent;
    text-style: italic;
    margin: 1 0;
    padding: 1;
    background: $background;
    border-left: solid white;
}

/* ===== BUTTON SYSTEM ===== */
.buttons-horizontal {
    align: center middle;
    width: 100%;
    height: auto;
    margin: 1;
}

.buttons-vertical {
    align: center middle;
    width: 100%;
    height: auto;
}

.buttons-horizontal Button {
    width: 1fr;
    min-width: 12;
    height: 3;
    margin: 0 1;
}

.buttons-vertical Button {
    width: 100%;
    height: 3;
    margin: 1 0;
}

.button-full-width {
    width: 100%;
    height: 3;
}

/* ===== STATUS & STATE SYSTEM ===== */
.status-enabled {
    color: $success;
    text-style: bold;
}

.status-disabled {
    color: $text 50%;
    text-style: italic;
}

.status-warning {
    color: $warning;
    text-style: bold;
}

.status-error {
    color: $error;
    text-style: bold;
}

/* ===== FORM SYSTEM ===== */
.form-item {
    margin: 0 0 1 0;
    padding: 1;
    background: $background;
    border: solid white;
    height: auto;
    min-height: 4;
}

.form-item Label {
    text-style: bold;
    margin-bottom: 0;
}

.form-item Select {
    margin-top: 0;
    margin-bottom: 0;
    height: 3;
    width: 100%;
}

.form-item Switch {
    margin-top: 0;
    margin-bottom: 0;
    height: 3;
}

.form-item Input {
    margin-top: 0;
    margin-bottom: 0;
    height: 3;
    width: 100%;
}

/* ===== CONTENT SECTIONS ===== */
.content-section {
    margin: 2 0;
    padding: 2;
    background: $surface;
    border: solid white;
    height: auto;
}

.content-container {
    width: 100%;
    height: auto;
    background: $background;
    border: solid white;
    padding: 1;
    margin-bottom: 1;
}

.warning-box {
    background: $warning 20%;
    color: white;
    padding: 1;
    margin: 1 0;
    border: solid $warning;
    height: auto;
    min-height: 5;
    width: 100%;
}

/* ===== TAB SYSTEM ===== */
.tab-container {
    width: 100%;
    height: 1fr;
    margin: 0;
}

.tab-scroll {
    width: 100%;
    height: 1fr;
    min-height: 15;
    overflow-y: auto;
    scrollbar-gutter: stable;
}

/* ===== FOOTER SYSTEM ===== */
.footer-container {
    dock: bottom;
    width: 100%;
    height: auto;
    padding: 1;
    background: $background;
    border-top: solid white;
}

/* ===== UTILITY CLASSES ===== */
.hidden {
    display: none;
}

.full-height {
    height: 1fr;
}

.auto-height {
    height: auto;
}

.min-height-10 {
    min-height: 5;
}

.min-height-15 {
    min-height: 8;
}

.no-margin {
    margin: 0;
}

.no-padding {
    padding: 0;
}

.text-left {
    text-align: left;
}

.text-center {
    text-align: center;
}

.text-bold {
    text-style: bold;
}

.text-italic {
    text-style: italic;
}

/* ===== IMAGE DISPLAY SYSTEM ===== */
.image-options-grid {
    grid-size: 2 2;
    grid-gutter: 1 2;
    width: 100%;
    margin: 1 0;
    height: auto;
    min-height: 15;
}

.image-option-container {
    border: solid white;
    padding: 1;
    height: auto;
    min-height: 15;
    align: center middle;
    background: $surface;
}

.coat-of-arms-image {
    max-width: 100%;
    max-height: 12;
    align: center middle;
    margin: 1;
}

.image-fallback {
    border: dashed gray;
    padding: 1;
    text-align: center;
    background: $warning 10%;
    color: gray;
    height: 12;
    align: center middle;
}

.image-option-button {
    width: 100%;
    margin-top: 1;
    background: $primary;
    color: white;
    border: solid $primary-darken-3;
}

.image-option-button:hover {
    background: $primary-lighten-3;
}

.info-message {
    text-align: center;
    margin: 1 0;
    padding: 1;
    background: $background;
    border-left: solid $accent;
    color: $text;
}

.error-message {
    color: $error;
    text-style: bold;
    text-align: center;
    margin: 2 0;
    padding: 2;
    background: $error 10%;
    border: solid $error;
}

/* ===== QUESTION SPECIFIC SCROLLING ===== */
.question-pane {
    height: 1fr;
    max-height: 85vh;
}

.question-container {
    height: 1fr;
    min-height: 50vh;
    overflow-y: auto;
    scrollbar-gutter: stable;
}

.question-tabs {
    height: 1fr;
    max-height: 90vh;
}

/* ===== ANSWER BUTTON STYLING ===== */
.answer-buttons-column {
    width: 100%;
    height: auto;
    min-height: 15;
    padding: 1;
}

.answer-buttons-column Button {
    width: 100%;
    height: 5;
    margin: 1 0;
    min-height: 5;
    text-align: center;
    padding: 1 2;
}

.multi-image-button {
    background: $primary;
    color: white;
    border: solid $primary-darken-3;
    text-align: center;
    padding: 1 2;
    width: 100%;
    height: 5;
    min-height: 5;
    margin: 1 0;
    text-style: bold;
}

.options-header {
    text-align: center;
    text-style: bold;
    color: $primary;
    margin: 2 0 1 0;
    padding: 1;
}

/* ===== MULTI-IMAGE LAYOUT STYLING ===== */
.images-row {
    width: 100%;
    height: auto;
    min-height: 20;
    max-height: 30;
    margin: 2 0;
    padding: 1;
}

.image-container {
    width: 1fr;
    height: auto;
    min-height: 15;
    max-height: 20;
    margin: 0 1;
    border: solid white;
    padding: 1;
    align: center middle;
}

.multi-question-image {
    width: 100%;
    height: auto;
    max-height: 18;
    align: center middle;
}

.image-option-label {
    text-align: center;
    text-style: bold;
    color: $primary;
    margin-top: 1;
    height: 1;
}

/* ===== SINGLE-IMAGE LAYOUT STYLING ===== */
.single-image-container {
    width: 100%;
    height: auto;
    margin: 2 0;
    padding: 1;
    align: center middle;
}

.single-question-image {
    width: 90%;
    height: auto;
    align: center middle;
}
"""


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
