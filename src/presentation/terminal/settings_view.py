"""Settings Management Screen for Integran terminal UI."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
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

from src.application.commands.save_user_settings_command import (
    SaveUserSettingsCommand,
    SaveUserSettingsCommandHandler,
)
from src.application.commands.toggle_developer_mode_command import (
    ToggleDeveloperModeCommand,
    ToggleDeveloperModeCommandHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQuery,
    LoadUserSettingsQueryHandler,
)
from src.domain.shared.services import EventBusInterface
from src.domain.user.models.user_models import (
    FederalState,
    Language,
    ThemeMode,
    UserPreferences,
    UserSettings,
)
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class SettingsWidget(EventAwareWidget):
    """Main settings widget with tabbed interface."""

    def __init__(
        self,
        event_bus: EventBusInterface,
        load_user_settings_query_handler: LoadUserSettingsQueryHandler,
        save_user_settings_command_handler: SaveUserSettingsCommandHandler,
        toggle_developer_mode_command_handler: ToggleDeveloperModeCommandHandler,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.load_user_settings_query_handler = load_user_settings_query_handler
        self.save_user_settings_command_handler = save_user_settings_command_handler
        self.toggle_developer_mode_command_handler = (
            toggle_developer_mode_command_handler
        )
        self.current_settings: UserSettings | None = None

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for settings updates."""
        # Subscribe to user settings events if needed
        pass

    def compose(self) -> ComposeResult:
        """Compose the settings interface."""
        yield Header(show_clock=True)
        with Container(classes="container-full"):
            with TabbedContent(id="settings-tabs", classes="tab-container"):
                with TabPane("General", id="general"):  # noqa: SIM117
                    with VerticalScroll(classes="tab-scroll"):  # noqa: SIM117
                        yield from self._compose_general_settings()
                with TabPane("Learning", id="learning"):  # noqa: SIM117
                    with VerticalScroll(classes="tab-scroll"):  # noqa: SIM117
                        yield from self._compose_learning_settings()
                with TabPane("Spaced Repetition", id="fsrs"):  # noqa: SIM117
                    with VerticalScroll(classes="tab-scroll"):  # noqa: SIM117
                        yield from self._compose_fsrs_settings()
                with TabPane("Developer", id="developer"):  # noqa: SIM117
                    with VerticalScroll(classes="tab-scroll"):  # noqa: SIM117
                        yield from self._compose_developer_settings()
                with TabPane("Advanced", id="advanced"):  # noqa: SIM117
                    with VerticalScroll(classes="tab-scroll"):  # noqa: SIM117
                        yield from self._compose_advanced_settings()
            yield Container(
                Horizontal(
                    Button("Save Changes", id="save", variant="primary"),
                    Button("Reset to Defaults", id="reset", variant="warning"),
                    Button("Back to Menu", id="cancel", variant="default"),
                    classes="buttons-horizontal",
                ),
                classes="footer-container",
            )
        yield Footer()

    def _compose_general_settings(self) -> ComposeResult:
        """Compose general settings tab."""
        yield Label("Interface Settings", classes="text-section-header")
        yield Container(
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
            classes="form-item",
        )
        yield Container(
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
            classes="form-item",
        )
        yield Container(
            Label("Notifications:"),
            Switch(value=True, id="notifications-switch"),
            classes="form-item",
        )
        yield Container(
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
            classes="form-item",
        )

        yield Label("Location Settings", classes="text-section-header")
        yield Container(
            Label("Federal State:"),
            Select(
                [(state.display_name, state.value) for state in FederalState],
                value=FederalState.GENERAL.value,
                id="federal-state-select",
            ),
            Static(
                "Select your federal state for state-specific questions",
                classes="help-text",
            ),
            classes="form-item",
        )

    def _compose_learning_settings(self) -> ComposeResult:
        """Compose learning settings tab."""
        yield Label("Learning Preferences", classes="text-section-header")
        yield Container(
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
            classes="form-item",
        )
        yield Container(
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
            classes="form-item",
        )
        yield Container(
            Label("Show Explanations:"),
            Switch(value=True, id="explanations-switch"),
            Static("Show detailed explanations after answering", classes="help-text"),
            classes="form-item",
        )
        yield Container(
            Label("Auto Advance:"),
            Switch(value=False, id="auto-advance-switch"),
            Static("Automatically proceed to next question", classes="help-text"),
            classes="form-item",
        )

    def _compose_fsrs_settings(self) -> ComposeResult:
        """Compose FSRS (spaced repetition) settings tab."""
        yield Label("Spaced Repetition Algorithm", classes="text-section-header")
        yield Static(
            "Configure FSRS (Free Spaced Repetition Scheduler) algorithm settings.\n"
            "These settings control how the app determines which questions to show for optimal learning.",
            classes="help-text",
        )

        yield Container(
            Label("Desired Retention Rate:"),
            Select(
                [
                    ("80% - More reviews, faster learning", 0.80),
                    ("85% - Balanced approach", 0.85),
                    ("90% - Recommended default", 0.90),
                    ("95% - Fewer reviews, slower learning", 0.95),
                ],
                value=0.90,
                id="retention-rate-select",
            ),
            Static(
                "Target probability of recalling learned questions",
                classes="help-text",
            ),
            classes="form-item",
        )

        yield Container(
            Label("Mastery Threshold (days):"),
            Select(
                [
                    ("14 days - Conservative", 14),
                    ("21 days - Moderate", 21),
                    ("30 days - Recommended", 30),
                    ("45 days - Aggressive", 45),
                ],
                value=30,
                id="mastery-threshold-select",
            ),
            Static(
                "Questions with stability above this threshold are considered mastered",
                classes="help-text",
            ),
            classes="form-item",
        )

        yield Container(
            Label("Leech Detection Threshold:"),
            Select(
                [
                    ("5 lapses - Sensitive", 5),
                    ("8 lapses - Recommended", 8),
                    ("12 lapses - Moderate", 12),
                    ("15 lapses - Tolerant", 15),
                ],
                value=8,
                id="leech-threshold-select",
            ),
            Static(
                "Number of failures before flagging a question as problematic",
                classes="help-text",
            ),
            classes="form-item",
        )

        yield Container(
            Label("Sequential Mode Intelligence:"),
            Switch(value=True, id="fsrs-sequential-switch"),
            Static(
                "Apply FSRS filtering to sequential mode (excludes mastered questions)",
                classes="help-text",
            ),
            classes="form-item",
        )

        yield Container(
            Label("Include Mastered Occasionally:"),
            Switch(value=False, id="include-mastered-switch"),
            Static(
                "Periodically review well-learned questions for reinforcement",
                classes="help-text",
            ),
            classes="form-item",
        )

    def _compose_developer_settings(self) -> ComposeResult:
        """Compose developer settings tab."""
        yield Label("Developer Mode", classes="text-section-header")
        yield Static(
            "⚠️ Developer Mode enables advanced features that use external APIs\n\nThese features may incur costs (~$50-80 for full dataset generation)",
            classes="warning-box",
        )
        yield Container(
            Label("Enable Developer Mode:"),
            Switch(value=False, id="developer-mode-switch"),
            Static(
                "Enables access to AI-powered content generation",
                classes="text-help",
            ),
            classes="form-item",
        )
        yield Container(
            Label("Current Status:", classes="status-label"),
            Static(
                "Disabled - Using local dataset only",
                id="developer-status",
                classes="status-text",
            ),
            classes="form-item",
        )
        yield Container(
            Label("Available Features:", classes="features-label"),
            OptionList(
                "📊 Dataset Generation (AI-powered)",
                "🖼️ Image Processing (AI descriptions)",
                "🌐 Multilingual Answer Generation",
                "🔧 Advanced Debug Tools",
                id="developer-features",
                disabled=True,
            ),
            classes="form-item",
        )
        yield Static(
            "💡 Tip: The existing final_dataset.json contains all 460 questions with complete multilingual content",
            classes="text-tip",
        )

    def _compose_advanced_settings(self) -> ComposeResult:
        """Compose advanced settings tab."""
        yield Label("Advanced Configuration", classes="text-section-header")
        yield Container(
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
            classes="form-item",
        )
        yield Container(
            Label("Export Settings:"),
            Button("Export to File", id="export-settings", variant="default"),
            classes="form-item",
        )
        yield Container(
            Label("Reset Everything:"),
            Button("Factory Reset", id="factory-reset", variant="error"),
            Static(
                "⚠️ This will delete all progress and settings",
                classes="text-warning",
            ),
            classes="form-item",
        )

    async def on_mount(self) -> None:
        """Initialize settings when widget is mounted."""
        await super().on_mount()
        await self._load_current_settings()

    async def _load_current_settings(self) -> None:
        """Load current user settings and populate the UI."""
        try:
            query = LoadUserSettingsQuery(user_id=1)
            result = await self.load_user_settings_query_handler.handle(query)

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

        federal_state_select = self.query_one("#federal-state-select", Select)
        federal_state_select.value = settings.preferences.federal_state.value

        # Learning settings
        daily_goal_select = self.query_one("#daily-goal-select", Select)
        daily_goal_select.value = settings.preferences.daily_goal

        timeout_select = self.query_one("#timeout-select", Select)
        timeout_select.value = settings.preferences.session_timeout_minutes

        explanations_switch = self.query_one("#explanations-switch", Switch)
        explanations_switch.value = settings.preferences.show_explanations

        auto_advance_switch = self.query_one("#auto-advance-switch", Switch)
        auto_advance_switch.value = settings.preferences.auto_advance

        # FSRS settings
        retention_rate_select = self.query_one("#retention-rate-select", Select)
        retention_rate_select.value = settings.preferences.desired_retention_rate

        mastery_threshold_select = self.query_one("#mastery-threshold-select", Select)
        mastery_threshold_select.value = (
            settings.preferences.mastery_stability_threshold
        )

        leech_threshold_select = self.query_one("#leech-threshold-select", Select)
        leech_threshold_select.value = settings.preferences.leech_detection_threshold

        fsrs_sequential_switch = self.query_one("#fsrs-sequential-switch", Switch)
        fsrs_sequential_switch.value = settings.preferences.sequential_mode_uses_fsrs

        include_mastered_switch = self.query_one("#include-mastered-switch", Switch)
        include_mastered_switch.value = (
            settings.preferences.include_mastered_occasionally
        )

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
            command = ToggleDeveloperModeCommand(user_id=1, enabled=event.value)
            result = await self.toggle_developer_mode_command_handler.handle(command)

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
            command = SaveUserSettingsCommand(user_settings=updated_settings)
            result = await self.save_user_settings_command_handler.handle(command)

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
            command = SaveUserSettingsCommand(user_settings=default_settings)
            result = await self.save_user_settings_command_handler.handle(command)

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

    @on(Button.Pressed, "#export-settings")
    async def on_export_settings(self) -> None:
        """Export settings to file."""
        try:
            if not self.current_settings:
                await self._show_error("No settings to export")
                return

            # Create export data
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "user_settings": {
                    "user_id": self.current_settings.user_id,
                    "language": self.current_settings.language.value,
                    "theme_mode": self.current_settings.theme_mode.value,
                    "developer_mode": {
                        "enabled": self.current_settings.developer_mode.enabled,
                        "use_gemini": self.current_settings.developer_mode.use_gemini,
                        "api_usage_warnings": self.current_settings.developer_mode.api_usage_warnings,
                    },
                    "first_time_setup": self.current_settings.first_time_setup,
                    "onboarding_completed": self.current_settings.onboarding_completed,
                    "preferences": {
                        "daily_goal": self.current_settings.preferences.daily_goal,
                        "session_timeout_minutes": self.current_settings.preferences.session_timeout_minutes,
                        "show_explanations": self.current_settings.preferences.show_explanations,
                        "auto_advance": self.current_settings.preferences.auto_advance,
                        "theme_mode": self.current_settings.preferences.theme_mode.value,
                        "language": self.current_settings.preferences.language.value,
                        "enable_notifications": self.current_settings.preferences.enable_notifications,
                        "reminder_time": self.current_settings.preferences.reminder_time,
                        "federal_state": self.current_settings.preferences.federal_state.value,
                        "custom_settings": self.current_settings.preferences.custom_settings,
                    },
                    "flow_state": {
                        "current_screen": self.current_settings.flow_state.current_screen,
                        "session_in_progress": self.current_settings.flow_state.session_in_progress,
                        "current_session_id": self.current_settings.flow_state.current_session_id,
                        "last_question_id": self.current_settings.flow_state.last_question_id,
                        "setup_step": self.current_settings.flow_state.setup_step,
                        "flow_data": self.current_settings.flow_state.flow_data,
                    },
                },
            }

            # Write to file
            import json
            from pathlib import Path

            export_path = Path("data/settings_export.json")
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            await self._show_success(f"Settings exported to {export_path}")
            logger.info(f"Successfully exported settings to {export_path}")

        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            await self._show_error("Export failed - check logs for details")

    @on(Button.Pressed, "#factory-reset")
    async def on_factory_reset(self) -> None:
        """Perform factory reset with confirmation."""
        try:
            # Simple confirmation - in a full implementation you'd use a proper dialog
            await self._show_warning(
                "Factory reset requested - this will delete all data!"
            )
            # For now, just show a warning without actually resetting
            await self._show_error(
                "Factory reset not implemented yet - use with caution!"
            )

        except Exception as e:
            logger.error(f"Error during factory reset: {e}")
            await self._show_error("Factory reset failed")

    async def _gather_settings_from_ui(self) -> UserSettings:
        """Gather all settings values from UI components."""
        if not self.current_settings:
            raise ValueError("No current settings available")

        # General settings
        language_select = self.query_one("#language-select", Select)
        theme_select = self.query_one("#theme-select", Select)
        notifications_switch = self.query_one("#notifications-switch", Switch)
        reminder_select = self.query_one("#reminder-select", Select)
        federal_state_select = self.query_one("#federal-state-select", Select)

        # Learning settings
        daily_goal_select = self.query_one("#daily-goal-select", Select)
        timeout_select = self.query_one("#timeout-select", Select)
        explanations_switch = self.query_one("#explanations-switch", Switch)
        auto_advance_switch = self.query_one("#auto-advance-switch", Switch)

        # FSRS settings
        retention_rate_select = self.query_one("#retention-rate-select", Select)
        mastery_threshold_select = self.query_one("#mastery-threshold-select", Select)
        leech_threshold_select = self.query_one("#leech-threshold-select", Select)
        fsrs_sequential_switch = self.query_one("#fsrs-sequential-switch", Switch)
        include_mastered_switch = self.query_one("#include-mastered-switch", Switch)

        # Create updated preferences with type guards
        daily_goal = 20
        if daily_goal_select.value and isinstance(daily_goal_select.value, int):
            daily_goal = daily_goal_select.value

        timeout_minutes = 60
        if timeout_select.value and isinstance(timeout_select.value, int):
            timeout_minutes = timeout_select.value

        # FSRS values with type guards
        retention_rate = 0.90
        if retention_rate_select.value and isinstance(
            retention_rate_select.value, int | float
        ):
            retention_rate = float(retention_rate_select.value)

        mastery_threshold = 30
        if mastery_threshold_select.value and isinstance(
            mastery_threshold_select.value, int
        ):
            mastery_threshold = mastery_threshold_select.value

        leech_threshold = 8
        if leech_threshold_select.value and isinstance(
            leech_threshold_select.value, int
        ):
            leech_threshold = leech_threshold_select.value

        updated_preferences = UserPreferences(
            daily_goal=daily_goal,
            session_timeout_minutes=timeout_minutes,
            show_explanations=explanations_switch.value,
            auto_advance=auto_advance_switch.value,
            theme_mode=ThemeMode(str(theme_select.value)),
            language=Language(str(language_select.value)),
            enable_notifications=notifications_switch.value,
            reminder_time=str(reminder_select.value),
            federal_state=FederalState(str(federal_state_select.value)),
            desired_retention_rate=retention_rate,
            mastery_stability_threshold=mastery_threshold,
            leech_detection_threshold=leech_threshold,
            sequential_mode_uses_fsrs=fsrs_sequential_switch.value,
            include_mastered_occasionally=include_mastered_switch.value,
            retrievability_exclusion_threshold=0.9,  # Keep default for now
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
        logger.info(f"Success: {message}")
        self.notify(message, severity="information", timeout=3.0)

    async def _show_warning(self, message: str) -> None:
        """Show warning notification."""
        logger.warning(f"Warning: {message}")
        self.notify(message, severity="warning", timeout=5.0)

    async def _show_error(self, message: str) -> None:
        """Show error notification."""
        logger.error(f"Error: {message}")
        self.notify(message, severity="error", timeout=5.0)


class SettingsScreen(Screen[None]):
    """Settings management screen."""

    BINDINGS = [
        ("escape", "back_to_menu", "Back to Menu"),
    ]

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Settings specific styling */
    .warning-box {
        color: white;
    }

    .status-label {
        text-style: bold;
        color: $primary;
    }

    .status-text {
        margin-top: 1;
        padding: 1;
        border: solid white;
        background: $surface;
    }

    .features-label {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
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
    )

    def __init__(
        self,
        event_bus: EventBusInterface,
        load_user_settings_query_handler: LoadUserSettingsQueryHandler,
        save_user_settings_command_handler: SaveUserSettingsCommandHandler,
        toggle_developer_mode_command_handler: ToggleDeveloperModeCommandHandler,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.load_user_settings_query_handler = load_user_settings_query_handler
        self.save_user_settings_command_handler = save_user_settings_command_handler
        self.toggle_developer_mode_command_handler = (
            toggle_developer_mode_command_handler
        )

    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        yield SettingsWidget(
            event_bus=self.event_bus,
            load_user_settings_query_handler=self.load_user_settings_query_handler,
            save_user_settings_command_handler=self.save_user_settings_command_handler,
            toggle_developer_mode_command_handler=self.toggle_developer_mode_command_handler,
        )

    def action_back_to_menu(self) -> None:
        """Return to main menu (Escape key)."""
        self.app.pop_screen()
