"""Tests for bookmark integration with practice modes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.queries.bookmark_queries import (
    GetBookmarksQuery,
    GetBookmarksQueryHandler,
    GetBookmarksQueryResult,
)
from src.domain.content.models.question_models import Question
from src.domain.user.models.bookmark_models import Bookmark, BookmarkCollection


class MockBookmarkPracticeScreen:
    """Mock bookmark practice screen for testing."""

    def __init__(self, bookmark_query_handler, practice_mode="bookmarks"):
        """Initialize mock bookmark practice screen."""
        self.bookmark_query_handler = bookmark_query_handler
        self.practice_mode = practice_mode
        self.current_question_index = 0
        self.questions = []
        self.bookmark_questions = []
        self.session_id = None
        self.user_id = 1
        self.total_questions = 0
        self.completed_questions = 0
        self.is_practice_complete = False

    async def load_bookmark_questions(self) -> bool:
        """Load questions from bookmarks."""
        try:
            query = GetBookmarksQuery(user_id=self.user_id, limit=None)
            result = await self.bookmark_query_handler.handle(query)

            if result.success and not result.bookmarks.is_empty:
                self.bookmark_questions = result.bookmarks.bookmarks
                self.questions = self._convert_bookmarks_to_questions(
                    self.bookmark_questions
                )
                self.total_questions = len(self.questions)
                return True
            else:
                self.questions = []
                self.total_questions = 0
                return False

        except Exception:
            self.questions = []
            self.total_questions = 0
            return False

    def _convert_bookmarks_to_questions(
        self, bookmarks: list[Bookmark]
    ) -> list[Question]:
        """Convert bookmarks to questions for practice."""
        questions = []
        for bookmark in bookmarks:
            # Mock question creation from bookmark
            question = Question(
                id=bookmark.question_id,
                question=f"Question {bookmark.question_id}",
                options='["A", "B", "C", "D"]',
                correct="A",
                category="Test",
                difficulty="medium",
                question_type="general",
                is_image_question=False,
                page_number=1,
            )
            questions.append(question)
        return questions

    def get_current_question(self) -> Question | None:
        """Get current question."""
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def move_to_next_question(self) -> bool:
        """Move to next question."""
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            return True
        else:
            self.is_practice_complete = True
            return False

    def get_progress_percentage(self) -> float:
        """Get practice progress percentage."""
        if self.total_questions == 0:
            return 0.0
        return (self.completed_questions / self.total_questions) * 100

    def submit_answer(self, answer: str) -> bool:
        """Submit answer for current question."""
        current_question = self.get_current_question()
        if current_question:
            self.completed_questions += 1
            return current_question.correct == answer
        return False


class MockBookmarkQuestionWidget:
    """Mock bookmark question widget for testing."""

    def __init__(self, question: Question, bookmark_info: Bookmark = None):
        """Initialize mock bookmark question widget."""
        self.question = question
        self.bookmark_info = bookmark_info
        self.show_bookmark_notes = False
        self.bookmark_notes_visible = False

    def toggle_bookmark_notes(self) -> None:
        """Toggle bookmark notes visibility."""
        self.bookmark_notes_visible = not self.bookmark_notes_visible

    def get_bookmark_notes(self) -> str | None:
        """Get bookmark notes."""
        return self.bookmark_info.notes if self.bookmark_info else None

    def has_bookmark_notes(self) -> bool:
        """Check if bookmark has notes."""
        if self.bookmark_info is None:
            return False
        return self.bookmark_info.notes is not None


class TestBookmarkPracticeIntegration:
    """Test bookmark practice integration."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock(spec=GetBookmarksQueryHandler)

    @pytest.fixture
    def sample_bookmarks(self):
        """Create sample bookmarks for practice."""
        return [
            Bookmark(
                id=1,
                user_id=1,
                question_id=101,
                notes="Constitutional law - important for exam",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=1,
                question_id=102,
                notes="German history - remember the dates",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=3,
                user_id=1,
                question_id=103,
                notes=None,  # No notes
                created_at=datetime.now(UTC),
            ),
        ]

    @pytest.fixture
    def bookmark_collection(self, sample_bookmarks):
        """Create bookmark collection."""
        return BookmarkCollection(user_id=1, bookmarks=sample_bookmarks, total_count=3)

    @pytest.fixture
    def bookmark_practice_screen(self, mock_bookmark_query_handler):
        """Create bookmark practice screen."""
        return MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )

    @pytest.mark.asyncio
    async def test_bookmark_practice_screen_load_questions_success(
        self, bookmark_practice_screen, mock_bookmark_query_handler, bookmark_collection
    ):
        """Test successful loading of bookmark questions."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(bookmark_collection)
        )

        # Act
        result = await bookmark_practice_screen.load_bookmark_questions()

        # Assert
        assert result is True
        assert len(bookmark_practice_screen.questions) == 3
        assert bookmark_practice_screen.total_questions == 3
        assert bookmark_practice_screen.questions[0].id == 101
        assert bookmark_practice_screen.questions[1].id == 102
        assert bookmark_practice_screen.questions[2].id == 103

    @pytest.mark.asyncio
    async def test_bookmark_practice_screen_load_questions_empty(
        self, bookmark_practice_screen, mock_bookmark_query_handler
    ):
        """Test loading bookmark questions when no bookmarks exist."""
        # Arrange
        empty_collection = BookmarkCollection(user_id=1, bookmarks=[], total_count=0)
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(empty_collection)
        )

        # Act
        result = await bookmark_practice_screen.load_bookmark_questions()

        # Assert
        assert result is False
        assert len(bookmark_practice_screen.questions) == 0
        assert bookmark_practice_screen.total_questions == 0

    @pytest.mark.asyncio
    async def test_bookmark_practice_screen_load_questions_error(
        self, bookmark_practice_screen, mock_bookmark_query_handler
    ):
        """Test loading bookmark questions with error."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.error_result("Database error")
        )

        # Act
        result = await bookmark_practice_screen.load_bookmark_questions()

        # Assert
        assert result is False
        assert len(bookmark_practice_screen.questions) == 0
        assert bookmark_practice_screen.total_questions == 0

    @pytest.mark.asyncio
    async def test_bookmark_practice_screen_question_navigation(
        self, bookmark_practice_screen, mock_bookmark_query_handler, bookmark_collection
    ):
        """Test question navigation in bookmark practice."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(bookmark_collection)
        )
        await bookmark_practice_screen.load_bookmark_questions()

        # Act & Assert
        # Initially at first question
        assert bookmark_practice_screen.current_question_index == 0
        current_question = bookmark_practice_screen.get_current_question()
        assert current_question is not None
        assert current_question.id == 101

        # Move to next question
        can_move = bookmark_practice_screen.move_to_next_question()
        assert can_move is True
        assert bookmark_practice_screen.current_question_index == 1
        current_question = bookmark_practice_screen.get_current_question()
        assert current_question.id == 102

        # Move to last question
        can_move = bookmark_practice_screen.move_to_next_question()
        assert can_move is True
        assert bookmark_practice_screen.current_question_index == 2
        current_question = bookmark_practice_screen.get_current_question()
        assert current_question.id == 103

        # Try to move beyond last question
        can_move = bookmark_practice_screen.move_to_next_question()
        assert can_move is False
        assert bookmark_practice_screen.is_practice_complete is True

    @pytest.mark.asyncio
    async def test_bookmark_practice_screen_progress_tracking(
        self, bookmark_practice_screen, mock_bookmark_query_handler, bookmark_collection
    ):
        """Test progress tracking in bookmark practice."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(bookmark_collection)
        )
        await bookmark_practice_screen.load_bookmark_questions()

        # Act & Assert
        # Initially no progress
        assert bookmark_practice_screen.get_progress_percentage() == 0.0

        # Answer first question
        bookmark_practice_screen.submit_answer("A")
        assert bookmark_practice_screen.get_progress_percentage() == 33.33333333333333

        # Answer second question
        bookmark_practice_screen.submit_answer("B")
        assert bookmark_practice_screen.get_progress_percentage() == 66.66666666666666

        # Answer third question
        bookmark_practice_screen.submit_answer("C")
        assert bookmark_practice_screen.get_progress_percentage() == 100.0

    def test_bookmark_practice_screen_empty_state(self, bookmark_practice_screen):
        """Test bookmark practice screen with empty state."""
        # Without loading questions
        assert bookmark_practice_screen.total_questions == 0
        assert bookmark_practice_screen.get_current_question() is None
        assert bookmark_practice_screen.get_progress_percentage() == 0.0
        # move_to_next_question returns False and sets is_practice_complete to True when no questions
        assert bookmark_practice_screen.move_to_next_question() is False
        assert bookmark_practice_screen.is_practice_complete is True

    def test_bookmark_practice_screen_submit_answer_without_question(
        self, bookmark_practice_screen
    ):
        """Test submitting answer without current question."""
        # Without loading questions
        result = bookmark_practice_screen.submit_answer("A")
        assert result is False
        assert bookmark_practice_screen.completed_questions == 0


class TestBookmarkQuestionWidget:
    """Test bookmark question widget functionality."""

    @pytest.fixture
    def sample_question(self):
        """Create sample question."""
        return Question(
            id=101,
            question="What is the capital of Germany?",
            options='["Berlin", "Munich", "Hamburg", "Frankfurt"]',
            correct="Berlin",
            category="Geography",
            difficulty="medium",
            question_type="general",
            is_image_question=False,
            page_number=1,
        )

    @pytest.fixture
    def sample_bookmark_with_notes(self):
        """Create sample bookmark with notes."""
        return Bookmark(
            id=1,
            user_id=1,
            question_id=101,
            notes="Capital city - very important for the exam",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_bookmark_without_notes(self):
        """Create sample bookmark without notes."""
        return Bookmark(
            id=2, user_id=1, question_id=101, notes=None, created_at=datetime.now(UTC)
        )

    def test_bookmark_question_widget_with_notes(
        self, sample_question, sample_bookmark_with_notes
    ):
        """Test bookmark question widget with notes."""
        # Arrange
        widget = MockBookmarkQuestionWidget(
            question=sample_question, bookmark_info=sample_bookmark_with_notes
        )

        # Act & Assert
        assert widget.question == sample_question
        assert widget.bookmark_info == sample_bookmark_with_notes
        assert widget.has_bookmark_notes() is True
        assert (
            widget.get_bookmark_notes() == "Capital city - very important for the exam"
        )
        assert widget.bookmark_notes_visible is False

        # Toggle notes visibility
        widget.toggle_bookmark_notes()
        assert widget.bookmark_notes_visible is True

        widget.toggle_bookmark_notes()
        assert widget.bookmark_notes_visible is False

    def test_bookmark_question_widget_without_notes(
        self, sample_question, sample_bookmark_without_notes
    ):
        """Test bookmark question widget without notes."""
        # Arrange
        widget = MockBookmarkQuestionWidget(
            question=sample_question, bookmark_info=sample_bookmark_without_notes
        )

        # Act & Assert
        assert widget.question == sample_question
        assert widget.bookmark_info == sample_bookmark_without_notes
        assert widget.has_bookmark_notes() is False
        assert widget.get_bookmark_notes() is None
        assert widget.bookmark_notes_visible is False

        # Toggle notes visibility (should work even without notes)
        widget.toggle_bookmark_notes()
        assert widget.bookmark_notes_visible is True

    def test_bookmark_question_widget_without_bookmark_info(self, sample_question):
        """Test bookmark question widget without bookmark info."""
        # Arrange
        widget = MockBookmarkQuestionWidget(
            question=sample_question, bookmark_info=None
        )

        # Act & Assert
        assert widget.question == sample_question
        assert widget.bookmark_info is None
        assert widget.has_bookmark_notes() is False
        assert widget.get_bookmark_notes() is None
        assert widget.bookmark_notes_visible is False

        # Toggle notes visibility (should work even without bookmark info)
        widget.toggle_bookmark_notes()
        assert widget.bookmark_notes_visible is True


class TestBookmarkPracticePerformance:
    """Test bookmark practice performance scenarios."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock(spec=GetBookmarksQueryHandler)

    @pytest.fixture
    def large_bookmark_collection(self):
        """Create large bookmark collection for performance testing."""
        bookmarks = [
            Bookmark(
                id=i,
                user_id=1,
                question_id=i,
                notes=f"Bookmark {i} notes",
                created_at=datetime.now(UTC),
            )
            for i in range(1, 1001)  # 1000 bookmarks
        ]
        return BookmarkCollection(user_id=1, bookmarks=bookmarks, total_count=1000)

    @pytest.mark.asyncio
    async def test_bookmark_practice_performance_large_dataset(
        self, mock_bookmark_query_handler, large_bookmark_collection
    ):
        """Test bookmark practice performance with large dataset."""
        # Arrange
        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(large_bookmark_collection)
        )

        # Act
        import time

        start_time = time.time()
        result = await practice_screen.load_bookmark_questions()
        end_time = time.time()

        # Assert
        assert result is True
        assert len(practice_screen.questions) == 1000
        assert practice_screen.total_questions == 1000

        # Should load efficiently
        loading_time = end_time - start_time
        assert loading_time < 2.0  # Should load in under 2 seconds

    @pytest.mark.asyncio
    async def test_bookmark_practice_memory_usage(
        self, mock_bookmark_query_handler, large_bookmark_collection
    ):
        """Test bookmark practice memory usage."""
        # Arrange
        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(large_bookmark_collection)
        )

        # Act
        await practice_screen.load_bookmark_questions()

        # Test navigation through all questions
        questions_navigated = 0
        while not practice_screen.is_practice_complete:
            current_question = practice_screen.get_current_question()
            if current_question:
                questions_navigated += 1
                practice_screen.submit_answer("A")

            if not practice_screen.move_to_next_question():
                break

        # Assert
        assert questions_navigated == 1000
        assert practice_screen.completed_questions == 1000
        assert practice_screen.is_practice_complete is True

    @pytest.mark.asyncio
    async def test_bookmark_practice_concurrent_loading(
        self, mock_bookmark_query_handler, large_bookmark_collection
    ):
        """Test concurrent bookmark practice loading."""
        # Arrange
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(large_bookmark_collection)
        )

        # Create multiple practice screens
        screens = [
            MockBookmarkPracticeScreen(
                bookmark_query_handler=mock_bookmark_query_handler
            )
            for _ in range(5)
        ]

        # Act
        import asyncio

        tasks = [screen.load_bookmark_questions() for screen in screens]
        results = await asyncio.gather(*tasks)

        # Assert
        assert all(results)
        assert all(len(screen.questions) == 1000 for screen in screens)
        assert mock_bookmark_query_handler.handle.call_count == 5


class TestBookmarkPracticeEdgeCases:
    """Test bookmark practice edge cases."""

    @pytest.fixture
    def mock_bookmark_query_handler(self):
        """Mock bookmark query handler."""
        return AsyncMock(spec=GetBookmarksQueryHandler)

    @pytest.mark.asyncio
    async def test_bookmark_practice_single_bookmark(self, mock_bookmark_query_handler):
        """Test bookmark practice with single bookmark."""
        # Arrange
        single_bookmark = [
            Bookmark(
                id=1,
                user_id=1,
                question_id=101,
                notes="Only bookmark",
                created_at=datetime.now(UTC),
            )
        ]
        collection = BookmarkCollection(
            user_id=1, bookmarks=single_bookmark, total_count=1
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(collection)
        )

        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )

        # Act
        result = await practice_screen.load_bookmark_questions()

        # Assert
        assert result is True
        assert len(practice_screen.questions) == 1
        assert practice_screen.total_questions == 1

        # Test navigation
        current_question = practice_screen.get_current_question()
        assert current_question is not None
        assert current_question.id == 101

        # Cannot move to next question
        can_move = practice_screen.move_to_next_question()
        assert can_move is False
        assert practice_screen.is_practice_complete is True

    @pytest.mark.asyncio
    async def test_bookmark_practice_duplicate_question_ids(
        self, mock_bookmark_query_handler
    ):
        """Test bookmark practice with duplicate question IDs."""
        # Arrange
        duplicate_bookmarks = [
            Bookmark(
                id=1,
                user_id=1,
                question_id=101,
                notes="First bookmark",
                created_at=datetime.now(UTC),
            ),
            Bookmark(
                id=2,
                user_id=1,
                question_id=101,  # Same question ID
                notes="Second bookmark",
                created_at=datetime.now(UTC),
            ),
        ]
        collection = BookmarkCollection(
            user_id=1, bookmarks=duplicate_bookmarks, total_count=2
        )
        mock_bookmark_query_handler.handle.return_value = (
            GetBookmarksQueryResult.success_result(collection)
        )

        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )

        # Act
        result = await practice_screen.load_bookmark_questions()

        # Assert
        assert result is True
        assert len(practice_screen.questions) == 2  # Both bookmarks create questions
        assert practice_screen.total_questions == 2

        # Both questions should have the same ID
        assert practice_screen.questions[0].id == 101
        assert practice_screen.questions[1].id == 101

    @pytest.mark.asyncio
    async def test_bookmark_practice_network_interruption(
        self, mock_bookmark_query_handler
    ):
        """Test bookmark practice with network interruption."""
        # Arrange
        mock_bookmark_query_handler.handle.side_effect = TimeoutError("Network timeout")

        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )

        # Act
        result = await practice_screen.load_bookmark_questions()

        # Assert
        assert result is False
        assert len(practice_screen.questions) == 0
        assert practice_screen.total_questions == 0

    @pytest.mark.asyncio
    async def test_bookmark_practice_recovery_after_error(
        self, mock_bookmark_query_handler
    ):
        """Test bookmark practice recovery after error."""
        # Arrange
        practice_screen = MockBookmarkPracticeScreen(
            bookmark_query_handler=mock_bookmark_query_handler
        )

        # First call fails
        mock_bookmark_query_handler.handle.side_effect = [
            GetBookmarksQueryResult.error_result("Database error"),
            GetBookmarksQueryResult.success_result(
                BookmarkCollection(
                    user_id=1,
                    bookmarks=[
                        Bookmark(
                            id=1,
                            user_id=1,
                            question_id=101,
                            notes="Recovered bookmark",
                            created_at=datetime.now(UTC),
                        )
                    ],
                    total_count=1,
                )
            ),
        ]

        # Act
        # First attempt fails
        result1 = await practice_screen.load_bookmark_questions()
        assert result1 is False
        assert len(practice_screen.questions) == 0

        # Second attempt succeeds
        result2 = await practice_screen.load_bookmark_questions()
        assert result2 is True
        assert len(practice_screen.questions) == 1
        assert practice_screen.questions[0].id == 101
