# Developer Guide

This guide provides architecture guidelines and technical reference for developers working on the Integran project.

## 🏗️ Architecture Overview

Integran follows **Domain-Driven Design (DDD)** with **CQRS** patterns and **event-driven** communication for clean separation of concerns.

## 🏗️ CQRS Architecture Principles

Integran implements a clean CQRS architecture with strict layer separation and dependency inversion.

### Core Principles
1. **Domain-Driven Design**: Business logic in domain services with single responsibilities
2. **CQRS**: Separate command (write) and query (read) operations
3. **Event-Driven**: Async communication between bounded contexts
4. **Dependency Inversion**: Domain defines interfaces, infrastructure implements
5. **Local-First**: SQLite storage, no cloud dependencies

### Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  • UI Components (Terminal/Web/Mobile)                              │
│  • User Input Handling                                              │
│  • Display Results                                                  │
│  • NO Business Logic                                                │
│  • MUST use Application Commands/Queries ONLY                       │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Commands/Queries
┌─────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                            │
│  • Command Handlers (execute/handle methods)                        │
│  • Query Handlers (handle methods)                                  │
│  • Event Handlers (cross-context coordination)                      │
│  • Thin Coordinators (< 50 lines)                                   │
│  • NO Business Logic                                                │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Domain Services
┌─────────────────────────────────────────────────────────────────────┐
│                          DOMAIN LAYER                               │
│  • Business Logic (ALL business rules here)                         │
│  • Domain Services (call method)                                    │
│  • Domain Events (DomainEvent base class)                           │
│  • Repository Interfaces (owned by domain)                          │
│  • MUST NOT import from infrastructure                              │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓ Interface Implementation
┌─────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                           │
│  • Database Implementation (SQLite)                                 │
│  • Event Bus Implementation                                         │
│  • Repository Implementations                                       │
│  • External APIs                                                    │
│  • Configuration                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Bounded Contexts
- **Learning**: Spaced repetition scheduling, session management, progress tracking
- **Content**: Question management, multilingual answers, image processing  
- **Analytics**: Performance tracking, difficulty analysis, optimization
- **User**: User configuration, preferences, developer mode control

### Directory Structure

```
src/
├── domain/                        # Domain Layer - Business Logic
│   ├── learning/services/          # ScheduleCard, CompleteLearningSession
│   ├── content/services/           # GenerateAnswer, ProcessImage, BuildDataset
│   ├── analytics/services/         # Performance analysis, optimization
│   ├── user/services/              # User configuration, preferences
│   └── shared/                     # Base classes, events, interfaces
├── application/                    # Application Layer - Coordination
│   ├── commands/                   # Command handlers (write operations)
│   ├── queries/                    # Query handlers (read operations) 
│   ├── events/handlers/            # Cross-context event handling
│   └── workflows/                  # Complex workflow coordination
├── infrastructure/                 # Infrastructure Layer - Implementation
│   ├── database/                   # SQLite database operations
│   ├── messaging/                  # Event bus implementation
│   ├── repositories/               # Repository implementations
│   └── config/                     # Configuration and settings
└── presentation/                   # Presentation Layer - UI
    ├── terminal/                   # Terminal UI implementation
    └── cli/                        # Command-line interfaces
```

## 🔄 Data Flow Patterns

### CORRECT CQRS Data Flow

```
USER ACTION
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: UI Component                                          │
│  1. User clicks answer button                                       │
│  2. Calls Application Command Handler                               │
└─────────────────────────────────────────────────────────────────────┘
     │ command.execute() or command.handle()
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: Command Handler                                        │
│  1. Validates input                                                 │
│  2. Creates domain service request                                  │
│  3. Calls domain service                                            │
│  4. Returns result                                                  │
└─────────────────────────────────────────────────────────────────────┘
     │ domain_service.call(request)
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN: Domain Service                                              │
│  1. Applies business rules                                          │
│  2. Uses repository interfaces                                      │
│  3. Updates state                                                   │
│  4. Publishes domain events                                         │
└─────────────────────────────────────────────────────────────────────┘
     │ repository.save() + event_bus.publish()
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: Repositories + Event Bus                           │
│  1. Saves to database                                               │
│  2. Distributes events to handlers                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### ❌ PROBLEMATIC Patterns 

```
❌ WRONG: Presentation → Domain (Bypassing Application)
┌─────────────────┐    ┌─────────────────┐
│  Presentation   │───→│     Domain      │  
└─────────────────┘    └─────────────────┘
                                │
                                ↓
                       ┌─────────────────┐
                       │ Infrastructure  │
                       └─────────────────┘

❌ WRONG: Domain → Infrastructure (Direct Import)
┌─────────────────┐    ┌─────────────────┐
│     Domain      │───→│ Infrastructure  │  
└─────────────────┘    └─────────────────┘
   from src.infrastructure.messaging import EventBus

❌ WRONG: Missing CQRS Methods
┌─────────────────┐
│   Commands      │  Missing execute() or handle() methods
└─────────────────┘
┌─────────────────┐
│    Queries      │  Missing handle() methods  
└─────────────────┘
```

### ✅ CORRECT Patterns (Target Architecture)

```
✅ CORRECT: Full CQRS Flow
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Presentation   │───→│  Application    │───→│     Domain      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ↓
                                               ┌─────────────────┐
                                               │ Infrastructure  │
                                               └─────────────────┘

✅ CORRECT: Dependency Inversion
┌─────────────────┐    ┌─────────────────┐
│     Domain      │───→│   Interfaces    │  
└─────────────────┘    └─────────────────┘
                                ↑
                                │ implements
                       ┌─────────────────┐
                       │ Infrastructure  │
                       └─────────────────┘

✅ CORRECT: CQRS Methods
┌─────────────────┐
│   Commands      │  execute() or handle() methods ✓
└─────────────────┘
┌─────────────────┐
│    Queries      │  handle() methods ✓
└─────────────────┘
```

## 🔧 CQRS Implementation Guidelines

### Command Pattern Implementation

All commands must implement either `execute()` or `handle()` methods:

```python
@dataclass
class SaveUserSettingsCommand:
    """Command to save user settings."""
    user_id: int
    settings: dict[str, Any]

class SaveUserSettingsCommandHandler:
    """Command handler with proper CQRS pattern."""
    
    def __init__(self, user_repository: UserRepository, event_bus: EventBusInterface):
        self.save_settings_service = SaveUserSettings(event_bus, user_repository)
        
    async def handle(self, command: SaveUserSettingsCommand) -> SaveUserSettingsCommandResult:
        """Handle command using domain service."""
        request = SaveUserSettingsRequest(
            user_id=command.user_id,
            settings=command.settings
        )
        result = await self.save_settings_service.call(request)
        return SaveUserSettingsCommandResult(
            success=result.success,
            error_message=result.error_message
        )
```

### Query Pattern Implementation

All queries must implement `handle()` methods for read operations:

```python
@dataclass
class GetUserPreferencesQuery:
    """Query to get user preferences."""
    user_id: int

class GetUserPreferencesQueryHandler:
    """Query handler with direct database access."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        
    async def handle(self, query: GetUserPreferencesQuery) -> GetUserPreferencesResult:
        """Handle query with direct repository access."""
        user_settings = await self.user_repository.get_user_settings(query.user_id)
        return GetUserPreferencesResult(
            success=True,
            preferences=user_settings
        )
```

### Domain Event Implementation

Domain events must be defined in the domain layer, not infrastructure:

```python
# ✅ CORRECT: In src/domain/shared/events.py
@dataclass
class DomainEvent(ABC):
    """Base class for all domain events."""
    event_id: str
    occurred_at: datetime
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC)

# ✅ CORRECT: In src/domain/user/events/user_events.py  
@dataclass
class UserSettingsChangedEvent(DomainEvent):
    """Event published when user settings change."""
    user_id: int
    setting_key: str
    old_value: Any
    new_value: Any
```

### Repository Interface Pattern

Domain must own repository interfaces, infrastructure implements them:

```python
# ✅ CORRECT: In src/domain/shared/repositories.py
from abc import ABC, abstractmethod

class UserRepository(ABC):
    """User repository interface owned by domain."""
    
    @abstractmethod
    async def get_user_settings(self, user_id: int) -> UserSettings | None:
        """Get user settings by ID."""
        pass
        
    @abstractmethod
    async def save_user_settings(self, user_id: int, settings: dict) -> UserSettings:
        """Save user settings."""
        pass

# ✅ CORRECT: In src/infrastructure/repositories/user_repository.py
class UserRepositoryImpl(UserRepository):
    """User repository implementation."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def get_user_settings(self, user_id: int) -> UserSettings | None:
        """Implementation of interface method."""
        # Database implementation
        pass
```

## 📊 Data Overview

**Complete Dataset**: 460 questions with multilingual explanations (EN/DE/TR/UK/AR) and 92 images for visual questions.

**Data Location**: `data/final_dataset.json` (ready for use)

**Database**: SQLite with FSRS tables for local learning state

## 🗄️ Database Schema Overview

**Local SQLite Database** with FSRS tables for spaced repetition learning:

### Core Tables
- **`fsrs_cards`**: Individual learning states (difficulty, stability, retrievability)
- **`review_history`**: Complete review log with FSRS state transitions
- **`learning_sessions`**: Study session tracking and statistics
- **`questions`**: Question data with multilingual explanations
- **`leech_cards`**: Difficult question detection and management
- **`user_settings`**: User preferences and configuration
- **`algorithm_config`**: FSRS parameters and optimization settings

### Key Features
- **FSRS Algorithm**: Scientific spaced repetition with DSR memory model
- **Local-First**: All data stored locally, no cloud dependencies
- **Performance Optimized**: Indexes for fast question scheduling and analytics

## 🧠 FSRS Learning System

**Free Spaced Repetition Scheduler (FSRS)** - Scientific spaced repetition algorithm

### Core Features
- **DSR Memory Model**: Tracks Difficulty, Stability, Retrievability for each card
- **Adaptive Scheduling**: Personalizes review intervals based on performance
- **Leech Detection**: Identifies difficult questions needing special attention
- **Analytics**: Performance tracking and learning insights

### Learning States
- **New**: Never studied before
- **Learning**: Initial learning phase with short intervals
- **Review**: Successfully learned, scheduled for spaced review  
- **Relearning**: Previously learned but forgotten

**Implementation**: All FSRS logic is in the `ScheduleCard` domain service

## 🤖 PDF Question Extraction

### Overview

The application includes a sophisticated PDF extraction system using Google's Gemini AI to extract questions from the official BAMF PDF. This is a **developer-only feature** - end users never need to set this up.

### Environment Variables

These environment variables are **ONLY needed for developers** who want to extract questions from the PDF using AI. **End users don't need these** as the app comes with pre-extracted question data.

The application supports **two authentication methods** for Google Gemini AI:

#### Method 1: Vertex AI with Service Account (Recommended)
```bash
# Required variables
export USE_VERTEX_AI=true                           # Enable Vertex AI authentication (default)
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"  # Service account JSON file
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

#### Method 2: API Key (Legacy)
```bash
# Required variables  
export USE_VERTEX_AI=false                         # Disable Vertex AI, use API key instead
export GEMINI_API_KEY="your-gemini-api-key"        # Google AI API key
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

#### Required vs Optional Variables:

**Always Required:**
- `GCP_PROJECT_ID` - Your Google Cloud Project ID

**Required for Vertex AI (Method 1):**
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON file
- `USE_VERTEX_AI=true` (or omit, as this is the default)

**Required for API Key (Method 2):**
- `GEMINI_API_KEY` - Google AI Studio API key
- `USE_VERTEX_AI=false`

**Optional (have sensible defaults):**
- `GCP_REGION` - Defaults to "us-central1"
- `GEMINI_MODEL` - Defaults to "gemini-2.5-pro-preview-06-05"

### Important Notes

⚠️ **Cost Warning**: Using the Gemini API will incur charges on your Google Cloud account
- **Not Required**: The app works perfectly without these variables using pre-extracted data
- **For Developers Only**: Only needed if you want to re-extract questions from the PDF
- **One-Time Use**: Question extraction is typically done once during development
- **Vertex AI Recommended**: More secure and scalable than API keys

#### When You Need These Variables:
- ✅ You're a developer modifying the question extraction process
- ✅ You want to re-extract questions from a new PDF version
- ✅ You're contributing to the project's question database

#### When You DON'T Need These Variables:
- ❌ You're just using the app to study for the exam
- ❌ You're running the trainer for practice sessions
- ❌ You're a regular end user

The application automatically uses pre-extracted question data from `data/questions.json` and will never call external APIs during normal usage.

### Available Commands

#### Working Commands
```bash
# Setup and initialization
integran-setup                        # Database setup and initialization

# Dataset verification
python scripts/verify_dataset.py      # Verify final dataset integrity

# Development tools (requires API keys)
integran-direct-extract               # PDF question extraction
python scripts/export_for_review.py   # Export data for review
python scripts/import_from_review.py  # Import reviewed data
```

#### Dataset Status: Complete ✅
- **data/final_dataset.json**: 460 questions with multilingual explanations (EN/DE/TR/UK/AR) and images
- **No dataset generation needed** - complete dataset already exists

#### Planned Commands (Not Implemented)
```bash
# Main application (after Terminal UI implementation)
# integran                             # Terminal trainer
# integran-backup-data                 # Data backup/restore
```


### Dataset Structure

The `data/final_dataset.json` format:

```json
{
  "id": 21,
  "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
  "options": ["Bild 1", "Bild 2", "Bild 3", "Bild 4"],
  "correct": "Bild 1",
  "category": "Symbols",
  "difficulty": "easy",
  "images": [
    {
      "path": "images/page_9_img_2.png",
      "description": "German federal eagle on yellow background",
      "context": "Official coat of arms of Germany since 1950"
    }
  ],
  "answers": {
    "en": {
      "explanation": "The German federal eagle is the official coat of arms...",
      "why_others_wrong": {"B": "This shows...", "C": "This is..."},
      "key_concept": "German federal symbols",
      "mnemonic": "Eagle = Germany (like USA)"
    },
    "de": {
      "explanation": "Der Bundesadler ist das offizielle Wappen...",
      "key_concept": "Deutsche Staatssymbole",
      "mnemonic": "Adler = Deutschland"
    }
  }
}
```


## 🔧 Development Setup

### Prerequisites

- Python 3.12+
- Conda environment
- uv package manager
- Git

### Development Installation

1. Clone and setup:
```bash
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
ruff check .
ruff format .
```

### Testing

The project includes comprehensive test coverage with 453 tests passing and 43.40% coverage:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=src

# Run tests with verbose output
pytest -v

# Run quality checks (all passing)
make lint        # Ruff linting
make typecheck   # MyPy type checking
make test        # Full test suite
```

### Code Quality

The project uses several tools for code quality:

- **Ruff**: Linting and formatting
- **MyPy**: Type checking
- **Pytest**: Testing with coverage reporting

### Making Changes

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Run linting: `ruff check . --fix && ruff format .`
5. Commit and push
6. Create a pull request

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass (453 tests)
5. Run quality checks: `make check-all`
6. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for modules and classes
- Maintain test coverage above 80%
- Use descriptive commit messages

## 🚀 Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag
4. Push to GitHub
5. GitHub Actions will handle the release

## 📊 Data Flow Architecture

### Understanding the Complete Data Flow

One of the most critical aspects of the Integran architecture is understanding how data flows between the presentation, application, domain, and infrastructure layers. This section explains the complete flow using the example of a user answering a question.

### 🔄 Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  • UI Components (Terminal/Web/Mobile)                              │
│  • User Input Handling                                              │
│  • Display Results                                                  │
│  • NO Business Logic                                                │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕
┌─────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                            │
│  • Thin Coordinators (< 50 lines)                                  │
│  • Command/Query Handlers                                           │
│  • Event Handlers                                                   │
│  • Orchestrates Domain Services                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕
┌─────────────────────────────────────────────────────────────────────┐
│                          DOMAIN LAYER                               │
│  • Business Logic                                                   │
│  • Domain Services (ScheduleCard, etc.)                             │
│  • Domain Events                                                    │
│  • FSRS Algorithm                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕
┌─────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                           │
│  • Database (SQLite)                                                │
│  • Event Bus                                                        │
│  • Repositories                                                     │
│  • External APIs (Gemini)                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 📍 Example: User Answers a Question

#### Success Flow: Correct Answer with "Good" Rating

```
USER INTERACTION
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: QuestionWidget (question_view.py)                    │
│                                                                     │
│  1. User clicks answer option                                       │
│  2. Answer revealed as correct ✓                                    │
│  3. User clicks "Good" rating button                                │
│  4. submit_answer_with_rating(rating=3) called                      │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Creates ScheduleCardRequest
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN: ScheduleCard Service (schedule_card.py)                    │
│                                                                     │
│  1. Validates request (card_id > 0, valid rating)                  │
│  2. Gets/Creates FSRS card from database                           │
│  3. Calculates FSRS parameters:                                    │
│     • Difficulty: 5.0 → 4.8 (easier after correct)                 │
│     • Stability: 1.0 → 4.14 (more stable)                          │
│     • Next Review: now → in 4 days                                 │
│  4. Updates database with new state                                │
│  5. Records review history                                          │
│  6. Publishes CardScheduledEvent                                   │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Event Published
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: EventBus (enhanced_event_bus.py)                   │
│                                                                     │
│  1. Receives CardScheduledEvent                                     │
│  2. Finds registered handlers: [CardScheduledHandler]               │
│  3. Calls handler.handle(event) asynchronously                      │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Async Handler Call
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: CardScheduledHandler (card_scheduled_handler.py)      │
│                                                                     │
│  1. Updates performance metrics                                     │
│  2. Checks for leech status (if rating=1)                           │
│  3. Updates daily statistics                                        │
│  4. Triggers analytics calculations                                 │
└─────────────────────────────────────────────────────────────────────┘
     │
     │ Analytics Update
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESULT: Updated State in Database                                  │
│                                                                     │
│  • FSRS card updated with new schedule                             │
│  • Review history recorded                                          │
│  • Analytics updated                                                │
│  • Stats page shows: 1 question answered, 100% correct             │
└─────────────────────────────────────────────────────────────────────┘
```

#### Failure Flow: Wrong Answer with "Again" Rating

```
USER INTERACTION
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: QuestionWidget                                        │
│                                                                     │
│  1. User clicks wrong answer option                                 │
│  2. Answer revealed as incorrect ✗                                  │
│  3. User clicks "Again" rating button                               │
│  4. submit_answer_with_rating(rating=1) called                      │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN: ScheduleCard Service                                        │
│                                                                     │
│  1. FSRS calculations for "Again":                                  │
│     • Difficulty: 5.0 → 5.2 (harder after fail)                    │
│     • Stability: 4.14 → 0.4 (much less stable)                     │
│     • State: REVIEW → RELEARNING                                    │
│     • Next Review: in 10 minutes                                   │
│  2. Increments lapse_count                                          │
│  3. Publishes CardScheduledEvent with rating=1                      │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: CardScheduledHandler                                   │
│                                                                     │
│  1. Special handling for "Again" rating:                            │
│     • Checks leech threshold (8 lapses)                             │
│     • May create LeechDetectedEvent                                 │
│     • Updates failure statistics                                    │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESULT: Card in Relearning State                                   │
│                                                                     │
│  • Card scheduled for short interval (10 min)                      │
│  • Lapse count incremented                                          │
│  • Stats show: 1 question answered, 0% correct                     │
│  • Potential leech detection if multiple failures                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 🔍 Critical Implementation Details

#### 1. **Event Handler Registration (CRITICAL!)**
```python
# In MainContainer.__init__():
self._event_subscription_manager = EventSubscriptionManager(self._event_bus)
self._setup_event_handlers()

# In _setup_event_handlers():
card_scheduled_handler = CardScheduledHandler(self._db_manager)
self._event_subscription_manager.subscribe(CardScheduledEvent, card_scheduled_handler)
```

**Without this registration**: Events are published but nothing happens!

#### 2. **Proper Service Injection**
```python
# WRONG: Publishing events directly from UI
event = CardScheduledEvent(...)  # Dummy data
await self.event_bus.publish(event)  # Bypasses domain logic!

# CORRECT: Call domain service
request = ScheduleCardRequest(card_id=1, rating=FSRSRating.GOOD, ...)
result = await self.schedule_card_service.call(request)  # Proper flow
```

#### 3. **Auto-Creation of FSRS Cards**
```python
# In ScheduleCard service:
card = await self._get_card_by_id(request.card_id)
if not card:
    # Auto-create for new questions
    card = self.db_manager.create_fsrs_card(question_id=request.card_id, user_id=1)
```

### 📈 Data Flow for Statistics Display

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION: ProgressScreen requests stats                         │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION: GetSessionProgressQueryHandler                         │
│  • Direct database query (CQRS read side)                           │
│  • No domain logic needed for reads                                 │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE: DatabaseManager                                     │
│  • get_fsrs_learning_stats()                                        │
│  • Aggregates: cards_learning, cards_review, retention_rate         │
└─────────────────────────────────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESULT: Statistics Displayed                                        │
│  • Questions answered: X                                            │
│  • Correct: Y%                                                      │
│  • Cards in learning/review states                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 🚨 Common Data Flow Issues

1. **Missing Event Handlers**
   - **Symptom**: Actions complete but stats don't update
   - **Fix**: Register handlers in MainContainer

2. **Bypassing Domain Layer**
   - **Symptom**: Events published but no business logic runs
   - **Fix**: Always call domain services, never publish events directly from UI

3. **No FSRS Cards**
   - **Symptom**: "Card not found" errors
   - **Fix**: Auto-create cards in ScheduleCard service

4. **Stale Statistics**
   - **Symptom**: Stats don't reflect recent answers
   - **Fix**: Ensure CardScheduledHandler updates analytics

### 🎯 Key Takeaways

1. **Presentation Layer**: Only handles UI, calls domain services
2. **Domain Layer**: Contains ALL business logic (FSRS calculations)
3. **Application Layer**: Thin coordination, event handling
4. **Infrastructure Layer**: Data persistence, event distribution

5. **Event Flow**: Domain services publish events → Event bus distributes → Handlers process
6. **CQRS Pattern**: Commands go through domain services, queries go direct to database

## 📋 Adding Commands and Queries - Developer Guide

### 🎯 CQRS Implementation Guidelines

This section provides a step-by-step guide for adding new commands and queries while respecting the CQRS architecture flow and event-driven patterns.

#### **RESPECT ARCHITECTURE FLOW:**
```
Domain Layer (Services/Models) defines interface
     ↓ 
Application Layer (Commands/Queries) uses domain interfaces correctly
     ↓
Domain service populates all required attributes and publishes events
     ↓
Event handlers process cross-context communication
```

### ✅ Step-by-Step: Adding a New Command

#### Step 1: Define Domain Models and Events
```python
# In src/domain/[context]/events/[context]_events.py
@dataclass
class UserSettingsChangedEvent(DomainEvent):
    """Event published when user settings are updated."""
    user_id: int
    setting_key: str
    old_value: Any
    new_value: Any
    
    def __post_init__(self):
        super().__init__()
```

#### Step 2: Create Domain Service
```python
# In src/domain/[context]/services/[service_name].py
@dataclass
class SaveUserSettingsRequest:
    """Request to save user settings."""
    user_id: int
    settings: dict[str, Any]
    updated_by: str = "system"

@dataclass 
class SaveUserSettingsResult:
    """Result of saving user settings."""
    success: bool
    user_id: int
    updated_settings: dict[str, Any] | None = None
    error_message: str | None = None

class SaveUserSettings(DomainService[SaveUserSettingsRequest, SaveUserSettingsResult]):
    """Domain service for saving user settings with business logic."""
    
    def __init__(self, event_bus: EventBus, user_repository: UserRepository):
        super().__init__(event_bus)
        self.user_repository = user_repository
        
    async def call(self, request: SaveUserSettingsRequest) -> SaveUserSettingsResult:
        """Save user settings and publish events."""
        try:
            # 1. Validate business rules
            if not request.settings:
                return SaveUserSettingsResult(
                    success=False,
                    user_id=request.user_id,
                    error_message="Settings cannot be empty"
                )
            
            # 2. Get current settings for comparison
            current_settings = await self.user_repository.get_user_settings(request.user_id)
            
            # 3. Apply business logic
            updated_settings = await self.user_repository.save_user_settings(
                request.user_id, request.settings
            )
            
            # 4. Publish domain events for changed settings
            for key, new_value in request.settings.items():
                old_value = current_settings.get(key)
                if old_value != new_value:
                    event = UserSettingsChangedEvent(
                        user_id=request.user_id,
                        setting_key=key,
                        old_value=old_value,
                        new_value=new_value
                    )
                    await self.publish_event(event)
            
            return SaveUserSettingsResult(
                success=True,
                user_id=request.user_id,
                updated_settings=updated_settings
            )
            
        except Exception as e:
            return SaveUserSettingsResult(
                success=False,
                user_id=request.user_id,
                error_message=str(e)
            )
```

#### Step 3: Create Application Command
```python
# In src/application/commands/save_user_settings_command.py
@dataclass
class SaveUserSettingsCommand:
    """Command to save user settings."""
    user_id: int
    settings: dict[str, Any]
    updated_by: str = "user"

@dataclass
class SaveUserSettingsCommandResult:
    """Result of save user settings command."""
    success: bool
    error_message: str | None = None

class SaveUserSettingsCommandHandler:
    """Thin application layer handler that coordinates domain service."""
    
    def __init__(self, user_repository: UserRepository, event_bus: EventBus):
        self.save_settings_service = SaveUserSettings(event_bus, user_repository)
        
    async def handle(self, command: SaveUserSettingsCommand) -> SaveUserSettingsCommandResult:
        """Handle save user settings command using domain service."""
        request = SaveUserSettingsRequest(
            user_id=command.user_id,
            settings=command.settings,
            updated_by=command.updated_by
        )
        
        result = await self.save_settings_service.call(request)
        
        return SaveUserSettingsCommandResult(
            success=result.success,
            error_message=result.error_message
        )
```

#### Step 4: Create Event Handler (If Cross-Context Communication Needed)
```python
# In src/application/events/handlers/user_settings_changed_handler.py
class UserSettingsChangedHandler:
    """Handle user settings changes for cross-context updates."""
    
    def __init__(self, analytics_repository: AnalyticsRepository):
        self.analytics_repository = analytics_repository
        
    async def handle(self, event: UserSettingsChangedEvent) -> None:
        """Handle user settings changed event."""
        # Update analytics when language preference changes
        if event.setting_key == "language":
            await self.analytics_repository.record_language_change(
                event.user_id, event.old_value, event.new_value
            )
```

#### Step 5: Register in Container
```python
# In src/infrastructure/containers/main_container.py
def _setup_event_handlers(self) -> None:
    """Register all event handlers."""
    # ... existing handlers ...
    
    # Register new handler
    user_settings_handler = UserSettingsChangedHandler(self._analytics_repository)
    self._event_subscription_manager.subscribe(
        UserSettingsChangedEvent, 
        user_settings_handler.handle
    )

def get_save_user_settings_command_handler(self) -> SaveUserSettingsCommandHandler:
    """Get save user settings command handler."""
    return SaveUserSettingsCommandHandler(
        user_repository=self._user_repository,
        event_bus=self._event_bus
    )
```

### ✅ Step-by-Step: Adding a New Query

#### Step 1: Create Query Models
```python
# In src/application/queries/get_user_preferences_query.py
@dataclass
class GetUserPreferencesQuery:
    """Query to get user preferences."""
    user_id: int
    include_defaults: bool = True

@dataclass
class UserPreferencesData:
    """User preferences data."""
    user_id: int
    language: Language
    developer_mode: bool
    custom_settings: dict[str, Any]
    last_updated: datetime

@dataclass
class GetUserPreferencesResult:
    """Result of get user preferences query."""
    success: bool
    preferences: UserPreferencesData | None = None
    error_message: str | None = None
```

#### Step 2: Create Query Handler (Direct Database Access - CQRS Read Side)
```python
class GetUserPreferencesQueryHandler:
    """Query handler for user preferences - direct database access."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        
    async def handle(self, query: GetUserPreferencesQuery) -> GetUserPreferencesResult:
        """Handle get user preferences query."""
        try:
            # Direct database query - no domain logic needed for reads
            user_settings = await self.user_repository.get_user_settings(query.user_id)
            
            if not user_settings:
                if query.include_defaults:
                    # Return default preferences
                    preferences = UserPreferencesData(
                        user_id=query.user_id,
                        language=Language.ENGLISH,
                        developer_mode=False,
                        custom_settings={},
                        last_updated=datetime.now(UTC)
                    )
                    return GetUserPreferencesResult(success=True, preferences=preferences)
                else:
                    return GetUserPreferencesResult(
                        success=False,
                        error_message="User preferences not found"
                    )
            
            # Convert to preferences data
            preferences = UserPreferencesData(
                user_id=user_settings.user_id,
                language=user_settings.language,
                developer_mode=user_settings.developer_mode,
                custom_settings=user_settings.custom_settings,
                last_updated=user_settings.updated_at
            )
            
            return GetUserPreferencesResult(success=True, preferences=preferences)
            
        except Exception as e:
            return GetUserPreferencesResult(
                success=False,
                error_message=str(e)
            )
```

### ⚡ CQRS Best Practices

#### Commands (Write Operations)
1. **Always go through Domain Services** - Commands must use domain services for business logic
2. **Publish Domain Events** - Domain services publish events for cross-context communication
3. **Thin Application Layer** - Command handlers should be < 50 lines, just coordination
4. **Validate in Domain** - Business rule validation happens in domain services

#### Queries (Read Operations)  
1. **Direct Database Access** - Queries can bypass domain layer for performance
2. **No Business Logic** - Queries just format and return data
3. **Projection-Friendly** - Design for read models and projections
4. **Fast and Simple** - Optimize for read performance

#### Events (Cross-Context Communication)
1. **Domain Events Only** - Only domain services publish events
2. **Async Handlers** - Event handlers run asynchronously
3. **Error Isolation** - Handler failures don't affect other handlers
4. **Event Sourcing Ready** - Events contain all necessary data

### 🔍 Architecture Verification Checklist

Before submitting code, verify:

✅ **Domain Layer Compliance:**
- [ ] Domain service defines clear request/result interfaces
- [ ] Business logic is in domain service, not application layer
- [ ] Domain events are published for important state changes
- [ ] No infrastructure dependencies in domain layer

✅ **Application Layer Compliance:**
- [ ] Command handlers are thin coordinators (< 50 lines)
- [ ] Queries bypass domain for direct database access
- [ ] Event handlers process cross-context communication
- [ ] No business logic in application layer

✅ **Event Flow Compliance:**
- [ ] Domain services publish events, not UI components
- [ ] Event handlers are registered in MainContainer
- [ ] Events contain all necessary data for handlers
- [ ] Event flow respects dependencies defined in `docs/event-flows.yaml`

### 📝 Testing Guidelines

#### Test Domain Services
```python
@pytest.mark.asyncio
async def test_save_user_settings_success():
    """Test successful user settings save."""
    # Arrange
    mock_repo = AsyncMock()
    mock_event_bus = AsyncMock()
    service = SaveUserSettings(mock_event_bus, mock_repo)
    
    request = SaveUserSettingsRequest(
        user_id=1,
        settings={"language": "german", "developer_mode": True}
    )
    
    # Act
    result = await service.call(request)
    
    # Assert
    assert result.success is True
    mock_event_bus.publish.assert_called()  # Verify event published
```

#### Test Application Handlers
```python
@pytest.mark.asyncio
async def test_command_handler_coordinates_domain_service():
    """Test command handler coordinates domain service correctly."""
    # Arrange
    mock_repo = AsyncMock()
    mock_event_bus = AsyncMock()
    handler = SaveUserSettingsCommandHandler(mock_repo, mock_event_bus)
    
    command = SaveUserSettingsCommand(user_id=1, settings={"theme": "dark"})
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result.success is True
    # Verify domain service was called (indirectly through mocks)
```

## ✅ Architecture Validation Checklist

Before submitting any code changes, verify CQRS/DDD compliance:

### Domain Layer Compliance
- [ ] **No Infrastructure Imports**: Domain files must not import from `src.infrastructure`
- [ ] **Domain Events in Domain**: All `DomainEvent` classes must be in `src/domain`
- [ ] **Repository Interfaces**: Domain owns repository interfaces in `src/domain/shared/repositories.py`
- [ ] **Business Logic**: All business rules are in domain services, not application layer
- [ ] **Event Publishing**: Domain services publish domain events for state changes

### Application Layer Compliance  
- [ ] **Command Methods**: All commands have `execute()` or `handle()` methods
- [ ] **Query Methods**: All queries have `handle()` methods
- [ ] **Thin Coordinators**: Command/query handlers are < 50 lines
- [ ] **No Business Logic**: Application layer only coordinates, no business rules
- [ ] **Domain Service Usage**: Commands use domain services, not direct repository access

### CQRS Pattern Compliance
- [ ] **Command Separation**: Write operations go through commands + domain services
- [ ] **Query Separation**: Read operations can access repositories directly
- [ ] **Event Handling**: Cross-context communication uses domain events
- [ ] **Layer Flow**: Presentation → Application → Domain → Infrastructure

### Dependency Inversion Compliance
- [ ] **Interface Ownership**: Domain owns interfaces, infrastructure implements
- [ ] **EventBus Interface**: Domain services use `EventBusInterface`, not concrete `EventBus`
- [ ] **Repository Abstraction**: Domain services use repository interfaces
- [ ] **No Outward Dependencies**: Domain layer has no dependencies on outer layers

### Testing Verification
```bash
# Run architecture tests to verify compliance
pytest tests/unit/architecture/ -v

# Run all quality checks
make check-all

# Should be 0 failing tests for clean architecture
```

## 🔧 Development Setup

### Quick Start
```bash
# Clone and setup environment
git clone <repository>
cd integran
make env-create
conda activate integran
make install

# Run quality checks
make check-all  # Must be green before any commits
```

### Making Changes
1. **Read TODO.md** - Check current critical issues and priorities
2. **Run Architecture Tests** - `pytest tests/unit/architecture/ -v`
3. **Follow CQRS Patterns** - Use examples in this guide
4. **Validate Changes** - `make check-all` must pass
5. **Update Tests** - Add/update tests for new functionality

### Key Commands
```bash
make lint        # Code linting with ruff
make format      # Code formatting
make typecheck   # Type checking with mypy  
make test        # Run test suite
make check-all   # Run all quality checks
```

## 📚 Additional Resources

- **[Event Flow Definition](./event-flows.yaml)** - Event flow specifications
- **[Dataset Generation Guide](./dataset-generation-guide.md)** - Dataset workflow
- [TODO.md](../TODO.md) - Current priorities and critical issues

---

This guide provides the foundation for maintaining clean CQRS/DDD architecture. Always refer to failing architecture tests in TODO.md for current issues that need addressing.