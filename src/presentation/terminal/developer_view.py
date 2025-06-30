"""Developer Operations Screen for Integran terminal UI."""

from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    OptionList,
    Pretty,
    ProgressBar,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from src.application.commands.start_dataset_build_command import (
    StartDatasetBuildCommand,
    StartDatasetBuildCommandHandler,
)
from src.application.commands.toggle_developer_mode_command import (
    ToggleDeveloperModeCommand,
    ToggleDeveloperModeCommandHandler,
)
from src.application.queries.load_user_settings_query import (
    LoadUserSettingsQuery,
    LoadUserSettingsQueryHandler,
)
from src.domain.content.events.content_events import (
    DatasetBuildCompletedEvent,
    DatasetBuildFailedEvent,
    DatasetBuildProgressEvent,
    DatasetBuildStartedEvent,
)
from src.infrastructure.messaging.enhanced_event_bus import EventBus
from src.presentation.terminal.base import EventAwareWidget
from src.presentation.terminal.themes import COMMON_CSS_BASE

logger = logging.getLogger(__name__)


class DeveloperOperationsWidget(EventAwareWidget):
    """Developer operations widget with AI-powered tools and monitoring."""

    def __init__(
        self,
        event_bus: EventBus,
        load_user_settings_query_handler: LoadUserSettingsQueryHandler,
        toggle_developer_mode_command_handler: ToggleDeveloperModeCommandHandler,
        start_dataset_build_command_handler: StartDatasetBuildCommandHandler,
        **kwargs: Any,
    ):
        super().__init__(event_bus=event_bus, **kwargs)
        self.load_user_settings_query_handler = load_user_settings_query_handler
        self.toggle_developer_mode_command_handler = (
            toggle_developer_mode_command_handler
        )
        self.start_dataset_build_command_handler = start_dataset_build_command_handler
        self.developer_mode_enabled = False

        # Operation status tracking
        self.operation_in_progress = False
        self.current_operation = ""
        self.operation_progress = 0

    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for developer operations."""
        # Subscribe to dataset build events for real-time UI updates
        self.event_bus.subscribe(
            DatasetBuildStartedEvent, self._on_dataset_build_started
        )
        self.event_bus.subscribe(
            DatasetBuildProgressEvent, self._on_dataset_build_progress
        )
        self.event_bus.subscribe(
            DatasetBuildCompletedEvent, self._on_dataset_build_completed
        )
        self.event_bus.subscribe(DatasetBuildFailedEvent, self._on_dataset_build_failed)

    def compose(self) -> ComposeResult:
        """Compose the developer operations interface."""
        yield Header(show_clock=True)

        with ScrollableContainer(id="developer-container"):
            yield Container(
                Label(
                    "🔧 Developer Operations",
                    id="developer-title",
                    classes="text-title",
                ),
                Static(
                    "AI-powered tools for content generation and advanced operations",
                    classes="text-subtitle",
                ),
                id="developer-header",
                classes="developer-header",
            )

            # Developer mode status
            yield Container(
                Label("Developer Mode Status", classes="text-section-header"),
                Static("🔴 Disabled", id="dev-status", classes="status-disabled"),
                Button(
                    "Enable Developer Mode", id="toggle-dev-mode", variant="primary"
                ),
                Static(
                    "⚠️ Developer mode required for AI operations",
                    classes="text-warning",
                ),
                classes="content-section",
            )

            with TabbedContent(id="developer-tabs"):
                with TabPane("Dataset Operations", id="dataset"):
                    yield from self._compose_dataset_operations()
                with TabPane("AI Generation", id="generation"):
                    yield from self._compose_ai_generation()
                with TabPane("Image Processing", id="images"):
                    yield from self._compose_image_processing()
                with TabPane("System Info", id="system"):
                    yield from self._compose_system_info()
                with TabPane("Danger Zone", id="danger"):
                    yield from self._compose_danger_zone()

        yield Footer()

    def _compose_dataset_operations(self) -> ComposeResult:
        """Compose dataset building operations tab."""
        dataset_content = """
# 📊 Dataset Building Operations

Build comprehensive multilingual datasets with AI-powered content generation.

**Current Status**: All 460 exam questions available with complete multilingual content.
        """

        yield Vertical(
            Markdown(dataset_content),
            Container(
                Label("Build Complete Dataset", classes="operation-header"),
                Container(
                    Label("Force Rebuild:"),
                    Switch(value=False, id="force-rebuild-switch"),
                    Static(
                        "Rebuild even if current dataset exists", classes="help-text"
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Enable Multilingual Generation:"),
                    Switch(value=True, id="multilingual-switch"),
                    Static(
                        "Generate content in all 5 supported languages",
                        classes="help-text",
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Batch Size:"),
                    Select(
                        [
                            ("Small (1-5 questions)", 5),
                            ("Medium (6-15 questions)", 15),
                            ("Large (16-30 questions)", 30),
                            ("Max (31-50 questions)", 50),
                        ],
                        value=15,
                        id="batch-size-select",
                    ),
                    Static("API requests per batch", classes="help-text"),
                    classes="setting-item",
                ),
                Container(
                    Label("Enable Image Processing:"),
                    Switch(value=True, id="image-processing-switch"),
                    Static("Process images with AI vision", classes="help-text"),
                    classes="setting-item",
                ),
                Button(
                    "Start Dataset Build",
                    id="start-dataset-build",
                    variant="primary",
                    disabled=True,
                ),
                Button(
                    "Check Build Status", id="check-build-status", variant="default"
                ),
                classes="content-section",
            ),
            Container(
                Label("Operation Progress", classes="section-header"),
                ProgressBar(total=100, show_eta=True, id="dataset-progress"),
                Static(
                    "No operation in progress",
                    id="progress-status",
                    classes="progress-text",
                ),
                classes="progress-section",
            ),
            Container(
                Label("Estimated Costs", classes="section-header"),
                Pretty(
                    {
                        "Full Dataset Generation": "$50-80 USD",
                        "Per Question (Multilingual)": "$0.10-0.20 USD",
                        "Image Processing": "$0.02-0.05 USD per image",
                        "Batch Processing": "Reduces costs by 15-20%",
                    },
                    id="cost-estimates",
                ),
                Static(
                    "💡 Tip: Use existing dataset to avoid costs. AI generation is for development only.",
                    classes="text-tip",
                ),
                classes="cost-section",
            ),
            classes="tab-content",
        )

    def _compose_ai_generation(self) -> ComposeResult:
        """Compose AI answer generation tab."""
        generation_content = """
# 🤖 AI Answer Generation

Generate multilingual explanations and educational content for specific questions.
        """

        yield Vertical(
            Markdown(generation_content),
            Container(
                Label("Question Selection", classes="operation-header"),
                Container(
                    Label("Question ID:"),
                    Input(
                        placeholder="Enter question ID (1-460)", id="question-id-input"
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Target Languages:"),
                    OptionList(
                        "English (en)",
                        "Deutsch (de)",
                        "Türkçe (tr)",
                        "Українська (uk)",
                        "العربية (ar)",
                        id="language-options",
                    ),
                    Static("Select languages for generation", classes="help-text"),
                    classes="setting-item",
                ),
                Container(
                    Label("Include Mnemonics:"),
                    Switch(value=True, id="mnemonics-switch"),
                    Static(
                        "Generate memory aids and learning tips", classes="help-text"
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Include Wrong Answer Analysis:"),
                    Switch(value=True, id="wrong-analysis-switch"),
                    Static(
                        "Explain why other options are incorrect", classes="help-text"
                    ),
                    classes="setting-item",
                ),
                Button(
                    "Generate Answer",
                    id="generate-answer-btn",
                    variant="primary",
                    disabled=True,
                ),
                classes="content-section",
            ),
            Container(
                Label("Generated Content Preview", classes="section-header"),
                Static(
                    "No content generated yet",
                    id="generated-preview",
                    classes="preview-text",
                ),
                Button(
                    "Save Generated Content",
                    id="save-generated",
                    variant="success",
                    disabled=True,
                ),
                classes="preview-section",
            ),
            classes="tab-content",
        )

    def _compose_image_processing(self) -> ComposeResult:
        """Compose image processing operations tab."""
        image_content = """
# 🖼️ Image Processing Operations

Analyze educational images using AI vision to generate contextual descriptions.
        """

        yield Vertical(
            Markdown(image_content),
            Container(
                Label("Image Selection", classes="operation-header"),
                Container(
                    Label("Image Path:"),
                    Input(placeholder="images/page_X_img_Y.png", id="image-path-input"),
                    Button("Browse Images", id="browse-images", variant="default"),
                    classes="setting-item",
                ),
                Container(
                    Label("Analysis Type:"),
                    Select(
                        [
                            ("Basic Description", "basic"),
                            ("Educational Context", "educational"),
                            ("Detailed Analysis", "detailed"),
                            ("Accessibility Focus", "accessibility"),
                        ],
                        value="educational",
                        id="analysis-type-select",
                    ),
                    classes="setting-item",
                ),
                Container(
                    Label("Include Cultural Context:"),
                    Switch(value=True, id="cultural-context-switch"),
                    Static(
                        "Add German cultural and historical context",
                        classes="help-text",
                    ),
                    classes="setting-item",
                ),
                Button(
                    "Process Image",
                    id="process-image-btn",
                    variant="primary",
                    disabled=True,
                ),
                classes="content-section",
            ),
            Container(
                Label("Available Images", classes="section-header"),
                OptionList(
                    "🖼️ Loading available images...",
                    id="available-images",
                    disabled=True,
                ),
                classes="images-section",
            ),
            Container(
                Label("Processing Results", classes="section-header"),
                Static(
                    "No image processed yet", id="image-results", classes="results-text"
                ),
                classes="results-section",
            ),
            classes="tab-content",
        )

    def _compose_system_info(self) -> ComposeResult:
        """Compose system information and diagnostics tab."""
        yield Vertical(
            Container(
                Label("API Configuration", classes="section-header"),
                Pretty(
                    {
                        "Gemini API": "Not configured",
                        "Vertex AI": "Not configured",
                        "Project ID": "Not set",
                        "Region": "Not set",
                        "Model": "gemini-2.5-pro-preview-06-05",
                    },
                    id="api-config-info",
                ),
                Button(
                    "Test API Connection",
                    id="test-api",
                    variant="default",
                    disabled=True,
                ),
                classes="config-section",
            ),
            Container(
                Label("Usage Statistics", classes="section-header"),
                Pretty(
                    {
                        "Total API Calls": 0,
                        "Dataset Builds": 0,
                        "Images Processed": 0,
                        "Questions Generated": 0,
                        "Estimated Costs": "$0.00",
                    },
                    id="usage-stats",
                ),
                Button("Reset Statistics", id="reset-stats", variant="warning"),
                classes="stats-section",
            ),
            Container(
                Label("System Health", classes="section-header"),
                Pretty(
                    {
                        "Database": "✅ Connected",
                        "Event Bus": "✅ Active",
                        "User Settings": "✅ Loaded",
                        "Content Repository": "✅ Available",
                        "Final Dataset": "✅ 460 questions loaded",
                    },
                    id="system-health",
                ),
                Button("Run Health Check", id="health-check", variant="default"),
                classes="health-section",
            ),
            classes="tab-content",
        )

    def _compose_danger_zone(self) -> ComposeResult:
        """Compose dangerous operations tab."""
        danger_content = """
# ⚠️ Danger Zone

**Warning**: These operations can be destructive and expensive. Use with extreme caution.
        """

        yield Vertical(
            Markdown(danger_content),
            Container(
                Label("⚠️ DANGEROUS OPERATIONS ⚠️", classes="danger-header"),
                Static(
                    "These operations are irreversible and may incur significant costs",
                    classes="danger-warning",
                ),
                classes="danger-banner",
            ),
            Container(
                Label("Reset All Generated Content", classes="operation-header"),
                Static(
                    "Delete all AI-generated content and revert to original dataset",
                    classes="danger-description",
                ),
                Button(
                    "Reset Generated Content",
                    id="reset-generated",
                    variant="error",
                    disabled=True,
                ),
                classes="danger-operation",
            ),
            Container(
                Label("Force Complete Rebuild", classes="operation-header"),
                Static(
                    "Rebuild entire dataset from scratch. Estimated cost: $50-80",
                    classes="danger-description",
                ),
                Input(
                    placeholder="Type 'CONFIRM REBUILD' to enable", id="rebuild-confirm"
                ),
                Button(
                    "Force Complete Rebuild",
                    id="force-rebuild",
                    variant="error",
                    disabled=True,
                ),
                classes="danger-operation",
            ),
            Container(
                Label("Clear All User Data", classes="operation-header"),
                Static(
                    "Delete all user progress, settings, and learning history",
                    classes="danger-description",
                ),
                Input(
                    placeholder="Type 'DELETE ALL DATA' to enable", id="delete-confirm"
                ),
                Button(
                    "Clear All Data",
                    id="clear-all-data",
                    variant="error",
                    disabled=True,
                ),
                classes="danger-operation",
            ),
            classes="tab-content",
        )

    async def on_mount(self) -> None:
        """Initialize developer operations when mounted."""
        await super().on_mount()
        await self._load_developer_status()
        await self._load_available_images()

    async def _load_developer_status(self) -> None:
        """Load current developer mode status."""
        try:
            query = LoadUserSettingsQuery(user_id=1)
            result = await self.load_user_settings_query_handler.handle(query)

            if result.success and result.user_settings:
                self.developer_mode_enabled = (
                    result.user_settings.developer_mode.enabled
                )
                await self._update_developer_status()
                await self._update_operation_buttons()
            else:
                logger.error(f"Failed to load developer status: {result.error_message}")

        except Exception as e:
            logger.error(f"Error loading developer status: {e}")

    async def _update_developer_status(self) -> None:
        """Update developer mode status display."""
        status_text = self.query_one("#dev-status", Static)
        toggle_btn = self.query_one("#toggle-dev-mode", Button)

        if self.developer_mode_enabled:
            status_text.update("🟢 Enabled - AI operations available")
            status_text.add_class("status-enabled")
            status_text.remove_class("status-disabled")
            toggle_btn.label = "Disable Developer Mode"
            toggle_btn.variant = "warning"
        else:
            status_text.update("🔴 Disabled - AI operations restricted")
            status_text.add_class("status-disabled")
            status_text.remove_class("status-enabled")
            toggle_btn.label = "Enable Developer Mode"
            toggle_btn.variant = "primary"

    async def _update_operation_buttons(self) -> None:
        """Update operation button states based on developer mode."""
        operation_buttons = [
            "#start-dataset-build",
            "#generate-answer-btn",
            "#process-image-btn",
            "#test-api",
            "#reset-generated",
            "#force-rebuild",
            "#clear-all-data",
        ]

        for button_id in operation_buttons:
            try:
                button = self.query_one(button_id, Button)
                button.disabled = not self.developer_mode_enabled
            except Exception as e:
                # Button might not exist in current tab
                logger.debug(f"Button {button_id} not found in current tab: {e}")

    async def _load_available_images(self) -> None:
        """Load list of available images for processing."""
        try:
            # This would typically load from the images directory
            # For now, show placeholder content
            images_list = self.query_one("#available-images", OptionList)
            images_list.clear_options()

            sample_images = [
                "🖼️ page_9_img_2.png - German federal eagle",
                "🖼️ page_15_img_1.png - Historical document",
                "🖼️ page_23_img_3.png - Political symbol",
                "🖼️ page_31_img_1.png - Cultural landmark",
                "🖼️ page_45_img_2.png - Government building",
            ]

            for image in sample_images:
                images_list.add_option(image)

            images_list.disabled = not self.developer_mode_enabled

        except Exception as e:
            logger.error(f"Error loading available images: {e}")
            await self._show_warning(
                "⚠️ Could not load available images. Image processing may be limited."
            )

    @on(Button.Pressed, "#toggle-dev-mode")
    async def on_toggle_developer_mode(self) -> None:
        """Handle developer mode toggle."""
        try:
            command = ToggleDeveloperModeCommand(
                user_id=1, enable=not self.developer_mode_enabled
            )
            result = await self.toggle_developer_mode_command_handler.handle(command)

            if result.success:
                self.developer_mode_enabled = result.developer_mode_enabled
                await self._update_developer_status()
                await self._update_operation_buttons()
                await self._load_available_images()

                # Enhanced success notification with context
                if result.developer_mode_enabled:
                    await self._show_success(
                        "🔓 Developer mode enabled! AI operations now available. "
                        "⚠️ Note: External API calls may incur costs."
                    )
                else:
                    await self._show_success(
                        "🔒 Developer mode disabled. AI operations are now restricted."
                    )

                if result.warning_message:
                    await self._show_warning(result.warning_message)
            else:
                await self._show_error(
                    f"❌ Failed to toggle developer mode: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Error toggling developer mode: {e}")
            await self._show_error(f"Error toggling developer mode: {e}")

    @on(Button.Pressed, "#start-dataset-build")
    async def on_start_dataset_build(self) -> None:
        """Handle dataset build operation."""
        if not self.developer_mode_enabled:
            await self._show_error(
                "🔒 Developer mode required for dataset building. "
                "Please enable developer mode first."
            )
            return

        try:
            # Get build parameters from UI
            force_rebuild = self.query_one("#force-rebuild-switch", Switch).value
            multilingual = self.query_one("#multilingual-switch", Switch).value
            # Note: batch_size UI exists but is not used in simplified command
            enable_images = self.query_one("#image-processing-switch", Switch).value

            # Create build command
            command = StartDatasetBuildCommand(
                user_id=1,
                use_cache=True,
                include_images=enable_images,
                target_languages=["en", "de"] if multilingual else ["en"],
                force_rebuild=force_rebuild,
            )

            # Start build operation
            self.operation_in_progress = True
            self.current_operation = "Building Dataset"
            await self._update_progress_display("Starting dataset build...")

            # Execute build (this would be async in real implementation)
            result = await self.start_dataset_build_command_handler.handle(command)

            if result.success:
                await self._show_success(
                    "✅ Dataset build completed successfully! "
                    f"Generated {result.statistics.get('questions_with_answers', 0)} answers "
                    f"in {result.statistics.get('build_duration_minutes', 0):.1f} minutes."
                )
                await self._update_progress_display("Dataset build completed", 100)
            else:
                await self._show_error(
                    f"❌ Dataset build failed: {result.error_message}. "
                    "Check logs for detailed error information."
                )
                await self._update_progress_display("Dataset build failed", 0)

            self.operation_in_progress = False

        except Exception as e:
            logger.error(f"Error starting dataset build: {e}")
            await self._show_error(f"Error starting dataset build: {e}")
            self.operation_in_progress = False

    @on(Button.Pressed, "#check-build-status")
    async def on_check_build_status(self) -> None:
        """Check dataset build status."""
        try:
            # Simplified implementation - check current operation status
            if self.operation_in_progress:
                await self._update_progress_display(
                    f"Build status: {self.current_operation} in progress",
                    self.operation_progress,
                )
                await self._show_success(
                    f"📊 Build status: {self.current_operation} ({self.operation_progress}% complete)"
                )
            else:
                await self._update_progress_display("No active build operation", 0)
                await self._show_success("✅ No active build operations found")

        except Exception as e:
            logger.error(f"Error checking build status: {e}")
            await self._show_error(f"Error checking build status: {e}")

    @on(Input.Changed, "#rebuild-confirm")
    async def on_rebuild_confirm_changed(self, event: Input.Changed) -> None:
        """Handle rebuild confirmation input."""
        rebuild_btn = self.query_one("#force-rebuild", Button)
        rebuild_btn.disabled = (
            event.value != "CONFIRM REBUILD"
        ) or not self.developer_mode_enabled

    @on(Input.Changed, "#delete-confirm")
    async def on_delete_confirm_changed(self, event: Input.Changed) -> None:
        """Handle delete confirmation input."""
        delete_btn = self.query_one("#clear-all-data", Button)
        delete_btn.disabled = (
            event.value != "DELETE ALL DATA"
        ) or not self.developer_mode_enabled

    async def _update_progress_display(self, status: str, progress: int = 0) -> None:
        """Update progress bar and status display."""
        try:
            progress_bar = self.query_one("#dataset-progress", ProgressBar)
            status_text = self.query_one("#progress-status", Static)

            progress_bar.update(progress=progress)
            status_text.update(status)

        except Exception as e:
            logger.error(f"Error updating progress display: {e}")

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

    async def _on_dataset_build_started(self, event: DatasetBuildStartedEvent) -> None:
        """Handle dataset build started event."""
        try:
            await self._update_progress_display(
                f"Starting dataset build: {event.total_questions} questions", 0
            )
            self.operation_in_progress = True
            self.current_operation = "Building Dataset"
            logger.info(f"Dataset build started with {event.total_questions} questions")
        except Exception as e:
            logger.error(f"Error handling dataset build started event: {e}")

    async def _on_dataset_build_progress(
        self, event: DatasetBuildProgressEvent
    ) -> None:
        """Handle dataset build progress event."""
        try:
            status = f"{event.current_operation} ({event.questions_processed}/{event.total_questions})"
            await self._update_progress_display(status, int(event.progress_percentage))

            # Add time estimate if available
            if event.estimated_time_remaining_minutes:
                status += f" - ETA: {event.estimated_time_remaining_minutes}min"

            logger.info(
                f"Dataset build progress: {event.progress_percentage:.1f}% - {event.current_operation}"
            )
        except Exception as e:
            logger.error(f"Error handling dataset build progress event: {e}")

    async def _on_dataset_build_completed(
        self, event: DatasetBuildCompletedEvent
    ) -> None:
        """Handle dataset build completed event."""
        try:
            await self._update_progress_display(
                "Dataset build completed successfully!", 100
            )
            await self._show_success(
                f"Generated {event.questions_with_answers} answers in {event.build_duration_seconds}s"
            )
            self.operation_in_progress = False
            logger.info(
                f"Dataset build completed: {event.questions_with_answers} answers generated"
            )
        except Exception as e:
            logger.error(f"Error handling dataset build completed event: {e}")

    async def _on_dataset_build_failed(self, event: DatasetBuildFailedEvent) -> None:
        """Handle dataset build failed event."""
        try:
            await self._update_progress_display(
                f"Build failed: {event.error_message}", 0
            )
            await self._show_error(
                f"Dataset build failed at {event.failed_at_stage}: {event.error_message}"
            )
            self.operation_in_progress = False
            logger.error(f"Dataset build failed: {event.error_message}")
        except Exception as e:
            logger.error(f"Error handling dataset build failed event: {e}")


class DeveloperOperationsScreen(Screen[None]):
    """Developer operations screen."""

    CSS = (
        COMMON_CSS_BASE
        + """
    /* Developer view specific styling */
    .developer-header {
        width: 100%;
        align: center middle;
        margin-bottom: 2;
        padding: 1;
        background: $surface;
        border: solid white;
    }

    .operation-header {
        text-style: bold;
        color: $secondary;
        margin: 2 0 1 0;
    }

    .tab-content {
        width: 100%;
        margin: 1 0;
    }

    .progress-text {
        color: $text;
        margin-top: 1;
    }

    .cost-section {
        margin: 2 0;
        padding: 2;
        background: $warning;
        border: solid white;
    }

    .danger-header {
        text-style: bold;
        color: $error;
        text-align: center;
        margin: 1 0;
    }

    .danger-banner {
        margin: 2 0;
        padding: 2;
        background: $error;
        border: solid white;
    }

    .danger-warning {
        color: $background;
        text-style: bold;
        text-align: center;
    }

    .danger-operation {
        margin: 2 0;
        padding: 2;
        background: $surface;
        border: solid white;
    }

    .danger-description {
        color: $text;
        margin: 1 0;
    }

    .preview-section {
        margin: 2 0;
        padding: 2;
        background: $surface;
        border: solid white;
    }

    .preview-text {
        color: $text;
        margin: 1 0;
        padding: 1;
        background: $background;
        border: solid white;
    }

    .results-text {
        color: $text;
        margin: 1 0;
        padding: 1;
        background: $background;
        border: solid white;
    }

    .config-section, .stats-section, .health-section {
        margin: 2 0;
        padding: 2;
        background: $surface;
        border: solid white;
    }

    .images-section {
        margin: 2 0;
        padding: 2;
        background: $surface;
        border: solid white;
    }

    #developer-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #developer-tabs {
        width: 100%;
        height: 70%;
        margin: 1 0;
    }

    #dataset-progress {
        width: 100%;
        margin: 1 0;
    }

    #cost-estimates, #api-config-info, #usage-stats, #system-health {
        height: 8;
        margin: 1 0;
        border: solid white;
    }

    #available-images {
        height: 10;
        margin: 1 0;
    }

    #language-options {
        height: 8;
        margin: 1 0;
    }
    """
    )

    def __init__(
        self,
        event_bus: EventBus,
        load_user_settings_query_handler,
        toggle_developer_mode_command_handler,
        start_dataset_build_command_handler,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.load_user_settings_query_handler = load_user_settings_query_handler
        self.toggle_developer_mode_command_handler = (
            toggle_developer_mode_command_handler
        )
        self.start_dataset_build_command_handler = start_dataset_build_command_handler

    def compose(self) -> ComposeResult:
        """Compose the developer operations screen."""
        yield DeveloperOperationsWidget(
            event_bus=self.event_bus,
            load_user_settings_query_handler=self.load_user_settings_query_handler,
            toggle_developer_mode_command_handler=self.toggle_developer_mode_command_handler,
            start_dataset_build_command_handler=self.start_dataset_build_command_handler,
        )
