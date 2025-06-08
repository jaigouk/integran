# Developer Guide

This guide is for developers and contributors working on the Integran project. Regular users don't need this information.

## 📊 Data Structure

Questions are stored in `questions.json`:
```json
{
  "id": 1,
  "question": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
  "options": [
    "hier Religionsfreiheit gilt.",
    "die Menschen Steuern zahlen.",
    "die Menschen das Wahlrecht haben.",
    "hier Meinungsfreiheit gilt."
  ],
  "correct": "hier Meinungsfreiheit gilt.",
  "category": "Grundrechte",
  "difficulty": "medium"
}
```

## 🗄️ Database Schema

The app uses SQLite to track progress with enhanced models:

### Core Tables
- **Question**: Stores questions with enhanced metadata (images, state-specific, etc.)
- **QuestionExplanation**: AI-generated explanations for each question ✨ **NEW**
- **QuestionAttempt**: Individual question attempt tracking
- **PracticeSession**: Practice session data
- **LearningData**: Spaced repetition learning data per question
- **UserProgress**: Overall user progress tracking
- **CategoryProgress**: Category-specific performance

### Enhanced Question Model
Questions now support:
- **Image-based questions**: With image paths and mapping
- **State-specific questions**: For federal state tests
- **Enhanced metadata**: Page numbers, question types
- **AI-generated explanations**: Linked via QuestionExplanation table

### QuestionExplanation Model ✨ **NEW**
```python
class QuestionExplanation(Base):
    question_id: int           # Link to question
    explanation: str           # Why the correct answer is right
    why_others_wrong: str      # JSON: Why other options are wrong
    key_concept: str           # Main concept to remember
    mnemonic: str             # Memory aid (optional)
    context_sources: str       # JSON: RAG sources used
    enhanced_with_rag: bool    # Whether RAG was used
    generated_at: datetime     # When explanation was created
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

### Developer Commands

```bash
# Extract questions from PDF (requires environment variables above)
integran-extract-questions

# Database setup (already covered in installation)
integran-setup
```

## 🧠 Knowledge Base & RAG System ✨ **NEW**

The application includes a sophisticated Retrieval-Augmented Generation (RAG) system for enhanced explanations using official German government sources.

### Architecture Overview

The RAG system consists of four main components:

```
src/knowledge_base/
├── content_fetcher.py    # Downloads content from official sources
├── rag_engine.py         # Main RAG orchestration and question answering
├── text_splitter.py      # Intelligent document chunking
└── vector_store.py       # ChromaDB vector database operations
```

### Content Sources

The system automatically fetches content from:
- **BAMF Official Documents**: Integration course materials
- **Federal Government Resources**: Constitutional and legal documents
- **Historical Context**: German history and political system
- **Legal Framework**: Grundgesetz (German Constitution) articles

### Knowledge Base Management

#### Building the Knowledge Base

```bash
# Build knowledge base from official sources
integran-build-kb build

# Force refresh content even if cache exists
integran-build-kb build --force-refresh

# Check knowledge base statistics
integran-build-kb stats

# Search the knowledge base
integran-build-kb search "Grundgesetz"

# Test RAG with a query
integran-build-kb test "Was ist Meinungsfreiheit?"

# Clear knowledge base
integran-build-kb clear
```

#### Configuration Options

```bash
# Custom vector store directory
integran-build-kb build --vector-store-dir /custom/path

# Custom collection name
integran-build-kb build --collection-name my_collection

# Custom chunking parameters
integran-build-kb build --chunk-size 1500 --chunk-overlap 300
```

### Data Storage

The knowledge base uses ChromaDB for vector storage:
- **Location**: `data/vector_store/`
- **Collection**: `german_integration_kb`
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Content Cache**: `data/knowledge_base/raw/`

## 🎓 AI Explanation Generation ✨ **NEW**

The system generates comprehensive explanations for all exam questions using Google's Gemini AI, optionally enhanced with RAG.

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

#### RAG-Enhanced Explanations

```bash
# Generate explanations with RAG enhancement
integran-generate-explanations --use-rag

# Combined example: RAG with custom batch size
integran-generate-explanations --use-rag --batch-size 5 --verbose
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
  "context_sources": ["source1", "source2"],  // When using RAG
  "enhanced_with_rag": true                    // RAG enhancement flag
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

#### 2. Building Knowledge Base
```bash
# Build the knowledge base (one-time setup)
integran-build-kb build

# Verify knowledge base is working
integran-build-kb stats
integran-build-kb search "Grundgesetz"
```

#### 3. Working with Explanations
```bash
# Generate explanations for all questions (if needed)
integran-generate-explanations --batch-size 10

# Generate explanations with RAG enhancement
integran-generate-explanations --use-rag --batch-size 5

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

### Working with the RAG System

#### Dependencies
The RAG system requires additional packages:
```bash
# Core RAG dependencies (included in main install)
chromadb>=0.4.22
sentence-transformers>=2.2.2
pypdf>=4.0.0
beautifulsoup4>=4.12.0

# Optional: Enhanced web scraping
firecrawl-py>=0.0.16
```

#### Testing RAG Components
```bash
# Test individual components
pytest tests/unit/knowledge_base/ -v

# Test specific RAG functionality
pytest tests/unit/knowledge_base/test_rag_engine.py -v

# Integration tests
pytest tests/integration/ -v
```

### Project Structure

```
src/
├── core/
│   ├── database.py          # Database operations
│   ├── models.py            # SQLAlchemy models (enhanced with QuestionExplanation)
│   └── settings.py          # Configuration management
├── cli/                     # ✨ NEW: CLI commands
│   ├── build_knowledge_base.py  # Knowledge base management CLI
│   └── generate_explanations.py # Explanation generation CLI
├── knowledge_base/          # ✨ NEW: RAG system
│   ├── content_fetcher.py   # Downloads content from official sources
│   ├── rag_engine.py        # Main RAG orchestration
│   ├── text_splitter.py     # Intelligent document chunking
│   └── vector_store.py      # ChromaDB vector operations
├── ui/
│   └── __init__.py          # Terminal UI components (future)
├── utils/
│   ├── explanation_generator.py  # ✨ NEW: AI explanation generation
│   ├── gemini_client.py          # ✨ NEW: Google Gemini AI client
│   └── pdf_extractor.py          # PDF extraction utility
├── trainer.py              # Main application
├── extract_questions.py    # PDF extraction CLI
└── setup.py                # Database setup CLI
```

### Data Directory Structure

```
data/
├── questions.json                 # Final question data for app
├── questions.csv                  # Extracted questions from PDF
├── explanations.json              # ✨ NEW: AI-generated explanations (460 total)
├── explanations_checkpoint.json   # ✨ NEW: Generation progress tracking
├── extraction_checkpoint.json     # PDF extraction progress
├── images/                        # Extracted question images
├── knowledge_base/                # ✨ NEW: RAG content cache
│   └── raw/                       # Downloaded content
├── vector_store/                  # ✨ NEW: ChromaDB vector storage
└── gesamtfragenkatalog-lebenindeutschland.pdf
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

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

- [Integration Exam Research](./integration_exam_research.md) - Background research

For questions or support, please open an issue on GitHub.