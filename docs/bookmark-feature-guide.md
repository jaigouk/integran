# Bookmark Feature Architecture Guide

> **📚 Related Documentation**  
> - **[Developer Guide](./developer-guide.md)** - Complete CQRS/DDD architecture guidelines and best practices  
> - **[Event Flows](./event-flows.yaml)** - System-wide event flow specifications  
> - **[Dataset Generation Guide](./dataset-generation-guide.md)** - Dataset workflow and AI extraction  

---

This guide demonstrates CQRS/DDD architecture patterns through the bookmark feature implementation in Integran. Use this as a **complete reference** for understanding how to properly implement features following clean architecture principles.

**🎯 This is the canonical example** of CQRS/DDD implementation in Integran - all new features should follow these patterns.

## 🎯 Architecture Overview

The bookmark feature serves as a **complete example** of implementing CQRS/DDD patterns, showing how all layers work together to deliver business value while maintaining clean separation of concerns.

### Why This Feature Demonstrates Good Architecture

1. **Full CQRS Implementation**: Separate command and query paths with proper handlers
2. **Domain-Driven Design**: Rich domain models with business logic encapsulation
3. **Event-Driven Architecture**: Proper domain event publishing and handling
4. **Dependency Inversion**: Interfaces owned by domain, implemented by infrastructure
5. **Layer Separation**: Clean boundaries between presentation, application, domain, and infrastructure

## 🏗️ CQRS Architecture Implementation

### Layer Responsibilities in Bookmark Feature

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  • BookmarkView (Terminal UI)                                       │
│  • User Actions (Add/Remove/View bookmarks)                         │
│  • Display bookmark lists and statistics                            │
│  • Calls application command/query handlers                         │
│  • NO business logic                                                │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Commands/Queries
┌─────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                            │
│  • AddBookmarkCommandHandler                                        │
│  • RemoveBookmarkCommandHandler                                     │
│  • GetBookmarksQueryHandler                                         │
│  • BookmarkEventHandlers                                            │
│  • Thin coordinators (< 50 lines)                                   │
│  • NO business logic                                                │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Repository Interfaces
┌─────────────────────────────────────────────────────────────────────┐
│                          DOMAIN LAYER                               │
│  • Bookmark Entity (with validation)                                │
│  • BookmarkRepository Interface                                     │
│  • Domain Events (BookmarkAddedEvent, etc.)                         │
│  • Business rules and validation                                    │
│  • ALL business logic here                                          │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Interface Implementation
┌─────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                           │
│  • BookmarkRepositoryImpl (SQLite)                                  │
│  • Database table with indexes                                      │
│  • Event bus implementation                                         │
│  • External integrations                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Architecture Principles Demonstrated

1. **Commands Flow Through Domain**: Write operations use domain services
2. **Queries Can Bypass Domain**: Read operations go direct to repositories for performance
3. **Events Enable Cross-Context Communication**: Domain events trigger analytics updates
4. **Interfaces Enable Testability**: Mock repositories for unit testing
5. **Validation at Domain Boundary**: Business rules enforced in domain models

## 🔄 Data Flow Patterns

### Write Operation: Adding a Bookmark

```
USER ACTION: Click bookmark button
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: BookmarkView                                          │
│  1. User clicks bookmark button                                     │
│  2. Creates AddBookmarkCommand                                      │
│  3. Calls command handler                                           │
│  4. Updates UI based on result                                      │
└─────────────────────────────────────────────────────────────────────┘
     │ handler.handle(command)
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: AddBookmarkCommandHandler                              │
│  1. Validates command structure                                     │
│  2. Calls repository to add bookmark                                │
│  3. Publishes domain event                                          │
│  4. Returns success/failure result                                  │
└─────────────────────────────────────────────────────────────────────┘
     │ repository.add_bookmark()
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN: BookmarkRepository Interface                                │
│  1. Defines contract for bookmark operations                        │
│  2. Owned by domain layer                                           │
│  3. Enforces business rules through validation                      │
└─────────────────────────────────────────────────────────────────────┘
     │ implementation
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: BookmarkRepositoryImpl                              │
│  1. Implements domain interface                                     │
│  2. Handles database operations                                     │
│  3. Manages transactions and concurrency                            │
│  4. Converts between domain and data models                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Read Operation: Getting Bookmarks

```
USER ACTION: View bookmarks page
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: BookmarkView                                          │
│  1. User navigates to bookmarks                                     │
│  2. Creates GetBookmarksQuery                                       │
│  3. Calls query handler                                             │
│  4. Displays results                                                │
└─────────────────────────────────────────────────────────────────────┘
     │ handler.handle(query)
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: GetBookmarksQueryHandler                               │
│  1. Direct repository access (CQRS read side)                       │
│  2. No domain service needed                                        │
│  3. Optimized for read performance                                  │
│  4. Returns formatted data                                          │
└─────────────────────────────────────────────────────────────────────┘
     │ repository.get_bookmarks()
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: BookmarkRepositoryImpl                              │
│  1. Optimized SQL query with pagination                             │
│  2. Uses database indexes for performance                           │
│  3. Returns domain objects                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Event Flow: Cross-Context Communication

#### Complete Event Flow Diagram

```
COMMAND: AddBookmarkCommand
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ AddBookmarkCommandHandler                                           │
│  1. Calls repository.add_bookmark()                                 │
│  2. Publishes BookmarkAddedEvent                                    │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ event_bus.publish(BookmarkAddedEvent)
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: EventBus                                            │
│  • Receives: BookmarkAddedEvent                                     │
│  • Finds all registered handlers                                    │
│  • Calls handlers in parallel (async)                               │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Dispatches to multiple handlers
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     EVENT HANDLERS (Parallel)                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ BookmarkAddedEventHandler                                   │    │
│  │  • Records analytics activity                               │    │
│  │  • Updates user engagement metrics                          │    │
│  │  • Increments question bookmark count                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ NotificationEventHandler (if exists)                        │    │
│  │  • Sends notification to user                               │    │
│  │  • Updates notification preferences                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ SyncEventHandler (if exists)                                │    │
│  │  • Syncs bookmark to external service                       │    │
│  │  • Updates sync status                                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

#### Event Flow for Different Operations

**1. Adding a Bookmark**

```
AddBookmarkCommand → AddBookmarkCommandHandler → repository.add_bookmark()
                                                ↓
                                         BookmarkAddedEvent
                                                ↓
                                           Event Bus
                                                ↓
                     ┌─────────────────────────────────────────────┐
                     │                                             │
                     ↓                                             ↓
    BookmarkAddedEventHandler                          Future: NotificationHandler
    • record_bookmark_activity()                       • send_bookmark_notification()
    • update_user_engagement_metrics()                 • update_notification_preferences()
    • increment_question_bookmark_count()
```

**2. Removing a Bookmark**

```
RemoveBookmarkCommand → RemoveBookmarkCommandHandler → repository.remove_bookmark()
                                                    ↓
                                          BookmarkRemovedEvent
                                                    ↓
                                              Event Bus
                                                    ↓
                       ┌─────────────────────────────────────────────┐
                       │                                             │
                       ↓                                             ↓
      BookmarkRemovedEventHandler                        Future: NotificationHandler
      • record_bookmark_activity()                       • send_removal_notification()
      • update_user_engagement_metrics()                 • update_notification_preferences()
      • decrement_question_bookmark_count()
```

**3. Viewing Bookmarks**

```
GetBookmarksQuery → GetBookmarksQueryHandler → repository.get_bookmarks()
                                            ↓
                                   BookmarksViewedEvent
                                            ↓
                                      Event Bus
                                            ↓
                  ┌─────────────────────────────────────────────────────┐
                  │                                                     │
                  ↓                                                     ↓
    BookmarksViewedEventHandler                           Future: AnalyticsHandler
    • record_bookmark_activity()                          • track_view_patterns()
    • track_practice_session_start() (if practice mode)   • update_usage_metrics()
    • record_feature_usage() (if manage mode)
    • record_empty_state_view() (if no bookmarks)
```

#### Event Handler Registration Flow

```
APPLICATION STARTUP
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ MainContainer._setup_event_handlers()                              │
│                                                                     │
│  1. Create event handlers                                           │
│  2. Register with EventSubscriptionManager                          │
│  3. Map events to handlers                                          │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ EventSubscriptionManager Registration                               │
│                                                                     │
│  BookmarkAddedEvent → [BookmarkAddedEventHandler]                  │
│  BookmarkRemovedEvent → [BookmarkRemovedEventHandler]              │
│  BookmarksViewedEvent → [BookmarksViewedEventHandler]              │
│                                                                     │
│  (Future events can be added here)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

#### Error Handling in Event Flow

```
EVENT HANDLER FAILURE
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ BookmarkAddedEventHandler                                           │
│  try:                                                               │
│    await analytics_repository.record_activity(...)                 │
│  except Exception as e:                                             │
│    logger.error(f"Failed to handle event: {e}")                    │
│    # Error is logged but NOT propagated                             │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Other handlers continue to run
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ NotificationEventHandler                                            │
│  • Runs independently                                               │
│  • Failure in BookmarkAddedEventHandler doesn't affect this        │
│  • Resilient event handling                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## 🎨 Domain Model Design

### Bookmark Entity

```python
@dataclass
class Bookmark:
    """Domain entity with business rules and validation."""
    id: int
    user_id: int
    question_id: int
    notes: str | None
    created_at: datetime

    def __post_init__(self):
        """Enforce business invariants."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")
        if self.notes and len(self.notes) > 1000:
            raise ValueError("Notes cannot exceed 1000 characters")

    def has_notes(self) -> bool:
        """Domain behavior."""
        return self.notes is not None and self.notes.strip() != ""

    def age_in_days(self) -> int:
        """Calculate age of bookmark in days."""
        now = datetime.now(UTC)
        if self.created_at.tzinfo is None:
            # Handle naive datetime (from database)
            created_utc = self.created_at.replace(tzinfo=UTC)
        else:
            created_utc = self.created_at
        
        delta = now - created_utc
        return delta.days
    
    def is_recent(self, days: int = 7) -> bool:
        """Check if bookmark was created within specified days."""
        return self.age_in_days() <= days
```

**Key Domain Patterns**:

- **Validation in Constructor**: Business rules enforced at creation
- **Domain Methods**: Behavior co-located with data
- **Immutable by Design**: Dataclass with validation
- **Self-Documenting**: Clear method names expressing business concepts

### BookmarkCollection Value Object

The `BookmarkCollection` value object provides sophisticated collection management with built-in business logic for working with multiple bookmarks.

```python
@dataclass
class BookmarkCollection:
    """Value object representing a collection of bookmarks with business logic."""
    user_id: int
    bookmarks: list[Bookmark] = field(default_factory=list)
    total_count: int = 0
    
    def __post_init__(self):
        """Validate collection and set defaults."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        
        # Auto-set total_count if not provided
        if self.total_count == 0 and self.bookmarks:
            self.total_count = len(self.bookmarks)
    
    @property
    def question_ids(self) -> list[int]:
        """Get list of question IDs in the collection."""
        return [bookmark.question_id for bookmark in self.bookmarks]
    
    @property
    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self.bookmarks) == 0
    
    @property
    def bookmark_count(self) -> int:
        """Get number of bookmarks in collection."""
        return len(self.bookmarks)
    
    def contains_question(self, question_id: int) -> bool:
        """Check if a specific question is bookmarked."""
        return question_id in self.question_ids
    
    def get_bookmark_by_question_id(self, question_id: int) -> Bookmark | None:
        """Get bookmark for a specific question."""
        for bookmark in self.bookmarks:
            if bookmark.question_id == question_id:
                return bookmark
        return None
    
    def get_recent_bookmarks(self, days: int = 7) -> list[Bookmark]:
        """Get bookmarks created within specified days."""
        return [bookmark for bookmark in self.bookmarks if bookmark.is_recent(days)]
    
    def get_bookmarks_with_notes(self) -> list[Bookmark]:
        """Get bookmarks that have notes."""
        return [bookmark for bookmark in self.bookmarks if bookmark.has_notes()]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive collection statistics."""
        if self.is_empty:
            return {
                "total_count": 0,
                "recent_count": 0,
                "with_notes_count": 0,
                "oldest_bookmark_age_days": 0,
                "newest_bookmark_age_days": 0,
                "average_age_days": 0,
            }
        
        recent_bookmarks = self.get_recent_bookmarks()
        with_notes_bookmarks = self.get_bookmarks_with_notes()
        ages = [bookmark.age_in_days() for bookmark in self.bookmarks]
        
        return {
            "total_count": self.bookmark_count,
            "recent_count": len(recent_bookmarks),
            "with_notes_count": len(with_notes_bookmarks),
            "oldest_bookmark_age_days": max(ages) if ages else 0,
            "newest_bookmark_age_days": min(ages) if ages else 0,
            "average_age_days": sum(ages) / len(ages) if ages else 0,
        }
    
    def sort_by_date(self, descending: bool = True) -> BookmarkCollection:
        """Return new collection sorted by creation date."""
        sorted_bookmarks = sorted(
            self.bookmarks, key=lambda b: b.created_at, reverse=descending
        )
        return BookmarkCollection(
            user_id=self.user_id,
            bookmarks=sorted_bookmarks,
            total_count=self.total_count,
        )
    
    def limit(self, count: int, offset: int = 0) -> BookmarkCollection:
        """Return new collection with pagination support."""
        limited_bookmarks = self.bookmarks[offset : offset + count]
        return BookmarkCollection(
            user_id=self.user_id,
            bookmarks=limited_bookmarks,
            total_count=self.total_count,
        )
```

**BookmarkCollection Patterns**:
- **Rich Value Object**: Encapsulates collection behavior and business logic
- **Immutable Operations**: Methods return new instances rather than modifying state
- **Built-in Analytics**: Provides statistics and metrics out of the box
- **Pagination Support**: Native support for limiting and offsetting results
- **Query Methods**: Convenient methods for filtering and searching
- **Fluent Interface**: Methods can be chained for complex operations

**Usage in Query Handlers**:
```python
class GetBookmarksQueryHandler:
    async def handle(self, query: GetBookmarksQuery) -> GetBookmarksQueryResult:
        # Repository returns BookmarkCollection
        collection = await self.bookmark_repository.get_bookmarks(
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset
        )
        
        # Use collection methods for business logic
        if query.sort_by_date:
            collection = collection.sort_by_date(descending=query.sort_order == "desc")
        
        if query.recent_only:
            recent_bookmarks = collection.get_recent_bookmarks(days=7)
            collection = BookmarkCollection(
                user_id=query.user_id,
                bookmarks=recent_bookmarks,
                total_count=collection.total_count
            )
        
        return GetBookmarksQueryResult.success_result(collection)
```

### Repository Interface

```python
class BookmarkRepository(ABC):
    """Interface owned by domain layer."""

    @abstractmethod
    async def add_bookmark(self, user_id: int, question_id: int, notes: str | None) -> Bookmark:
        """Add a bookmark with business validation."""
        pass

    @abstractmethod
    async def get_bookmarks(self, user_id: int, limit: int = 20, offset: int = 0) -> BookmarkCollection:
        """Get user's bookmarks with pagination."""
        pass

    @abstractmethod
    async def remove_bookmark(self, user_id: int, question_id: int) -> bool:
        """Remove a bookmark."""
        pass

    @abstractmethod
    async def get_bookmark_by_question(self, user_id: int, question_id: int) -> Bookmark | None:
        """Check if question is bookmarked."""
        pass
    
    @abstractmethod
    async def update_bookmark_notes(self, user_id: int, question_id: int, notes: str | None) -> bool:
        """Update notes for an existing bookmark."""
        pass
```

**Repository Interface Principles**:

- **Domain-Centric API**: Methods express business operations
- **Abstract Base Class**: Enforces implementation contracts
- **Business Language**: Method names use domain terminology
- **Error Handling**: Raises domain exceptions for business rule violations

## 🎯 Command Implementation

### Command Structure

```python
@dataclass
class AddBookmarkCommand:
    """Command with validation and clear intent."""
    user_id: int
    question_id: int
    notes: str | None = None

    def __post_init__(self):
        """Validate command data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")

@dataclass
class AddBookmarkCommandResult:
    """Structured result with success/failure information."""
    success: bool
    bookmark_id: int | None = None
    error_message: str | None = None
    
    @classmethod
    def success_result(cls, bookmark_id: int) -> AddBookmarkCommandResult:
        """Create successful result using factory method."""
        return cls(success=True, bookmark_id=bookmark_id)
    
    @classmethod
    def error_result(cls, message: str) -> AddBookmarkCommandResult:
        """Create error result using factory method."""
        return cls(success=False, error_message=message)
```

### Command Handler

```python
class AddBookmarkCommandHandler:
    """Thin application layer coordinator."""

    def __init__(self, bookmark_repository: BookmarkRepository, event_bus: EventBusInterface):
        self.bookmark_repository = bookmark_repository
        self.event_bus = event_bus

    async def handle(self, command: AddBookmarkCommand) -> AddBookmarkCommandResult:
        """Handle command with proper error handling."""
        try:
            # Delegate to repository (domain logic)
            bookmark = await self.bookmark_repository.add_bookmark(
                user_id=command.user_id,
                question_id=command.question_id,
                notes=command.notes
            )

            # Publish domain event
            event = BookmarkAddedEvent(
                user_id=command.user_id,
                question_id=command.question_id,
                bookmark_id=bookmark.id,
                notes=command.notes
            )
            await self.event_bus.publish(event)

            return AddBookmarkCommandResult.success_result(bookmark.id)

        except RepositoryError as e:
            return AddBookmarkCommandResult.error_result(str(e))
```

**Command Handler Patterns**:

- **Single Responsibility**: Each handler handles one command type
- **Dependency Injection**: Repository and event bus injected
- **Error Handling**: Converts exceptions to result objects
- **Event Publishing**: Publishes domain events for side effects

### UpdateBookmarkNotesCommand

The `UpdateBookmarkNotesCommand` allows users to modify notes on existing bookmarks.

```python
@dataclass
class UpdateBookmarkNotesCommand:
    """Command to update notes on an existing bookmark."""
    user_id: int
    question_id: int
    notes: str | None
    
    def __post_init__(self):
        """Validate command data."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.question_id <= 0:
            raise ValueError("Question ID must be positive")

@dataclass
class UpdateBookmarkNotesCommandResult:
    """Result of updating bookmark notes."""
    success: bool
    error_message: str | None = None
    
    @classmethod
    def success_result(cls) -> UpdateBookmarkNotesCommandResult:
        """Create successful result."""
        return cls(success=True)
    
    @classmethod
    def error_result(cls, message: str) -> UpdateBookmarkNotesCommandResult:
        """Create error result."""
        return cls(success=False, error_message=message)

class UpdateBookmarkNotesCommandHandler:
    """Handler for updating bookmark notes."""
    
    def __init__(self, bookmark_repository: BookmarkRepository, event_bus: EventBusInterface):
        self.bookmark_repository = bookmark_repository
        self.event_bus = event_bus
    
    async def handle(self, command: UpdateBookmarkNotesCommand) -> UpdateBookmarkNotesCommandResult:
        """Handle update bookmark notes command."""
        try:
            # Check if bookmark exists
            existing_bookmark = await self.bookmark_repository.get_bookmark_by_question(
                user_id=command.user_id,
                question_id=command.question_id
            )
            
            if not existing_bookmark:
                return UpdateBookmarkNotesCommandResult.error_result(
                    "Bookmark not found"
                )
            
            # Update notes via repository
            updated_bookmark = await self.bookmark_repository.update_bookmark_notes(
                user_id=command.user_id,
                question_id=command.question_id,
                notes=command.notes
            )
            
            # Publish domain event (if implemented)
            # event = BookmarkNotesUpdatedEvent(
            #     user_id=command.user_id,
            #     question_id=command.question_id,
            #     bookmark_id=updated_bookmark.id,
            #     old_notes=existing_bookmark.notes,
            #     new_notes=command.notes
            # )
            # await self.event_bus.publish(event)
            
            return UpdateBookmarkNotesCommandResult.success_result()
            
        except RepositoryError as e:
            return UpdateBookmarkNotesCommandResult.error_result(str(e))
        except Exception as e:
            return UpdateBookmarkNotesCommandResult.error_result(f"Unexpected error: {e}")
```

**Update Command Patterns**:
- **Existence Check**: Verifies bookmark exists before updating
- **Repository Method**: Uses dedicated update method for notes
- **Event Publishing**: Ready for future event implementation
- **Error Handling**: Specific error for non-existent bookmarks

### Factory Methods Pattern

All command and query result classes use the factory methods pattern for creating instances, improving code readability and reducing boilerplate.

```python
# ✅ CORRECT: Using factory methods
class AddBookmarkCommandHandler:
    async def handle(self, command: AddBookmarkCommand) -> AddBookmarkCommandResult:
        try:
            bookmark = await self.bookmark_repository.add_bookmark(...)
            return AddBookmarkCommandResult.success_result(bookmark.id)
        except RepositoryError as e:
            return AddBookmarkCommandResult.error_result(str(e))

# ❌ VERBOSE: Direct instantiation
class AddBookmarkCommandHandler:
    async def handle(self, command: AddBookmarkCommand) -> AddBookmarkCommandResult:
        try:
            bookmark = await self.bookmark_repository.add_bookmark(...)
            return AddBookmarkCommandResult(
                success=True,
                bookmark_id=bookmark.id,
                error_message=None
            )
        except RepositoryError as e:
            return AddBookmarkCommandResult(
                success=False,
                bookmark_id=None,
                error_message=str(e)
            )
```

**Factory Method Benefits**:
- **Cleaner Code**: Less repetitive parameter passing
- **Type Safety**: Factory methods ensure correct parameter combinations
- **Consistency**: Standardized result creation across all handlers
- **Maintainability**: Changes to result structure only need updates in factory methods

## 📊 Query Implementation

### Query Structure

```python
@dataclass
class GetBookmarksQuery:
    """Query with pagination and filtering options."""
    user_id: int
    limit: int = 20
    offset: int = 0
    sort_by: str = "created_at"
    sort_order: str = "desc"

    def __post_init__(self):
        """Validate query parameters."""
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")
        if self.limit <= 0 or self.limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if self.offset < 0:
            raise ValueError("Offset must be non-negative")
```

### Query Handler

```python
class GetBookmarksQueryHandler:
    """Query handler with direct repository access."""

    def __init__(self, bookmark_repository: BookmarkRepository):
        self.bookmark_repository = bookmark_repository

    async def handle(self, query: GetBookmarksQuery) -> GetBookmarksQueryResult:
        """Handle query with optimized read path."""
        try:
            # Direct repository access (CQRS read side)
            bookmarks = await self.bookmark_repository.get_bookmarks(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset
            )

            return GetBookmarksQueryResult(
                success=True,
                bookmarks=bookmarks,
                total_count=len(bookmarks)
            )

        except RepositoryError as e:
            return GetBookmarksQueryResult(
                success=False,
                error_message=str(e)
            )
```

**Query Handler Patterns**:

- **Direct Repository Access**: Bypasses domain layer for read performance
- **Optimized for Reads**: Tailored for specific UI requirements
- **Pagination Support**: Handles large result sets efficiently
- **Error Handling**: Graceful failure with error messages

## 🔔 Event-Driven Architecture

### Event System Overview

The bookmark feature demonstrates a complete event-driven architecture where actions trigger events that enable cross-context communication. Here's how the event system works:

#### All Bookmark Events

```
📝 BOOKMARK LIFECYCLE EVENTS
├── BookmarkAddedEvent
│   ├── Triggered by: AddBookmarkCommandHandler
│   ├── Handled by: BookmarkAddedEventHandler
│   └── Side effects: Analytics, metrics, notifications
│
├── BookmarkRemovedEvent
│   ├── Triggered by: RemoveBookmarkCommandHandler
│   ├── Handled by: BookmarkRemovedEventHandler
│   └── Side effects: Analytics cleanup, metrics update
│
├── BookmarksViewedEvent
│   ├── Triggered by: GetBookmarksQueryHandler
│   ├── Handled by: BookmarksViewedEventHandler
│   └── Side effects: Usage tracking, engagement metrics
│
└── BookmarkNotesUpdatedEvent (future)
    ├── Triggered by: UpdateBookmarkNotesCommandHandler
    ├── Handled by: BookmarkNotesUpdatedEventHandler
    └── Side effects: Search index update, analytics
```

#### Event Flow Timing

```
USER ACTION                   IMMEDIATE RESPONSE              ASYNC SIDE EFFECTS
    │                              │                              │
    ↓                              ↓                              ↓
┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│ Add         │              │ UI Updates  │              │ Analytics   │
│ Bookmark    │─────────────→│ Bookmark    │─────────────→│ Recording   │
│ Button      │              │ Button      │              │ (async)     │
│ Clicked     │              │ State       │              │             │
└─────────────┘              └─────────────┘              └─────────────┘
      │                            │                              │
      │                            │                              ↓
      │                            │                    ┌─────────────┐
      │                            │                    │ User        │
      │                            │                    │ Engagement  │
      │                            │                    │ Metrics     │
      │                            │                    │ Update      │
      │                            │                    └─────────────┘
      │                            │                              │
      │                            │                              ↓
      │                            │                    ┌─────────────┐
      │                            │                    │ Question    │
      │                            │                    │ Popularity  │
      │                            │                    │ Tracking    │
      │                            │                    └─────────────┘
      │                            │
      ↓                            ↓
┌─────────────┐              ┌─────────────┐
│ Command     │              │ Command     │
│ Executed    │              │ Result      │
│ (sync)      │              │ Returned    │
│             │              │ (sync)      │
└─────────────┘              └─────────────┘
      │                            │
      ↓                            ↓
┌─────────────┐              ┌─────────────┐
│ Domain      │              │ UI State    │
│ Event       │              │ Updated     │
│ Published   │              │ (reactive)  │
│ (async)     │              │             │
└─────────────┘              └─────────────┘
```

#### Event Handler Dependencies

```
EVENT HANDLER DEPENDENCY GRAPH

BookmarkAddedEvent
├── BookmarkAddedEventHandler
│   ├── Depends on: AnalyticsRepository
│   ├── Updates: bookmark_activities table
│   ├── Updates: user_engagement_metrics table
│   └── Updates: question_bookmark_counts table
│
├── NotificationEventHandler (future)
│   ├── Depends on: NotificationService
│   ├── Updates: user_notifications table
│   └── Side effect: Email/push notification sent
│
└── SyncEventHandler (future)
    ├── Depends on: ExternalSyncService
    ├── Updates: sync_status table
    └── Side effect: Bookmark synced to cloud

BookmarkRemovedEvent
├── BookmarkRemovedEventHandler
│   ├── Depends on: AnalyticsRepository
│   ├── Updates: bookmark_activities table (removal record)
│   ├── Updates: user_engagement_metrics table
│   └── Updates: question_bookmark_counts table (decrement)
│
└── CleanupEventHandler (future)
    ├── Depends on: CacheService
    ├── Side effect: Remove from cache
    └── Side effect: Clean up related data

BookmarksViewedEvent
└── BookmarksViewedEventHandler
    ├── Depends on: AnalyticsRepository
    ├── Updates: bookmark_activities table
    ├── Updates: feature_usage table
    └── Conditional: practice_sessions table (if practice mode)
```

#### Event Processing Pipeline

```
EVENT PROCESSING PIPELINE

1. EVENT PUBLICATION
   ┌─────────────────────────────────────────────────────────────────┐
   │ Command Handler                                                 │
   │ await event_bus.publish(BookmarkAddedEvent(...))                │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
2. EVENT DISTRIBUTION
   ┌─────────────────────────────────────────────────────────────────┐
   │ EventBus                                                        │
   │ • Validates event type                                          │
   │ • Finds registered handlers                                     │
   │ • Creates async tasks for each handler                          │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
3. PARALLEL HANDLER EXECUTION
   ┌─────────────────────────────────────────────────────────────────┐
   │ asyncio.gather()                                                │
   │                                                                 │
   │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
   │ │ Handler 1       │ │ Handler 2       │ │ Handler 3       │     │
   │ │ (Analytics)     │ │ (Notifications) │ │ (Sync)          │     │
   │ │                 │ │                 │ │                 │     │
   │ │ Success: ✓      │ │ Success: ✓      │ │ Failure: ✗      │     │
   │ └─────────────────┘ └─────────────────┘ └─────────────────┘     │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
4. ERROR HANDLING & LOGGING
   ┌─────────────────────────────────────────────────────────────────┐
   │ Individual Handler Error Handling                               │
   │ • Failed handlers log errors                                    │
   │ • Successful handlers complete normally                         │
   │ • No handler failure affects others                             │
   │ • Original command success is not affected                      │
   └─────────────────────────────────────────────────────────────────┘
```

### Domain Events

**Complete Event Definitions**:

```python
from datetime import datetime
from uuid import uuid4

@dataclass
class BookmarkAddedEvent(DomainEvent):
    """Event published when a user bookmarks a question.
    
    This event enables cross-context communication for analytics,
    notifications, and sync operations.
    """
    user_id: int
    question_id: int
    bookmark_id: int
    notes: str | None = None
    
    # Inherited from DomainEvent base class:
    # event_id: str (auto-generated UUID)
    # occurred_at: datetime (auto-generated timestamp)

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()

@dataclass
class BookmarkRemovedEvent(DomainEvent):
    """Event published when a user removes a bookmark.
    
    Contains optional bookmark_id for cases where bookmark wasn't found.
    """
    user_id: int
    question_id: int
    bookmark_id: int | None = None  # May be None if bookmark wasn't found
    
    # Inherited from DomainEvent base class:
    # event_id: str (auto-generated UUID)
    # occurred_at: datetime (auto-generated timestamp)

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()

@dataclass
class BookmarksViewedEvent(DomainEvent):
    """Event published when a user views their bookmarks collection."""
    user_id: int
    bookmark_count: int
    view_type: str  # 'list', 'practice', 'manage'
    
    # Inherited from DomainEvent base class:
    # event_id: str (auto-generated UUID)
    # occurred_at: datetime (auto-generated timestamp)

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()

@dataclass
class BookmarkNotesUpdatedEvent(DomainEvent):
    """Event published when bookmark notes are updated (future implementation)."""
    user_id: int
    question_id: int
    bookmark_id: int
    old_notes: str | None
    new_notes: str | None
    
    # Inherited from DomainEvent base class:
    # event_id: str (auto-generated UUID)
    # occurred_at: datetime (auto-generated timestamp)

    def __post_init__(self) -> None:
        """Initialize parent DomainEvent fields."""
        super().__init__()
```

**Event Metadata Usage**:

```python
# Events automatically include metadata for tracking
event = BookmarkAddedEvent(
    user_id=1,
    question_id=42,
    bookmark_id=123,
    notes="Important concept"
)

# Metadata available for handlers:
print(f"Event ID: {event.event_id}")           # UUID4 string
print(f"Occurred at: {event.occurred_at}")     # UTC timestamp
print(f"Event name: {event.event_name}")       # "BookmarkAddedEvent"
```

### Event Handlers

**Core Event Handler Implementation**:

```python
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

class BookmarkAddedEventHandler:
    """Handle bookmark added events for analytics and cross-context updates."""

    def __init__(self, analytics_repository: AnalyticsRepository):
        self.analytics_repository = analytics_repository

    async def handle(self, event: BookmarkAddedEvent) -> None:
        """Handle bookmark added event with conditional logic."""
        try:
            # Always record basic activity
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                activity_type="bookmark_added",
                metadata={
                    "bookmark_id": event.bookmark_id,
                    "notes": event.notes,
                    "timestamp": event.occurred_at,
                    "event_id": event.event_id,
                    "has_notes": event.notes is not None and len(event.notes.strip()) > 0
                }
            )

            # Conditional processing based on event data
            if event.notes and len(event.notes.strip()) > 0:
                # Special handling for bookmarks with notes
                await self._handle_bookmark_with_notes(event)
            
            # Update user engagement metrics
            await self.analytics_repository.update_user_engagement_metrics(
                user_id=event.user_id,
                activity_type="bookmark_created",
                timestamp=event.occurred_at
            )

            # Question popularity tracking
            await self.analytics_repository.increment_question_bookmark_count(
                question_id=event.question_id
            )

            logger.debug(f"Successfully processed BookmarkAddedEvent {event.event_id}")

        except Exception as e:
            # Resilient error handling - log but don't propagate
            logger.error(
                f"Failed to handle bookmark added event {event.event_id}: {e}",
                extra={
                    "event_id": event.event_id,
                    "user_id": event.user_id,
                    "question_id": event.question_id,
                    "error_type": type(e).__name__
                }
            )

    async def _handle_bookmark_with_notes(self, event: BookmarkAddedEvent) -> None:
        """Special processing for bookmarks that include notes."""
        try:
            # Update note-specific analytics
            await self.analytics_repository.record_note_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                note_content=event.notes,
                activity_type="note_created_with_bookmark"
            )
            
            # Future: Could trigger note indexing for search
            logger.debug(f"Processed bookmark with notes for question {event.question_id}")
            
        except Exception as e:
            logger.warning(f"Failed to handle bookmark notes: {e}")


class BookmarkRemovedEventHandler:
    """Handle bookmark removed events for cleanup and analytics."""

    def __init__(self, analytics_repository: AnalyticsRepository):
        self.analytics_repository = analytics_repository

    async def handle(self, event: BookmarkRemovedEvent) -> None:
        """Handle bookmark removed event with error scenarios."""
        try:
            # Handle case where bookmark_id might be None
            if event.bookmark_id is None:
                logger.warning(
                    f"BookmarkRemovedEvent without bookmark_id for user {event.user_id}, "
                    f"question {event.question_id}"
                )
                # Still record the attempt for analytics
                await self._record_removal_attempt(event)
                return

            # Record removal activity
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                activity_type="bookmark_removed",
                metadata={
                    "bookmark_id": event.bookmark_id,
                    "timestamp": event.occurred_at,
                    "event_id": event.event_id
                }
            )

            # Update engagement metrics
            await self.analytics_repository.update_user_engagement_metrics(
                user_id=event.user_id,
                activity_type="bookmark_removed",
                timestamp=event.occurred_at
            )

            # Decrement question popularity
            await self.analytics_repository.decrement_question_bookmark_count(
                question_id=event.question_id
            )

            logger.debug(f"Successfully processed BookmarkRemovedEvent {event.event_id}")

        except Exception as e:
            logger.error(
                f"Failed to handle bookmark removed event {event.event_id}: {e}",
                extra={
                    "event_id": event.event_id,
                    "user_id": event.user_id,
                    "question_id": event.question_id,
                    "bookmark_id": event.bookmark_id
                }
            )

    async def _record_removal_attempt(self, event: BookmarkRemovedEvent) -> None:
        """Record failed removal attempts for debugging."""
        try:
            await self.analytics_repository.record_bookmark_activity(
                user_id=event.user_id,
                question_id=event.question_id,
                activity_type="bookmark_removal_failed",
                metadata={
                    "reason": "bookmark_not_found",
                    "timestamp": event.occurred_at,
                    "event_id": event.event_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to record removal attempt: {e}")
```

**Advanced Event Handler Patterns**:

```python
class ConditionalEventHandler:
    """Example of conditional event processing patterns."""
    
    async def handle(self, event: BookmarkAddedEvent) -> None:
        """Demonstrate conditional event handling patterns."""
        
        # 1. Conditional processing based on event data
        if event.notes:
            await self.process_bookmark_with_notes(event)
        else:
            await self.process_bookmark_without_notes(event)
        
        # 2. Conditional processing based on user behavior
        user_bookmark_count = await self.get_user_bookmark_count(event.user_id)
        if user_bookmark_count == 1:
            await self.handle_first_bookmark(event)
        elif user_bookmark_count % 10 == 0:
            await self.handle_milestone_bookmark(event)
        
        # 3. Conditional processing based on question properties
        question = await self.get_question(event.question_id)
        if question.difficulty == "hard":
            await self.handle_difficult_question_bookmark(event)
        
        # 4. Time-based conditional processing
        if self.is_peak_study_time(event.occurred_at):
            await self.update_peak_time_metrics(event)

class RetryableEventHandler:
    """Example of event handler with retry logic."""
    
    async def handle(self, event: BookmarkAddedEvent) -> None:
        """Handle event with exponential backoff retry."""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                await self.process_event(event)
                return  # Success
                
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to process event after {max_retries} retries: {e}")
                    await self.handle_permanent_failure(event, e)
                    return
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Event processing failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
```

**Event Handler Error Scenarios**:

1. **Repository Failures**: Database connection issues, constraint violations
2. **Network Failures**: External service timeouts, API rate limits  
3. **Data Validation**: Invalid event data, missing required fields
4. **Resource Constraints**: Memory limits, disk space issues
5. **Concurrent Modifications**: Race conditions, optimistic locking failures

**Event Handler Logging Strategy**:

```python
# Structured logging for better observability
logger.info(
    "Processing bookmark event",
    extra={
        "event_type": "BookmarkAddedEvent",
        "event_id": event.event_id,
        "user_id": event.user_id,
        "question_id": event.question_id,
        "has_notes": bool(event.notes),
        "processing_time_ms": processing_time
    }
)
```

**Event Handler Testing Patterns**:

```python
class MockAnalyticsRepository:
    """Mock for testing event handlers."""
    
    def __init__(self):
        self.activities = []
        self.metrics = []
    
    async def record_bookmark_activity(self, **kwargs):
        self.activities.append(kwargs)
    
    async def update_user_engagement_metrics(self, **kwargs):
        self.metrics.append(kwargs)

# Test conditional event handling
async def test_bookmark_with_notes_handling():
    mock_repo = MockAnalyticsRepository()
    handler = BookmarkAddedEventHandler(mock_repo)
    
    event = BookmarkAddedEvent(
        user_id=1,
        question_id=42,
        bookmark_id=123,
        notes="Important concept to review"
    )
    
    await handler.handle(event)
    
    # Verify both regular and note-specific activities were recorded
    assert len(mock_repo.activities) == 2  # One regular, one note-specific
    assert any(activity["activity_type"] == "bookmark_added" for activity in mock_repo.activities)
    assert any(activity["activity_type"] == "note_created_with_bookmark" for activity in mock_repo.activities)
```

**Event Handler Patterns**:

- **Resilient Error Handling**: Failures don't affect other handlers or core operations
- **Conditional Processing**: Different handling based on event data and context
- **Cross-Context Updates**: Updates analytics, metrics, and other bounded contexts
- **Asynchronous Processing**: Non-blocking event handling with proper error isolation
- **Structured Logging**: Rich context for debugging and monitoring
- **Graceful Degradation**: Partial failures don't prevent core functionality

## 🏗️ Infrastructure Implementation

### Thread Pool Pattern for Async/Sync Bridging

The bookmark repository demonstrates a sophisticated async/sync bridging pattern that enables async application code to work seamlessly with blocking SQLite operations.

**Core Thread Pool Implementation**:

```python
import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')

class BookmarkRepositoryImpl(BookmarkRepository):
    """SQLite implementation with async/sync bridging."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager."""
        self.db = db_manager

    async def _run_in_executor[T](self, func: Callable[[], T]) -> T:
        """Run a blocking database operation in thread pool.
        
        This is the core pattern that bridges async/sync worlds:
        1. Takes a blocking function (Callable[[], T])
        2. Executes it in a thread pool to avoid blocking the event loop
        3. Returns the result asynchronously
        
        Benefits:
        - Non-blocking: Event loop remains responsive
        - Type-safe: Preserves function return types
        - Error-safe: Exceptions are properly propagated
        - Performance: Reuses thread pool for efficiency
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)
```

**Pattern Application Examples**:

```python
    async def add_bookmark(
        self, user_id: int, question_id: int, notes: str | None = None
    ) -> Bookmark:
        """Add bookmark using thread pool pattern."""

        def _add_bookmark() -> Bookmark:
            """Blocking database operation (runs in thread pool)."""
            try:
                with self.db.get_session() as session:
                    # Check for existing bookmark
                    existing_query = select(BookmarkModel).where(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.question_id == question_id,
                    )
                    existing_result = session.execute(existing_query)
                    existing_bookmark = existing_result.scalar_one_or_none()

                    if existing_bookmark:
                        raise RepositoryError(
                            f"Bookmark already exists for user {user_id} and question {question_id}",
                            "DUPLICATE_BOOKMARK",
                        )

                    # Create new bookmark
                    bookmark_model = BookmarkModel(
                        user_id=user_id, 
                        question_id=question_id, 
                        notes=notes
                    )
                    session.add(bookmark_model)
                    session.commit()

                    return self._model_to_entity(bookmark_model)

            except RepositoryError:
                raise  # Re-raise domain errors
            except IntegrityError as e:
                raise RepositoryError(
                    f"Integrity constraint violation: {e}", "INTEGRITY_ERROR"
                ) from e
            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        # Execute blocking operation in thread pool
        return await self._run_in_executor(_add_bookmark)

    async def get_bookmarks(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> BookmarkCollection:
        """Get bookmarks with pagination using thread pool."""

        def _get_bookmarks() -> BookmarkCollection:
            """Blocking database operation for complex queries."""
            try:
                with self.db.get_session() as session:
                    # Build query for bookmarks
                    query = (
                        select(BookmarkModel)
                        .where(BookmarkModel.user_id == user_id)
                        .order_by(BookmarkModel.created_at.desc())
                    )

                    # Apply pagination
                    if limit is not None:
                        query = query.limit(limit)
                    if offset > 0:
                        query = query.offset(offset)

                    # Execute query
                    result = session.execute(query)
                    bookmark_models = result.scalars().all()

                    # Get total count (separate query)
                    count_query = select(func.count(BookmarkModel.id)).where(
                        BookmarkModel.user_id == user_id
                    )
                    count_result = session.execute(count_query)
                    total_count = count_result.scalar() or 0

                    # Convert to entities
                    bookmarks = [
                        self._model_to_entity(model) for model in bookmark_models
                    ]

                    return BookmarkCollection(
                        user_id=user_id, 
                        bookmarks=bookmarks, 
                        total_count=total_count
                    )

            except SQLAlchemyError as e:
                raise RepositoryError(f"Database error: {e}", "DATABASE_ERROR") from e
            except Exception as e:
                raise RepositoryError(f"Unexpected error: {e}", "UNKNOWN_ERROR") from e

        return await self._run_in_executor(_get_bookmarks)
```

**Model Conversion Patterns**:

```python
    def _model_to_entity(self, model: BookmarkModel) -> Bookmark:
        """Convert SQLAlchemy model to domain entity.
        
        Key responsibilities:
        1. Transform database types to domain types
        2. Handle timezone conversion for datetime fields
        3. Validate data integrity during conversion
        4. Isolate domain from infrastructure concerns
        """
        # Handle timezone for created_at (SQLite stores naive datetime)
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        return Bookmark(
            id=model.id,
            user_id=model.user_id,
            question_id=model.question_id,
            notes=model.notes,
            created_at=created_at,
        )
```

### Advanced Thread Pool Patterns

**Performance Optimization Patterns**:

```python
class OptimizedBookmarkRepository(BookmarkRepository):
    """Advanced patterns for high-performance async/sync bridging."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        # Custom thread pool for database operations
        self.db_executor = ThreadPoolExecutor(
            max_workers=10,  # Adjust based on database connection pool
            thread_name_prefix="bookmark_db"
        )
    
    async def _run_in_db_executor[T](self, func: Callable[[], T]) -> T:
        """Run database operation in dedicated thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.db_executor, func)
    
    async def batch_get_bookmarks(
        self, user_ids: list[int]
    ) -> dict[int, BookmarkCollection]:
        """Batch operation example using thread pool."""
        
        def _batch_get_bookmarks() -> dict[int, BookmarkCollection]:
            """Optimized batch query in single database session."""
            results = {}
            try:
                with self.db.get_session() as session:
                    # Single query for all users
                    query = (
                        select(BookmarkModel)
                        .where(BookmarkModel.user_id.in_(user_ids))
                        .order_by(BookmarkModel.user_id, BookmarkModel.created_at.desc())
                    )
                    
                    result = session.execute(query)
                    all_bookmarks = result.scalars().all()
                    
                    # Group by user_id
                    user_bookmarks = {}
                    for bookmark in all_bookmarks:
                        if bookmark.user_id not in user_bookmarks:
                            user_bookmarks[bookmark.user_id] = []
                        user_bookmarks[bookmark.user_id].append(bookmark)
                    
                    # Create collections
                    for user_id in user_ids:
                        user_models = user_bookmarks.get(user_id, [])
                        bookmarks = [self._model_to_entity(m) for m in user_models]
                        results[user_id] = BookmarkCollection(
                            user_id=user_id,
                            bookmarks=bookmarks,
                            total_count=len(bookmarks)
                        )
                    
                    return results
                    
            except SQLAlchemyError as e:
                raise RepositoryError(f"Batch query error: {e}", "DATABASE_ERROR") from e
        
        return await self._run_in_db_executor(_batch_get_bookmarks)
```

**Error Handling in Thread Pool Operations**:

```python
    async def resilient_bookmark_operation(self, user_id: int) -> BookmarkCollection:
        """Example of resilient error handling in thread pool operations."""
        
        def _get_with_retry() -> BookmarkCollection:
            """Blocking operation with built-in retry logic."""
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    with self.db.get_session() as session:
                        # Database operation here
                        query = select(BookmarkModel).where(BookmarkModel.user_id == user_id)
                        result = session.execute(query)
                        models = result.scalars().all()
                        
                        bookmarks = [self._model_to_entity(m) for m in models]
                        return BookmarkCollection(
                            user_id=user_id,
                            bookmarks=bookmarks,
                            total_count=len(bookmarks)
                        )
                        
                except (ConnectionError, SQLAlchemyError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                        continue
                    raise RepositoryError(
                        f"Failed after {max_retries} attempts: {e}", 
                        "RETRY_EXHAUSTED"
                    ) from e
            
            # Should never reach here
            raise RepositoryError(
                f"Unexpected retry failure: {last_error}", 
                "UNKNOWN_ERROR"
            )
        
        return await self._run_in_executor(_get_with_retry)
```

### Thread Pool Pattern Benefits

**Performance Benefits**:
1. **Non-blocking Event Loop**: Database operations don't block async code
2. **Concurrent Operations**: Multiple database operations can run simultaneously
3. **Resource Efficiency**: Thread pool reuses threads for multiple operations
4. **Scalability**: Can handle many concurrent requests without blocking

**Architectural Benefits**:
1. **Clean Async Interface**: Repository appears fully async to application layer
2. **Blocking Code Isolation**: SQLite blocking calls contained in thread functions
3. **Error Boundary**: Exceptions from blocking code are properly handled
4. **Type Safety**: Generic type parameters preserve function signatures

**Implementation Guidelines**:

```python
# ✅ CORRECT: Thread pool pattern
async def repository_method(self, params) -> ReturnType:
    def _blocking_operation() -> ReturnType:
        # All blocking database code here
        with self.db.get_session() as session:
            # SQLite operations
            return result
    
    return await self._run_in_executor(_blocking_operation)

# ❌ INCORRECT: Blocking the event loop
async def repository_method(self, params) -> ReturnType:
    # This blocks the entire event loop!
    with self.db.get_session() as session:
        # Direct blocking call in async context
        return result

# ❌ INCORRECT: Mixing async/sync incorrectly
async def repository_method(self, params) -> ReturnType:
    def _blocking_operation():
        # Missing proper error handling and type hints
        pass
    
    # Missing await - this returns a coroutine!
    return self._run_in_executor(_blocking_operation)
```

**Thread Pool Best Practices**:

1. **Separate Thread Functions**: Keep blocking operations in separate functions
2. **Proper Error Handling**: Translate infrastructure errors to domain errors
3. **Type Annotations**: Use generic type parameters for type safety
4. **Resource Management**: Use context managers for database sessions
5. **Connection Pooling**: Coordinate with database connection pool size
6. **Monitoring**: Log thread pool usage and performance metrics

**Infrastructure Patterns Summary**:

- **Async/Sync Bridge**: Thread pool pattern enables async interface with blocking SQLite
- **Model Conversion**: Clean separation between database and domain models  
- **Error Translation**: Infrastructure errors become domain-specific exceptions
- **Transaction Management**: Proper database session and transaction handling
- **Performance Optimization**: Batching, connection pooling, and retry logic
- **Type Safety**: Generic functions preserve compile-time type checking

## 📋 Testing Strategy

### Unit Testing

```python
class TestBookmarkDomain:
    """Test domain logic in isolation."""

    def test_bookmark_validation(self):
        """Test business rule validation."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            Bookmark(id=1, user_id=0, question_id=1, notes=None, created_at=datetime.now(UTC))

    def test_bookmark_has_notes(self):
        """Test domain behavior."""
        bookmark = Bookmark(id=1, user_id=1, question_id=1, notes="Test", created_at=datetime.now(UTC))
        assert bookmark.has_notes() is True

        bookmark_no_notes = Bookmark(id=1, user_id=1, question_id=1, notes=None, created_at=datetime.now(UTC))
        assert bookmark_no_notes.has_notes() is False

class TestBookmarkCommands:
    """Test command handlers."""

    @pytest.mark.asyncio
    async def test_add_bookmark_command_success(self):
        """Test successful bookmark addition."""
        mock_repository = AsyncMock(spec=BookmarkRepository)
        mock_event_bus = AsyncMock(spec=EventBusInterface)

        handler = AddBookmarkCommandHandler(mock_repository, mock_event_bus)
        command = AddBookmarkCommand(user_id=1, question_id=42, notes="Test")

        # Mock repository response
        mock_repository.add_bookmark.return_value = Bookmark(
            id=1, user_id=1, question_id=42, notes="Test", created_at=datetime.now(UTC)
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.bookmark_id == 1
        mock_event_bus.publish.assert_called_once()
```

### Integration Testing

```python
class TestBookmarkWorkflows:
    """Test complete bookmark workflows."""

    @pytest.mark.asyncio
    async def test_complete_bookmark_lifecycle(self):
        """Test add, query, and remove bookmark workflow."""
        # Setup
        user_id = 1
        question_id = 42

        # Add bookmark
        add_command = AddBookmarkCommand(user_id=user_id, question_id=question_id, notes="Test")
        add_result = await self.add_handler.handle(add_command)
        assert add_result.success is True

        # Query bookmarks
        get_query = GetBookmarksQuery(user_id=user_id)
        get_result = await self.get_handler.handle(get_query)
        assert get_result.success is True
        assert len(get_result.bookmarks) == 1

        # Remove bookmark
        remove_command = RemoveBookmarkCommand(user_id=user_id, question_id=question_id)
        remove_result = await self.remove_handler.handle(remove_command)
        assert remove_result.success is True
```

## 🔍 Common Architecture Patterns

### ✅ Correct Patterns

**Command Flow**:

```python
# ✅ CORRECT: Command → Handler → Repository → Domain Logic
class AddBookmarkCommandHandler:
    async def handle(self, command: AddBookmarkCommand):
        # Validate command
        # Call repository (domain logic)
        # Publish events
        # Return result
```

**Query Flow**:

```python
# ✅ CORRECT: Query → Handler → Repository → Direct Data Access
class GetBookmarksQueryHandler:
    async def handle(self, query: GetBookmarksQuery):
        # Direct repository access for performance
        # Format data for UI
        # Return result
```

**Event Flow**:

```python
# ✅ CORRECT: Domain Service → Event Bus → Event Handler
class BookmarkAddedEventHandler:
    async def handle(self, event: BookmarkAddedEvent):
        # Update analytics
        # Cross-context communication
        # Resilient error handling
```

### ❌ Anti-Patterns to Avoid

**Bypassing Application Layer**:

```python
# ❌ WRONG: UI directly calling repository
class BookmarkView:
    async def add_bookmark(self, question_id: int):
        # This bypasses validation and events!
        bookmark = await self.repository.add_bookmark(user_id=1, question_id=question_id)
```

**Business Logic in Application Layer**:

```python
# ❌ WRONG: Business logic in command handler
class AddBookmarkCommandHandler:
    async def handle(self, command: AddBookmarkCommand):
        # This is business logic!
        if command.notes and len(command.notes) > 1000:
            return AddBookmarkCommandResult(success=False, error_message="Notes too long")
```

**Missing Event Handlers**:

```python
# ❌ WRONG: Publishing events without handlers
await self.event_bus.publish(BookmarkAddedEvent(...))
# Nothing happens - no handler registered!
```

## 🎯 Key Takeaways

### Architecture Benefits Demonstrated

1. **Testability**: Each layer can be tested in isolation
2. **Maintainability**: Clear separation of concerns
3. **Scalability**: Easy to add new features and handlers
4. **Flexibility**: UI can change without affecting business logic
5. **Consistency**: Patterns repeated across all features

### CQRS/DDD Principles Applied

1. **Command Query Separation**: Different paths for reads and writes
2. **Domain-Driven Design**: Business logic in domain layer
3. **Event-Driven Architecture**: Loose coupling through events
4. **Dependency Inversion**: Domain defines interfaces
5. **Single Responsibility**: Each component has one job

### Best Practices Illustrated

1. **Rich Domain Models**: Entities with behavior and validation
2. **Thin Application Layer**: Coordinators without business logic
3. **Resilient Event Handling**: Failures don't cascade
4. **Proper Error Handling**: Domain exceptions converted to results
5. **Async/Sync Bridge**: Thread pools for blocking operations

## 🚀 Next Steps

When implementing new features, use this bookmark feature as a template:

1. **Start with Domain**: Define entities and repository interfaces
2. **Add Commands**: Implement write operations with validation
3. **Add Queries**: Implement read operations with optimization
4. **Add Events**: Enable cross-context communication
5. **Test Thoroughly**: Unit, integration, and architecture tests

This architecture ensures maintainable, testable, and scalable code that follows industry best practices for complex applications.
