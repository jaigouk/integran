"""Tests for time-based performance analysis functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.analytics.services.analyze_performance import ProgressAnalytics


class TestTimeBasedAnalytics:
    """Test time-based performance analysis features."""

    @pytest.fixture
    def mock_analytics_repository(self):
        """Create a mock analytics repository."""
        repo = Mock()
        repo.get_hourly_session_stats = AsyncMock()
        repo.get_daily_study_patterns = AsyncMock()
        repo.get_learning_stats = AsyncMock()
        repo.get_session_progress = AsyncMock()
        repo.get_category_progress = AsyncMock()
        return repo

    @pytest.fixture
    def progress_analytics(self, mock_analytics_repository):
        """Create ProgressAnalytics service with mocked repository."""
        return ProgressAnalytics(analytics_repository=mock_analytics_repository)

    @pytest.mark.asyncio
    async def test_analyze_study_times_with_data(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test _analyze_study_times with actual session data."""
        # Mock hourly session stats data
        mock_hourly_stats = {
            9: {
                "count": 5,
                "avg_accuracy": 0.85,
                "total_duration": 1500,
            },  # High performance morning
            14: {
                "count": 3,
                "avg_accuracy": 0.90,
                "total_duration": 900,
            },  # Very high accuracy afternoon
            19: {
                "count": 2,
                "avg_accuracy": 0.75,
                "total_duration": 600,
            },  # Lower accuracy evening
            22: {
                "count": 1,
                "avg_accuracy": 0.60,
                "total_duration": 300,
            },  # Poor late night
        }

        # Fill in other hours with empty data
        for hour in range(24):
            if hour not in mock_hourly_stats:
                mock_hourly_stats[hour] = {
                    "count": 0,
                    "avg_accuracy": 0.0,
                    "total_duration": 0,
                }

        mock_analytics_repository.get_hourly_session_stats.return_value = (
            mock_hourly_stats
        )

        # Call the method
        result = await progress_analytics._analyze_study_times(user_id=1)

        # Verify results
        assert len(result) == 3, "Should return exactly 3 recommended times"
        assert all(isinstance(time, str) for time in result), (
            "All results should be strings"
        )
        assert all(":" in time for time in result), (
            "All results should be in HH:MM format"
        )

        # The highest accuracy time (14:00) should be first
        assert "14:00" in result, "14:00 should be recommended (highest accuracy)"

        # Should prefer morning over evening due to better performance
        assert "09:00" in result, (
            "09:00 should be recommended (good frequency + accuracy)"
        )

    @pytest.mark.asyncio
    async def test_analyze_study_times_no_data(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test _analyze_study_times with no session data."""
        # Mock empty hourly stats
        empty_stats = {
            hour: {"count": 0, "avg_accuracy": 0.0, "total_duration": 0}
            for hour in range(24)
        }
        mock_analytics_repository.get_hourly_session_stats.return_value = empty_stats

        # Call the method
        result = await progress_analytics._analyze_study_times(user_id=1)

        # Should return default recommendations
        assert result == ["09:00", "14:00", "19:00"], (
            "Should return default times when no data available"
        )

    @pytest.mark.asyncio
    async def test_analyze_study_times_handles_exception(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test _analyze_study_times handles repository exceptions gracefully."""
        # Mock repository to raise an exception
        mock_analytics_repository.get_hourly_session_stats.side_effect = Exception(
            "Database error"
        )

        # Call the method
        result = await progress_analytics._analyze_study_times(user_id=1)

        # Should return default recommendations despite error
        assert result == ["09:00", "14:00", "19:00"], (
            "Should return defaults when exception occurs"
        )

    @pytest.mark.asyncio
    async def test_analyze_study_times_scoring_logic(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test the scoring logic prioritizes accuracy over frequency."""
        # Create data where frequency conflicts with accuracy
        mock_hourly_stats = {
            # High frequency, low accuracy
            10: {"count": 10, "avg_accuracy": 0.50, "total_duration": 3000},
            # Low frequency, high accuracy
            15: {"count": 2, "avg_accuracy": 0.95, "total_duration": 600},
            # Medium frequency, medium accuracy
            20: {"count": 5, "avg_accuracy": 0.75, "total_duration": 1500},
        }

        # Fill in other hours with empty data
        for hour in range(24):
            if hour not in mock_hourly_stats:
                mock_hourly_stats[hour] = {
                    "count": 0,
                    "avg_accuracy": 0.0,
                    "total_duration": 0,
                }

        mock_analytics_repository.get_hourly_session_stats.return_value = (
            mock_hourly_stats
        )

        # Call the method
        result = await progress_analytics._analyze_study_times(user_id=1)

        # High accuracy should win despite lower frequency (accuracy has 50% weight)
        assert "15:00" in result, (
            "15:00 should be recommended (highest accuracy despite low frequency)"
        )

    @pytest.mark.asyncio
    async def test_get_study_forecast_with_daily_patterns(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test _get_study_forecast uses real daily patterns for workload distribution."""
        # Mock learning stats
        mock_analytics_repository.get_learning_stats.return_value = {
            "due_today": 15,
            "due_tomorrow": 12,
            "due_week": 50,
        }

        # Mock daily patterns that show user studies more on weekdays
        mock_daily_patterns = [
            {
                "date": "2024-06-17",  # Monday
                "session_count": 2,
                "sessions": [
                    {"total_questions": 20},
                    {"total_questions": 15},
                ],
            },
            {
                "date": "2024-06-18",  # Tuesday
                "session_count": 1,
                "sessions": [{"total_questions": 25}],
            },
            {
                "date": "2024-06-16",  # Sunday
                "session_count": 1,
                "sessions": [{"total_questions": 5}],
            },
        ]

        mock_analytics_repository.get_daily_study_patterns.return_value = (
            mock_daily_patterns
        )

        # Call the method
        result = await progress_analytics._get_study_forecast(user_id=1)

        # Verify the forecast uses real data
        assert result.reviews_due_today == 15
        assert result.reviews_due_tomorrow == 12
        assert result.reviews_due_week == 50

        # Verify workload distribution reflects actual patterns
        assert "Mon" in result.workload_distribution
        assert "Tue" in result.workload_distribution

        # Monday should have more questions (35 total) than Sunday (5 total)
        assert result.workload_distribution["Mon"] > result.workload_distribution["Sun"]

        # Peak day should be Monday (highest question count)
        assert result.peak_review_day == "Mon"

    @pytest.mark.asyncio
    async def test_get_study_forecast_fallback_behavior(
        self, progress_analytics, mock_analytics_repository
    ):
        """Test _get_study_forecast handles missing data gracefully."""
        # Mock learning stats
        mock_analytics_repository.get_learning_stats.return_value = {
            "due_today": 10,
            "due_tomorrow": 8,
            "due_week": 30,
        }

        # Mock empty daily patterns
        mock_analytics_repository.get_daily_study_patterns.return_value = []

        # Call the method
        result = await progress_analytics._get_study_forecast(user_id=1)

        # Should use fallback defaults
        assert result.peak_review_day == "Monday"
        assert len(result.workload_distribution) == 7  # All 7 days
        assert all(
            day in result.workload_distribution
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        )
