"""Bookmark management screen and widgets for the Integran trainer."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ListItem, ListView, Static

from src.application.commands.bookmark_commands import (
    AddBookmarkCommand,
    RemoveBookmarkCommand,
    RemoveBookmarkCommandHandler,
)
from src.application.queries.bookmark_queries import (
    GetBookmarksQuery,
    GetBookmarksQueryHandler,
)
from src.domain.user.models.bookmark_models import Bookmark
from src.presentation.terminal.question_view import PracticeScreen

logger = logging.getLogger(__name__)


class BookmarkCommandHandler(Protocol):
    """Protocol for bookmark command handlers."""

    async def handle(self, command: AddBookmarkCommand | RemoveBookmarkCommand) -> Any:
        """Handle bookmark command."""
        ...


class BookmarkItem(ListItem):
    """Individual bookmark item widget."""

    def __init__(self, bookmark: Bookmark, **kwargs: Any) -> None:
        """Initialize bookmark item."""
        super().__init__(**kwargs)
        self.bookmark = bookmark

    def compose(self) -> ComposeResult:
        """Compose the bookmark item."""
        # Create display text with question ID and notes preview
        notes_preview = ""
        if self.bookmark.notes:
            notes_preview = (
                f" - {self.bookmark.notes[:50]}..."
                if len(self.bookmark.notes) > 50
                else f" - {self.bookmark.notes}"
            )

        display_text = f"Question {self.bookmark.question_id}{notes_preview}"

        yield Container(
            Static(display_text, classes="bookmark-text"),
            Horizontal(
                Button(
                    "Practice", id=f"practice-{self.bookmark.id}", variant="primary"
                ),
                Button("Remove", id=f"remove-{self.bookmark.id}", variant="error"),
                classes="bookmark-actions",
            ),
            classes="bookmark-item",
        )


class BookmarkScreen(Screen[None]):
    """Screen for managing bookmarks."""

    BINDINGS = [
        ("p", "practice_all", "Practice All"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
    ]

    bookmarks: reactive[list[Bookmark]] = reactive(list)
    is_loading: reactive[bool] = reactive(False)
    error_message: reactive[str] = reactive("")

    def __init__(
        self,
        bookmark_query_handler: GetBookmarksQueryHandler,
        bookmark_command_handler: RemoveBookmarkCommandHandler,
        user_id: int = 1,
        **kwargs: Any,
    ) -> None:
        """Initialize bookmark screen."""
        super().__init__(**kwargs)
        self.bookmark_query_handler = bookmark_query_handler
        self.bookmark_command_handler = bookmark_command_handler
        self.user_id = user_id

    def compose(self) -> ComposeResult:
        """Compose the bookmark screen."""
        yield Header(show_clock=True)
        yield Container(
            Static("📖 Your Bookmarked Questions", classes="text-title"),
            Static("Select questions to practice or manage", classes="text-subtitle"),
            Container(
                Static("Loading bookmarks...", id="loading-text", classes="text-muted"),
                classes="loading-container",
            ),
            Container(
                Static("No bookmarks found.", id="empty-text", classes="text-muted"),
                Static(
                    "Start bookmarking questions during practice to see them here.",
                    classes="text-help",
                ),
                classes="empty-container",
            ),
            Container(
                VerticalScroll(
                    ListView(id="bookmark-list", classes="bookmark-list"),
                    classes="bookmark-scroll",
                ),
                Horizontal(
                    Button(
                        "Practice All Bookmarks", id="practice-all", variant="success"
                    ),
                    Button("Refresh List", id="refresh", variant="default"),
                    Button("Back to Menu", id="back", variant="warning"),
                    classes="bookmark-buttons",
                ),
                classes="bookmark-container",
            ),
            Container(
                Static("", id="error-text", classes="text-error"),
                classes="error-container",
            ),
            classes="main-container",
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Load bookmarks when screen is mounted."""
        await self.load_bookmarks()

    async def load_bookmarks(self) -> None:
        """Load user's bookmarks."""
        try:
            self.is_loading = True
            self.error_message = ""

            # Show loading state
            loading_container = self.query_one(".loading-container")
            bookmark_container = self.query_one(".bookmark-container")
            empty_container = self.query_one(".empty-container")
            error_container = self.query_one(".error-container")

            loading_container.display = True
            bookmark_container.display = False
            empty_container.display = False
            error_container.display = False

            # Query bookmarks
            query = GetBookmarksQuery(user_id=self.user_id)
            result = await self.bookmark_query_handler.handle(query)

            if result.success and result.bookmarks:
                self.bookmarks = result.bookmarks.bookmarks

                if self.bookmarks:
                    # Show bookmark list
                    await self.populate_bookmark_list()
                    bookmark_container.display = True
                else:
                    # Show empty state
                    empty_container.display = True

                loading_container.display = False
            else:
                # Show error
                self.error_message = result.error_message or "Failed to load bookmarks"
                error_text = self.query_one("#error-text", Static)
                error_text.update(self.error_message)
                error_container.display = True
                loading_container.display = False

        except Exception as e:
            logger.exception("Error loading bookmarks")
            self.error_message = f"Error loading bookmarks: {str(e)}"
            error_text = self.query_one("#error-text", Static)
            error_text.update(self.error_message)
            self.query_one(".error-container").display = True
            self.query_one(".loading-container").display = False
        finally:
            self.is_loading = False

    async def populate_bookmark_list(self) -> None:
        """Populate the bookmark list with items."""
        bookmark_list = self.query_one("#bookmark-list", ListView)
        bookmark_list.clear()

        for bookmark in self.bookmarks:
            bookmark_item = BookmarkItem(bookmark)
            bookmark_list.append(bookmark_item)

    @on(Button.Pressed, "#practice-all")
    def action_practice_all(self) -> None:
        """Practice all bookmarked questions."""
        if not self.bookmarks:
            self.app.bell()
            return

        # Start practice session with bookmarked questions
        practice_screen = PracticeScreen(
            practice_mode="bookmarks",
            user_repository=getattr(self.app, "user_repository", None),
            submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
            if hasattr(self.app, "container")
            else None,
            start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_command_handler=self.app.container.get_bookmark_command_handler()
            if hasattr(self.app, "container")
            else None,
            bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
            if hasattr(self.app, "container")
            else None,
        )
        self.app.push_screen(practice_screen)

    @on(Button.Pressed, "#refresh")
    def action_refresh(self) -> None:
        """Refresh the bookmark list."""
        self.call_after_refresh(self.load_bookmarks)

    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses from bookmark items."""
        button_id = event.button.id or ""

        if button_id.startswith("practice-"):
            # Extract bookmark ID and start practice with single question
            bookmark_id = int(button_id.replace("practice-", ""))
            bookmark = next((b for b in self.bookmarks if b.id == bookmark_id), None)
            if bookmark:
                await self.practice_single_bookmark(bookmark)

        elif button_id.startswith("remove-"):
            # Extract bookmark ID and remove bookmark
            bookmark_id = int(button_id.replace("remove-", ""))
            await self.remove_bookmark(bookmark_id)

    async def practice_single_bookmark(self, _bookmark: Bookmark) -> None:
        """Practice a single bookmarked question."""
        try:
            # Create a practice session for single question
            # This would require extending PracticeScreen to accept specific questions
            # For now, we'll start a general practice session
            practice_screen = PracticeScreen(
                practice_mode="random",  # Could be extended to support specific questions
                user_repository=getattr(self.app, "user_repository", None),
                submit_answer_command_handler=self.app.container.get_submit_answer_command_handler()
                if hasattr(self.app, "container")
                else None,
                start_practice_command_handler=self.app.container.get_start_practice_session_command_handler()
                if hasattr(self.app, "container")
                else None,
                bookmark_command_handler=self.app.container.get_bookmark_command_handler()
                if hasattr(self.app, "container")
                else None,
                bookmark_status_handler=self.app.container.get_bookmark_status_query_handler()
                if hasattr(self.app, "container")
                else None,
            )
            self.app.push_screen(practice_screen)

        except Exception as e:
            logger.exception("Error starting practice for bookmark")
            self.error_message = f"Error starting practice: {str(e)}"
            error_text = self.query_one("#error-text", Static)
            error_text.update(self.error_message)
            self.query_one(".error-container").display = True

    async def remove_bookmark(self, bookmark_id: int) -> None:
        """Remove a bookmark."""
        try:
            # Find the bookmark
            bookmark = next((b for b in self.bookmarks if b.id == bookmark_id), None)
            if not bookmark:
                return

            # Remove bookmark
            command = RemoveBookmarkCommand(
                user_id=self.user_id, question_id=bookmark.question_id
            )
            result = await self.bookmark_command_handler.handle(command)

            if result.success:
                # Refresh the list
                await self.load_bookmarks()
            else:
                self.error_message = result.error_message or "Failed to remove bookmark"
                error_text = self.query_one("#error-text", Static)
                error_text.update(self.error_message)
                self.query_one(".error-container").display = True

        except Exception as e:
            logger.exception("Error removing bookmark")
            self.error_message = f"Error removing bookmark: {str(e)}"
            error_text = self.query_one("#error-text", Static)
            error_text.update(self.error_message)
            self.query_one(".error-container").display = True


class BookmarkButton(Static):
    """Reusable bookmark toggle button widget."""

    class BookmarkToggled(Message):
        """Message sent when bookmark is toggled."""

        def __init__(self, question_id: int, is_bookmarked: bool) -> None:
            """Initialize bookmark toggled message."""
            super().__init__()
            self.question_id = question_id
            self.is_bookmarked = is_bookmarked

    is_bookmarked: reactive[bool] = reactive(False)
    is_loading: reactive[bool] = reactive(False)

    def __init__(
        self,
        question_id: int,
        bookmark_command_handler: BookmarkCommandHandler,
        user_id: int = 1,
        **kwargs: Any,
    ) -> None:
        """Initialize bookmark button."""
        super().__init__(**kwargs)
        self.question_id = question_id
        self.bookmark_command_handler = bookmark_command_handler
        self.user_id = user_id

    def compose(self) -> ComposeResult:
        """Compose the bookmark button."""
        yield Button(
            "📖" if self.is_bookmarked else "📖",
            id="bookmark-toggle",
            variant="warning" if self.is_bookmarked else "default",
            disabled=self.is_loading,
        )

    def watch_is_bookmarked(self, is_bookmarked: bool) -> None:
        """Update button appearance when bookmark status changes."""
        button = self.query_one("#bookmark-toggle", Button)
        button.label = "📖" if is_bookmarked else "📖"
        button.variant = "warning" if is_bookmarked else "default"

    def watch_is_loading(self, is_loading: bool) -> None:
        """Update button state when loading."""
        button = self.query_one("#bookmark-toggle", Button)
        button.disabled = is_loading
        if is_loading:
            button.label = "⏳"

    @on(Button.Pressed, "#bookmark-toggle")
    async def toggle_bookmark(self) -> None:
        """Toggle bookmark status."""
        try:
            self.is_loading = True

            if self.is_bookmarked:
                # Remove bookmark
                remove_command = RemoveBookmarkCommand(
                    user_id=self.user_id, question_id=self.question_id
                )
                result = await self.bookmark_command_handler.handle(remove_command)
                if result.success:
                    self.is_bookmarked = False
                    self.post_message(
                        self.BookmarkToggled(self.question_id, self.is_bookmarked)
                    )
            else:
                # Add bookmark
                add_command = AddBookmarkCommand(
                    user_id=self.user_id, question_id=self.question_id
                )
                result = await self.bookmark_command_handler.handle(add_command)
                if result.success:
                    self.is_bookmarked = True
                    self.post_message(
                        self.BookmarkToggled(self.question_id, self.is_bookmarked)
                    )

        except Exception:
            logger.exception("Error toggling bookmark")
        finally:
            self.is_loading = False
