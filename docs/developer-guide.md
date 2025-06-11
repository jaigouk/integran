# Developer Guide

This guide is for developers and contributors working on the Integran project. Regular users don't need this information.

## 🎯 Phase 1.8 Architecture Overview

As of 2025-01-09, Integran has undergone a complete architecture refactor (Phase 1.8-1.9.4) to address critical image mapping issues and introduce multilingual support. The new system is built around three core components:

1. **ImageProcessor** - AI vision for accurate image-to-question mapping
2. **AnswerEngine** - Multilingual answer generation (5 languages)
3. **DataBuilder** - Unified pipeline orchestrating the entire workflow

## 📊 Enhanced Data Structure

Questions are now stored in `questions.json` with the new Phase 1.8 multilingual format:

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
      "description": "German federal eagle on yellow background with red claws and beak",
      "context": "Official coat of arms of Germany since 1950"
    }
  ],
  "answers": {
    "en": {
      "explanation": "The German federal eagle is the official coat of arms of Germany...",
      "why_others_wrong": {
        "B": "This shows a different coat of arms...",
        "C": "This is not the federal eagle...",
        "D": "This image shows a state symbol..."
      },
      "key_concept": "German federal symbols and constitutional emblems",
      "mnemonic": "Eagle = Germany (like USA has eagle too)"
    },
    "de": {
      "explanation": "Der Bundesadler ist das offizielle Wappen Deutschlands...",
      "why_others_wrong": {
        "B": "Das zeigt ein anderes Wappen...",
        "C": "Das ist nicht der Bundesadler...",
        "D": "Dieses Bild zeigt ein Landeswappen..."
      },
      "key_concept": "Deutsche Staatssymbole und Verfassungsembleme",
      "mnemonic": "Adler = Deutschland"
    },
    "tr": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." },
    "uk": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." },
    "ar": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." }
  },
  "rag_sources": ["grundgesetz.de", "bundesregierung.de"]
}
```

## 🗄️ Database Schema (Phase 1.8)

The app uses SQLite to track progress with enhanced models supporting multilingual content:

### Core Tables
- **Question**: Enhanced with Phase 1.8 multilingual support
- **QuestionAttempt**: Individual question attempt tracking
- **PracticeSession**: Practice session data
- **LearningData**: Spaced repetition learning data per question
- **UserProgress**: Overall user progress tracking
- **CategoryProgress**: Category-specific performance
- **UserSettings**: User preferences including language selection
- **QuestionExplanation**: ⚠️ **DEPRECATED** (kept for migration compatibility)

### Enhanced Question Model (Phase 1.8)
```python
class Question(Base):
    # Basic fields
    id: int
    question: str
    options: str              # JSON serialized list
    correct: str
    category: str
    difficulty: str
    
    # Enhanced fields
    question_type: str        # "general" or "state_specific"
    state: str               # Federal state for state-specific questions
    page_number: int         # PDF page number
    is_image_question: int   # Boolean flag
    
    # Phase 1.8 NEW: Multilingual support
    images_data: str         # JSON serialized list of image objects
    multilingual_answers: str # JSON serialized multilingual data
    rag_sources: str         # JSON serialized list of sources
    
    # Legacy fields (deprecated but kept for migration)
    image_paths: str         # DEPRECATED: Use images_data
    image_mapping: str       # DEPRECATED: Use images_data
```

### User Settings Model (Phase 1.8)
```python
class UserSettings(Base):
    setting_key: str         # e.g., "preferred_language"
    setting_value: str       # JSON serialized value
    created_at: datetime
    updated_at: datetime
```

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

### Developer Commands (Phase 1.8)

```bash
# PRIMARY COMMAND: Build complete multilingual dataset
integran-build-dataset

# Database setup with language preference
integran-setup --language en

# Backup and restore data
integran-backup-data backup
integran-backup-data restore --suffix 20250609_124243

# Direct PDF extraction (developers only):
integran-direct-extract  # Single-question extraction with checkpointing
```

## 🏗️ Current Data Pipeline (2025-06-11 Update)

⚠️ **Important**: The unified `integran-build-dataset` command is outdated. Use the new step-by-step process documented in the [Dataset Generation Guide](./dataset-generation-guide.md).

### Current Workflow (Multi-Step Process)

The current system uses multiple scripts for different phases:

```bash
# STEP 0: Extract from PDF (usually already done)
python src/cli/direct_extract.py

# STEP 1: Extract images (already done)  
python scripts/extract_images.py

# STEP 2: Fix image answers (already done)
python scripts/fix_image_answers.py

# STEP 3: Generate explanations (main task)
python scripts/generate_explanations.py
python scripts/retry_failed_questions.py

# STEP 4: Create final dataset
python scripts/finalize_dataset.py
```

### Quick Start for Most Developers

Most developers only need to run the final step:

```bash
# Create final dataset from existing progress
python scripts/finalize_dataset.py
```

📖 **For complete details, see**: [Dataset Generation Guide](./dataset-generation-guide.md)

### Advanced Options

```bash
# Force rebuild everything from scratch
integran-build-dataset --force-rebuild

# Disable RAG enhancement for faster processing
integran-build-dataset --no-rag

# Skip multilingual generation (testing only)
integran-build-dataset --no-multilingual

# Use larger batch size for faster processing
integran-build-dataset --batch-size 20

# Check current build status
integran-build-dataset --status

# Enable verbose logging
integran-build-dataset --verbose
```

### Prerequisites

Before running `integran-build-dataset`, ensure:

1. **Extraction completed**: `data/extraction_checkpoint.json` must exist and be completed
2. **Gemini API configured**: Required for image descriptions and multilingual answers
3. **Images extracted**: `data/images/` directory contains extracted PDF images
4. **Optional**: Firecrawl API key for enhanced RAG content fetching

### Output Structure

The generated `data/questions.json` includes:

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
      "description": "German federal eagle on yellow background with red claws and beak",
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
      "why_others_wrong": {"B": "Das zeigt...", "C": "Das ist..."},
      "key_concept": "Deutsche Staatssymbole",
      "mnemonic": "Adler = Deutschland"
    },
    "tr": "...",
    "uk": "...",
    "ar": "..."
  },
  "rag_sources": ["grundgesetz.de", "bundestag.de"]
}
```

### Progress Tracking

The command uses checkpoint system for resumability:

```bash
# View build progress
integran-build-dataset --status

# Resume interrupted build
integran-build-dataset  # Automatically resumes from checkpoint
```

Progress is saved in `data/dataset_checkpoint.json`.

## 🔧 Data Generation Overview

The application uses AI-powered explanations generated with Google Gemini for all exam questions. The RAG system was removed as it was not used in the final dataset generation.

## 🎓 AI Explanation Generation ✨ **NEW**

The system generates comprehensive explanations for all exam questions using Google's Gemini AI.

### Explanation Generation Process

#### Basic Explanation Generation

```bash
# Generate explanations for all 460 questions
integran-generate-explanations

# Use specific batch size (default: 10)
integran-generate-explanations --batch-size 15

# Start fresh (ignore existing checkpoint)
integran-generate-explanations --no-resume

# Enable verbose logging
integran-generate-explanations --verbose
```


### Explanation Structure

Each generated explanation includes:

```json
{
  "question_id": 1,
  "question_text": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
  "correct_answer": "hier Meinungsfreiheit gilt.",
  "explanation": "Detailed explanation of why this answer is correct...",
  "why_others_wrong": {
    "incorrect_option_1": "Why this option is wrong...",
    "incorrect_option_2": "Why this option is wrong..."
  },
  "key_concept": "Meinungsfreiheit (Artikel 5 Grundgesetz)",
  "mnemonic": "Memory aid to remember the concept",
}
```

### Checkpoint System

The explanation generation includes robust checkpoint support:

- **Resume Capability**: Automatically resumes from last successful batch
- **Progress Tracking**: Saves progress in `data/explanations_checkpoint.json`
- **Error Handling**: Continues with next batch if one fails
- **Cost Optimization**: Never re-generates existing explanations

### Cost and Performance

- **Total Questions**: 460 explanations
- **Estimated Cost**: $10-20 USD for complete generation
- **Time**: ~1-2 hours for all questions
- **API Calls**: ~50-100 requests (depending on batch size)
- **Rate Limiting**: Built-in throttling to respect API limits

### Output Files

- **Final Output**: `data/explanations.json` (used by the application)
- **Checkpoint**: `data/explanations_checkpoint.json` (for resume capability)
- **Progress Tracking**: Detailed batch completion logs

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

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=src

# Run tests with verbose output
pytest -v
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

### Complete Developer Workflow ✨ **NEW**

For developers working on the AI-enhanced question system:

#### 1. Initial Setup
```bash
# Clone and setup environment
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install

# Setup environment variables (if working with AI features)
cp .env.example .env
# Edit .env with your Google Cloud credentials
```

# Knowledge base building removed as RAG was not used

#### 3. Working with Explanations
```bash
# Generate explanations for all questions (if needed)
integran-generate-explanations --batch-size 10

# RAG enhancement removed as it was not used

# Check progress during generation
tail -f data/explanations_checkpoint.json
```

#### 4. Development Cycle
```bash
# Make your changes
# ...

# Run full test suite
make check-all

# Or individually:
make lint        # Linting
make typecheck   # Type checking  
make test        # Tests
make coverage    # Coverage report
```

#### 5. Quality Assurance
```bash
# Before committing, ensure:
pytest --cov=src --cov-report=term-missing  # 80%+ coverage required
ruff check . --fix && ruff format .         # Code quality
mypy src/                                    # Type checking
```

# RAG system removed as it was not used in final dataset generation

### Current Project Structure (Phase 1.8)

```
src/
├── core/                           # ✨ NEW: Core business logic
│   ├── __init__.py
│   ├── models.py                   # Enhanced with Phase 1.8 multilingual support
│   ├── database.py                 # Enhanced with migration scripts
│   ├── settings.py                 # Configuration management
│   ├── image_processor.py          # ✨ NEW: AI vision & question-image mapping
│   ├── answer_engine.py            # ✨ NEW: Multilingual answer generation
│   └── data_builder.py             # ✨ NEW: Unified pipeline orchestrator
# knowledge_base/ removed as RAG was not used in final dataset
├── cli/                            # Simplified CLI commands
│   ├── __init__.py
│   ├── backup_data.py              # Keep (works)
│   ├── build_dataset.py            # ✨ NEW: Main unified command
│   └── direct_extract.py           # Direct PDF extraction with checkpointing
├── utils/                          # Only working utilities
│   ├── __init__.py
│   ├── question_loader.py          # Simple utility to check for questions file
│   ├── gemini_client.py            # Gemini API client utilities
│   └── explanation_generator.py    # Keep (works with new system)
├── ui/                             # Future terminal UI
│   └── __init__.py
├── trainer.py                      # ✨ UPDATED: Supports new multilingual format
├── setup.py                        # ✨ UPDATED: Phase 1.8 schema support
└── direct_pdf_processor.py         # Direct PDF extraction with structured output
```

### Data Directory Structure (Phase 1.8)

```
data/
├── questions.json                 # ✨ UPDATED: Phase 1.8 multilingual format
├── extraction_checkpoint.json     # Source of truth (460 questions)
├── dataset_checkpoint.json        # ✨ NEW: Build progress tracking
├── images/                        # All extracted question images (42 image questions)
# knowledge_base/ and vector_store/ removed as RAG was not used
├── trainer.db                     # SQLite database (created by setup)
└── gesamtfragenkatalog-lebenindeutschland.pdf

# REMOVED in Phase 1.8 cleanup:
# ├── questions.csv              # REMOVED: Replaced by unified format
# ├── explanations.json          # REMOVED: Integrated into questions.json
# ├── explanations_checkpoint.json # REMOVED: Replaced by dataset_checkpoint.json
```

## 🧪 Testing Strategy (Phase 1.8)

The refactored codebase includes comprehensive test coverage (169 tests) with specific focus on the image mapping issues that prompted the refactor.

### Test Structure

```
tests/
├── unit/
│   ├── core/                        # Core component tests
│   │   ├── test_image_processor.py      # Image processing validation
│   │   ├── test_answer_engine.py        # Multilingual answer generation
│   │   ├── test_data_builder.py         # Pipeline orchestration
│   │   ├── test_image_mapping_validation.py  # ✨ Critical mapping tests
│   │   ├── test_data_builder_validation.py   # End-to-end validation
│   │   ├── test_database.py             # Database operations
│   │   └── test_models.py               # Data models
# knowledge_base/ tests removed as RAG was not used
│   └── cli/                        # CLI command tests
│       └── test_build_dataset.py
├── integration/                    # End-to-end tests
│   └── test_cli_integration.py
└── conftest.py                     # Test configuration
```

### Critical Validation Tests

The image mapping validation tests specifically target the issues that caused the refactor:

```python
# tests/unit/core/test_image_mapping_validation.py
def test_known_image_question_validation():
    """Test validation against known problematic image questions."""
    # Tests specific question IDs: 21, 22, 209, 226, 275, etc.
    # Ensures all 42 image questions are properly detected and mapped
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/core/                    # Core component tests
pytest tests/unit/core/test_image_*        # Image mapping tests only
pytest tests/integration/                  # Integration tests

# Run with coverage (required: 80%+)
pytest --cov=src --cov-report=term-missing

# Run specific critical tests
pytest tests/unit/core/test_image_mapping_validation.py -v
pytest tests/unit/core/test_data_builder_validation.py -v
```

## 🔧 Updated Development Workflow (Phase 1.8)

### For New Contributors

1. **Clone and Setup**:
```bash
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install
```

2. **Run Tests** (should all pass):
```bash
pytest  # All 169 tests should pass
```

3. **Try the Application**:
```bash
integran-setup --language en  # Setup with English preference
integran --stats              # View current status
```

### For Core Development

If you're working on the data pipeline or core components:

1. **Understand the Architecture**:
   - Review `src/core/data_builder.py` - main orchestrator
   - Check `src/core/image_processor.py` - image mapping logic
   - Study `src/core/answer_engine.py` - multilingual generation

2. **Work with Test Data**:
```bash
# The tests use mock data, but you can check real data:
ls data/extraction_checkpoint.json  # Source of truth
ls data/images/                     # Extracted images
```

3. **Build Complete Dataset** (requires API keys):
```bash
# Only if you have Gemini API configured
integran-build-dataset --status     # Check current status
# integran-build-dataset --force-rebuild  # Full rebuild (~$80 cost)
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass (169 tests)
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

## 📋 Phase 1.8 Summary for Developers

### What Changed in the Refactor

**Problem Solved**: Fixed critical image mapping issues where 25/42 image questions had broken image paths.

**Solution**: Complete architecture refactor with three new core components:
1. **ImageProcessor** - AI vision for accurate image descriptions and mapping
2. **AnswerEngine** - Multilingual answer generation in 5 languages
3. **DataBuilder** - Unified pipeline replacing scattered broken utilities

### Key Developer Benefits

✅ **Single Command**: `integran-build-dataset` replaces 5+ broken commands  
✅ **Comprehensive Tests**: 169 tests including critical image mapping validation  
✅ **Quality Assurance**: All 42 image questions now properly mapped and described  
✅ **Multilingual Support**: English, German, Turkish, Ukrainian, Arabic  
✅ **Enhanced RAG**: Official German government sources via Firecrawl  
✅ **Future-Ready**: Clean architecture for UI and feature development  

### For Different Developer Types

**End Users**: No changes needed - app works out of the box with pre-extracted data  
**Contributors**: Focus on tests and quality - all critical mapping issues resolved  
**Core Developers**: Use `integran-build-dataset` for complete pipeline (requires API keys)  
**UI Developers**: New multilingual data format ready for display in terminal UI  

**Last Updated**: January 9, 2025 - Phase 1.8-1.9.4 Complete