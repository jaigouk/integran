"""Core module for Leben in Deutschland trainer."""

# Legacy imports (to be gradually migrated)
from src.core.database import DatabaseManager
from src.core.domain_events import (
    # Content Context Events
    AnswerGeneratedEvent,
    # Learning Context Events
    CardScheduledEvent,
    DatabaseMigrationEvent,
    DataExportedEvent,
    DataImportedEvent,
    ImageProcessedEvent,
    InterleavingOptimizedEvent,
    # Analytics Context Events
    LeechDetectedEvent,
    PerformanceAnalyzedEvent,
    ProgressTrackedEvent,
    QuestionLoadedEvent,
    SessionCompletedEvent,
    SessionStartedEvent,
    # User Context Events
    SettingsSavedEvent,
    # System Events
    SystemErrorEvent,
    # Factory Functions
    create_card_scheduled_event,
    create_leech_detected_event,
)
from src.core.domain_service import (
    BusinessRuleViolationError,
    DomainService,
    DomainServiceError,
    ValidationError,
    log_domain_operation,
    validate_request,
)

# DDD Infrastructure (Phase 1)
from src.core.event_bus import DomainEvent, EventBus
from src.core.models import (
    AnswerStatus,
    Difficulty,
    LearningStats,
    PracticeMode,
    QuestionData,
    QuestionResult,
    SessionStats,
)

__all__ = [
    # Legacy exports
    "DatabaseManager",
    "QuestionData",
    "QuestionResult",
    "SessionStats",
    "LearningStats",
    "Difficulty",
    "PracticeMode",
    "AnswerStatus",
    # DDD Infrastructure
    "EventBus",
    "DomainEvent",
    "DomainService",
    "DomainServiceError",
    "ValidationError",
    "BusinessRuleViolationError",
    "log_domain_operation",
    "validate_request",
    # Domain Events
    "CardScheduledEvent",
    "SessionStartedEvent",
    "SessionCompletedEvent",
    "ProgressTrackedEvent",
    "AnswerGeneratedEvent",
    "ImageProcessedEvent",
    "QuestionLoadedEvent",
    "LeechDetectedEvent",
    "PerformanceAnalyzedEvent",
    "InterleavingOptimizedEvent",
    "SettingsSavedEvent",
    "DataExportedEvent",
    "DataImportedEvent",
    "SystemErrorEvent",
    "DatabaseMigrationEvent",
    "create_card_scheduled_event",
    "create_leech_detected_event",
]
