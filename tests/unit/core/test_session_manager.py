"""Tests for session manager functionality."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.core.database import DatabaseManager
from src.core.learning.domain.services.schedule_card import ScheduleCard
from src.core.models import FSRSCard, FSRSRating, Question
from src.core.session_manager import (
    QuestionPresentation,
    SessionConfig,
    SessionManager,
    SessionProgress,
    SessionType,
)


class TestSessionManager:
    """Test session manager functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def mock_schedule_card_service(self):
        """Create mock ScheduleCard domain service."""
        return Mock(spec=ScheduleCard)

    @pytest.fixture
    def session_manager(self, mock_db_manager, mock_schedule_card_service):
        """Create session manager with mock dependencies."""
        return SessionManager(mock_db_manager, mock_schedule_card_service)

    @pytest.fixture
    def sample_config(self):
        """Create sample session configuration."""
        return SessionConfig(
            session_type=SessionType.REVIEW,
            max_reviews=20,
            max_new_cards=10,
            target_retention=0.9,
            categories=["Politik", "Geschichte"],
        )

    @pytest.fixture
    def sample_question(self):
        """Create sample question."""
        return Question(
            id=100,
            question="Sample question?",
            options='["A", "B", "C", "D"]',
            correct="A",
            category="Politik",
            difficulty="medium",
        )

    @pytest.fixture
    def sample_card(self):
        """Create sample FSRS card."""
        return FSRSCard(
            card_id=1,
            question_id=100,
            user_id=1,
            difficulty=5.0,
            stability=2.0,
            retrievability=0.9,
            state=2,
            review_count=3,
            lapse_count=0,
            last_review_date=datetime.now(UTC).timestamp() - 86400,
            next_review_date=datetime.now(UTC).timestamp(),
            created_at=datetime.now(UTC).timestamp(),
            updated_at=datetime.now(UTC).timestamp(),
        )

    def test_start_session_creates_learning_session(
        self, session_manager, mock_db_manager, sample_config
    ):
        """Test that starting a session creates a learning session in database."""
        mock_db_manager.create_learning_session.return_value = 1

        with patch.object(session_manager, "_get_session_questions", return_value=[]):
            session_id, questions = session_manager.start_session(sample_config)

        assert session_id == 1
        mock_db_manager.create_learning_session.assert_called_once_with(
            session_type="review",
            user_id=1,
            target_retention=0.9,
            max_reviews=20,
        )

    def test_start_session_tracks_progress(
        self, session_manager, mock_db_manager, sample_config
    ):
        """Test that starting a session creates progress tracking."""
        mock_db_manager.create_learning_session.return_value = 1
        mock_questions = [Mock(), Mock()]

        with patch.object(
            session_manager, "_get_session_questions", return_value=mock_questions
        ):
            session_id, questions = session_manager.start_session(sample_config)

        # Check that session is tracked
        assert session_id in session_manager._active_sessions
        progress = session_manager._active_sessions[session_id]
        assert isinstance(progress, SessionProgress)
        assert progress.questions_total == 2
        assert progress.questions_completed == 0

    @pytest.mark.asyncio
    async def test_submit_answer_correct(
        self,
        session_manager,
        mock_db_manager,
        mock_schedule_card_service,
        sample_card,
        sample_question,
    ):
        """Test submitting a correct answer."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=0,
            questions_correct=0,
            questions_incorrect=0,
            questions_skipped=0,
            average_response_time_ms=0,
            current_retention_rate=0.0,
            estimated_time_remaining_minutes=10,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=0,
        )

        # Setup mocks
        mock_db_manager.get_fsrs_card_by_id.return_value = sample_card
        mock_db_manager.get_question.return_value = sample_question

        from src.core.learning.domain.services.schedule_card import ScheduleCardResult
        from src.core.models import FSRSState

        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=1,
            question_id=100,
            difficulty_before=5.0,
            stability_before=2.0,
            retrievability_before=0.9,
            state_before=FSRSState.REVIEW,
            difficulty_after=4.8,
            stability_after=2.5,
            retrievability_after=0.85,
            state_after=FSRSState.REVIEW,
            next_review_date=datetime.now(UTC),
            next_interval_days=3.0,
        )
        mock_schedule_card_service.call.return_value = mock_schedule_result

        # Submit answer
        result = await session_manager.submit_answer(
            session_id=1,
            card_id=1,
            user_answer="A",  # Correct answer
            response_time_ms=3000,
        )

        # Verify
        assert result == mock_schedule_result
        assert mock_schedule_card_service.call.call_count == 1

        # Verify the request was created correctly
        call_args = mock_schedule_card_service.call.call_args[0][0]
        assert call_args.card_id == 1
        assert (
            call_args.rating == FSRSRating.GOOD
        )  # Good rating for correct answer in reasonable time
        assert call_args.response_time_ms == 3000
        assert call_args.session_id == 1

        # Check progress update
        progress = session_manager._active_sessions[1]
        assert progress.questions_completed == 1
        assert progress.questions_correct == 1

    @pytest.mark.asyncio
    async def test_submit_answer_incorrect(
        self,
        session_manager,
        mock_db_manager,
        mock_schedule_card_service,
        sample_card,
        sample_question,
    ):
        """Test submitting an incorrect answer."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=0,
            questions_correct=0,
            questions_incorrect=0,
            questions_skipped=0,
            average_response_time_ms=0,
            current_retention_rate=0.0,
            estimated_time_remaining_minutes=10,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=0,
        )

        # Setup mocks
        mock_db_manager.get_fsrs_card_by_id.return_value = sample_card
        mock_db_manager.get_question.return_value = sample_question

        from src.core.learning.domain.services.schedule_card import ScheduleCardResult
        from src.core.models import FSRSState

        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=1,
            question_id=100,
            difficulty_before=5.0,
            stability_before=2.0,
            retrievability_before=0.9,
            state_before=FSRSState.REVIEW,
            difficulty_after=5.2,
            stability_after=1.5,
            retrievability_after=0.75,
            state_after=FSRSState.REVIEW,
            next_review_date=datetime.now(UTC),
            next_interval_days=1.0,
        )
        mock_schedule_card_service.call.return_value = mock_schedule_result

        # Submit wrong answer
        await session_manager.submit_answer(
            session_id=1,
            card_id=1,
            user_answer="B",  # Wrong answer
            response_time_ms=5000,
        )

        # Verify rating is AGAIN for wrong answer
        call_args = mock_schedule_card_service.call.call_args[0][0]
        assert call_args.card_id == 1
        assert call_args.rating == FSRSRating.AGAIN
        assert call_args.response_time_ms == 5000
        assert call_args.session_id == 1

        # Check progress update
        progress = session_manager._active_sessions[1]
        assert progress.questions_completed == 1
        assert progress.questions_incorrect == 1

    @pytest.mark.asyncio
    async def test_submit_answer_skipped(
        self,
        session_manager,
        mock_db_manager,
        mock_schedule_card_service,
        sample_card,
        sample_question,
    ):
        """Test submitting a skipped answer."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=0,
            questions_correct=0,
            questions_incorrect=0,
            questions_skipped=0,
            average_response_time_ms=0,
            current_retention_rate=0.0,
            estimated_time_remaining_minutes=10,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=0,
        )

        # Setup mocks
        mock_db_manager.get_fsrs_card_by_id.return_value = sample_card
        mock_db_manager.get_question.return_value = sample_question

        from src.core.learning.domain.services.schedule_card import ScheduleCardResult
        from src.core.models import FSRSState

        mock_schedule_result = ScheduleCardResult(
            success=True,
            card_id=1,
            question_id=100,
            difficulty_before=5.0,
            stability_before=2.0,
            retrievability_before=0.9,
            state_before=FSRSState.REVIEW,
            difficulty_after=5.5,
            stability_after=1.0,
            retrievability_after=0.7,
            state_after=FSRSState.REVIEW,
            next_review_date=datetime.now(UTC),
            next_interval_days=1.0,
        )
        mock_schedule_card_service.call.return_value = mock_schedule_result

        # Submit skipped answer
        await session_manager.submit_answer(
            session_id=1,
            card_id=1,
            user_answer=None,  # Skipped
            response_time_ms=1000,
        )

        # Verify rating is AGAIN for skipped
        call_args = mock_schedule_card_service.call.call_args[0][0]
        assert call_args.card_id == 1
        assert call_args.rating == FSRSRating.AGAIN
        assert call_args.response_time_ms == 1000
        assert call_args.session_id == 1

        # Check progress update
        progress = session_manager._active_sessions[1]
        assert progress.questions_completed == 1
        assert progress.questions_skipped == 1

    @pytest.mark.asyncio
    async def test_submit_answer_session_not_found(self, session_manager):
        """Test submitting answer for non-existent session."""
        with pytest.raises(ValueError, match="Session 999 not found"):
            await session_manager.submit_answer(
                session_id=999,
                card_id=1,
                user_answer="A",
                response_time_ms=3000,
            )

    @pytest.mark.asyncio
    async def test_submit_answer_card_not_found(self, session_manager, mock_db_manager):
        """Test submitting answer for non-existent card."""
        # Setup session
        session_manager._active_sessions[1] = Mock()
        mock_db_manager.get_fsrs_card_by_id.return_value = None

        with pytest.raises(ValueError, match="Card 1 not found"):
            await session_manager.submit_answer(
                session_id=1,
                card_id=1,
                user_answer="A",
                response_time_ms=3000,
            )

    def test_get_session_progress(self, session_manager):
        """Test getting session progress."""
        start_time = datetime.now(UTC)
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=10,
            questions_completed=3,
            questions_correct=2,
            questions_incorrect=1,
            questions_skipped=0,
            average_response_time_ms=4000,
            current_retention_rate=0.67,
            estimated_time_remaining_minutes=5,
            session_start_time=start_time,
            elapsed_time_minutes=0,
        )

        progress = session_manager.get_session_progress(1)

        assert progress.session_id == 1
        assert progress.questions_total == 10
        assert progress.questions_completed == 3
        assert progress.questions_correct == 2

    def test_get_session_progress_not_found(self, session_manager):
        """Test getting progress for non-existent session."""
        with pytest.raises(ValueError, match="Session 999 not found"):
            session_manager.get_session_progress(999)

    def test_end_session(self, session_manager, mock_db_manager):
        """Test ending a session."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=10,
            questions_completed=8,
            questions_correct=6,
            questions_incorrect=2,
            questions_skipped=0,
            average_response_time_ms=3500,
            current_retention_rate=0.75,
            estimated_time_remaining_minutes=2,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=15,
        )

        summary = session_manager.end_session(1)

        # Verify database call
        mock_db_manager.end_learning_session.assert_called_once_with(1)

        # Verify summary
        assert summary["session_id"] == 1
        assert summary["questions_completed"] == 8
        assert summary["accuracy_percentage"] == 75.0
        assert summary["correct_answers"] == 6
        assert summary["completion_rate"] == 80.0

        # Session should be removed
        assert 1 not in session_manager._active_sessions

    def test_end_session_not_found(self, session_manager):
        """Test ending non-existent session."""
        with pytest.raises(ValueError, match="Session 999 not found"):
            session_manager.end_session(999)

    def test_pause_session(self, session_manager):
        """Test pausing a session."""
        session_manager._active_sessions[1] = Mock()

        # Should not raise exception
        session_manager.pause_session(1)

    def test_pause_session_not_found(self, session_manager):
        """Test pausing non-existent session."""
        with pytest.raises(ValueError, match="Session 999 not found"):
            session_manager.pause_session(999)

    def test_get_next_question(
        self,
        session_manager,
        mock_db_manager,
        sample_card,
        sample_question,
    ):
        """Test getting next question."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=2,
            questions_correct=1,
            questions_incorrect=1,
            questions_skipped=0,
            average_response_time_ms=3000,
            current_retention_rate=0.5,
            estimated_time_remaining_minutes=3,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=5,
        )

        # Setup mocks
        mock_db_manager.get_due_fsrs_cards.return_value = [sample_card]
        mock_db_manager.get_question.return_value = sample_question

        presentation = session_manager.get_next_question(1)

        assert isinstance(presentation, QuestionPresentation)
        assert presentation.question == sample_question
        assert presentation.card == sample_card
        assert presentation.question_number == 3  # questions_completed + 1
        assert (
            presentation.predicted_retention > 0
        )  # Basic check that retention is calculated

    def test_get_next_question_session_complete(self, session_manager):
        """Test getting next question when session is complete."""
        # Setup completed session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=5,  # All questions completed
            questions_correct=4,
            questions_incorrect=1,
            questions_skipped=0,
            average_response_time_ms=3000,
            current_retention_rate=0.8,
            estimated_time_remaining_minutes=0,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=10,
        )

        presentation = session_manager.get_next_question(1)

        assert presentation is None

    def test_get_next_question_no_due_cards(self, session_manager, mock_db_manager):
        """Test getting next question when no cards are due."""
        # Setup session
        session_manager._active_sessions[1] = SessionProgress(
            session_id=1,
            questions_total=5,
            questions_completed=2,
            questions_correct=1,
            questions_incorrect=1,
            questions_skipped=0,
            average_response_time_ms=3000,
            current_retention_rate=0.5,
            estimated_time_remaining_minutes=3,
            session_start_time=datetime.now(UTC),
            elapsed_time_minutes=5,
        )

        mock_db_manager.get_due_fsrs_cards.return_value = []

        presentation = session_manager.get_next_question(1)

        assert presentation is None

    def test_get_session_questions_review_type(
        self,
        session_manager,
        mock_db_manager,
        sample_card,
        sample_question,
    ):
        """Test getting questions for review session."""
        config = SessionConfig(session_type=SessionType.REVIEW, max_reviews=10)

        mock_db_manager.get_due_fsrs_cards.return_value = [sample_card]
        mock_db_manager.get_question.return_value = sample_question

        with patch.object(
            session_manager, "_create_question_presentation"
        ) as mock_create:
            mock_presentation = Mock()
            mock_create.return_value = mock_presentation

            questions = session_manager._get_session_questions(config, user_id=1)

            assert len(questions) == 1
            assert questions[0] == mock_presentation

    def test_get_session_questions_learn_type(
        self, session_manager, mock_db_manager, sample_card, sample_question
    ):
        """Test getting questions for learn session."""
        config = SessionConfig(session_type=SessionType.LEARN, max_new_cards=5)

        # Setup mock session and query
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.limit.return_value.all.return_value = [
                sample_card
            ]
            mock_db_manager.get_question.return_value = sample_question

            with patch.object(
                session_manager, "_create_question_presentation"
            ) as mock_create:
                mock_presentation = Mock()
                mock_create.return_value = mock_presentation

                questions = session_manager._get_session_questions(config, user_id=1)

                assert len(questions) == 1

    def test_create_question_presentation(
        self, session_manager, sample_question, sample_card
    ):
        """Test creating question presentation."""
        presentation = session_manager._create_question_presentation(
            sample_question, sample_card, question_num=3, total=10
        )

        assert isinstance(presentation, QuestionPresentation)
        assert presentation.question == sample_question
        assert presentation.card == sample_card
        assert presentation.question_number == 3
        assert presentation.total_questions == 10
        assert (
            presentation.predicted_retention > 0
        )  # Basic check that retention is calculated

    def test_get_difficulty_rating_new(self, session_manager):
        """Test difficulty rating for new card."""
        card = Mock()
        card.review_count = 0

        rating = session_manager._get_difficulty_rating(card)

        assert rating == "New"

    def test_get_difficulty_rating_very_hard(self, session_manager):
        """Test difficulty rating for very hard card."""
        card = Mock()
        card.review_count = 5
        card.lapse_count = 8

        rating = session_manager._get_difficulty_rating(card)

        assert rating == "Very Hard"

    def test_get_difficulty_rating_hard(self, session_manager):
        """Test difficulty rating for hard card."""
        card = Mock()
        card.review_count = 5
        card.lapse_count = 3

        rating = session_manager._get_difficulty_rating(card)

        assert rating == "Hard"

    def test_get_difficulty_rating_learning(self, session_manager):
        """Test difficulty rating for learning card."""
        card = Mock()
        card.review_count = 2
        card.lapse_count = 1

        rating = session_manager._get_difficulty_rating(card)

        assert rating == "Learning"

    def test_get_difficulty_rating_review(self, session_manager):
        """Test difficulty rating for review card."""
        card = Mock()
        card.review_count = 5
        card.lapse_count = 1

        rating = session_manager._get_difficulty_rating(card)

        assert rating == "Review"

    def test_estimate_session_time(self, session_manager):
        """Test session time estimation."""
        time_estimate = session_manager._estimate_session_time(20)

        assert time_estimate == 10  # 20 * 0.5 minutes

    def test_estimate_session_time_minimum(self, session_manager):
        """Test session time estimation minimum."""
        time_estimate = session_manager._estimate_session_time(1)

        assert time_estimate == 1  # Minimum 1 minute
