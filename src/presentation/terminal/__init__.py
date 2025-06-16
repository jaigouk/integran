"""Terminal UI module for Integran - Rich/Textual based interface."""

from .base import AsyncUIUpdater, ComponentRegistry, EventAwareApp, EventAwareWidget
from .themes import (
    COMPONENT_STYLES,
    INTEGRAN_COLOR_SYSTEM,
    INTEGRAN_THEME,
    UIConstants,
    format_percentage,
    get_difficulty_color,
    get_progress_color,
)

__all__ = [
    # Base classes
    "EventAwareApp",
    "EventAwareWidget",
    "AsyncUIUpdater",
    "ComponentRegistry",
    # Themes and styling
    "INTEGRAN_THEME",
    "INTEGRAN_COLOR_SYSTEM",
    "UIConstants",
    "COMPONENT_STYLES",
    "get_difficulty_color",
    "get_progress_color",
    "format_percentage",
]
