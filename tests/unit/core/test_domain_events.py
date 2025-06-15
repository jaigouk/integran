"""Tests for Domain Events and factory functions."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.shared.events import (
    CardScheduledEvent,
    LeechDetectedEvent,
    create_card_scheduled_event,
    create_leech_detected_event,
)


class MockFSRSResult:
    """Mock FSRS result for testing."""

    def __init__(self):
        self.difficulty = 5.0
        self.stability = 2.5
        self.retrievability = 0.85
        self.next_review_date = datetime.now(UTC)


class TestDomainEventFactories:
    """Test domain event factory functions."""

    def test_create_card_scheduled_event(self):
        """Test create_card_scheduled_event factory function."""
        # Create mock FSRS result
        fsrs_result = MockFSRSResult()

        event = create_card_scheduled_event(
            card_id=123,
            question_id=456,
            fsrs_result=fsrs_result,
            rating=3,
            response_time_ms=2500,
            session_id=789,
        )

        # Verify event properties
        assert isinstance(event, CardScheduledEvent)
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.new_difficulty == 5.0
        assert event.new_stability == 2.5
        assert event.new_retrievability == 0.85
        assert event.next_review_date == fsrs_result.next_review_date
        assert event.rating == 3
        assert event.response_time_ms == 2500
        assert event.session_id == 789

    def test_create_card_scheduled_event_no_session(self):
        """Test create_card_scheduled_event without session ID."""
        fsrs_result = MockFSRSResult()

        event = create_card_scheduled_event(
            card_id=123,
            question_id=456,
            fsrs_result=fsrs_result,
            rating=2,
            response_time_ms=3000,
        )

        # Verify event properties
        assert isinstance(event, CardScheduledEvent)
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.rating == 2
        assert event.response_time_ms == 3000
        assert event.session_id is None

    def test_create_leech_detected_event_default_threshold(self):
        """Test create_leech_detected_event with default threshold."""
        event = create_leech_detected_event(
            card_id=123,
            question_id=456,
            lapse_count=10,
        )

        # Verify event properties
        assert isinstance(event, LeechDetectedEvent)
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.lapse_count == 10
        assert event.leech_threshold == 8  # Default threshold
        assert event.difficulty_level == "unknown"  # Default difficulty

        # With lapse_count (10) >= threshold*2 (16), should recommend suspend
        # Actually, 10 < 16, so should be "note_added"
        assert event.recommended_action == "note_added"

    def test_create_leech_detected_event_suspend_action(self):
        """Test create_leech_detected_event with suspend recommendation."""
        event = create_leech_detected_event(
            card_id=123,
            question_id=456,
            lapse_count=20,  # >= 8*2 = 16
            leech_threshold=8,
            difficulty_level="hard",
        )

        # Verify event properties
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.lapse_count == 20
        assert event.leech_threshold == 8
        assert event.difficulty_level == "hard"
        assert event.recommended_action == "suspend"

    def test_create_leech_detected_event_modified_action(self):
        """Test create_leech_detected_event with modified recommendation."""
        event = create_leech_detected_event(
            card_id=123,
            question_id=456,
            lapse_count=13,  # >= 8*1.5 = 12 but < 8*2 = 16
            leech_threshold=8,
            difficulty_level="medium",
        )

        # Verify event properties
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.lapse_count == 13
        assert event.leech_threshold == 8
        assert event.difficulty_level == "medium"
        assert event.recommended_action == "modified"

    def test_create_leech_detected_event_note_action(self):
        """Test create_leech_detected_event with note_added recommendation."""
        event = create_leech_detected_event(
            card_id=123,
            question_id=456,
            lapse_count=10,  # < 8*1.5 = 12
            leech_threshold=8,
            difficulty_level="easy",
        )

        # Verify event properties
        assert event.card_id == 123
        assert event.question_id == 456
        assert event.lapse_count == 10
        assert event.leech_threshold == 8
        assert event.difficulty_level == "easy"
        assert event.recommended_action == "note_added"

    def test_create_leech_detected_event_custom_threshold(self):
        """Test create_leech_detected_event with custom threshold."""
        event = create_leech_detected_event(
            card_id=123,
            question_id=456,
            lapse_count=15,
            leech_threshold=5,  # Custom threshold
            difficulty_level="hard",
        )

        # With threshold=5, lapse_count=15 >= 5*2 = 10, should be suspend
        assert event.leech_threshold == 5
        assert event.recommended_action == "suspend"

    def test_domain_events_inherit_from_base(self):
        """Test that domain events inherit proper base functionality."""
        fsrs_result = MockFSRSResult()

        # Test CardScheduledEvent
        card_event = create_card_scheduled_event(
            card_id=1,
            question_id=2,
            fsrs_result=fsrs_result,
            rating=3,
            response_time_ms=1000,
        )
        assert hasattr(card_event, "event_id")
        assert hasattr(card_event, "occurred_at")
        assert card_event.event_id is not None
        assert card_event.occurred_at is not None

        # Test LeechDetectedEvent
        leech_event = create_leech_detected_event(
            card_id=1, question_id=2, lapse_count=5
        )
        assert hasattr(leech_event, "event_id")
        assert hasattr(leech_event, "occurred_at")
        assert leech_event.event_id is not None
        assert leech_event.occurred_at is not None

    def test_domain_event_post_init_methods(self):
        """Test that domain events properly call __post_init__ methods."""
        from src.domain.shared.events import (
            AnswerGeneratedEvent,
            DatabaseMigrationEvent,
            DataExportedEvent,
            DataImportedEvent,
            ImageProcessedEvent,
            InterleavingOptimizedEvent,
            PerformanceAnalyzedEvent,
            ProgressTrackedEvent,
            QuestionLoadedEvent,
            SessionCompletedEvent,
            SessionStartedEvent,
            SettingsSavedEvent,
            SystemErrorEvent,
        )

        # Test SessionStartedEvent
        session_started = SessionStartedEvent(
            session_id=1,
            user_id=1,
            session_type="review",
            target_retention=0.9,
            max_reviews=50,
        )
        assert session_started.event_id is not None
        assert session_started.occurred_at is not None

        # Test SessionCompletedEvent
        session_completed = SessionCompletedEvent(
            session_id=1,
            user_id=1,
            duration_seconds=300,
            questions_reviewed=10,
            questions_correct=8,
            new_cards_learned=2,
            retention_rate=0.8,
        )
        assert session_completed.event_id is not None
        assert session_completed.occurred_at is not None

        # Test ProgressTrackedEvent
        progress_tracked = ProgressTrackedEvent(
            user_id=1,
            date="2023-01-01",
            reviews_completed=10,
            new_cards_learned=5,
            retention_rate=0.85,
            study_streak_days=3,
        )
        assert progress_tracked.event_id is not None
        assert progress_tracked.occurred_at is not None

        # Test AnswerGeneratedEvent
        answer_generated = AnswerGeneratedEvent(
            question_id=1, languages=["en", "de"], generation_time_ms=1500, success=True
        )
        assert answer_generated.event_id is not None
        assert answer_generated.occurred_at is not None

        # Test ImageProcessedEvent
        image_processed = ImageProcessedEvent(
            question_id=1,
            image_paths=["test.jpg"],
            descriptions=["test description"],
            processing_time_ms=2000,
            success=True,
        )
        assert image_processed.event_id is not None
        assert image_processed.occurred_at is not None

        # Test QuestionLoadedEvent
        question_loaded = QuestionLoadedEvent(
            question_count=100,
            categories=["Politics", "Geography"],
            image_question_count=20,
            language="en",
            source_file="questions.json",
        )
        assert question_loaded.event_id is not None
        assert question_loaded.occurred_at is not None

        # Test PerformanceAnalyzedEvent
        performance_analyzed = PerformanceAnalyzedEvent(
            user_id=1,
            analysis_period_days=30,
            retention_rate=0.85,
            weak_categories=["Politics"],
            strong_categories=["Geography"],
            recommendations=["Focus on Politics"],
        )
        assert performance_analyzed.event_id is not None
        assert performance_analyzed.occurred_at is not None

        # Test InterleavingOptimizedEvent
        interleaving_optimized = InterleavingOptimizedEvent(
            session_id=1,
            strategy_used="random",
            categories_mixed=["Politics", "Geography"],
            optimization_score=0.75,
            question_count=20,
        )
        assert interleaving_optimized.event_id is not None
        assert interleaving_optimized.occurred_at is not None

        # Test SettingsSavedEvent
        settings_saved = SettingsSavedEvent(
            user_id=1,
            setting_key="language",
            old_value="en",
            new_value="de",
            setting_type="string",
        )
        assert settings_saved.event_id is not None
        assert settings_saved.occurred_at is not None

        # Test DataExportedEvent
        data_exported = DataExportedEvent(
            user_id=1,
            export_type="full",
            file_path="export.json",
            record_count=1000,
            file_size_bytes=50000,
        )
        assert data_exported.event_id is not None
        assert data_exported.occurred_at is not None

        # Test DataImportedEvent
        data_imported = DataImportedEvent(
            user_id=1,
            import_type="full",
            source_file="import.json",
            records_imported=1000,
            conflicts_resolved=10,
            import_strategy="merge",
        )
        assert data_imported.event_id is not None
        assert data_imported.occurred_at is not None

        # Test SystemErrorEvent
        system_error = SystemErrorEvent(
            error_type="DatabaseError",
            error_message="Connection failed",
            component="database",
            severity="high",
        )
        assert system_error.event_id is not None
        assert system_error.occurred_at is not None

        # Test DatabaseMigrationEvent
        db_migration = DatabaseMigrationEvent(
            migration_version="1.0.0",
            migration_type="schema",
            success=True,
            duration_ms=5000,
        )
        assert db_migration.event_id is not None
        assert db_migration.occurred_at is not None
