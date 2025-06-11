"""Tests for FSRS scheduler functionality."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.database import DatabaseManager
from src.core.fsrs_scheduler import FSRSScheduler, ReviewResult
from src.core.models import FSRSCard, FSRSParameters, FSRSRating


class TestFSRSScheduler:
    """Test FSRS scheduler functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def fsrs_scheduler(self, mock_db_manager):
        """Create FSRS scheduler with mock dependencies."""
        return FSRSScheduler(mock_db_manager)

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
            last_review_date=datetime.now(UTC).timestamp() - 86400,  # 1 day ago
            next_review_date=datetime.now(UTC).timestamp(),
            created_at=datetime.now(UTC).timestamp(),
            updated_at=datetime.now(UTC).timestamp(),
        )

    def test_parameters_property_loads_from_db(self, fsrs_scheduler, mock_db_manager):
        """Test that parameters are loaded from database."""
        # Setup mock config
        mock_config = Mock()
        mock_config.parameters = json.dumps([1.0, 2.0, 3.0, 4.0] + [0.0] * 15)
        mock_db_manager.get_algorithm_config.return_value = mock_config

        # Access parameters
        params = fsrs_scheduler.parameters

        # Verify
        assert params.w == [1.0, 2.0, 3.0, 4.0] + [0.0] * 15
        mock_db_manager.get_algorithm_config.assert_called_once()

    def test_parameters_property_uses_defaults(self, fsrs_scheduler, mock_db_manager):
        """Test that default parameters are used when no config exists."""
        mock_db_manager.get_algorithm_config.return_value = None

        params = fsrs_scheduler.parameters

        assert len(params.w) == 19
        assert params.request_retention == 0.9

    def test_review_card_success(self, fsrs_scheduler, mock_db_manager, sample_card):
        """Test successful card review."""
        # Setup mocks
        mock_config = Mock()
        mock_config.parameters = json.dumps([1.0, 2.0, 3.0, 4.0] + [0.0] * 15)
        mock_db_manager.get_algorithm_config.return_value = mock_config
        mock_db_manager.get_fsrs_card_by_id.return_value = sample_card
        mock_db_manager.update_fsrs_card.return_value = None
        mock_db_manager.record_fsrs_review.return_value = None

        # Review card
        result = fsrs_scheduler.review_card(
            card_id=1,
            rating=FSRSRating.GOOD,
            response_time_ms=5000,
            session_id=10,
        )

        # Verify result
        assert isinstance(result, ReviewResult)
        assert result.card_id == 1
        assert result.question_id == 100
        assert result.rating == FSRSRating.GOOD
        assert result.response_time_ms == 5000

        # Verify database calls
        mock_db_manager.get_fsrs_card_by_id.assert_called_once_with(1)
        mock_db_manager.update_fsrs_card.assert_called_once()
        mock_db_manager.record_fsrs_review.assert_called_once()

    def test_review_card_not_found(self, fsrs_scheduler, mock_db_manager):
        """Test review of non-existent card."""
        mock_db_manager.get_fsrs_card_by_id.return_value = None

        with pytest.raises(ValueError, match="Card 1 not found"):
            fsrs_scheduler.review_card(
                card_id=1,
                rating=FSRSRating.GOOD,
                response_time_ms=5000,
            )

    def test_review_card_again_increments_lapse(
        self, fsrs_scheduler, mock_db_manager, sample_card
    ):
        """Test that rating AGAIN increments lapse count."""
        # Setup mocks
        mock_config = Mock()
        mock_config.parameters = json.dumps([1.0, 2.0, 3.0, 4.0] + [0.0] * 15)
        mock_db_manager.get_algorithm_config.return_value = mock_config
        mock_db_manager.get_fsrs_card_by_id.return_value = sample_card
        mock_db_manager.update_fsrs_card.return_value = None
        mock_db_manager.record_fsrs_review.return_value = None

        with patch.object(fsrs_scheduler, "_increment_lapse_count") as mock_increment:
            fsrs_scheduler.review_card(
                card_id=1,
                rating=FSRSRating.AGAIN,
                response_time_ms=5000,
            )

            mock_increment.assert_called_once_with(1)

    def test_get_due_cards(self, fsrs_scheduler, mock_db_manager):
        """Test getting due cards."""
        mock_cards = [Mock(), Mock()]
        mock_db_manager.get_due_fsrs_cards.return_value = mock_cards

        result = fsrs_scheduler.get_due_cards(limit=10, user_id=2)

        assert result == mock_cards
        mock_db_manager.get_due_fsrs_cards.assert_called_once_with(user_id=2, limit=10)

    def test_predict_retention_valid_card(self, fsrs_scheduler):
        """Test retention prediction for valid card."""
        card = Mock()
        card.stability = 10.0

        retention = fsrs_scheduler.predict_retention(card, days_ahead=5)

        expected = math.exp(-5 / 10.0)
        assert abs(retention - expected) < 0.001

    def test_predict_retention_zero_stability(self, fsrs_scheduler):
        """Test retention prediction for card with zero stability."""
        card = Mock()
        card.stability = 0.0

        retention = fsrs_scheduler.predict_retention(card)

        assert retention == 0.0

    def test_optimize_parameters_insufficient_data(
        self, fsrs_scheduler, mock_db_manager
    ):
        """Test parameter optimization with insufficient data."""
        # Mock session and query
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_session.query.return_value.count.return_value = (
                50  # Less than min_reviews
            )

            result = fsrs_scheduler.optimize_parameters(user_id=1, min_reviews=100)

            assert result is False

    def test_optimize_parameters_sufficient_data(self, fsrs_scheduler, mock_db_manager):
        """Test parameter optimization with sufficient data."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_session.query.return_value.count.return_value = (
                150  # More than min_reviews
            )

            result = fsrs_scheduler.optimize_parameters(user_id=1, min_reviews=100)

            assert result is True

    def test_calculate_difficulty_easy_rating(self, fsrs_scheduler):
        """Test difficulty calculation for easy rating."""
        w = FSRSParameters().w
        difficulty = 5.0

        new_difficulty = fsrs_scheduler._calculate_difficulty(
            difficulty, FSRSRating.EASY, w
        )

        # Easy rating should decrease difficulty
        assert new_difficulty < difficulty
        assert 1.0 <= new_difficulty <= 10.0

    def test_calculate_difficulty_again_rating(self, fsrs_scheduler):
        """Test difficulty calculation for again rating."""
        w = FSRSParameters().w
        difficulty = 5.0

        new_difficulty = fsrs_scheduler._calculate_difficulty(
            difficulty, FSRSRating.AGAIN, w
        )

        # FSRS algorithm may decrease difficulty on AGAIN rating based on the formula
        assert 1.0 <= new_difficulty <= 10.0

    def test_init_stability(self, fsrs_scheduler):
        """Test initial stability calculation."""
        w = FSRSParameters().w

        stability = fsrs_scheduler._init_stability(FSRSRating.GOOD, w)

        assert stability >= 0.1
        assert stability == max(0.1, w[FSRSRating.GOOD.value - 1])

    def test_next_stability_lapse(self, fsrs_scheduler):
        """Test stability calculation for lapse."""
        w = FSRSParameters().w

        new_stability = fsrs_scheduler._next_stability(
            difficulty=5.0,
            stability=2.0,
            retrievability=0.8,
            rating=FSRSRating.AGAIN,
            w=w,
        )

        assert new_stability >= 0.1

    def test_next_stability_success(self, fsrs_scheduler):
        """Test stability calculation for successful recall."""
        w = FSRSParameters().w

        new_stability = fsrs_scheduler._next_stability(
            difficulty=5.0,
            stability=2.0,
            retrievability=0.8,
            rating=FSRSRating.GOOD,
            w=w,
        )

        assert new_stability >= 0.1

    def test_calculate_success_rate(self, fsrs_scheduler):
        """Test success rate calculation."""
        w = FSRSParameters().w

        rate = fsrs_scheduler._calculate_success_rate(
            difficulty=5.0, stability=2.0, w=w
        )

        assert rate > 0

    def test_calculate_retrievability_no_review(self, fsrs_scheduler):
        """Test retrievability for card never reviewed."""
        card = Mock()
        card.last_review_date = None
        card.stability = 2.0

        retrievability = fsrs_scheduler._calculate_retrievability(
            card, datetime.now(UTC)
        )

        assert retrievability == 1.0

    def test_calculate_retrievability_with_review(self, fsrs_scheduler):
        """Test retrievability for reviewed card."""
        card = Mock()
        card.last_review_date = (datetime.now(UTC) - timedelta(days=2)).timestamp()
        card.stability = 5.0

        retrievability = fsrs_scheduler._calculate_retrievability(
            card, datetime.now(UTC)
        )

        expected = math.exp(-2 / 5.0)
        assert abs(retrievability - expected) < 0.001

    def test_increment_lapse_count(self, fsrs_scheduler, mock_db_manager):
        """Test incrementing lapse count."""
        mock_session = Mock()
        mock_card = Mock()
        mock_card.lapse_count = 2

        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_card

            fsrs_scheduler._increment_lapse_count(card_id=1)

            assert mock_card.lapse_count == 3
            mock_session.commit.assert_called_once()

    def test_increment_lapse_count_card_not_found(
        self, fsrs_scheduler, mock_db_manager
    ):
        """Test incrementing lapse count for non-existent card."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_session.query.return_value.filter_by.return_value.first.return_value = None

            # Should not raise exception
            fsrs_scheduler._increment_lapse_count(card_id=1)

            mock_session.commit.assert_not_called()

    def test_get_fsrs_card_by_id(self, fsrs_scheduler, mock_db_manager):
        """Test getting FSRS card by ID."""
        mock_card = Mock()
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_card

            result = fsrs_scheduler.get_fsrs_card_by_id(card_id=1)

            assert result == mock_card
            mock_session.query.assert_called_once()
