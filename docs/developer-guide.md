# Developer Guide

This guide is for developers and contributors working on the Integran project. Regular users don't need this information.

## 🎯 Current Status: Phase 4.1 - Application Layer Architecture Fix

🚨 **PRIORITY**: Fix application layer architectural violations identified through DDD + CQRS research before proceeding to Terminal UI implementation.

**Current Status as of 2025-01-16:**
- ✅ **Domain Layer Complete**: All 4 bounded contexts with proper domain services
- ✅ **Infrastructure Complete**: EventBus, database, repositories working correctly  
- ✅ **CQRS Structure Created**: Commands, queries, events, workflows, projections organized
- 🚨 **Application Layer Issues**: Contains business logic violations that need fixing
- 📋 **Next Priority**: Terminal UI implementation after architecture fix

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
- **Infrastructure**: EventBus, database, repositories, external APIs

### Current Architecture Status

```
src/
├── domain/                        # ✅ COMPLETE - Domain Layer
│   ├── learning/services/          # ScheduleCard (FSRS algorithm)
│   ├── content/services/           # GenerateAnswer, ProcessImage, CreateImageMapping
│   ├── analytics/services/         # AnalyzePerformance, DetectLeech, OptimizeInterleaving
│   └── shared/                     # Base classes, events, domain service interface
├── application/                    # 🚨 NEEDS FIXING - Application Layer
│   ├── commands/                   # Write operations (need to be thinned)
│   ├── queries/                    # Read operations (OK as-is)
│   ├── events/handlers/            # Cross-context event handling (OK)
│   ├── workflows/                  # 🚨 TOO THICK - contains business logic
│   └── projections/                # Read model projections (OK)
├── infrastructure/                 # ✅ COMPLETE - Infrastructure Layer
│   ├── database/database.py        # DatabaseManager, SQLite operations
│   ├── messaging/event_bus.py      # EventBus implementation
│   └── repositories/               # Data access
└── presentation/                   # 📋 TODO - Terminal UI
    └── terminal/                   # Rich/Textual implementation (next priority)
```

## 🚨 Phase 4.1: Identified Architecture Issues

**Research Finding**: DDD + CQRS best practices research revealed 3 critical violations:

#### Problem 1: Application Layer Too Thick (600+ lines)
- **Issue**: `src/application/workflows/complete_learning_session_workflow.py` contains business logic
- **Violation**: Application should be thin coordinators, not business logic containers
- **Solution**: Extract to domain services in Learning Context

#### Problem 2: Business Logic Duplication
- **Issue**: Logic duplicated between domain services and application workflows  
- **Violation**: Domain services should contain ALL business logic
- **Solution**: Move complex logic to domain services exclusively

#### Problem 3: Commands Too Thick
- **Issue**: Command handlers contain business logic instead of just coordination
- **Violation**: CQRS commands should validate input and delegate to domain
- **Solution**: Thin command handlers to < 50 lines each

#### ✅ What's Working (Keep These)
- **Domain Layer**: All domain services properly implemented
- **Infrastructure**: EventBus, database, repositories working correctly
- **CQRS Structure**: Commands, queries, events organized properly
- **Test Coverage**: 288 tests passing, all quality checks green

## 🎯 Phase 4.1 Solution: Thin Application Layer

### Required Fixes

#### Step 1: Extract Business Logic to Domain
- **Create** `CompleteLearningSession` domain service in Learning Context
- **Move** complex logic from `src/application/workflows/complete_learning_session_workflow.py`
- **Create** `BuildDataset` domain service in Content Context  
- **Move** logic from `src/application/workflows/build_dataset_workflow.py`

#### Step 2: Thin Command Handlers
- **Refactor** commands to be coordinators only (< 50 lines each)
- **Pattern**: Validate input → Call domain service → Return result
- **Keep** queries as direct database access for performance

#### Step 3: Verify Architecture
- **Test** all business logic works after extraction
- **Confirm** application layer files are thin
- **Validate** domain services handle all complex operations

### Target Architecture (After Phase 4.1 Fix)

**Thin Application Layer:**
```
src/application/
├── commands/                       # Thin coordinators (< 50 lines each)
│   ├── start_session_command.py   # Validates input → calls domain service
│   ├── submit_answer_command.py   # Validates input → calls ScheduleCard
│   └── build_dataset_command.py   # Validates input → calls BuildDataset
├── queries/                        # Direct database access (performance)
│   ├── get_session_progress_query.py
│   ├── get_due_cards_query.py
│   └── get_user_stats_query.py
├── events/handlers/                # Cross-context coordinators
│   ├── card_scheduled_handler.py
│   └── content_processed_handler.py
└── projections/                    # Read model projections
    └── user_progress_projection.py
```

**Domain Layer (Business Logic):**
```
src/domain/
├── learning/services/
│   ├── schedule_card.py            # FSRS algorithm (KEEP)
│   └── complete_learning_session.py  # NEW: Session business logic
├── content/services/
│   ├── generate_answer.py          # Multilingual generation (KEEP)
│   ├── process_image.py            # Image processing (KEEP) 
│   └── build_dataset.py            # NEW: Dataset building logic
└── analytics/services/
    ├── analyze_performance.py      # Performance analysis (KEEP)
    ├── detect_leech.py             # Leech detection (KEEP)
    └── optimize_interleaving.py    # Interleaving optimization (KEEP)
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

## 📚 Additional Resources

- **[Dataset Generation Guide](./dataset-generation-guide.md)** - Complete workflow for generating final_dataset.json
- [Integration Exam Research](./integration_exam_research.md) - Background research

For questions or support, please open an issue on GitHub.

---

## 📋 Quick Start for New Developers

### Architecture Status
- **Domain Layer**: Complete with all 4 bounded contexts and domain services
- **Infrastructure**: EventBus, database, repositories working correctly  
- **Application Layer**: Thin coordinators with proper DDD separation (Phase 4.1 ✅ Complete)
- **CQRS Structure**: Commands, queries, events, workflows properly organized
- **Quality Assurance**: 453 tests passing, all linting and type checks green
- **Current Phase**: Terminal UI implementation (Phase 6) - architecture ready

### For Different Developer Roles
- **New Contributors**: Focus on Terminal UI development after Phase 4.1 fixes
- **Domain Developers**: Extend existing contexts or add new bounded contexts  
- **UI Developers**: Terminal interface ready for Rich/Textual implementation
- **Algorithm Developers**: FSRS implementation complete, ready for optimization  

---

**Last Updated**: January 17, 2025 - Phase 4.1 Complete, Terminal UI Implementation Next