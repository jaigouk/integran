"""Settings Management Screen for Integran terminal UI."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    OptionList,
    Pretty,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from src.domain.user.models.user_models import (
    Language,
    LoadUserSettingsRequest,
    SaveUserSettingsRequest,
    ThemeMode,
    ToggleDeveloperModeRequest,
    UserPreferences,
    UserSettings,
)
from src.domain.user.services.load_user_settings import LoadUserSettings
from src.domain.user.services.save_user_settings import SaveUserSettings
from src.domain.user.services.toggle_developer_mode import ToggleDeveloperMode
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.base import EventAwareWidget

logger = logging.getLogger(__name__)


class SettingsWidget(EventAwareWidget):
    """Main settings widget with tabbed interface."""

    def __init__(
        self,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.user_repository = user_repository
        self.current_settings: UserSettings | None = None

        # Initialize user services
        self.load_user_settings = LoadUserSettings(event_bus, user_repository)
        self.save_user_settings = SaveUserSettings(event_bus, user_repository)
        self.toggle_developer_mode = ToggleDeveloperMode(event_bus, user_repository)

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for settings updates."""
        # Subscribe to user settings events if needed
        pass

    def compose(self) -> ComposeResult:
        """Compose the settings interface."""
        yield Header(show_clock=True)
        with TabbedContent(id="settings-tabs"):
            with TabPane("General", id="general"):
                yield from self._compose_general_settings()
            with TabPane("Learning", id="learning"):
                yield from self._compose_learning_settings()
            with TabPane("Developer", id="developer"):
                yield from self._compose_developer_settings()
            with TabPane("Advanced", id="advanced"):
                yield from self._compose_advanced_settings()
        yield Container(
            Horizontal(
                Button("Save Changes", id="save", variant="primary"),
                Button("Reset to Defaults", id="reset", variant="warning"),
                Button("Back to Menu", id="cancel", variant="default"),
                classes="settings-actions",
            ),
            classes="settings-footer",
        )
        yield Footer()

    def _compose_general_settings(self) -> ComposeResult:
        """Compose general settings tab."""
        yield Vertical(
            Label("Interface Settings", classes="section-header"),
            Container(
                Label("Language:"),
                Select(
                    [
                        ("English", Language.ENGLISH.value),
                        ("Deutsch", Language.GERMAN.value),
                        ("Türkçe", Language.TURKISH.value),
                        ("Українська", Language.UKRAINIAN.value),
                        ("العربية", Language.ARABIC.value),
                    ],
                    value=Language.ENGLISH.value,
                    id="language-select",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Theme Mode:"),
                Select(
                    [
                        ("Auto (System)", ThemeMode.AUTO.value),
                        ("Light", ThemeMode.LIGHT.value),
                        ("Dark", ThemeMode.DARK.value),
                    ],
                    value=ThemeMode.AUTO.value,
                    id="theme-select",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Notifications:"),
                Switch(value=True, id="notifications-switch"),
                classes="setting-item",
            ),
            Container(
                Label("Reminder Time (24h):"),
                Select(
                    [
                        ("08:00", "08:00"),
                        ("12:00", "12:00"),
                        ("16:00", "16:00"),
                        ("19:00", "19:00"),
                        ("21:00", "21:00"),
                    ],
                    value="19:00",
                    id="reminder-select",
                ),
                classes="setting-item",
            ),
            classes="settings-section",
        )

    def _compose_learning_settings(self) -> ComposeResult:
        """Compose learning settings tab."""
        yield Vertical(
            Label("Learning Preferences", classes="section-header"),
            Container(
                Label("Daily Goal (questions):"),
                Select(
                    [
                        ("10 questions", 10),
                        ("20 questions", 20),
                        ("30 questions", 30),
                        ("50 questions", 50),
                        ("100 questions", 100),
                    ],
                    value=20,
                    id="daily-goal-select",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Session Timeout:"),
                Select(
                    [
                        ("30 minutes", 30),
                        ("60 minutes", 60),
                        ("90 minutes", 90),
                        ("120 minutes", 120),
                        ("No timeout", 0),
                    ],
                    value=60,
                    id="timeout-select",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Show Explanations:"),
                Switch(value=True, id="explanations-switch"),
                Static(
                    "Show detailed explanations after answering", classes="help-text"
                ),
                classes="setting-item",
            ),
            Container(
                Label("Auto Advance:"),
                Switch(value=False, id="auto-advance-switch"),
                Static("Automatically proceed to next question", classes="help-text"),
                classes="setting-item",
            ),
            classes="settings-section",
        )

    def _compose_developer_settings(self) -> ComposeResult:
        """Compose developer settings tab."""
        yield Vertical(
            Label("Developer Mode", classes="section-header"),
            Container(
                Static(
                    "⚠️ Developer Mode enables advanced features that use external APIs",
                    classes="warning-text",
                ),
                Static(
                    "These features may incur costs (~$50-80 for full dataset generation)",
                    classes="warning-text",
                ),
                classes="warning-box",
            ),
            Container(
                Label("Enable Developer Mode:"),
                Switch(value=False, id="developer-mode-switch"),
                Static(
                    "Enables access to AI-powered content generation",
                    classes="help-text",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Current Status:", classes="status-label"),
                Static(
                    "Disabled - Using local dataset only",
                    id="developer-status",
                    classes="status-text",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Available Features:", classes="features-label"),
                OptionList(
                    "📊 Dataset Generation (AI-powered)",
                    "🖼️ Image Processing (AI descriptions)",
                    "🌐 Multilingual Answer Generation",
                    "🔧 Advanced Debug Tools",
                    id="developer-features",
                    disabled=True,
                ),
                classes="setting-item",
            ),
            Static(
                "💡 Tip: The existing final_dataset.json contains all 460 questions with complete multilingual content",
                classes="tip-text",
            ),
            classes="settings-section",
        )

    def _compose_advanced_settings(self) -> ComposeResult:
        """Compose advanced settings tab."""
        yield Vertical(
            Label("Advanced Configuration", classes="section-header"),
            Container(
                Label("Debug Information:"),
                Pretty(
                    {
                        "version": "0.1.0",
                        "database": "data/trainer.db",
                        "dataset": "data/final_dataset.json",
                        "config_path": "~/.config/integran/",
                    },
                    id="debug-info",
                ),
                classes="setting-item",
            ),
            Container(
                Label("Export Settings:"),
                Button("Export to File", id="export-settings", variant="default"),
                classes="setting-item",
            ),
            Container(
                Label("Reset Everything:"),
                Button("Factory Reset", id="factory-reset", variant="error"),
                Static(
                    "⚠️ This will delete all progress and settings",
                    classes="warning-text",
                ),
                classes="setting-item",
            ),
            classes="settings-section",
        )

    async def on_mount(self) -> None:
        """Initialize settings when widget is mounted."""
        await super().on_mount()
        await self._load_current_settings()

    async def _load_current_settings(self) -> None:
        """Load current user settings and populate the UI."""
        try:
            request = LoadUserSettingsRequest(user_id=1)
            result = await self.load_user_settings.call(request)

            if result.success and result.user_settings:
                self.current_settings = result.user_settings
                await self._populate_settings_ui()
            else:
                logger.error(f"Failed to load settings: {result.error_message}")
                await self._show_error("Failed to load current settings")

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            await self._show_error(f"Error loading settings: {e}")

    async def _populate_settings_ui(self) -> None:
        """Populate UI with current settings values."""
        if not self.current_settings:
            return

        settings = self.current_settings

        # General settings
        language_select = self.query_one("#language-select", Select)
        language_select.value = settings.language.value

        theme_select = self.query_one("#theme-select", Select)
        theme_select.value = settings.theme_mode.value

        notifications_switch = self.query_one("#notifications-switch", Switch)
        notifications_switch.value = settings.preferences.enable_notifications

        reminder_select = self.query_one("#reminder-select", Select)
        reminder_select.value = settings.preferences.reminder_time

        # Learning settings
        daily_goal_select = self.query_one("#daily-goal-select", Select)
        daily_goal_select.value = settings.preferences.daily_goal

        timeout_select = self.query_one("#timeout-select", Select)
        timeout_select.value = settings.preferences.session_timeout_minutes

        explanations_switch = self.query_one("#explanations-switch", Switch)
        explanations_switch.value = settings.preferences.show_explanations

        auto_advance_switch = self.query_one("#auto-advance-switch", Switch)
        auto_advance_switch.value = settings.preferences.auto_advance

        # Developer settings
        developer_switch = self.query_one("#developer-mode-switch", Switch)
        developer_switch.value = settings.developer_mode.enabled

        await self._update_developer_status()

    async def _update_developer_status(self) -> None:
        """Update developer mode status display."""
        if not self.current_settings:
            return

        status_text = self.query_one("#developer-status", Static)
        features_list = self.query_one("#developer-features", OptionList)

        if self.current_settings.developer_mode.enabled:
            status_text.update("🟢 Enabled - AI features available")
            status_text.add_class("status-enabled")
            status_text.remove_class("status-disabled")
            features_list.disabled = False
        else:
            status_text.update("🔴 Disabled - Using local dataset only")
            status_text.add_class("status-disabled")
            status_text.remove_class("status-enabled")
            features_list.disabled = True

    @on(Switch.Changed, "#developer-mode-switch")
    async def on_developer_mode_toggle(self, event: Switch.Changed) -> None:
        """Handle developer mode toggle."""
        try:
            request = ToggleDeveloperModeRequest(user_id=1, enable=event.value)
            result = await self.toggle_developer_mode.call(request)

            if result.success:
                self.current_settings = result.user_settings
                await self._update_developer_status()

                if result.warning_message:
                    await self._show_warning(result.warning_message)
            else:
                logger.error(f"Failed to toggle developer mode: {result.error_message}")
                await self._show_error("Failed to update developer mode")
                # Revert the switch
                event.switch.value = not event.value

        except Exception as e:
            logger.error(f"Error toggling developer mode: {e}")
            await self._show_error(f"Error updating developer mode: {e}")
            # Revert the switch
            event.switch.value = not event.value

    @on(Button.Pressed, "#save")
    async def on_save_settings(self) -> None:
        """Save all settings changes."""
        try:
            if not self.current_settings:
                await self._show_error("No settings loaded")
                return

            # Gather all settings from UI
            updated_settings = await self._gather_settings_from_ui()

            # Save settings
            request = SaveUserSettingsRequest(user_settings=updated_settings)
            result = await self.save_user_settings.call(request)

            if result.success:
                self.current_settings = result.user_settings
                await self._show_success("Settings saved successfully!")
            else:
                logger.error(f"Failed to save settings: {result.error_message}")
                await self._show_error("Failed to save settings")

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            await self._show_error(f"Error saving settings: {e}")

    @on(Button.Pressed, "#reset")
    async def on_reset_settings(self) -> None:
        """Reset settings to defaults."""
        try:
            # Create default settings
            default_settings = UserSettings.create_default(user_id=1)

            # Save defaults
            request = SaveUserSettingsRequest(user_settings=default_settings)
            result = await self.save_user_settings.call(request)

            if result.success:
                self.current_settings = result.user_settings
                await self._populate_settings_ui()
                await self._show_success("Settings reset to defaults!")
            else:
                logger.error(f"Failed to reset settings: {result.error_message}")
                await self._show_error("Failed to reset settings")

        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            await self._show_error(f"Error resetting settings: {e}")

    @on(Button.Pressed, "#cancel")
    async def on_cancel_settings(self) -> None:
        """Cancel settings changes and return to main menu."""
        self.app.pop_screen()

    async def _gather_settings_from_ui(self) -> UserSettings:
        """Gather all settings values from UI components."""
        if not self.current_settings:
            raise ValueError("No current settings available")

        # General settings
        language_select = self.query_one("#language-select", Select)
        theme_select = self.query_one("#theme-select", Select)
        notifications_switch = self.query_one("#notifications-switch", Switch)
        reminder_select = self.query_one("#reminder-select", Select)

        # Learning settings
        daily_goal_select = self.query_one("#daily-goal-select", Select)
        timeout_select = self.query_one("#timeout-select", Select)
        explanations_switch = self.query_one("#explanations-switch", Switch)
        auto_advance_switch = self.query_one("#auto-advance-switch", Switch)

        # Create updated preferences with type guards
        daily_goal = 20
        if daily_goal_select.value and isinstance(daily_goal_select.value, int):
            daily_goal = daily_goal_select.value

        timeout_minutes = 60
        if timeout_select.value and isinstance(timeout_select.value, int):
            timeout_minutes = timeout_select.value

        updated_preferences = UserPreferences(
            daily_goal=daily_goal,
            session_timeout_minutes=timeout_minutes,
            show_explanations=explanations_switch.value,
            auto_advance=auto_advance_switch.value,
            theme_mode=ThemeMode(str(theme_select.value)),
            language=Language(str(language_select.value)),
            enable_notifications=notifications_switch.value,
            reminder_time=str(reminder_select.value),
            custom_settings=self.current_settings.preferences.custom_settings,
        )

        # Update settings with new preferences and language/theme
        return (
            self.current_settings.update_language(Language(str(language_select.value)))
            .update_preferences(updated_preferences)
            ._copy_with_updates(theme_mode=ThemeMode(str(theme_select.value)))
        )

    async def _show_success(self, message: str) -> None:
        """Show success notification."""
        # TODO: Implement notification system
        logger.info(f"Success: {message}")

    async def _show_warning(self, message: str) -> None:
        """Show warning notification."""
        # TODO: Implement notification system
        logger.warning(f"Warning: {message}")

    async def _show_error(self, message: str) -> None:
        """Show error notification."""
        # TODO: Implement notification system
        logger.error(f"Error: {message}")


class SettingsScreen(Screen[None]):
    """Settings management screen."""

    BINDINGS = [
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    CSS = """
    .settings-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }

    .settings-container {
        align: center middle;
        width: 90%;
        max-width: 120;
        height: auto;
        background: $surface;
        border: solid white;
        padding: 2;
    }

    .settings-section {
        width: 100%;
        margin: 1 0;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        border-bottom: solid white;
        padding-bottom: 1;
    }

    .setting-item {
        margin: 1 0;
        padding: 1;
        background: $background;
        border: solid white;
    }

    .setting-item Label {
        text-style: bold;
        margin-bottom: 1;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }

    .warning-text {
        color: $warning;
        text-style: bold;
    }

    .warning-box {
        background: $warning;
        color: white;
        padding: 1;
        margin: 1 0;
        border: solid white;
    }

    .tip-text {
        color: $accent;
        text-style: italic;
        margin: 1 0;
        padding: 1;
        background: $background;
        border-left: solid white;
    }

    .status-label {
        text-style: bold;
        color: $primary;
    }

    .status-text {
        margin-top: 1;
        padding: 1;
        border: solid white;
    }

    .status-enabled {
        color: $success;
        background: $success;
    }

    .status-disabled {
        color: $error;
        background: $error;
    }

    .features-label {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
    }

    .settings-footer {
        margin-top: 2;
        width: 100%;
    }

    .settings-actions {
        align: center middle;
        width: 100%;
        margin: 2;
    }

    .settings-actions Button {
        width: 1fr;
        height: 3;
    }

    #settings-tabs {
        width: 100%;
        height: 60;
        margin: 1 0;
    }

    #developer-features {
        height: 8;
        margin-top: 1;
    }

    #debug-info {
        height: 8;
        margin-top: 1;
        border: solid white;
    }
    """

    def __init__(
        self,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.user_repository = user_repository

    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        yield SettingsWidget(
            event_bus=self.event_bus,
            user_repository=self.user_repository,
        )

    def action_back_to_menu(self) -> None:
        """Return to main menu (Escape key)."""
        self.app.pop_screen()
