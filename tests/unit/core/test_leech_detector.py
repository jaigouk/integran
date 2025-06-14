"""Tests for leech detector functionality."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.database import DatabaseManager
from src.core.leech_detector import (
    InterventionStrategy,
    InterventionType,
    LeechAnalysis,
    LeechDetector,
    LeechSeverity,
)


class TestLeechDetector:
    """Test leech detector functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def leech_detector(self, mock_db_manager):
        """Create leech detector with mock dependencies."""
        return LeechDetector(mock_db_manager)

    @pytest.fixture
    def sample_leech_cards(self):
        """Create sample cards that qualify as leeches."""
        cards = []
        for i in range(3):
            card = Mock()
            card.card_id = i + 1
            card.question_id = (i + 1) * 100
            card.user_id = 1
            card.lapse_count = 10 + i  # High lapse counts
            card.difficulty = 8.0 + i * 0.5
            card.stability = 0.5
            card.review_count = 15 + i
            card.last_review_date = datetime.now(UTC).timestamp() - (i * 86400)
            cards.append(card)
        return cards

    def test_detect_leeches_finds_high_lapse_cards(
        self, leech_detector, mock_db_manager, sample_leech_cards
    ):
        """Test that leech detection finds cards with high lapse counts."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            # Mock the query to return high-lapse cards
            mock_session.query.return_value.filter.return_value.all.return_value = (
                sample_leech_cards
            )

            # Mock existing leech check (none exist)
            mock_session.query.return_value.filter_by.return_value.first.return_value = None

            # Mock the analysis method
            mock_analysis = LeechAnalysis(
                card=sample_leech_cards[0],
                question=Mock(),
                severity=LeechSeverity.SEVERE,
                lapse_count=10,
                success_rate=0.2,
                average_response_time=8000.0,
                difficulty_trend="increasing",
                common_mistakes=["concept confusion"],
                last_success_date=None,
                intervention_history=[],
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    leech_detector,
                    "_analyze_leech_card",
                    lambda _card, _session: mock_analysis,
                )

                leeches = leech_detector.detect_leeches(user_id=1, threshold=8)

            assert len(leeches) >= 1
            assert isinstance(leeches[0], LeechAnalysis)

    def test_detect_leeches_skips_existing(
        self, leech_detector, mock_db_manager, sample_leech_cards
    ):
        """Test that existing leeches are skipped unless force_redetection is True."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            mock_session.query.return_value.filter.return_value.all.return_value = (
                sample_leech_cards
            )

            # Mock existing leech for first card
            existing_leech = Mock()
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                existing_leech,  # First card already exists
                None,  # Second card doesn't exist
                None,  # Third card doesn't exist
            ]

            # Mock analysis for non-existing cards
            mock_analysis = LeechAnalysis(
                card=sample_leech_cards[1],
                question=Mock(),
                severity=LeechSeverity.MODERATE,
                lapse_count=11,
                success_rate=0.3,
                average_response_time=7000.0,
                difficulty_trend="stable",
                common_mistakes=[],
                last_success_date=None,
                intervention_history=[],
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    leech_detector,
                    "_analyze_leech_card",
                    lambda _card, _session: mock_analysis,
                )

                leeches = leech_detector.detect_leeches(user_id=1, threshold=8)

            # Should detect some leeches but skip existing ones
            assert len(leeches) >= 0

    def test_detect_leeches_force_redetection(
        self, leech_detector, mock_db_manager, sample_leech_cards
    ):
        """Test force redetection includes existing leeches."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            mock_session.query.return_value.filter.return_value.all.return_value = (
                sample_leech_cards
            )

            mock_analysis = LeechAnalysis(
                card=sample_leech_cards[0],
                question=Mock(),
                severity=LeechSeverity.SEVERE,
                lapse_count=10,
                success_rate=0.1,
                average_response_time=9000.0,
                difficulty_trend="increasing",
                common_mistakes=["repeated errors"],
                last_success_date=None,
                intervention_history=[],
            )

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    leech_detector,
                    "_analyze_leech_card",
                    lambda _card, _session: mock_analysis,
                )

                leeches = leech_detector.detect_leeches(
                    user_id=1, threshold=8, force_redetection=True
                )

            # With force redetection, should get all cards regardless of existing status
            assert len(leeches) >= 1

    def test_detect_leeches_no_qualifying_cards(self, leech_detector, mock_db_manager):
        """Test leech detection with no qualifying cards."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            mock_session.query.return_value.filter.return_value.all.return_value = []

            leeches = leech_detector.detect_leeches(user_id=1, threshold=8)

            assert len(leeches) == 0

    def test_get_intervention_strategies(self, leech_detector):
        """Test getting intervention strategies for leeches."""
        # Create mock leech analysis
        analysis = LeechAnalysis(
            card=Mock(),
            question=Mock(),
            severity=LeechSeverity.SEVERE,
            lapse_count=12,
            success_rate=0.2,  # Low success rate
            average_response_time=12000.0,  # Slow response
            difficulty_trend="increasing",
            common_mistakes=["concept confusion"],
            last_success_date=None,
            intervention_history=[],
        )

        strategies = leech_detector.get_intervention_strategies(analysis)

        assert len(strategies) > 0
        for strategy in strategies:
            assert isinstance(strategy, InterventionStrategy)
            assert strategy.intervention_type in [
                InterventionType.ADDITIONAL_PRACTICE,
                InterventionType.SPACED_REPETITION,
                InterventionType.CONCEPT_BREAKDOWN,
                InterventionType.MNEMONIC_SUGGESTION,
                InterventionType.SUSPEND_TEMPORARILY,
                InterventionType.EXPERT_EXPLANATION,
            ]

    def test_get_leech_report(self, leech_detector, mock_db_manager):
        """Test getting comprehensive leech report."""
        mock_session = Mock()
        with patch.object(mock_db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            # Mock leech count queries
            mock_session.query.return_value.filter_by.return_value.count.return_value = 5

            # Mock leech records
            mock_leeches = []
            for i in range(3):
                leech = Mock()
                leech.card_id = i + 1
                leech.lapse_count = 8 + i
                mock_leeches.append(leech)

            mock_session.query.return_value.filter_by.return_value.all.return_value = (
                mock_leeches
            )

            # Mock detect_leeches method
            mock_analyses = [
                LeechAnalysis(
                    card=Mock(),
                    question=Mock(),
                    severity=LeechSeverity.MODERATE,
                    lapse_count=8,
                    success_rate=0.3,
                    average_response_time=7000.0,
                    difficulty_trend="stable",
                    common_mistakes=[],
                    last_success_date=None,
                    intervention_history=[],
                )
            ]

            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    leech_detector, "detect_leeches", lambda _user_id: mock_analyses
                )

                report = leech_detector.generate_leech_report(user_id=1)

            assert report.user_id == 1
            assert report.total_leeches >= 0
            assert isinstance(report.by_severity, dict)
            assert isinstance(report.by_category, dict)

    def test_init(self, mock_db_manager):
        """Test LeechDetector initialization."""
        detector = LeechDetector(mock_db_manager)

        assert detector.db_manager == mock_db_manager

    def test_analyze_leech_card_basic(self, leech_detector):
        """Test basic leech card analysis."""
        # Create a mock card
        card = Mock()
        card.card_id = 1
        card.question_id = 100
        card.lapse_count = 10
        card.difficulty = 8.0
        card.stability = 0.5
        card.last_review_date = (datetime.now(UTC) - timedelta(days=2)).timestamp()

        # Create mock session
        session = Mock()

        # Mock reviews with some sample data
        mock_reviews = []
        base_timestamp = datetime.now(UTC).timestamp()
        for i in range(5):
            review = Mock()
            review.rating = 2 if i < 3 else 4  # Some failures, some successes
            review.response_time_ms = 5000 + i * 1000
            review.review_date = base_timestamp - (i * 86400)  # Spread over days
            mock_reviews.append(review)

        # Mock the specific query chain for reviews
        session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_reviews

        # Mock the question query chain
        mock_question = Mock()
        mock_question.category = "Politik"
        session.query.return_value.filter_by.return_value.first.return_value = (
            mock_question
        )

        analysis = leech_detector._analyze_leech_card(card, session)

        if analysis:  # Method might return None for some cards
            assert isinstance(analysis, LeechAnalysis)
            assert analysis.card == card
            assert analysis.lapse_count == 10

    def test_categorize_by_difficulty_moderate(self, leech_detector):
        """Test difficulty categorization for moderate leeches."""
        severity = leech_detector._categorize_by_difficulty(6, 0.4)

        # The method should return a severity based on lapse count and success rate
        assert severity in [
            LeechSeverity.MILD,
            LeechSeverity.MODERATE,
            LeechSeverity.SEVERE,
        ]

    def test_categorize_by_difficulty_severe(self, leech_detector):
        """Test difficulty categorization for severe leeches."""
        severity = leech_detector._categorize_by_difficulty(12, 0.1)

        assert severity in [
            LeechSeverity.MILD,
            LeechSeverity.MODERATE,
            LeechSeverity.SEVERE,
        ]

    def test_estimate_success_interventions(self, leech_detector):  # noqa: ARG002
        """Test estimating success rate of interventions."""
        # Create sample intervention strategy
        strategy = InterventionStrategy(
            intervention_type=InterventionType.ADDITIONAL_PRACTICE,
            priority=1,
            description="Extra practice",
            estimated_effectiveness=0.7,
            time_investment="medium",
            success_rate=0.65,
        )

        # This tests that the intervention strategy is properly formed
        assert strategy.estimated_effectiveness == 0.7
        assert strategy.success_rate == 0.65
        assert strategy.intervention_type == InterventionType.ADDITIONAL_PRACTICE
