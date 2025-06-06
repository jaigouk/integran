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

The app uses SQLite to track progress:

- **failures**: Tracks incorrectly answered questions
- **sessions**: Records practice session data
- **progress**: Monitors overall improvement
- **categories**: Stores category-specific performance

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

### Project Structure

```
src/
├── core/
│   ├── database.py     # Database operations
│   ├── models.py       # SQLAlchemy models
│   └── settings.py     # Configuration management
├── utils/
│   └── pdf_extractor.py # PDF extraction utility
├── trainer.py          # Main application
├── extract_questions.py # PDF extraction CLI
└── setup.py           # Database setup CLI
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