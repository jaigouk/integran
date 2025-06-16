# Developer Guide

This guide is for developers and contributors working on the Integran project. Regular users don't need this information.

## 🎯 Current Status: Phase 6 - User Configuration & Event Flow DAG

🚨 **PRIORITY**: Implement user configuration system with developer mode control and design comprehensive event flow DAG for cross-platform compatibility.

**Current Status as of 2025-01-16:**
- ✅ **Domain Layer Complete**: All 4 bounded contexts with proper domain services
- ✅ **Infrastructure Complete**: EventBus, database, repositories working correctly  
- ✅ **CQRS Structure Created**: Commands, queries, events, workflows, projections organized
- ✅ **Application Layer Fixed**: Thin coordinators with proper DDD separation (Phase 4.1 Complete)
- ✅ **Terminal UI Complete**: Rich/Textual implementation finished (Phase 5 Complete)
- 🚨 **Current Priority**: User configuration domain + Event flow DAG design
- 📋 **Next Priority**: Cross-platform user flows and developer mode integration

## 🏗️ Architecture Overview

Integran is a **Domain-Driven Design (DDD)** application with **CQRS** patterns and **event-driven** communication.

### Core Principles
1. **Domain-Driven Design**: Business logic in domain services with single responsibilities
2. **CQRS**: Separate command (write) and query (read) operations
3. **Event-Driven**: Async communication between bounded contexts
4. **Local-First**: SQLite storage, no cloud dependencies
5. **Scientific Learning**: FSRS algorithm for spaced repetition

### Bounded Contexts
- **Learning**: FSRS scheduling, session management, progress tracking
- **Content**: Question management, multilingual answers, image processing  
- **Analytics**: Performance tracking, leech detection, interleaving optimization
- **User**: User configuration, preferences, developer mode control
- **Infrastructure**: EventBus, database, repositories, external APIs

### Current Architecture Status

```
src/
├── domain/                        # ✅ COMPLETE - Domain Layer
│   ├── learning/services/          # ScheduleCard, CompleteLearningSession
│   ├── content/services/           # GenerateAnswer, ProcessImage, BuildDataset
│   ├── analytics/services/         # AnalyzePerformance, DetectLeech, OptimizeInterleaving
│   ├── user/                      # 📋 NEW - User configuration domain
│   └── shared/                     # Base classes, events, domain service interface
├── application/                    # ✅ COMPLETE - Thin Application Layer
│   ├── commands/                   # Thin coordinators (< 50 lines each)
│   ├── queries/                    # Read operations (direct database access)
│   ├── events/handlers/            # Cross-context event handling
│   ├── workflows/                  # Thin coordinators (< 60 lines each)
│   └── projections/                # Read model projections
├── infrastructure/                 # ✅ COMPLETE - Infrastructure Layer
│   ├── database/database.py        # DatabaseManager, SQLite operations
│   ├── messaging/event_bus.py      # EventBus implementation
│   └── repositories/               # Data access
└── presentation/                   # ✅ COMPLETE - Presentation Layer
    ├── terminal/                   # Rich/Textual implementation
    └── cli/                        # Command-line interfaces
```

## 🎯 Phase 6: User Configuration & Event Flow Design

**Current Priority**: Implement comprehensive user configuration system and explicit event flow management for cross-platform compatibility.

### Phase 6.1: User Configuration Domain
#### New Bounded Context: User Configuration
- **Create** `src/domain/user/` with models, services, events
- **Add** `UserSettings` aggregate with developer mode, preferences
- **Implement** `SaveUserSettings` and `LoadUserSettings` domain services
- **Add** persistence through SQLite user_settings table

### Phase 6.2: Developer Mode Control
#### Service Access Control
- **Modify** content services to check developer mode before using Gemini
- **Add** `DeveloperModeRequiredError` for restricted operations
- **Update** `BuildDataset` and `ProcessImage` to require developer mode
- **Default**: `developer_mode = false`, `use_gemini = false`

### Phase 6.3: Event Flow DAG Design
#### Explicit Event Flow Management
- **Created** `docs/event-flows.yaml` for explicit event definition
- **Event Categories**: System, User, Learning, Content, Analytics, Developer
- **Flow Validation**: DAG compliance, dependency checking, circular detection
- **Cross-Platform**: Same events work across terminal, mobile, desktop, web

### Phase 6.4: User Flow Implementation
#### Core User Flows
1. **First-time Setup Flow**: Language → Developer Mode → Tutorial → Main Menu
2. **Daily Usage Flow**: Settings Load → Session Start → Learning Loop → Progress
3. **Settings Management Flow**: Open Settings → Change Prefs → Save → Update UI
4. **Developer Operations Flow**: Enable Dev Mode → API Operations → Dataset Generation

#### ✅ What's Already Working (Phase 4.1 & 5 Complete)
- **Domain Layer**: All 5 bounded contexts with proper domain services
- **Infrastructure**: EventBus, database, repositories working correctly
- **Application Layer**: Thin coordinators with proper DDD separation
- **Terminal UI**: Complete Rich/Textual implementation
- **Test Coverage**: 416+ tests passing, all quality checks green

## 🎯 Phase 6 Implementation Plan

### Step 1: User Configuration Domain (1-2 days)

#### Create User Bounded Context
- **New Directory**: `src/domain/user/`
- **Models**: `UserSettings`, `DeveloperMode`, `UserPreferences`
- **Services**: `SaveUserSettings`, `LoadUserSettings`, `ToggleDeveloperMode`
- **Events**: `UserSettingsChangedEvent`, `DeveloperModeToggledEvent`
- **Repository**: `UserSettingsRepository` with SQLite persistence

#### Database Schema Extensions
- **Extend** `user_settings` table with `developer_mode` boolean
- **Add** `user_preferences` JSON column for flexible settings
- **Add** `first_time_setup` flag for onboarding state
- **Add** `user_flow_state` for resume capabilities

### Step 2: Event Flow DAG Implementation (1-2 days)

#### Event Flow Engine
- **Create** `EventFlowOrchestrator` for DAG validation
- **Load** event definitions from `docs/event-flows.yaml`
- **Validate** event dependencies and prevent circular flows
- **Add** event sequence tracking and health monitoring

#### Event System Enhancements
- **Add** event flow validation to EventBus
- **Implement** event replay capabilities for debugging
- **Add** event dependency metadata storage
- **Create** event flow health check reports

### Step 3: Developer Mode Integration (1 day)

#### Service Access Control
- **Modify** `BuildDataset` to check developer mode before Gemini usage
- **Modify** `ProcessImage` to require developer mode for API calls
- **Add** `DeveloperModeRequiredError` exception
- **Default** all new installations to `developer_mode = false`

#### User-Friendly Error Messages
- **Add** clear messaging when developer features attempted without mode enabled
- **Guide** users to enable developer mode through settings
- **Protect** against accidental API usage and costs

### Target Architecture (After Phase 6 Implementation)

**Enhanced Domain Layer with User Configuration:**
```
src/domain/
├── learning/services/
│   ├── schedule_card.py            # FSRS algorithm
│   └── complete_learning_session.py  # Session business logic
├── content/services/
│   ├── generate_answer.py          # Multilingual generation (dev mode check)
│   ├── process_image.py            # Image processing (dev mode check)
│   └── build_dataset.py            # Dataset building (dev mode check)
├── analytics/services/
│   ├── analyze_performance.py      # Performance analysis
│   ├── detect_leech.py             # Leech detection
│   └── optimize_interleaving.py    # Interleaving optimization
├── user/                           # NEW: User Configuration Context
│   ├── models/
│   │   ├── user_settings.py        # UserSettings aggregate
│   │   └── developer_mode.py       # DeveloperMode value object
│   ├── services/
│   │   ├── save_user_settings.py   # Save preferences
│   │   ├── load_user_settings.py   # Load preferences
│   │   └── toggle_developer_mode.py # Developer mode control
│   └── events/
│       └── user_events.py          # User configuration events
└── shared/
    ├── events.py                   # Enhanced with user events
    └── services.py                 # Base classes with developer mode checks
```

**Event Flow Management:**
```
docs/
├── event-flows.yaml                # Explicit event flow definitions
└── event-flow-diagrams/            # Auto-generated flow visualizations

src/infrastructure/messaging/
├── event_bus.py                    # Enhanced with flow validation
├── event_flow_orchestrator.py     # NEW: DAG validation and monitoring
└── event_flow_health_checker.py   # NEW: Flow health monitoring
```

**Enhanced Terminal UI with Settings:**
```
src/presentation/terminal/
├── trainer_app.py                  # Main menu with settings option
├── settings_view.py                # NEW: Settings management screen
├── developer_view.py               # NEW: Developer operations screen
├── first_time_setup_view.py        # NEW: Onboarding wizard
└── base.py                         # Event-aware components
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

## 🔄 Event Flow Management

### Event Flow Definition File

The application uses an explicit event flow definition system through `docs/event-flows.yaml`:

```yaml
# Example event definition
events:
  AppStartedEvent:
    category: system
    triggers: [FirstTimeSetupEvent, UserSettingsLoadedEvent]
    dependencies: []
    description: "Application startup initialization"

# Example flow definition  
flows:
  first_time_setup:
    name: "First Time User Setup"
    sequence:
      - AppStartedEvent
      - FirstTimeSetupEvent
      - LanguageSelectedEvent
      - DeveloperModeToggledEvent
```

### Benefits of Explicit Event Flow Definition

1. **Cross-Platform Consistency**: Same event flows work across terminal, mobile, desktop, web
2. **DAG Validation**: Prevents circular dependencies and ensures proper event ordering
3. **Documentation**: Self-documenting event relationships and user flows
4. **Debugging**: Event sequence tracking and flow health monitoring
5. **Validation**: Runtime validation of event flow compliance

### Event Categories

- **System**: Application lifecycle (startup, shutdown, migration)
- **User**: User actions and preferences (settings, developer mode)
- **Learning**: FSRS scheduling and session management
- **Content**: Question processing and dataset generation
- **Analytics**: Performance tracking and analysis
- **Developer**: Developer-only operations (API usage, dataset building)

### User Flow Patterns

1. **First-time Setup**: `AppStarted` → `FirstTimeSetup` → `LanguageSelected` → `DeveloperModeToggled`
2. **Daily Usage**: `AppStarted` → `UserSettingsLoaded` → `SessionStarted` → Learning Loop
3. **Settings Management**: `SettingsOpened` → `UserSettingsChanged` → `SettingsSaved`
4. **Developer Operations**: `DeveloperModeToggled` → `DatasetBuildStarted` → AI Processing

## 📚 Additional Resources

- **[Event Flow Definition](./event-flows.yaml)** - Complete event flow specifications
- **[Dataset Generation Guide](./dataset-generation-guide.md)** - Complete workflow for generating final_dataset.json
- [Integration Exam Research](./integration_exam_research.md) - Background research

For questions or support, please open an issue on GitHub.

---

## 📋 Quick Start for New Developers

### Architecture Status
- **Domain Layer**: Complete with 4 bounded contexts, User context in development
- **Infrastructure**: EventBus, database, repositories working correctly  
- **Application Layer**: Thin coordinators with proper DDD separation (Phase 4.1 ✅ Complete)
- **CQRS Structure**: Commands, queries, events, workflows properly organized
- **Terminal UI**: Complete Rich/Textual implementation (Phase 5 ✅ Complete)
- **Event Flow System**: Explicit YAML definition created, validation engine planned
- **Quality Assurance**: 416+ tests passing, all linting and type checks green
- **Current Phase**: User Configuration & Event Flow DAG (Phase 6) - in progress

### For Different Developer Roles
- **New Contributors**: Focus on user configuration domain and event flow validation
- **Domain Developers**: Implement User bounded context, extend event flow system
- **UI Developers**: Add settings screens and first-time setup wizard to terminal UI
- **Platform Developers**: Use event flow YAML for mobile/desktop/web implementations
- **Algorithm Developers**: FSRS implementation complete, ready for user preference integration

### Current Development Priorities
1. **User Configuration Domain**: Create UserSettings aggregate and domain services
2. **Developer Mode Control**: Implement access restrictions for Gemini services
3. **Event Flow Validation**: Build DAG validation engine from YAML definitions
4. **Settings UI**: Add configuration screens to terminal interface
5. **Cross-Platform Events**: Ensure event flows work across all target platforms

---

**Last Updated**: June 16, 2025 - Phase 6 User Configuration & Event Flow DAG In Progress