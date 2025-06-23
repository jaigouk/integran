"""First-Time Setup Wizard for Integran terminal UI."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    Markdown,
    ProgressBar,
    Select,
    Static,
    Switch,
)

from src.domain.user.models.user_models import (
    Language,
    SaveUserSettingsRequest,
    ThemeMode,
    UserPreferences,
    UserSettings,
)
from src.domain.user.services.load_user_settings import LoadUserSettings
from src.domain.user.services.save_user_settings import SaveUserSettings
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.infrastructure.repositories.user_repository import UserSettingsRepository
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class FirstTimeSetupWidget(EventAwareWidget):
    """First-time setup wizard widget with step-by-step onboarding."""

    def __init__(
        self,
        event_bus: EventBus,
        user_repository: UserSettingsRepository,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.user_repository = user_repository
        self.current_step = 1
        self.total_steps = 5
        self.user_settings: UserSettings | None = None

        # Initialize user services
        self.load_user_settings = LoadUserSettings(event_bus, user_repository)
        self.save_user_settings = SaveUserSettings(event_bus, user_repository)

        # Store user selections throughout wizard
        self.selected_language = Language.ENGLISH
        self.selected_theme = ThemeMode.AUTO
        self.developer_mode_enabled = False
        self.notifications_enabled = True
        self.daily_goal = 20

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for setup wizard."""
        # Subscribe to setup-related events if needed
        pass

    def compose(self) -> ComposeResult:
        """Compose the setup wizard interface."""
        yield Header(show_clock=True)

        with ScrollableContainer(id="setup-container"):
            yield Container(
                Label(
                    "🇩🇪 Welcome to Integran", id="setup-title", classes="setup-title"
                ),
                Static(
                    "Your personal trainer for the German Integration Exam",
                    classes="setup-subtitle",
                ),
                ProgressBar(
                    total=self.total_steps, show_eta=False, id="setup-progress"
                ),
                id="setup-header",
                classes="setup-header",
            )

            yield Container(id="step-content", classes="step-content")

            yield Container(
                Horizontal(
                    Button(
                        "← Previous", id="prev-btn", variant="default", disabled=True
                    ),
                    Button("Next →", id="next-btn", variant="primary"),
                    Button("Skip Setup", id="skip-btn", variant="warning"),
                    classes="setup-navigation",
                ),
                classes="setup-footer",
            )

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize setup wizard when mounted."""
        await super().on_mount()
        await self._show_step(1)

    async def _show_step(self, step: int) -> None:
        """Show the specified setup step."""
        self.current_step = step

        # Update progress bar
        progress_bar = self.query_one("#setup-progress", ProgressBar)
        progress_bar.update(progress=step)

        # Update navigation buttons
        prev_btn = self.query_one("#prev-btn", Button)
        next_btn = self.query_one("#next-btn", Button)

        prev_btn.disabled = step == 1

        if step == self.total_steps:
            next_btn.label = "Complete Setup"
            next_btn.variant = "success"
        else:
            next_btn.label = "Next →"
            next_btn.variant = "primary"

        # Show step content
        step_content = self.query_one("#step-content", Container)
        await step_content.remove_children()

        if step == 1:
            await self._show_welcome_step(step_content)
        elif step == 2:
            await self._show_language_step(step_content)
        elif step == 3:
            await self._show_theme_step(step_content)
        elif step == 4:
            await self._show_developer_step(step_content)
        elif step == 5:
            await self._show_preferences_step(step_content)

    async def _show_welcome_step(self, container: Container) -> None:
        """Show welcome and introduction step."""
        welcome_content = """
# 🎯 Welcome to Integran!

Integran is your intelligent training companion for the **German Integration Exam** (Leben in Deutschland Test).

## ✨ What makes Integran special?

- **🧠 Scientific Learning**: Uses the FSRS algorithm for optimal spaced repetition
- **🌍 Multilingual Support**: Explanations in German, English, Turkish, Ukrainian, and Arabic
- **📊 Smart Analytics**: Tracks your progress and identifies difficult topics
- **🎯 Focused Practice**: 460 official exam questions with detailed explanations
- **🔒 Privacy First**: All data stored locally, no cloud dependency

## 📚 About the Exam

The Integration Exam consists of 33 multiple-choice questions:
- 30 general questions about German history, politics, and society
- 3 questions specific to your federal state
- You need 17 correct answers to pass

Let's get you set up for success! This wizard will take just 2-3 minutes.
        """

        await container.mount(
            Vertical(
                Markdown(welcome_content, id="welcome-markdown"),
                classes="step-section",
            )
        )

    async def _show_language_step(self, container: Container) -> None:
        """Show language selection step."""
        language_content = """
# 🌐 Choose Your Interface Language

Select the language for Integran's interface. You can change this later in settings.

**Note**: Question explanations are available in all supported languages regardless of your interface choice.
        """

        await container.mount(
            Vertical(
                Markdown(language_content),
                Container(
                    Label("Interface Language:", classes="setting-label"),
                    Select(
                        [
                            ("English", Language.ENGLISH.value),
                            ("Deutsch (German)", Language.GERMAN.value),
                            ("Türkçe (Turkish)", Language.TURKISH.value),
                            ("Українська (Ukrainian)", Language.UKRAINIAN.value),
                            ("العربية (Arabic)", Language.ARABIC.value),
                        ],
                        value=self.selected_language.value,
                        id="language-select",
                    ),
                    classes="setting-item",
                ),
                Static(
                    "💡 Tip: Choose the language you're most comfortable with for navigation",
                    classes="tip-text",
                ),
                classes="step-section",
            )
        )

    async def _show_theme_step(self, container: Container) -> None:
        """Show theme selection step."""
        theme_content = """
# 🎨 Choose Your Theme

Select a visual theme for the best learning experience.
        """

        await container.mount(
            Vertical(
                Markdown(theme_content),
                Container(
                    Label("Visual Theme:", classes="setting-label"),
                    Select(
                        [
                            ("🔄 Auto (Follow System)", ThemeMode.AUTO.value),
                            ("☀️ Light Theme", ThemeMode.LIGHT.value),
                            ("🌙 Dark Theme", ThemeMode.DARK.value),
                        ],
                        value=self.selected_theme.value,
                        id="theme-select",
                    ),
                    classes="setting-item",
                ),
                Static(
                    "💡 Tip: Auto theme will switch between light and dark based on your system settings",
                    classes="tip-text",
                ),
                classes="step-section",
            )
        )

    async def _show_developer_step(self, container: Container) -> None:
        """Show developer mode explanation step."""
        developer_content = """
# 🔧 Developer Features (Optional)

Integran includes advanced features for developers and power users.

## What is Developer Mode?

Developer mode enables AI-powered features that use external APIs:
- **🤖 Multilingual Answer Generation**: Create new explanations using AI
- **🖼️ Image Processing**: Generate descriptions for visual questions
- **📊 Advanced Dataset Tools**: Build custom question sets

## ⚠️ Important Notes

- **Cost Warning**: These features use Google Gemini AI and may incur costs (~$50-80 for full dataset generation)
- **Not Required**: The app works perfectly without developer mode using the included dataset
- **Complete Dataset**: All 460 exam questions with multilingual explanations are already included

## 💡 Recommendation

**For most users**: Keep developer mode disabled. You have everything needed to ace the exam!
        """

        await container.mount(
            Vertical(
                Markdown(developer_content),
                Container(
                    Label("Enable Developer Mode:", classes="setting-label"),
                    Switch(value=self.developer_mode_enabled, id="developer-switch"),
                    Static(
                        "Only enable if you understand the costs and need AI features",
                        classes="warning-text",
                    ),
                    classes="setting-item",
                ),
                Static(
                    "🎯 Recommended: Leave disabled for optimal learning experience",
                    classes="tip-text",
                ),
                classes="step-section",
            )
        )

    async def _show_preferences_step(self, container: Container) -> None:
        """Show learning preferences step."""
        preferences_content = """
# 🎯 Learning Preferences

Configure your learning goals and preferences for the best experience.
        """

        await container.mount(
            Vertical(
                Markdown(preferences_content),
                Container(
                    Label("Daily Learning Goal:", classes="setting-label"),
                    Select(
                        [
                            ("🚀 Light (10 questions/day)", 10),
                            ("⭐ Recommended (20 questions/day)", 20),
                            ("💪 Intensive (30 questions/day)", 30),
                            ("🔥 Power User (50 questions/day)", 50),
                        ],
                        value=self.daily_goal,
                        id="goal-select",
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Study Reminders:", classes="setting-label"),
                    Switch(value=self.notifications_enabled, id="notifications-switch"),
                    Static(
                        "Get gentle reminders to maintain your learning streak",
                        classes="help-text",
                    ),
                    classes="setting-item",
                ),
                Static(
                    "📈 Based on research: 20 questions/day provides optimal retention without fatigue",
                    classes="tip-text",
                ),
                Container(
                    Label("🎉 Ready to Begin!", classes="completion-header"),
                    Static(
                        "You're all set! After setup, you'll have access to:",
                        classes="completion-text",
                    ),
                    Static(
                        "• 460 official exam questions with detailed explanations",
                        classes="feature-item",
                    ),
                    Static(
                        "• Scientific spaced repetition learning (FSRS algorithm)",
                        classes="feature-item",
                    ),
                    Static(
                        "• Progress tracking and performance analytics",
                        classes="feature-item",
                    ),
                    Static(
                        "• Multilingual support for better understanding",
                        classes="feature-item",
                    ),
                    classes="completion-section",
                ),
                classes="step-section",
            )
        )

    @on(Select.Changed, "#language-select")
    async def on_language_changed(self, event: Select.Changed) -> None:
        """Handle language selection change."""
        if event.value:
            self.selected_language = Language(str(event.value))
            await self._show_success(f"✅ Language set to {event.value}")

    @on(Select.Changed, "#theme-select")
    async def on_theme_changed(self, event: Select.Changed) -> None:
        """Handle theme selection change."""
        if event.value:
            self.selected_theme = ThemeMode(str(event.value))

    @on(Switch.Changed, "#developer-switch")
    async def on_developer_changed(self, event: Switch.Changed) -> None:
        """Handle developer mode toggle."""
        self.developer_mode_enabled = event.value
        if event.value:
            await self._show_warning(
                "⚠️ Developer mode enabled. External API calls may incur costs (~$50-80 for full dataset)."
            )
        else:
            await self._show_success(
                "✅ Developer mode disabled. Safe for learning with existing content."
            )

    @on(Select.Changed, "#goal-select")
    async def on_goal_changed(self, event: Select.Changed) -> None:
        """Handle daily goal selection change."""
        if event.value and isinstance(event.value, int):
            self.daily_goal = event.value
            if event.value >= 30:
                await self._show_warning(
                    f"🔥 Ambitious goal! {event.value} questions/day is intensive."
                )
            else:
                await self._show_success(
                    f"🎯 Daily goal set to {event.value} questions"
                )

    @on(Switch.Changed, "#notifications-switch")
    async def on_notifications_changed(self, event: Switch.Changed) -> None:
        """Handle notifications toggle."""
        self.notifications_enabled = event.value

    @on(Button.Pressed, "#prev-btn")
    async def on_previous_step(self) -> None:
        """Go to previous setup step."""
        if self.current_step > 1:
            await self._show_step(self.current_step - 1)

    @on(Button.Pressed, "#next-btn")
    async def on_next_step(self) -> None:
        """Go to next setup step or complete setup."""
        # Add step completion feedback
        step_names = [
            "Welcome",
            "Language & Theme",
            "Developer Mode",
            "Learning Preferences",
            "Summary",
        ]
        if self.current_step <= len(step_names):
            await self._show_success(
                f"✅ {step_names[self.current_step - 1]} completed"
            )

        if self.current_step < self.total_steps:
            await self._show_step(self.current_step + 1)
        else:
            await self._complete_setup()

    @on(Button.Pressed, "#skip-btn")
    async def on_skip_setup(self) -> None:
        """Skip setup and use defaults."""
        await self._show_warning(
            "⚠️ Skipping setup and using default settings. "
            "You can change these later in the Settings screen."
        )
        await self._complete_setup(use_defaults=True)

    async def _complete_setup(self, use_defaults: bool = False) -> None:
        """Complete the setup process and save settings."""
        try:
            if use_defaults:
                # Use default settings
                user_settings = UserSettings.create_default(user_id=1)
                await self._show_success(
                    "⚡ Using optimized default settings for quick start"
                )
            else:
                # Create settings from user selections
                preferences = UserPreferences(
                    daily_goal=self.daily_goal,
                    session_timeout_minutes=60,
                    show_explanations=True,
                    auto_advance=False,
                    theme_mode=self.selected_theme,
                    language=self.selected_language,
                    enable_notifications=self.notifications_enabled,
                    reminder_time="19:00",
                )

                user_settings = UserSettings.create_default(user_id=1)
                user_settings = (
                    user_settings.update_language(self.selected_language)
                    .update_preferences(preferences)
                    ._copy_with_updates(
                        theme_mode=self.selected_theme,
                        developer_mode=user_settings.developer_mode.enable()
                        if self.developer_mode_enabled
                        else user_settings.developer_mode.disable(),
                    )
                    .complete_first_time_setup()
                )

            # Save settings
            request = SaveUserSettingsRequest(user_settings=user_settings)
            result = await self.save_user_settings.call(request)

            if result.success:
                await self._show_success(
                    "🎉 Setup completed successfully! Your preferences have been saved. "
                    "Redirecting to main menu..."
                )
                await self._show_completion_message()
                # Return to main menu after a short delay
                self.set_timer(3.0, self._return_to_main_menu)
            else:
                await self._show_error(
                    f"❌ Failed to save settings: {result.error_message}. "
                    "Please try again or contact support."
                )

        except Exception as e:
            logger.error(f"Error completing setup: {e}")
            await self._show_error(f"Error completing setup: {e}")

    async def _show_completion_message(self) -> None:
        """Show setup completion message."""
        step_content = self.query_one("#step-content", Container)
        await step_content.remove_children()

        completion_content = """
# 🎉 Setup Complete!

Welcome to Integran! Your personalized learning environment is ready.

## 🚀 What's Next?

You'll be taken to the main menu where you can:
- **Start Learning**: Begin with practice questions
- **Review Progress**: Check your learning statistics
- **Adjust Settings**: Fine-tune your preferences anytime

## 🎯 Success Tips

- **Consistency**: Study a little each day for best results
- **Review Mistakes**: Focus on questions you got wrong
- **Use Explanations**: Read the detailed explanations to understand concepts
- **Track Progress**: Monitor your improvement over time

**Good luck with your Integration Exam preparation!** 🍀
        """

        await step_content.mount(
            Vertical(
                Markdown(completion_content),
                Static(
                    "Returning to main menu in 3 seconds...", classes="completion-timer"
                ),
                classes="step-section",
            )
        )

        # Hide navigation buttons
        nav_container = self.query_one(".setup-footer", Container)
        nav_container.display = False

    def _return_to_main_menu(self) -> None:
        """Return to the main menu."""
        self.app.pop_screen()

    async def _show_error(self, message: str) -> None:
        """Show error message."""
        logger.error(f"Setup Error: {message}")
        self.notify(message, severity="error", timeout=5.0)

    async def _show_success(self, message: str) -> None:
        """Show success notification."""
        logger.info(f"Setup Success: {message}")
        self.notify(message, severity="information", timeout=3.0)

    async def _show_warning(self, message: str) -> None:
        """Show warning notification."""
        logger.warning(f"Setup Warning: {message}")
        self.notify(message, severity="warning", timeout=4.0)


class FirstTimeSetupScreen(Screen[None]):
    """First-time setup screen."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Setup view specific styling */
    .setup-header {
        width: 100%;
        align: center middle;
        margin-bottom: 2;
        padding: 1;
        background: $surface;
        border: solid white;
    }

    .step-content {
        width: 100%;
        max-width: 100;
        align: center middle;
        margin: 2 0;
        padding: 2;
        background: $background;
        border: solid white;
    }

    .step-section {
        width: 100%;
        margin: 1 0;
    }

    .setting-label {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .completion-header {
        text-style: bold;
        color: $success;
        text-align: center;
        margin: 2 0 1 0;
    }

    .completion-text {
        text-align: center;
        margin: 1 0;
        color: $text;
    }

    .completion-section {
        margin: 2 0;
        padding: 2;
        background: $success;
        border: solid white;
    }

    .feature-item {
        color: $background;
        margin: 1 0;
        padding-left: 2;
    }

    .completion-timer {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        margin-top: 2;
    }

    #setup-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #setup-progress {
        width: 80%;
        margin: 1 0;
    }

    #welcome-markdown {
        height: auto;
        margin: 1 0;
    }
    """
    )

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
        """Compose the setup screen."""
        yield FirstTimeSetupWidget(
            event_bus=self.event_bus,
            user_repository=self.user_repository,
        )
